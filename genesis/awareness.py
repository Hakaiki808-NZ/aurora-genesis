"""Functional awareness instrumentation for Genesis.

This is a bounded, inspectable *operational* monitor: not a consciousness
or sentience implementation, not an Aurora sensor, and not an authority gate.
No raw user messages, neural generations or engine secrets are recorded here.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import Any


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _label(value: Any) -> str:
    """Allow diagnostic identifiers, never arbitrary text, into the ledger."""
    return re.sub(r"[^a-zA-Z0-9_.:-]", "_", str(value))[:64] or "unknown"


def _probability(value: Any) -> float | None:
    try:
        n = float(value)
        return n if math.isfinite(n) and 0 <= n <= 1 else None
    except (ValueError, TypeError, OverflowError):
        return None


class AwarenessCore:
    """Genesis-owned telemetry, limited attention and evidence-based calibration.

    The Store owns transactions; the Engine and Guardians retain all existing
    execution authority. This class does not issue tools, actions or proofs.
    """

    def __init__(self, store: Any, identity: dict[str, Any], capabilities: Any,
                 *, attention_capacity: int = 5):
        if not 1 <= attention_capacity <= 20:
            raise ValueError("attention capacity must be between 1 and 20")
        self.store = store
        self.identity = identity
        self.capabilities = capabilities
        self.attention_capacity = attention_capacity
        with self.store.tx() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS awareness_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL, kind TEXT NOT NULL, label TEXT NOT NULL,
                salience REAL NOT NULL, confidence REAL,
                decision_id INTEGER, operational_outcome TEXT,
                details_json TEXT NOT NULL DEFAULT '{}'
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS awareness_event_decision
                          ON awareness_events(decision_id)""")
            db.execute("""CREATE TABLE IF NOT EXISTS awareness_evaluations (
                decision_id INTEGER PRIMARY KEY, correct INTEGER NOT NULL,
                evaluator TEXT NOT NULL, ts TEXT NOT NULL
            )""")

    def _record(self, *, kind: str, label: str, salience: float,
                confidence: float | None = None, decision_id: int | None = None,
                operational_outcome: str | None = None,
                details: dict[str, int | bool] | None = None) -> int:
        kind = _label(kind)
        label = _label(label)
        if not math.isfinite(salience) or not 0 <= salience <= 1:
            raise ValueError("salience must be a finite probability")
        if confidence is not None and _probability(confidence) is None:
            raise ValueError("confidence must be a finite probability")
        # Strict primitive whitelist prevents storing raw prompts, model output,
        # tool contents, or names supplied by external sources in details_json.
        safe_details = {}
        for key, value in (details or {}).items():
            if key in {"message_char_count", "decision_id"} and type(value) is int:
                safe_details[key] = max(0, min(value, 100000))
            elif key == "feedback_available" and type(value) is bool:
                safe_details[key] = value
        with self.store.tx() as db:
            cur = db.execute("""INSERT INTO awareness_events
                (ts, kind, label, salience, confidence, decision_id,
                 operational_outcome, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (_utc(), kind, label, salience, confidence, decision_id,
                 operational_outcome, json.dumps(safe_details)))
            # Bounded telemetry storage; evaluations older than the window are
            # also deleted so calibration uses only retained decisions.
            db.execute("""DELETE FROM awareness_events WHERE id NOT IN
                          (SELECT id FROM awareness_events ORDER BY id DESC LIMIT 2048)""")
            db.execute("""DELETE FROM awareness_evaluations WHERE decision_id NOT IN
                          (SELECT decision_id FROM awareness_events
                           WHERE kind='decision' AND decision_id IS NOT NULL)""")
            return int(cur.lastrowid)

    def begin_turn(self, message: str) -> None:
        self._record(kind="input", label="message_received", salience=0.45,
                     details={"message_char_count": len(message)})

    def end_turn(self, trace: dict[str, Any]) -> None:
        confidence = _probability(trace.get("confidence"))
        outcome = trace.get("outcome")
        outcome = outcome if outcome in {"success", "failure"} else "unknown"
        did = trace.get("decision_id")
        did = did if type(did) is int and did >= 0 else None
        self._record(kind="decision", label=trace.get("chosen_action", "unknown"),
                     salience=0.85 if outcome == "failure" else 0.65,
                     confidence=confidence, decision_id=did,
                     operational_outcome=outcome)
        if confidence is None or confidence < 0.65:
            self._record(kind="uncertainty", label="uncalibrated_or_low_confidence",
                         salience=0.9)
        if outcome == "failure":
            self._record(kind="discrepancy", label="operational_failure",
                         salience=1.0)

    def record_evaluation(self, decision_id: int, *, correct: bool,
                          evaluator: str) -> None:
        """Offline/trusted evaluator entry point; NEVER expose as public HTTP.

        Self-reported operational success is not a correctness label. The caller
        must independently verify the label; this method is not an auth check.
        """
        if type(decision_id) is not int or decision_id < 0:
            raise ValueError("invalid decision_id")
        if type(correct) is not bool or not evaluator or len(evaluator) > 80:
            raise ValueError("trusted boolean label and evaluator required")
        with self.store.tx() as db:
            row = db.execute("""SELECT id FROM awareness_events
                WHERE kind='decision' AND decision_id=? LIMIT 1""", (decision_id,)).fetchone()
            if row is None:
                raise ValueError("decision not present in awareness ledger")
            previous = db.execute("""SELECT correct FROM awareness_evaluations
                WHERE decision_id=?""", (decision_id,)).fetchone()
            if previous is not None and bool(previous[0]) != correct:
                raise ValueError("conflicting label requires an audited correction process")
            db.execute("""INSERT OR IGNORE INTO awareness_evaluations
                (decision_id, correct, evaluator, ts) VALUES (?, ?, ?, ?)""",
                (decision_id, int(correct), _label(evaluator), _utc()))

    def _calibration(self) -> dict[str, Any]:
        with self.store.tx() as db:
            rows = db.execute("""SELECT e.confidence, v.correct
                FROM awareness_evaluations v JOIN awareness_events e
                ON e.decision_id=v.decision_id AND e.kind='decision'
                WHERE e.confidence IS NOT NULL""").fetchall()
        pairs = [(float(r[0]), int(r[1])) for r in rows]
        n = len(pairs)
        return {
            "verified_labels": n,
            "brier_score": round(sum((p-y)**2 for p,y in pairs)/n, 4) if n else None,
            "accuracy": round(sum(y for _,y in pairs)/n, 4) if n else None,
            "well_sampled": n >= 30,
            "note": "Only externally checked correctness labels count. Decision success is not proof of correctness."
        }

    def snapshot(self) -> dict[str, Any]:
        with self.store.tx() as db:
            rows = db.execute("""SELECT id, kind, label, salience, confidence,
                operational_outcome FROM awareness_events
                ORDER BY id DESC LIMIT 40""").fetchall()
        # Newer events win ties while exceptionally salient discrepancies persist.
        ranked = sorted(enumerate(rows), key=lambda pair:
                        float(pair[1]["salience"]) * (0.94 ** pair[0]), reverse=True)
        attention = [{"kind": row["kind"], "label": row["label"],
                      "priority": round(float(row["salience"]) * (0.94 ** age), 3)}
                     for age, row in ranked[:self.attention_capacity]]
        last_decision = next((r for r in rows if r["kind"] == "decision"), None)
        return {
            "mode": "functional_observability_not_consciousness",
            "self_model": {
                "model": self.identity.get("model_name", "Genesis"),
                "role": "cognition",
                "capability_ceiling": self.capabilities.granted_level,
                "engine_authority": False,
                "engine_sensor_attested": False,
            },
            "attention": attention,
            "metacognition": self._calibration(),
            "last_decision": None if last_decision is None else {
                "action": last_decision["label"],
                "confidence_estimate": last_decision["confidence"],
                "operational_outcome": last_decision["operational_outcome"],
                "correctness_verified": self._is_evaluated(last_decision["id"]),
            },
            "limits": ["no subjective-experience inference",
                       "no independent sensors or real-world perception",
                       "no independent Engine/Angel attestation",
                       "no autonomous execution authorization"],
        }

    def _is_evaluated(self, event_id: int) -> bool:
        with self.store.tx() as db:
            row = db.execute("""SELECT 1 FROM awareness_evaluations v
                JOIN awareness_events e ON e.decision_id=v.decision_id
                WHERE e.id=? LIMIT 1""", (event_id,)).fetchone()
            return row is not None

    def healthy(self) -> bool:
        try:
            with self.store.tx() as db:
                return bool(db.execute("SELECT 1 FROM awareness_events LIMIT 1").fetchall() is not None)
        except Exception:
            return False
