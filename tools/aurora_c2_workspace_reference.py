"""C2 reversible local execution: isolated *reference* data workspace.

C2 is a legacy Aurora execution-policy tier, NOT a Genesis C/B/A standard.
This module executes only bounded SQLite workspace mutations; it cannot run
commands, change host files chosen by the Model, access networks or mutate
AWS resources. TestEngineSigner is deliberately a *test* issuer, not protected
private Aurora authority. Never connect this module to production Motor
without independent Engine authorization, isolation and qualification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import uuid

_KEY = re.compile(r"^[a-z][a-z0-9_-]{0,47}$")
_SCOPE = re.compile(r"^sandbox:[a-z][a-z0-9_-]{0,47}$")
_FIELDS = frozenset({
    "grant_id", "request_id", "subject", "session", "epoch",
    "scope", "key", "action", "digest", "target_request",
    "issued_at", "expires_at", "signature",
})


class C2Denied(ValueError):
    """The reference worker did not authorize or commit a mutation."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _date(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("timezone required")
        return dt.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError) as exc:
        raise C2Denied("invalid grant timestamp") from exc


def _canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_shape(*, scope: str, key: str, epoch: int, subject: str, session: str) -> None:
    if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
        raise C2Denied("scope is not an approved sandbox namespace")
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise C2Denied("invalid sandbox resource key")
    if type(epoch) is not int or epoch < 1:
        raise C2Denied("session epoch must be positive")
    if not isinstance(subject, str) or not 1 <= len(subject) <= 120:
        raise C2Denied("invalid subject")
    if not isinstance(session, str) or not 1 <= len(session) <= 120:
        raise C2Denied("invalid session")


class TestEngineSigner:
    """Offline demonstration only. NOT an attested Aurora signing service."""

    def __init__(self, key: bytes | None = None):
        self._key = key or secrets.token_bytes(32)
        if len(self._key) < 32:
            raise ValueError("test signing key must have at least 32 bytes")

    @property
    def verification_key(self) -> bytes:
        return self._key

    def issue(
        self, *, subject: str, session: str, epoch: int, scope: str,
        key: str, action: str, payload: str,
        target_request: str = "", lifetime_seconds: int = 60,
    ) -> dict:
        _validate_shape(scope=scope, key=key, epoch=epoch, subject=subject, session=session)
        if action not in {"write", "rollback"}:
            raise C2Denied("only reversible C2 actions exist")
        if not isinstance(payload, str):
            raise C2Denied("invalid payload")
        if action == "write":
            if target_request or len(payload.encode("utf-8")) > 4096:
                raise C2Denied("invalid local write payload")
        elif not target_request or payload != target_request:
            raise C2Denied("rollback must bind exact original request")
        if type(lifetime_seconds) is not int or not 1 <= lifetime_seconds <= 300:
            raise C2Denied("grant must expire within five minutes")
        now = _now()
        data = {
            "grant_id": uuid.uuid4().hex,
            "request_id": uuid.uuid4().hex,
            "subject": subject, "session": session, "epoch": epoch,
            "scope": scope, "key": key, "action": action,
            "digest": _digest(payload), "target_request": target_request,
            "issued_at": _iso(now),
            "expires_at": _iso(now + timedelta(seconds=lifetime_seconds)),
        }
        return {**data, "signature": hmac.new(self._key, _canonical(data), hashlib.sha256).hexdigest()}


class C2Sandbox:
    """A restrictive SQLite transaction journal, no generic Motor dispatcher.

    The database path is fixed by the host operator, never part of an action.
    One receipt is committed for each unique, signature-bound request.
    Rollbacks refuse to overwrite a subsequently modified resource.
    """

    def __init__(self, path: str | Path, verification_key: bytes):
        if not isinstance(verification_key, bytes) or len(verification_key) < 32:
            raise ValueError("invalid verifier key")
        self._key = verification_key
        self.path = Path(path)
        if self.path.is_symlink():
            raise C2Denied("sandbox database cannot be a symlink")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        if not stat.S_ISREG(self.path.stat().st_mode):
            raise C2Denied("sandbox database must be a regular file")
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS c2_resources (
                    scope TEXT NOT NULL, resource_key TEXT NOT NULL,
                    value TEXT NOT NULL, version INTEGER NOT NULL,
                    PRIMARY KEY(scope,resource_key)
                );
                CREATE TABLE IF NOT EXISTS c2_receipts (
                    request_id TEXT PRIMARY KEY, grant_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL, session TEXT NOT NULL,
                    epoch INTEGER NOT NULL, scope TEXT NOT NULL,
                    resource_key TEXT NOT NULL, action TEXT NOT NULL,
                    target_request TEXT, previous_value TEXT,
                    previous_version INTEGER, new_version INTEGER,
                    reverted INTEGER NOT NULL DEFAULT 0
                );
            """)

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=8)
        db.execute("PRAGMA busy_timeout=8000")
        return db

    def _verify(self, grant: dict, payload: str, now: datetime) -> None:
        if not isinstance(grant, dict) or set(grant) != _FIELDS:
            raise C2Denied("invalid signed grant schema")
        body = {k: v for k, v in grant.items() if k != "signature"}
        try:
            signature = hmac.new(self._key, _canonical(body), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, grant["signature"]):
                raise C2Denied("grant signature invalid")
        except (TypeError, ValueError) as exc:
            raise C2Denied("invalid grant encoding") from exc
        _validate_shape(
            scope=grant["scope"], key=grant["key"], epoch=grant["epoch"],
            subject=grant["subject"], session=grant["session"],
        )
        if grant["action"] not in {"write", "rollback"}:
            raise C2Denied("unsupported C2 action")
        if not isinstance(payload, str) or grant["digest"] != _digest(payload):
            raise C2Denied("signed payload does not match")
        if grant["action"] == "write":
            if grant["target_request"] or len(payload.encode("utf-8")) > 4096:
                raise C2Denied("invalid write bounds")
        elif not grant["target_request"] or payload != grant["target_request"]:
            raise C2Denied("rollback target mismatch")
        if not all(isinstance(grant[k], str) and len(grant[k]) == 32
                   for k in ("request_id", "grant_id")):
            raise C2Denied("invalid grant identifiers")
        issued, expiry = _date(grant["issued_at"]), _date(grant["expires_at"])
        if issued > now + timedelta(seconds=5) or expiry <= now or expiry <= issued:
            raise C2Denied("expired or future-dated grant")
        if expiry - issued > timedelta(seconds=300):
            raise C2Denied("grant lifetime too long")

    def execute(self, grant: dict, payload: str) -> dict:
        """Executes a bounded, local, undoable mutation; never invokes a tool."""
        self._verify(grant, payload, _now())
        scope, key = grant["scope"], grant["key"]
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM c2_receipts WHERE request_id=? OR grant_id=?",
                          (grant["request_id"], grant["grant_id"])).fetchone():
                raise C2Denied("replay of signed request or grant")
            existing = db.execute(
                "SELECT value,version FROM c2_resources WHERE scope=? AND resource_key=?",
                (scope, key),
            ).fetchone()
            if grant["action"] == "write":
                if existing is None:
                    count = db.execute("SELECT COUNT(*) FROM c2_resources WHERE scope=?", (scope,)).fetchone()[0]
                    if count >= 100:
                        raise C2Denied("scope quota of 100 keys reached")
                before, prior_version = existing if existing else (None, None)
                next_version = prior_version + 1 if prior_version is not None else 1
                db.execute(
                    "INSERT INTO c2_resources(scope,resource_key,value,version) VALUES(?,?,?,?) "
                    "ON CONFLICT(scope,resource_key) DO UPDATE SET value=excluded.value,version=excluded.version",
                    (scope, key, payload, next_version),
                )
                target = None
            else:
                target = db.execute(
                    "SELECT subject,session,epoch,scope,resource_key,previous_value,previous_version,new_version,reverted "
                    "FROM c2_receipts WHERE request_id=? AND action='write'",
                    (grant["target_request"],),
                ).fetchone()
                if not target or target[8]:
                    raise C2Denied("unknown or already reverted write")
                if target[:5] != (grant["subject"], grant["session"], grant["epoch"], scope, key):
                    raise C2Denied("rollback scope/session binding mismatch")
                if existing is None or existing[1] != target[7]:
                    raise C2Denied("rollback conflict: resource changed since original write")
                before, prior_version = existing
                if target[6] is None:
                    db.execute("DELETE FROM c2_resources WHERE scope=? AND resource_key=?", (scope, key))
                    next_version = None
                else:
                    next_version = existing[1] + 1
                    db.execute(
                        "UPDATE c2_resources SET value=?,version=? WHERE scope=? AND resource_key=?",
                        (target[5], next_version, scope, key),
                    )
                db.execute("UPDATE c2_receipts SET reverted=1 WHERE request_id=?", (grant["target_request"],))
            db.execute(
                "INSERT INTO c2_receipts(request_id,grant_id,subject,session,epoch,scope,"
                "resource_key,action,target_request,previous_value,previous_version,new_version)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (grant["request_id"], grant["grant_id"], grant["subject"], grant["session"],
                 grant["epoch"], scope, key, grant["action"], grant["target_request"] or None,
                 before, prior_version, next_version),
            )
        return {
            "request_id": grant["request_id"], "status": "COMMITTED",
            "action": grant["action"], "scope": scope,
            "key": key, "version": next_version, "reversible": grant["action"] == "write",
            "execution_tier": "C2", "production_engine_qualified": False,
        }

    def inspect_test_resource(self, scope: str, key: str) -> tuple[str, int] | None:
        """Local test-only inspection; not an authenticated Kyro endpoint."""
        if not _SCOPE.fullmatch(scope) or not _KEY.fullmatch(key):
            raise C2Denied("invalid local test scope")
        with self._db() as db:
            return db.execute(
                "SELECT value,version FROM c2_resources WHERE scope=? AND resource_key=?",
                (scope, key),
            ).fetchone()
