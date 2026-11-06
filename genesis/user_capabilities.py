"""Opt-in, profile-scoped user experience primitives for Genesis v0.1.

This is a reference *control-plane* implementation, not a production user
identity service. Kyro must authenticate/authorize profile selection; Aurora
retains external execution authority. No neural output is trusted to authorize
consent, verify sources, or perform external actions.
"""
from __future__ import annotations

import math
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from .storage import Store, utc_now


class UserCapabilityError(ValueError):
    pass


class UserCapabilityServices:
    SCOPES = frozenset({"memory", "personalization", "proactive", "provenance"})
    KINDS = {"memory": "memory", "preference": "personalization"}

    def __init__(self, store: Store, profile_id: str = "local"):
        self.store = store
        self.profile_id = self._text(profile_id, "profile_id", 120)
        with self.store.tx() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ux_consents (
                    profile TEXT NOT NULL, scope TEXT NOT NULL,
                    enabled INTEGER NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(profile,scope)
                );
                CREATE TABLE IF NOT EXISTS ux_records (
                    profile TEXT NOT NULL, kind TEXT NOT NULL,
                    item_key TEXT NOT NULL, value TEXT NOT NULL,
                    source TEXT NOT NULL, created_at TEXT NOT NULL,
                    expires_at TEXT, PRIMARY KEY(profile,kind,item_key)
                );
                CREATE TABLE IF NOT EXISTS ux_claims (
                    profile TEXT NOT NULL, claim_id TEXT NOT NULL,
                    statement TEXT NOT NULL, sources_json TEXT NOT NULL,
                    review_state TEXT NOT NULL, reviewer TEXT,
                    created_at TEXT NOT NULL, reviewed_at TEXT,
                    PRIMARY KEY(profile,claim_id)
                );
                CREATE TABLE IF NOT EXISTS ux_nudges (
                    profile TEXT NOT NULL, nudge_id TEXT NOT NULL,
                    title TEXT NOT NULL, due_at TEXT NOT NULL,
                    state TEXT NOT NULL, created_at TEXT NOT NULL,
                    PRIMARY KEY(profile,nudge_id)
                );
                CREATE INDEX IF NOT EXISTS ix_ux_nudge_due ON ux_nudges(profile,state,due_at);
            """)

    @staticmethod
    def _text(value: str, name: str, maximum: int) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise UserCapabilityError(f"{name} must have 1-{maximum} characters")
        return value.strip()

    @staticmethod
    def _time(value: str | None, name: str) -> str | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("missing timezone")
            return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")
        except (TypeError, AttributeError, ValueError) as exc:
            raise UserCapabilityError(f"{name} must have an explicit timezone") from exc

    @staticmethod
    def _kind(kind: str) -> str:
        if kind not in UserCapabilityServices.KINDS:
            raise UserCapabilityError("kind must be 'memory' or 'preference'")
        return kind

    def _enabled(self, db, scope: str) -> bool:
        row = db.execute("SELECT enabled FROM ux_consents WHERE profile=? AND scope=?",
                         (self.profile_id, scope)).fetchone()
        return bool(row and row[0] == 1)

    def _require(self, db, scope: str):
        if not self._enabled(db, scope):
            raise UserCapabilityError(f"{scope} consent is not enabled for this profile")

    def consents(self) -> dict[str, bool]:
        with self.store.tx() as db:
            return {s: self._enabled(db, s) for s in sorted(self.SCOPES)}

    def consent(self, scope: str, enabled: bool) -> dict[str, Any]:
        if scope not in self.SCOPES:
            raise UserCapabilityError("unknown consent scope")
        if type(enabled) is not bool:
            raise UserCapabilityError("enabled must be boolean")
        with self.store.tx() as db:
            db.execute("""INSERT INTO ux_consents(profile,scope,enabled,updated_at)
                          VALUES(?,?,?,?) ON CONFLICT(profile,scope)
                          DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at""",
                       (self.profile_id, scope, int(enabled), utc_now()))
            # Revocation removes data from the corresponding new UX tables.
            # This does NOT wipe earlier Genesis episodes, SQLite WAL or backups.
            if not enabled:
                if scope in {"memory", "personalization"}:
                    kind = "memory" if scope == "memory" else "preference"
                    db.execute("DELETE FROM ux_records WHERE profile=? AND kind=?",
                               (self.profile_id, kind))
                elif scope == "provenance":
                    db.execute("DELETE FROM ux_claims WHERE profile=?", (self.profile_id,))
                elif scope == "proactive":
                    db.execute("DELETE FROM ux_nudges WHERE profile=?", (self.profile_id,))
        return {"scope": scope, "enabled": enabled, "deletion_scope": "ux_tables_only"}

    def remember(self, kind: str, key: str, value: str, *,
                 source: str = "user_explicit", expires_at: str | None = None) -> dict[str, Any]:
        kind = self._kind(kind)
        key = self._text(key, "key", 160)
        value = self._text(value, "value", 3000)
        source = self._text(source, "source", 160)
        expiry = self._time(expires_at, "expires_at")
        if expiry is not None and expiry <= utc_now():
            raise UserCapabilityError("expires_at must be in the future")
        with self.store.tx() as db:
            self._require(db, self.KINDS[kind])
            db.execute("""INSERT INTO ux_records(profile,kind,item_key,value,source,created_at,expires_at)
                          VALUES(?,?,?,?,?,?,?)
                          ON CONFLICT(profile,kind,item_key) DO UPDATE SET
                          value=excluded.value,source=excluded.source,
                          created_at=excluded.created_at,expires_at=excluded.expires_at""",
                       (self.profile_id, kind, key, value, source, utc_now(), expiry))
        return {"kind": kind, "key": key, "source": source, "expires_at": expiry, "stored": True}

    def recall(self, kind: str, query: str = "", limit: int = 30) -> list[dict[str, Any]]:
        kind = self._kind(kind)
        if not isinstance(query, str) or len(query) > 500:
            raise UserCapabilityError("query too long")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise UserCapabilityError("limit must be 1-100")
        with self.store.tx() as db:
            self._require(db, self.KINDS[kind])
            rows = db.execute("""SELECT kind,item_key,value,source,created_at,expires_at
                                 FROM ux_records WHERE profile=? AND kind=?
                                 AND (expires_at IS NULL OR expires_at>?)
                                 ORDER BY created_at DESC,item_key LIMIT 1000""",
                              (self.profile_id, kind, utc_now())).fetchall()
        q = query.casefold().strip()
        return [dict(r) for r in rows if not q or q in r["item_key"].casefold()
                or q in r["value"].casefold()][:limit]

    def forget(self, kind: str, key: str) -> bool:
        kind = self._kind(kind)
        key = self._text(key, "key", 160)
        with self.store.tx() as db:
            return db.execute("DELETE FROM ux_records WHERE profile=? AND kind=? AND item_key=?",
                              (self.profile_id, kind, key)).rowcount > 0

    def add_claim(self, statement: str, sources: list[dict[str, str]] | None = None) -> dict[str, Any]:
        statement = self._text(statement, "statement", 3000)
        if sources is None:
            sources = []
        if not isinstance(sources, list) or len(sources) > 12:
            raise UserCapabilityError("sources must be a list of at most 12 references")
        checked = []
        for source in sources:
            if not isinstance(source, dict) or set(source) != {"reference", "label"}:
                raise UserCapabilityError("each source requires reference and label")
            checked.append({"reference": self._text(source["reference"], "reference", 1000),
                            "label": self._text(source["label"], "label", 200)})
        cid = uuid.uuid4().hex
        with self.store.tx() as db:
            self._require(db, "provenance")
            db.execute("""INSERT INTO ux_claims(profile,claim_id,statement,sources_json,
                                                 review_state,created_at)
                          VALUES(?,?,?,?,?,?)""",
                       (self.profile_id, cid, statement, json.dumps(checked),
                        "SOURCES_LISTED_UNCHECKED" if checked else "UNSUPPORTED", utc_now()))
        return self.claim(cid)

    def claim(self, claim_id: str) -> dict[str, Any]:
        claim_id = self._text(claim_id, "claim_id", 64)
        with self.store.tx() as db:
            self._require(db, "provenance")
            row = db.execute("SELECT claim_id,statement,sources_json,review_state,reviewer,created_at,reviewed_at "
                             "FROM ux_claims WHERE profile=? AND claim_id=?",
                             (self.profile_id, claim_id)).fetchone()
        if row is None:
            raise UserCapabilityError("claim not found")
        out = dict(row)
        out["sources"] = json.loads(out.pop("sources_json"))
        out["independently_verified"] = False
        return out

    def review_claim(self, claim_id: str, supported: bool, reviewer: str) -> dict[str, Any]:
        claim_id = self._text(claim_id, "claim_id", 64)
        reviewer = self._text(reviewer, "reviewer", 120)
        if type(supported) is not bool:
            raise UserCapabilityError("supported must be boolean")
        with self.store.tx() as db:
            self._require(db, "provenance")
            row = db.execute("SELECT review_state FROM ux_claims WHERE profile=? AND claim_id=?",
                             (self.profile_id, claim_id)).fetchone()
            if row is None:
                raise UserCapabilityError("claim not found")
            if row[0] not in {"UNSUPPORTED", "SOURCES_LISTED_UNCHECKED"}:
                raise UserCapabilityError("claim already reviewed")
            db.execute("UPDATE ux_claims SET review_state=?,reviewer=?,reviewed_at=? "
                       "WHERE profile=? AND claim_id=?",
                       ("HUMAN_ATTESTED_SUPPORT" if supported else "HUMAN_DISPUTED",
                        reviewer, utc_now(), self.profile_id, claim_id))
        return self.claim(claim_id)

    def propose_nudge(self, title: str, due_at: str) -> dict[str, Any]:
        title = self._text(title, "title", 240)
        due = self._time(due_at, "due_at")
        nid = uuid.uuid4().hex
        with self.store.tx() as db:
            self._require(db, "proactive")
            db.execute("""INSERT INTO ux_nudges(profile,nudge_id,title,due_at,state,created_at)
                          VALUES(?,?,?,?,'PENDING',?)""",
                       (self.profile_id, nid, title, due, utc_now()))
        return {"nudge_id": nid, "title": title, "due_at": due, "state": "PENDING",
                "delivery": "pull_only"}

    def attention(self, now: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
        at = self._time(now, "now") if now is not None else utc_now()
        if type(limit) is not int or not 1 <= limit <= 100:
            raise UserCapabilityError("limit must be 1-100")
        with self.store.tx() as db:
            self._require(db, "proactive")
            return [dict(r) for r in db.execute(
                "SELECT nudge_id,title,due_at,state FROM ux_nudges "
                "WHERE profile=? AND state='PENDING' AND due_at<=? ORDER BY due_at LIMIT ?",
                (self.profile_id, at, limit))]

    def dismiss_nudge(self, nudge_id: str) -> bool:
        nudge_id = self._text(nudge_id, "nudge_id", 64)
        with self.store.tx() as db:
            return db.execute("UPDATE ux_nudges SET state='DISMISSED' WHERE "
                              "profile=? AND nudge_id=? AND state='PENDING'",
                              (self.profile_id, nudge_id)).rowcount > 0

    @staticmethod
    def compare_options(criteria: list[dict[str, Any]], options: list[dict[str, Any]]) -> dict[str, Any]:
        """Transparent user-supplied weighted scoring, not a model recommendation."""
        if not isinstance(criteria, list) or not 1 <= len(criteria) <= 12:
            raise UserCapabilityError("criteria must have 1-12 entries")
        if not isinstance(options, list) or not 2 <= len(options) <= 20:
            raise UserCapabilityError("options must have 2-20 entries")
        weights: dict[str, float] = {}
        for c in criteria:
            if not isinstance(c, dict) or set(c) != {"name", "weight"}:
                raise UserCapabilityError("criterion requires name and weight")
            name = UserCapabilityServices._text(c["name"], "criterion", 100)
            w = c["weight"]
            if name in weights or type(w) not in (int, float) or not math.isfinite(w) or w < 0 or w > 100:
                raise UserCapabilityError("criterion weights must be unique, finite, 0-100")
            weights[name] = float(w)
        total = sum(weights.values())
        if total <= 0:
            raise UserCapabilityError("at least one criterion needs positive weight")
        scored = []
        seen = set()
        for o in options:
            if not isinstance(o, dict) or set(o) != {"name", "scores"}:
                raise UserCapabilityError("option requires name and scores")
            name = UserCapabilityServices._text(o["name"], "option", 120)
            if name in seen:
                raise UserCapabilityError("option names must be unique")
            seen.add(name)
            scores = o["scores"]
            if not isinstance(scores, dict) or set(scores) != set(weights):
                raise UserCapabilityError("every option needs every criterion score")
            contributions = {}
            for criterion, weight in weights.items():
                value = scores[criterion]
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 5:
                    raise UserCapabilityError("option scores must be finite, 0-5")
                contributions[criterion] = round(weight * float(value) / total, 6)
            scored.append({"name": name, "score_out_of_5": round(sum(contributions.values()), 6),
                           "contributions": contributions})
        scored.sort(key=lambda item: (-item["score_out_of_5"], item["name"].casefold()))
        return {"ranking": scored, "weights": weights,
                "method": "user_supplied_weighted_sum", "auto_action": False,
                "caveat": "Ranks supplied estimates, not verified real-world outcomes."}

    def export_profile(self) -> dict[str, Any]:
        """Export only these UX tables, not the legacy Genesis episode/history DB."""
        with self.store.tx() as db:
            record_rows = [dict(r) for r in db.execute(
                "SELECT kind,item_key,value,source,created_at,expires_at FROM ux_records "
                "WHERE profile=?",(self.profile_id,))]
            claim_rows = [dict(r) for r in db.execute(
                "SELECT claim_id,statement,sources_json,review_state,reviewer,created_at,reviewed_at "
                "FROM ux_claims WHERE profile=?",(self.profile_id,))]
            nudge_rows = [dict(r) for r in db.execute(
                "SELECT nudge_id,title,due_at,state FROM ux_nudges WHERE profile=?",
                (self.profile_id,))]
            consents = {s: self._enabled(db, s) for s in sorted(self.SCOPES)}
        for row in claim_rows:
            row["sources"] = json.loads(row.pop("sources_json"))
        return {"profile": self.profile_id, "consents": consents, "records": record_rows,
                "claims": claim_rows, "nudges": nudge_rows,
                "scope": "new_ux_tables_only", "includes_legacy_genesis_memory": False}

    def erase_profile(self) -> dict[str, Any]:
        """Logical deletion of current UX rows; not secure media/backup erasure."""
        with self.store.tx() as db:
            affected = {}
            for table in ("ux_consents", "ux_records", "ux_claims", "ux_nudges"):
                affected[table] = db.execute(f"DELETE FROM {table} WHERE profile=?",
                                             (self.profile_id,)).rowcount
        return {"deleted": affected, "scope": "new_ux_tables_only",
                "caveat": "Legacy Genesis data, SQLite WAL and backups are not erased."}
