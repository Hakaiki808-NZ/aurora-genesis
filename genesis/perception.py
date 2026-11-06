"""Structured perception and evidence-preserving belief revision for Genesis.

Operational world-state modelling, NOT consciousness, fact verification, Aurora
attestation or autonomous action. An authorized host registers sources in-process;
no network fetching, camera/microphone or HTTP write route is provided here.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .storage import norm

_SOURCE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,63}$")
_SOURCE_KINDS = {"external_feed", "connector", "local_clock", "machine_sensor", "user_report", "test_fixture"}
_MAX_AGE_SECONDS = 30 * 24 * 3600


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("observed_at must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _scalar(value: Any) -> str:
    if type(value) is str:
        if not 1 <= len(value.strip()) <= 512:
            raise ValueError("observation text must contain 1 to 512 characters")
    elif type(value) in {int, float}:
        if not math.isfinite(float(value)) or len(str(value)) > 80:
            raise ValueError("observation numeric value is invalid")
    elif type(value) is not bool:
        raise ValueError("observations must have scalar JSON values")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _field(value: str, *, maxlen: int = 100) -> str:
    if not isinstance(value, str):
        raise ValueError("entity/attribute must be strings")
    value = " ".join(value.strip().split())
    if not value or len(value) > maxlen or any(ord(c) < 32 for c in value):
        raise ValueError("entity/attribute is missing, long, or malformed")
    return value


class PerceptionCore:
    """A separate evidence ledger; never silently overwrites Store.facts.

    'Supported' and 'corroborated' describe recorded agreement, not objective
    truth. A claimed source is not cryptographically authenticated/attested.
    """

    def __init__(self, store: Any, *, clock: Callable[[], datetime] = _utc):
        self.store = store
        self._clock = clock
        with store.tx() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS perception_sources (
                source_id TEXT PRIMARY KEY, source_kind TEXT NOT NULL,
                independence_group TEXT NOT NULL, registered_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS perception_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                source_id TEXT NOT NULL REFERENCES perception_sources(source_id),
                entity TEXT NOT NULL, entity_norm TEXT NOT NULL,
                attribute TEXT NOT NULL, attribute_norm TEXT NOT NULL,
                value_json TEXT NOT NULL, observed_at TEXT NOT NULL,
                received_at TEXT NOT NULL, expires_at TEXT NOT NULL
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_perception_key
                ON perception_observations(entity_norm, attribute_norm, observed_at DESC, id DESC)""")

    def register_source(self, source_id: str, *, source_kind: str,
                        independence_group: str) -> dict[str, Any]:
        """Trusted HOST setup only, never expose to untrusted users or HTTP.

        Provenance groups represent common upstream data. Registration is not
        proof of a sensor or source's real-world authenticity.
        """
        if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
            raise ValueError("invalid source identifier")
        if source_kind not in _SOURCE_KINDS:
            raise ValueError("unsupported source kind")
        if not isinstance(independence_group, str) or not _SOURCE_ID.fullmatch(independence_group):
            raise ValueError("invalid independence group")
        with self.store.tx() as db:
            row = db.execute("SELECT * FROM perception_sources WHERE source_id=?", (source_id,)).fetchone()
            if row:
                if row["source_kind"] != source_kind or row["independence_group"] != independence_group:
                    raise ValueError("source registration is immutable; use a new source ID")
                return {"source_id": source_id, "status": "exists"}
            db.execute("INSERT INTO perception_sources VALUES (?,?,?,?)",
                       (source_id, source_kind, independence_group, _timestamp(self._clock()).isoformat()))
            return {"source_id": source_id, "status": "registered"}

    def observe(self, *, source_id: str, event_id: str, entity: str,
                attribute: str, value: str | int | float | bool,
                observed_at: datetime | None = None, ttl_seconds: int = 300) -> dict[str, Any]:
        """Ingest an attributed, timestamped *claim*, not an authenticated fact.

        Event IDs are stable deduplication keys supplied by the trusted adapter.
        An external event can never change Genesis' authorization/capabilities.
        """
        if not isinstance(event_id, str) or not _SOURCE_ID.fullmatch(event_id):
            raise ValueError("invalid event identifier")
        if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
            raise ValueError("invalid source identifier")
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= _MAX_AGE_SECONDS:
            raise ValueError("TTL must be between 1 and 2592000 seconds")
        entity = _field(entity, maxlen=160)
        attribute = _field(attribute, maxlen=80)
        encoded = _scalar(value)
        now = _timestamp(self._clock())
        seen = _timestamp(observed_at) if observed_at is not None else now
        if seen > now + timedelta(seconds=60):
            raise ValueError("observed_at is implausibly in the future")
        if seen < now - timedelta(seconds=_MAX_AGE_SECONDS):
            raise ValueError("observed_at is older than retention horizon")
        expiry = seen + timedelta(seconds=ttl_seconds)
        payload = (source_id, entity, norm(entity), attribute, norm(attribute),
                   encoded, seen.isoformat(), expiry.isoformat())
        with self.store.tx() as db:
            source = db.execute("SELECT 1 FROM perception_sources WHERE source_id=?", (source_id,)).fetchone()
            if not source:
                raise ValueError("source is not registered")
            existing = db.execute("""SELECT source_id, entity, entity_norm,
               attribute, attribute_norm, value_json, observed_at, expires_at
               FROM perception_observations WHERE event_id=?""", (event_id,)).fetchone()
            if existing:
                if tuple(existing) != payload:
                    raise ValueError("event_id reuse with altered evidence")
                return {"event_id": event_id, "status": "duplicate"}
            db.execute("""INSERT INTO perception_observations
                (event_id, source_id, entity, entity_norm, attribute,
                 attribute_norm, value_json, observed_at, received_at, expires_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, source_id, entity, norm(entity), attribute,
                 norm(attribute), encoded, seen.isoformat(), now.isoformat(), expiry.isoformat()))
            # Audit history is bounded; never mutate ordinary factual memory.
            db.execute("""DELETE FROM perception_observations WHERE id NOT IN
                (SELECT id FROM perception_observations ORDER BY id DESC LIMIT 8192)""")
        return {"event_id": event_id, "status": "recorded"}

    def observe_local_clock(self) -> dict[str, Any]:
        """A genuine local system observation, not attested Engine time."""
        now = _timestamp(self._clock())
        self.register_source("genesis-local-clock", source_kind="local_clock",
                             independence_group="host-clock")
        from uuid import uuid4
        return self.observe(source_id="genesis-local-clock", event_id=str(uuid4()),
                            entity="local_runtime", attribute="utc_time",
                            value=now.isoformat(), observed_at=now, ttl_seconds=3)

    def belief(self, entity: str, attribute: str) -> dict[str, Any]:
        entity = _field(entity, maxlen=160)
        attribute = _field(attribute, maxlen=80)
        with self.store.tx() as db:
            rows = db.execute("""SELECT o.*,s.independence_group,s.source_kind
                FROM perception_observations o JOIN perception_sources s USING(source_id)
                WHERE o.entity_norm=? AND o.attribute_norm=?
                ORDER BY o.observed_at DESC, o.id DESC LIMIT 8192""",
                (norm(entity), norm(attribute))).fetchall()
        # Most recently *observed* report from each source supersedes earlier
        # reports, even if an earlier report has a longer TTL.
        latest: dict[str, Any] = {}
        for row in rows:
            if row["source_id"] not in latest:
                latest[row["source_id"]] = row
        now = _timestamp(self._clock()).isoformat()
        fresh = [r for r in latest.values()
                 if r["observed_at"] <= now and r["expires_at"] > now]
        observed_count = len(rows)
        if not fresh:
            return {"entity": entity, "attribute": attribute,
                    "status": "stale" if observed_count else "unknown", "value": None,
                    "alternatives": [], "independent_groups": 0,
                    "fresh_sources": 0, "historical_events": observed_count,
                    "meaning": "No current evidence; absence of evidence is not evidence of absence."}
        by_value: dict[str, set[str]] = {}
        sources_by_value: dict[str, set[str]] = {}
        for r in fresh:
            by_value.setdefault(r["value_json"], set()).add(r["independence_group"])
            sources_by_value.setdefault(r["value_json"], set()).add(r["source_id"])
        alternatives = [{"value": json.loads(v), "independent_groups": len(groups),
                         "sources": len(sources_by_value[v])}
                        for v, groups in sorted(by_value.items())]
        conflict = len(alternatives) > 1
        status = ("contested" if conflict else "corroborated" if len(next(iter(by_value.values()))) >= 2
                  else "supported")
        # Agreement is not a probability; conflicts are never hidden by a
        # claimed trust label or repeated reports from the same provider.
        return {"entity": entity, "attribute": attribute,
                "status": status, "value": None if conflict else alternatives[0]["value"],
                "alternatives": alternatives, "independent_groups": len(set().union(*by_value.values())),
                "fresh_sources": len(fresh), "historical_events": observed_count,
                "meaning": "Evidence agreement, not objective verification or calibrated probability."}

    def status(self) -> dict[str, Any]:
        """Read-only, content-free health snapshot safe for Kyro displays."""
        with self.store.tx() as db:
            n_sources = db.execute("SELECT COUNT(*) FROM perception_sources").fetchone()[0]
            n_events = db.execute("SELECT COUNT(*) FROM perception_observations").fetchone()[0]
            keys = db.execute("""SELECT entity, attribute FROM perception_observations
                GROUP BY entity_norm, attribute_norm LIMIT 256""").fetchall()
        states = {key: 0 for key in ("unknown", "stale", "supported", "corroborated", "contested")}
        for item in keys:
            states[self.belief(item["entity"], item["attribute"])["status"]] += 1
        return {"source_registrations": n_sources, "observation_events": n_events,
                "sampled_belief_keys": len(keys), "belief_states": states,
                "sensor_attestation": False,
                "note": "Observations are claims; no Engine sensor trust is inferred. Status contains no raw values."}
