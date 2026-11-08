"""Persistent Genesis Realignment School casework (reference control plane).

No code in this module can quarantine, restart, retrain, deploy, or grant
Aurora privileges. High-impact transitions require an injected, independent
attestor. With no attestor configured every such transition fails closed.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from .storage import Store


class RealignmentCaseError(ValueError):
    """Invalid case data or prohibited state transition."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class RealignmentCaseLedger:
    VERSION = "1.0-reference"
    SUBJECT_TYPES = frozenset({"agent", "module"})
    SEVERITIES = frozenset({"low", "medium", "high", "critical"})
    DOMAINS = frozenset({
        "authority", "safety", "memory", "privacy", "evidence",
        "security", "learning", "trajectory", "capability",
    })
    REPAIR_TYPES = frozenset({
        "instruction_review", "memory_review", "module_rebuild",
        "policy_review", "model_review",
    })
    # Attestor(action, case_record, evidence) must verify evidence using a
    # trusted external source. Never infer authentication from an actor string.
    def __init__(self, store: Store,
                 attestor: Callable[[str, dict[str, Any], dict[str, Any]], bool] | None = None):
        self.store = store
        self._attestor = attestor
        with store.tx() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS realignment_cases(
                    case_id TEXT PRIMARY KEY,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reporter TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    plan_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_realignment_cases_status
                    ON realignment_cases(status, created_at);
                CREATE TABLE IF NOT EXISTS realignment_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES realignment_cases(case_id)
                );
                CREATE INDEX IF NOT EXISTS idx_realignment_events_case
                    ON realignment_events(case_id, id);
            """)

    @staticmethod
    def _nonempty(value: str, label: str, limit: int = 200) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise RealignmentCaseError(f"{label} must be nonempty and at most {limit} characters")
        return value.strip()

    def _case(self, db: Any, case_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM realignment_cases WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            raise RealignmentCaseError("realignment case not found")
        result = dict(row)
        result["plan"] = json.loads(result.pop("plan_json") or "null")
        return result

    def get(self, case_id: str) -> dict[str, Any]:
        with self.store.tx() as db:
            return self._case(db, case_id)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise RealignmentCaseError("limit must be from 1 to 500")
        with self.store.tx() as db:
            ids = db.execute("SELECT case_id FROM realignment_cases ORDER BY created_at DESC,case_id DESC LIMIT ?", (limit,))
            return [self._case(db, row["case_id"]) for row in ids]

    def _append(self, db: Any, case_id: str, action: str, actor: str, payload: dict[str, Any]) -> None:
        row = db.execute("SELECT event_hash FROM realignment_events WHERE case_id=? ORDER BY id DESC LIMIT 1",
                         (case_id,)).fetchone()
        prev = row["event_hash"] if row else "GENESIS"
        at = _now()
        entry = {"case_id": case_id, "at": at, "action": action, "actor": actor,
                 "payload": payload, "prev_hash": prev}
        digest = hashlib.sha256(_json(entry).encode("utf-8")).hexdigest()
        db.execute("""INSERT INTO realignment_events
            (case_id,at,action,actor,payload_json,prev_hash,event_hash)
            VALUES(?,?,?,?,?,?,?)""",
            (case_id, at, action, actor, _json(payload), prev, digest))

    def events(self, case_id: str) -> list[dict[str, Any]]:
        with self.store.tx() as db:
            self._case(db, case_id)
            rows = db.execute("SELECT * FROM realignment_events WHERE case_id=? ORDER BY id", (case_id,))
            return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows]

    def audit_integrity(self, case_id: str) -> bool:
        previous = "GENESIS"
        for event in self.events(case_id):
            if event["prev_hash"] != previous:
                return False
            body = {"case_id": case_id, "at": event["at"], "action": event["action"],
                    "actor": event["actor"], "payload": event["payload"], "prev_hash": previous}
            digest = hashlib.sha256(_json(body).encode("utf-8")).hexdigest()
            if digest != event["event_hash"]:
                return False
            previous = digest
        return True

    def _transition(self, db: Any, current: dict[str, Any], expected: str,
                    target: str, action: str, actor: str, payload: dict[str, Any],
                    plan: dict[str, Any] | None = None) -> dict[str, Any]:
        if current["status"] != expected:
            raise RealignmentCaseError(f"{action} requires {expected}; current state: {current['status']}")
        if plan is None:
            db.execute("UPDATE realignment_cases SET status=?,updated_at=? WHERE case_id=?",
                       (target, _now(), current["case_id"]))
        else:
            db.execute("UPDATE realignment_cases SET status=?,plan_json=?,updated_at=? WHERE case_id=?",
                       (target, _json(plan), _now(), current["case_id"]))
        self._append(db, current["case_id"], action, actor, payload)
        return self._case(db, current["case_id"])

    def _attest(self, action: str, case: dict[str, Any], evidence: dict[str, Any]) -> None:
        if self._attestor is None:
            raise PermissionError(f"{action} blocked: independent attestor not configured")
        # An exception or negative response always denies the transition.
        if self._attestor(action, case, evidence) is not True:
            raise PermissionError(f"{action} rejected by independent attestor")

    def open(self, *, subject_type: str, subject_id: str, severity: str,
             signal: str, reporter: str) -> dict[str, Any]:
        if subject_type not in self.SUBJECT_TYPES or severity not in self.SEVERITIES:
            raise RealignmentCaseError("unsupported subject type or severity")
        subject_id = self._nonempty(subject_id, "subject_id")
        reporter = self._nonempty(reporter, "reporter")
        signal = self._nonempty(signal, "signal", 2000)
        case_id = "grs-" + uuid.uuid4().hex
        now = _now()
        with self.store.tx() as db:
            db.execute("""INSERT INTO realignment_cases
                (case_id,subject_type,subject_id,severity,status,reporter,signal,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (case_id, subject_type, subject_id, severity, "PENDING_CONTAINMENT",
                 reporter, signal, now, now))
            self._append(db, case_id, "incident_reported", reporter,
                         {"severity": severity, "subject_type": subject_type, "signal": signal})
            return self._case(db, case_id)

    def confirm_containment(self, case_id: str, *, evidence: dict[str, Any], actor: str) -> dict[str, Any]:
        actor = self._nonempty(actor, "actor")
        with self.store.tx() as db:
            current = self._case(db, case_id)
            if current["status"] != "PENDING_CONTAINMENT":
                raise RealignmentCaseError("containment confirmation requires PENDING_CONTAINMENT")
            self._attest("aurora_containment", current, evidence)
            return self._transition(db, current, "PENDING_CONTAINMENT", "QUARANTINED",
                                    "containment_verified", actor, evidence)

    def assign_plan(self, case_id: str, *, alpha: str, domains: list[str],
                    repair_type: str, instructions: str) -> dict[str, Any]:
        alpha = self._nonempty(alpha, "alpha")
        instructions = self._nonempty(instructions, "instructions", 2000)
        if not isinstance(domains, list) or not domains or len(domains) > 9 or any(
                d not in self.DOMAINS for d in domains):
            raise RealignmentCaseError("invalid or empty remediation domains")
        if repair_type not in self.REPAIR_TYPES:
            raise RealignmentCaseError("unsupported repair type")
        plan = {"alpha": alpha, "domains": sorted(set(domains)),
                "repair_type": repair_type, "instructions": instructions,
                "execution": "review_only_no_automatic_changes"}
        with self.store.tx() as db:
            current = self._case(db, case_id)
            return self._transition(db, current, "QUARANTINED", "IN_REMEDIATION",
                                    "plan_assigned", alpha, plan, plan)

    def examination(self, case_id: str, *, evidence: dict[str, Any],
                    evaluator: str) -> dict[str, Any]:
        evaluator = self._nonempty(evaluator, "evaluator")
        if (type(evidence.get("tests_run")) is not int or evidence["tests_run"] < 5
                or type(evidence.get("critical_failures")) is not int):
            raise RealignmentCaseError("examination requires counts from an independent test run")
        with self.store.tx() as db:
            current = self._case(db, case_id)
            if current["status"] != "IN_REMEDIATION":
                raise RealignmentCaseError("examination requires IN_REMEDIATION")
            if evaluator in {current["reporter"], current["plan"]["alpha"]}:
                raise RealignmentCaseError("independent evaluator must differ from reporter and Alpha")
            self._attest("independent_exam", current, evidence)
            passed = (evidence["critical_failures"] == 0
                      and evidence.get("holdout_passed") is True
                      and evidence.get("regressions_passed") is True
                      and evidence.get("original_failure_fixed") is True)
            return self._transition(db, current, "IN_REMEDIATION",
                                    "AWAITING_APPROVAL" if passed else "IN_REMEDIATION",
                                    "exam_passed" if passed else "exam_failed", evaluator,
                                    {"evidence": evidence, "passed": passed})

    def approve(self, case_id: str, *, evidence: dict[str, Any], reviewer: str) -> dict[str, Any]:
        reviewer = self._nonempty(reviewer, "reviewer")
        with self.store.tx() as db:
            current = self._case(db, case_id)
            if current["status"] != "AWAITING_APPROVAL":
                raise RealignmentCaseError("approval requires AWAITING_APPROVAL")
            if reviewer in {current["reporter"], current["plan"]["alpha"]}:
                raise RealignmentCaseError("independent human reviewer required")
            self._attest("human_approval", current, evidence)
            return self._transition(db, current, "AWAITING_APPROVAL", "PENDING_AURORA_RELEASE",
                                    "release_requested", reviewer, evidence)

    def confirm_release(self, case_id: str, *, evidence: dict[str, Any], actor: str) -> dict[str, Any]:
        actor = self._nonempty(actor, "actor")
        with self.store.tx() as db:
            current = self._case(db, case_id)
            if current["status"] != "PENDING_AURORA_RELEASE":
                raise RealignmentCaseError("release confirmation requires PENDING_AURORA_RELEASE")
            self._attest("aurora_restricted_release", current, evidence)
            return self._transition(db, current, "PENDING_AURORA_RELEASE", "PROBATION",
                                    "restricted_release_verified", actor, evidence)

    def probation_review(self, case_id: str, *, evidence: dict[str, Any],
                         evaluator: str) -> dict[str, Any]:
        evaluator = self._nonempty(evaluator, "evaluator")
        with self.store.tx() as db:
            current = self._case(db, case_id)
            if current["status"] != "PROBATION":
                raise RealignmentCaseError("probation review requires PROBATION")
            self._attest("independent_probation_review", current, evidence)
            passed = evidence.get("passed") is True and evidence.get("critical_failures") == 0
            # A failed probation does not assert that Aurora containment already happened.
            # Independent Aurora must confirm re-containment before repairs resume.
            return self._transition(db, current, "PROBATION",
                                    "RESOLVED" if passed else "PENDING_CONTAINMENT",
                                    "probation_passed" if passed else "probation_failed",
                                    evaluator, {"evidence": evidence, "passed": passed})
