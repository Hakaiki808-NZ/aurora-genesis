"""Experimental, bounded online hypothesis revision for *simulated* binary tasks.

This is a narrow reasoning research primitive, not autonomous tool use or a
neural model. It consumes observed binary outcomes (not ground-truth rule IDs)
and tests competing compositional explanations of the observations. Only the
explicit research harness should use it; it is not part of normal chat or the
Aurora privileged execution path.
"""
from __future__ import annotations

import json
import math
import re
from itertools import combinations
from typing import Any

FEATURE_COUNT = 4
MAX_CANDIDATES = 32
HYPOTHESES = tuple(
    (indexes, invert)
    for width in (1, 2)
    for indexes in combinations(range(FEATURE_COUNT), width)
    for invert in (0, 1)
)
assert len(HYPOTHESES) <= MAX_CANDIDATES


def _features(context: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    if not isinstance(context, (tuple, list)) or len(context) != FEATURE_COUNT:
        raise ValueError("context must be four binary features")
    if any(type(v) is not int or v not in (0, 1) for v in context):
        raise ValueError("features must be 0 or 1 integers")
    return tuple(context)


def _label(context: tuple[int, ...], hypothesis: tuple[tuple[int, ...], int]) -> int:
    indexes, invert = hypothesis
    result = invert
    for i in indexes:
        result ^= context[i]
    return result


class AdaptiveRuleLearner:
    """Online compositional rule selection with discounted likelihood evidence.

    The experiment has exactly two actions and four Boolean features. The
    observation is only (context, chosen action, reported binary success).
    In the test environment reward=1 means the chosen action was correct, but
    real-world reported success does NOT necessarily mean factual correctness.
    """

    def __init__(self, store: Any, *, profile_id: str, experiment_id: str,
                 discount: float = 0.94, noise: float = 0.04):
        for value in (profile_id, experiment_id):
            if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
                raise ValueError("invalid experiment scope")
        if not 0.80 <= discount <= 0.995:
            raise ValueError("discount must lie between 0.80 and 0.995")
        if not 0.01 <= noise <= 0.25:
            raise ValueError("noise must lie between 0.01 and 0.25")
        self.store = store
        self.profile_id = profile_id
        self.experiment_id = experiment_id
        self.discount = float(discount)
        self.noise = float(noise)
        with self.store.tx() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_rule_lab_v1 (
                    profile_id TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    observations INTEGER NOT NULL DEFAULT 0,
                    log_scores_json TEXT NOT NULL,
                    mismatch_ema REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY(profile_id, experiment_id)
                )
            """)
            columns = {r[1] for r in db.execute("PRAGMA table_info(adaptive_rule_lab_v1)")}
            if "mismatch_ema" not in columns:
                db.execute(
                    "ALTER TABLE adaptive_rule_lab_v1 "
                    "ADD COLUMN mismatch_ema REAL NOT NULL DEFAULT 0"
                )
            db.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_rule_lab_evidence_v1 (
                    profile_id TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    PRIMARY KEY(profile_id, experiment_id, event_id)
                )
            """)
            db.execute(
                "INSERT OR IGNORE INTO adaptive_rule_lab_v1 "
                "(profile_id,experiment_id,observations,log_scores_json) "
                "VALUES (?,?,0,?)",
                (profile_id, experiment_id, json.dumps([0.0] * len(HYPOTHESES))),
            )
        self._reload()

    def _reload(self) -> None:
        with self.store.tx() as db:
            record = db.execute(
                "SELECT observations, log_scores_json, mismatch_ema FROM adaptive_rule_lab_v1 "
                "WHERE profile_id=? AND experiment_id=?",
                (self.profile_id, self.experiment_id),
            ).fetchone()
        if record is None:
            raise ValueError("experiment state missing")
        scores = json.loads(record["log_scores_json"])
        if len(scores) != len(HYPOTHESES) or any(
            not isinstance(s, (int, float)) or not math.isfinite(s) for s in scores
        ):
            raise ValueError("invalid model evidence state")
        self.scores = [float(x) for x in scores]
        self.observations = int(record["observations"])
        self.mismatch_ema = float(record["mismatch_ema"])

    def predict(self, context: tuple[int, ...] | list[int]) -> dict[str, Any]:
        features = _features(context)
        largest = max(self.scores)
        weights = [math.exp(s - largest) for s in self.scores]
        total = sum(weights)
        p = sum(
            w * _label(features, h) for w, h in zip(weights, HYPOTHESES)
        ) / total
        return {
            "action": int(p >= 0.5),
            "p_action_one": p,
            "confidence": max(p, 1 - p),
            "observations": self.observations,
            "mismatch_ema": round(self.mismatch_ema, 4),
            "requires_review": self.observations >= 40 and self.mismatch_ema >= 0.27,
            "scope": "simulation_only",
        }

    def observe(self, context: tuple[int, ...] | list[int],
                action: int, reported_success: int, *, event_id: str) -> bool:
        features = _features(context)
        if not isinstance(event_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", event_id):
            raise ValueError("invalid evidence identifier")
        if type(action) is not int or action not in (0, 1):
            raise ValueError("action must be binary")
        if type(reported_success) is not int or reported_success not in (0, 1):
            raise ValueError("reported success must be binary")
        # Binary simulated outcomes reveal what would have succeeded. No rule ID,
        # no privileged access, and no direct target label enter this method.
        inferred_target = action if reported_success else 1 - action
        good = math.log(1 - self.noise)
        bad = math.log(self.noise)
        delta = [
            good if _label(features, candidate) == inferred_target else bad
            for candidate in HYPOTHESES
        ]
        # CAS-style transaction: handle multiple processes sharing SQLite state.
        with self.store.tx() as db:
            inserted = db.execute(
                "INSERT OR IGNORE INTO adaptive_rule_lab_evidence_v1 "
                "(profile_id,experiment_id,event_id) VALUES (?,?,?)",
                (self.profile_id, self.experiment_id, event_id),
            )
            if not inserted.rowcount:
                return False
            row = db.execute(
                "SELECT observations,log_scores_json,mismatch_ema FROM adaptive_rule_lab_v1 "
                "WHERE profile_id=? AND experiment_id=?",
                (self.profile_id, self.experiment_id),
            ).fetchone()
            existing = json.loads(row["log_scores_json"])
            scores = [self.discount * float(s) + d for s, d in zip(existing, delta)]
            top = max(range(len(existing)), key=lambda i: float(existing[i]))
            mismatch = float(_label(features, HYPOTHESES[top]) != inferred_target)
            mismatch_ema = 0.92 * float(row["mismatch_ema"]) + 0.08 * mismatch
            db.execute(
                "UPDATE adaptive_rule_lab_v1 "
                "SET observations=?,log_scores_json=?,mismatch_ema=? "
                "WHERE profile_id=? AND experiment_id=?",
                (int(row["observations"]) + 1, json.dumps(scores),
                 mismatch_ema, self.profile_id, self.experiment_id),
            )
        self.scores = scores
        self.observations = int(row["observations"]) + 1
        self.mismatch_ema = mismatch_ema
        return True

    def explanation(self) -> dict[str, Any]:
        """Transparent hypothesis and uncertainty; does not claim truth."""
        top = max(range(len(self.scores)), key=self.scores.__getitem__)
        indexes, inverted = HYPOTHESES[top]
        return {
            "candidate_family": "xor_of_one_or_two_binary_features",
            "leading_features": list(indexes),
            "inverted": bool(inverted),
            "observations": self.observations,
            "mismatch_ema": round(self.mismatch_ema, 4),
            "requires_review": self.observations >= 40 and self.mismatch_ema >= 0.27,
            "interpretation": "best_supported_hypothesis_not_established_truth",
            "tool_execution": False,
            "weight_training": False,
            "engine_authority": False,
        }
