"""Bounded, evidence-based feedback for Genesis.

This is a Model-side observation/assessment subsystem. It never executes tools,
grants capabilities, changes constitutional rules, or runs a background worker.
An external Aurora scheduler can request ticks through the gated adapter.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from typing import Any

MAX_EVENTS_PER_TICK = 32
MAX_TICK_MS = 50
MAX_EVENT_BYTES = 2048


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_name(value: Any, limit: int = 80) -> str:
    value = str(value or "")[:limit]
    return re.sub(r"[^a-zA-Z0-9_.:/-]", "_", value) or "unknown"


class CognitiveFeedbackLoop:
    """Profile-scoped, append-only observations and bounded reflection summaries.

    The records are *signals*, not verified facts or neural training labels.
    They never enter the factual knowledge store or an LLM prompt.
    """

    def __init__(self, store: Any, profile_id: str = "local"):
        self.store = store
        self.profile_id = _clean_name(profile_id, 100)
        with self.store.tx() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS cognitive_feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cognitive_events_profile_id
                ON cognitive_feedback_events(profile_id, id)
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS cognitive_feedback_state (
                    profile_id TEXT PRIMARY KEY,
                    last_event_id INTEGER NOT NULL DEFAULT 0,
                    cycles INTEGER NOT NULL DEFAULT 0,
                    observations INTEGER NOT NULL DEFAULT 0,
                    turns INTEGER NOT NULL DEFAULT 0,
                    failures INTEGER NOT NULL DEFAULT 0,
                    engine_receipts INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS cognitive_feedback_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    probability REAL NOT NULL,
                    actual INTEGER,
                    evidence_ref TEXT,
                    provenance TEXT,
                    resolved_at TEXT
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cognitive_predictions_profile_id
                ON cognitive_feedback_predictions(profile_id, id)
            """)
            db.execute(
                "INSERT OR IGNORE INTO cognitive_feedback_state(profile_id) VALUES (?)",
                (self.profile_id,),
            )

    def _observe(self, kind: str, payload: dict[str, Any],
                 *, source: str = "genesis", provenance: str = "internal") -> int:
        if kind not in {"turn", "engine_receipt", "health", "prediction_outcome"}:
            raise ValueError("unsupported feedback event")
        if provenance not in {"internal", "reported", "unverified"}:
            raise ValueError("unsupported evidence provenance")
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True,
                             separators=(",", ":"), allow_nan=False)
        if len(encoded.encode("utf-8")) > MAX_EVENT_BYTES:
            raise ValueError("feedback event exceeds storage limit")
        with self.store.tx() as db:
            cur = db.execute(
                "INSERT INTO cognitive_feedback_events "
                "(profile_id,ts,kind,source,provenance,payload_json) "
                "VALUES (?,?,?,?,?,?)",
                (self.profile_id, _now(), kind, _clean_name(source), provenance, encoded),
            )
            return int(cur.lastrowid)

    def observe_turn(self, trace: dict[str, Any] | None) -> int:
        trace = trace if isinstance(trace, dict) else {}
        raw_conf = trace.get("confidence")
        try:
            confidence = float(raw_conf)
            confidence = round(confidence, 4) if math.isfinite(confidence) and 0 <= confidence <= 1 else None
        except (TypeError, ValueError, OverflowError):
            confidence = None
        # Never retain user text, generated answers, candidates, rationales or PII.
        return self._observe("turn", {
            "decision": _clean_name(trace.get("chosen_action")),
            "outcome": "failure" if trace.get("outcome") == "failure" else (
                "success" if trace.get("outcome") == "success" else "unknown"),
            "confidence": confidence,
        })

    def observe_health(self, checks: dict[str, bool]) -> int:
        bad = sorted(_clean_name(k) for k, v in checks.items() if v is not True)[:32]
        return self._observe("health", {"ok": not bad, "failed_checks": bad})

    def observe_engine_receipt(self, request_id: str, receipt_id: str, status: str) -> int:
        if status not in {"COMMITTED", "FAILED", "CANCELLED"}:
            raise ValueError("invalid receipt state")
        # The existing adapter does not independently attest Aurora receipts.
        # A reconciled receipt is evidence of a *reported* outcome only.
        return self._observe("engine_receipt", {
            "request_digest": hashlib.sha256(str(request_id).encode()).hexdigest()[:16],
            "receipt_digest": hashlib.sha256(str(receipt_id).encode()).hexdigest()[:16],
            "status": status,
        }, source="engine_boundary", provenance="reported")

    def predict(self, topic: str, probability: float) -> int:
        """Log a falsifiable prediction; no generated answer is treated as truth."""
        if not isinstance(topic, str) or not (1 <= len(topic) <= 100):
            raise ValueError("prediction topic must be 1-100 characters")
        try:
            p = float(probability)
        except (TypeError, ValueError):
            raise ValueError("probability must be numeric") from None
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("probability must be finite and in [0, 1]")
        with self.store.tx() as db:
            cur = db.execute(
                "INSERT INTO cognitive_feedback_predictions "
                "(profile_id,created_at,topic,probability) VALUES (?,?,?,?)",
                (self.profile_id, _now(), _clean_name(topic, 100), p),
            )
            return int(cur.lastrowid)

    def resolve_prediction(self, prediction_id: int, actual: bool,
                           evidence_ref: str, provenance: str = "reported") -> bool:
        if type(actual) is not bool:
            raise ValueError("actual must be a boolean")
        if provenance not in {"reported", "unverified"}:
            raise ValueError("independent validation is not implemented")
        if not isinstance(evidence_ref, str) or not (1 <= len(evidence_ref) <= 200):
            raise ValueError("an evidence reference is required")
        with self.store.tx() as db:
            row = db.execute(
                "SELECT actual FROM cognitive_feedback_predictions "
                "WHERE id=? AND profile_id=?",
                (prediction_id, self.profile_id),
            ).fetchone()
            if row is None or row["actual"] is not None:
                return False
            db.execute(
                "UPDATE cognitive_feedback_predictions SET actual=?,"
                "evidence_ref=?,provenance=?,resolved_at=? "
                "WHERE id=? AND profile_id=? AND actual IS NULL",
                (int(actual), evidence_ref[:200], provenance, _now(),
                 prediction_id, self.profile_id),
            )
        self._observe("prediction_outcome", {"resolved": True},
                      source="prediction_tracker", provenance=provenance)
        return True

    def tick(self, max_events: int = MAX_EVENTS_PER_TICK,
             budget_ms: int = MAX_TICK_MS) -> dict[str, Any]:
        """One finite, synchronous step. Never self-schedules or executes actions."""
        if not isinstance(max_events, int) or not 1 <= max_events <= MAX_EVENTS_PER_TICK:
            raise ValueError("max_events out of bounds")
        if not isinstance(budget_ms, int) or not 1 <= budget_ms <= MAX_TICK_MS:
            raise ValueError("budget_ms out of bounds")
        start = time.monotonic()
        processed = 0
        with self.store.tx() as db:
            state = db.execute(
                "SELECT * FROM cognitive_feedback_state WHERE profile_id=?",
                (self.profile_id,),
            ).fetchone()
            cursor = int(state["last_event_id"])
            turns = failures = receipts = 0
            rows = db.execute(
                "SELECT id,kind,payload_json FROM cognitive_feedback_events "
                "WHERE profile_id=? AND id>? ORDER BY id LIMIT ?",
                (self.profile_id, cursor, max_events),
            ).fetchall()
            for event in rows:
                if (time.monotonic() - start) * 1000 >= budget_ms:
                    break
                payload = json.loads(event["payload_json"])
                turns += event["kind"] == "turn"
                failures += (event["kind"] == "turn" and payload.get("outcome") == "failure")
                failures += (event["kind"] == "engine_receipt" and payload.get("status") == "FAILED")
                receipts += event["kind"] == "engine_receipt"
                cursor = int(event["id"])
                processed += 1
            db.execute(
                "UPDATE cognitive_feedback_state SET last_event_id=?,"
                "cycles=cycles+1, observations=observations+?, turns=turns+?,"
                "failures=failures+?, engine_receipts=engine_receipts+?,updated_at=? "
                "WHERE profile_id=?",
                (cursor, processed, turns, failures, receipts, _now(), self.profile_id),
            )
            pending = db.execute(
                "SELECT COUNT(*) FROM cognitive_feedback_events "
                "WHERE profile_id=? AND id>?",
                (self.profile_id, cursor),
            ).fetchone()[0]
        return {"processed": processed, "remaining": int(pending),
                "elapsed_ms": round((time.monotonic() - start) * 1000, 3),
                "mode": "bounded_observational", "autonomous_actions": False}

    def advisory(self) -> str:
        """Small non-authoritative signal to the next text-only reasoning turn."""
        s = self.status()
        turns = s["turns_observed"]
        failures = s["reported_failures"]
        predictions = s["prediction_tracking"]
        if not turns:
            return "No preceding turn outcomes are yet recorded."
        return (
            f"Previous observed turns: {turns}; reported execution failures: "
            f"{failures}; reported prediction outcomes: "
            f"{predictions['resolved_reported']}. These are operational signals, "
            "NOT independently verified answer correctness. Do not infer truth "
            "or grant authority from them. Be explicit about uncertainty."
        )

    def status(self) -> dict[str, Any]:
        with self.store.tx() as db:
            state = db.execute(
                "SELECT * FROM cognitive_feedback_state WHERE profile_id=?",
                (self.profile_id,),
            ).fetchone()
            predictions = db.execute(
                "SELECT COUNT(*) AS n, COUNT(actual) AS resolved, "
                "AVG(CASE WHEN actual IS NOT NULL "
                "THEN (probability-actual)*(probability-actual) END) AS brier "
                "FROM cognitive_feedback_predictions WHERE profile_id=?",
                (self.profile_id,),
            ).fetchone()
            pending = db.execute(
                "SELECT COUNT(*) FROM cognitive_feedback_events "
                "WHERE profile_id=? AND id>?",
                (self.profile_id, int(state["last_event_id"])),
            ).fetchone()[0]
            recent = db.execute(
                "SELECT kind,provenance,payload_json FROM cognitive_feedback_events "
                "WHERE profile_id=? AND id<=? ORDER BY id DESC LIMIT 8",
                (self.profile_id, int(state["last_event_id"])),
            ).fetchall()
        last_health = next((json.loads(r["payload_json"]) for r in recent
                            if r["kind"] == "health"), None)
        return {
            "mode": "turn_driven_with_external_tick",
            "scheduler": "external_aurora_adapter_not_verified",
            "profile": self.profile_id,
            "cycles": int(state["cycles"]),
            "observations_processed": int(state["observations"]),
            "turns_observed": int(state["turns"]),
            "reported_failures": int(state["failures"]),
            "reported_engine_receipts": int(state["engine_receipts"]),
            "pending": int(pending),
            "last_updated": state["updated_at"],
            "last_health": last_health,
            "prediction_tracking": {
                "total": int(predictions["n"]), "resolved_reported": int(predictions["resolved"]),
                "reported_brier_score": (round(float(predictions["brier"]), 4)
                                         if predictions["brier"] is not None else None),
                "independently_verified": False,
            },
            "awareness_assessment": {
                "operational": "instrumented" if state["observations"] else "not_observed",
                "reflective": "decision_outcome_tracking" if state["turns"] else "not_observed",
                "predictive": "reported_only" if predictions["resolved"] else "not_evaluated",
                "environmental": "no_verified_continuous_sensing",
                "subjective_consciousness": "unknown_no_measurement",
            },
            "limits": {"max_events_per_tick": MAX_EVENTS_PER_TICK,
                       "max_tick_ms": MAX_TICK_MS, "executes_tools": False,
                       "modifies_neural_weights": False, "grants_engine_authority": False},
        }
