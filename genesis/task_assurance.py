"""Evidence-backed task tracking for the public Genesis Model interface.

This module NEVER executes actions or grants Aurora authority. A task is not
completed simply because a model generated a plausible answer. Completion is
explicitly human-attested against predeclared acceptance criteria.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .storage import Store, utc_now


class TaskError(ValueError):
    pass


class TaskLedger:
    ACTIVE = {"DRAFT", "APPROVED", "WORKING", "REVIEW", "BLOCKED"}
    TERMINAL = {"COMPLETED_ATTESTED", "CANCELLED"}

    def __init__(self, store: Store):
        self.store = store
        with self.store.tx() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS assurance_tasks (
                    task_id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    criteria_json TEXT NOT NULL, status TEXT NOT NULL,
                    priority INTEGER NOT NULL, due_at TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_assurance_tasks_due
                    ON assurance_tasks(status, due_at);
                CREATE TABLE IF NOT EXISTS assurance_evidence (
                    evidence_id TEXT PRIMARY KEY, task_id TEXT NOT NULL,
                    criterion_index INTEGER NOT NULL, observation TEXT NOT NULL,
                    reference TEXT NOT NULL, source_type TEXT NOT NULL,
                    review_state TEXT NOT NULL DEFAULT 'PENDING',
                    reviewer TEXT, reviewed_at TEXT, created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES assurance_tasks(task_id)
                );
                CREATE INDEX IF NOT EXISTS idx_assurance_evidence_task
                    ON assurance_evidence(task_id, criterion_index);
                CREATE TABLE IF NOT EXISTS assurance_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    detail TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES assurance_tasks(task_id)
                );
            """)

    @staticmethod
    def _str(value: str, label: str, max_len: int) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > max_len:
            raise TaskError(f"{label} must contain 1-{max_len} characters")
        return value.strip()

    @staticmethod
    def _due(value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timezone missing")
            return parsed.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, AttributeError) as exc:
            raise TaskError("due_at must be an ISO-8601 timestamp with timezone") from exc

    @staticmethod
    def _event(db, task_id: str, kind: str, detail: str = "") -> None:
        db.execute("INSERT INTO assurance_events(task_id,event_type,detail,created_at) VALUES(?,?,?,?)",
                   (task_id, kind, detail, utc_now()))

    @staticmethod
    def _require(db, task_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM assurance_tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise TaskError("task not found")
        return dict(row)

    def create(self, title: str, criteria: list[str], priority: int = 50,
               due_at: str | None = None) -> dict[str, Any]:
        title = self._str(title, "title", 240)
        if not isinstance(criteria, list) or not 1 <= len(criteria) <= 20:
            raise TaskError("criteria must be a list of 1-20 conditions")
        criteria = [self._str(c, "criterion", 400) for c in criteria]
        if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 100:
            raise TaskError("priority must be between 0 and 100")
        due_at = self._due(due_at)
        task_id = uuid.uuid4().hex
        now = utc_now()
        with self.store.tx() as db:
            db.execute("INSERT INTO assurance_tasks VALUES(?,?,?,?,?,?,?,?)",
                       (task_id, title, json.dumps(criteria), "DRAFT", priority, due_at, now, now))
            self._event(db, task_id, "CREATED", "draft: no actions authorized")
        return self.get(task_id)

    def get(self, task_id: str) -> dict[str, Any]:
        with self.store.tx() as db:
            task = self._require(db, task_id)
            evidence = [dict(r) for r in db.execute(
                "SELECT * FROM assurance_evidence WHERE task_id=? ORDER BY created_at,evidence_id", (task_id,))]
        task["criteria"] = json.loads(task.pop("criteria_json"))
        task["evidence"] = evidence
        task["accepted_criteria"] = [i for i in range(len(task["criteria"]))
                                     if any(e["criterion_index"] == i and e["review_state"] == "ACCEPTED"
                                            for e in evidence)]
        task["completion_basis"] = ("human_attestation" if task["status"] == "COMPLETED_ATTESTED"
                                    else "not_complete")
        return task

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self.store.tx() as db:
            ids = [r[0] for r in db.execute(
                "SELECT task_id FROM assurance_tasks ORDER BY priority DESC,created_at DESC LIMIT ?", (limit,))]
        return [self.get(i) for i in ids]

    def due(self, now: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        at = self._due(now) if now is not None else datetime.now(timezone.utc).isoformat()
        limit = max(1, min(int(limit), 500))
        with self.store.tx() as db:
            ids = [r[0] for r in db.execute(
                "SELECT task_id FROM assurance_tasks WHERE due_at IS NOT NULL AND due_at<=? "
                "AND status NOT IN ('COMPLETED_ATTESTED','CANCELLED') "
                "ORDER BY due_at ASC LIMIT ?", (at, limit))]
        return [self.get(i) for i in ids]

    def transition(self, task_id: str, action: str) -> dict[str, Any]:
        states = {
            "approve": ({"DRAFT"}, "APPROVED"),
            "start": ({"APPROVED", "BLOCKED"}, "WORKING"),
            "review": ({"WORKING"}, "REVIEW"),
            "revise": ({"REVIEW"}, "WORKING"),
            "block": ({"APPROVED", "WORKING", "REVIEW"}, "BLOCKED"),
            "cancel": (self.ACTIVE, "CANCELLED"),
        }
        if action not in states:
            raise TaskError("unknown task transition")
        allowed, target = states[action]
        with self.store.tx() as db:
            task = self._require(db, task_id)
            if task["status"] not in allowed:
                raise TaskError(f"cannot {action} task in state {task['status']}")
            if action == "review" and not db.execute(
                "SELECT 1 FROM assurance_evidence WHERE task_id=? LIMIT 1", (task_id,)).fetchone():
                raise TaskError("cannot submit for review without evidence")
            db.execute("UPDATE assurance_tasks SET status=?,updated_at=? WHERE task_id=?",
                       (target, utc_now(), task_id))
            self._event(db, task_id, action.upper())
        return self.get(task_id)

    def submit_evidence(self, task_id: str, criterion_index: int, observation: str,
                        reference: str, source_type: str = "user") -> dict[str, Any]:
        observation = self._str(observation, "observation", 2000)
        reference = self._str(reference, "reference", 1000)
        if source_type not in {"user", "model", "tool", "aurora"}:
            raise TaskError("unrecognised source_type")
        eid = uuid.uuid4().hex
        with self.store.tx() as db:
            task = self._require(db, task_id)
            if task["status"] != "WORKING":
                raise TaskError("evidence accepted only while task is WORKING")
            criteria = json.loads(task["criteria_json"])
            if type(criterion_index) is not int or not 0 <= criterion_index < len(criteria):
                raise TaskError("invalid criterion_index")
            db.execute("INSERT INTO assurance_evidence(evidence_id,task_id,criterion_index,observation,reference,source_type,created_at) VALUES(?,?,?,?,?,?,?)",
                       (eid, task_id, criterion_index, observation, reference, source_type, utc_now()))
            self._event(db, task_id, "EVIDENCE_SUBMITTED", eid)
        return {"evidence_id": eid, "review_state": "PENDING", "task_id": task_id}

    def review_evidence(self, task_id: str, evidence_id: str, accepted: bool,
                        reviewer: str) -> dict[str, Any]:
        reviewer = self._str(reviewer, "reviewer", 120)
        if type(accepted) is not bool:
            raise TaskError("accepted must be boolean")
        with self.store.tx() as db:
            task = self._require(db, task_id)
            if task["status"] != "REVIEW":
                raise TaskError("task must be in REVIEW")
            row = db.execute("SELECT review_state FROM assurance_evidence WHERE evidence_id=? AND task_id=?",
                             (evidence_id, task_id)).fetchone()
            if row is None:
                raise TaskError("evidence not found")
            if row[0] != "PENDING":
                raise TaskError("evidence has already been reviewed")
            db.execute("UPDATE assurance_evidence SET review_state=?,reviewer=?,reviewed_at=? WHERE evidence_id=?",
                       ("ACCEPTED" if accepted else "REJECTED", reviewer, utc_now(), evidence_id))
            self._event(db, task_id, "EVIDENCE_REVIEWED", f"{evidence_id}:{'accepted' if accepted else 'rejected'}")
        return self.get(task_id)

    def complete(self, task_id: str, reviewer: str, human_confirmed: bool = False) -> dict[str, Any]:
        if human_confirmed is not True:
            raise TaskError("explicit human confirmation required for completion")
        reviewer = self._str(reviewer, "reviewer", 120)
        with self.store.tx() as db:
            task = self._require(db, task_id)
            if task["status"] != "REVIEW":
                raise TaskError("task must be in REVIEW")
            criteria = json.loads(task["criteria_json"])
            accepted = {r[0] for r in db.execute(
                "SELECT DISTINCT criterion_index FROM assurance_evidence "
                "WHERE task_id=? AND review_state='ACCEPTED'", (task_id,))}
            if accepted != set(range(len(criteria))):
                raise TaskError("each acceptance criterion needs human-accepted evidence")
            db.execute("UPDATE assurance_tasks SET status='COMPLETED_ATTESTED',updated_at=? WHERE task_id=?",
                       (utc_now(), task_id))
            self._event(db, task_id, "HUMAN_ATTESTED_COMPLETION", reviewer)
        return self.get(task_id)

    def events(self, task_id: str) -> list[dict[str, Any]]:
        with self.store.tx() as db:
            self._require(db, task_id)
            return [dict(r) for r in db.execute(
                "SELECT * FROM assurance_events WHERE task_id=? ORDER BY event_id", (task_id,))]
