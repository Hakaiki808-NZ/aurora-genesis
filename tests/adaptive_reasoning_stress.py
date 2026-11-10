"""Out-of-family and noisy-feedback controls for the Genesis adaptive-rule lab.

The expected *correct* outcome on unknown rule families is reporting a mismatch,
not claiming generalization. Accuracy is measured with simulator-only labels.
"""
from __future__ import annotations

import json
import random
import statistics
import tempfile
from pathlib import Path

from genesis.adaptive_reasoning import AdaptiveRuleLearner
from genesis.storage import Store

SEEDS = tuple(range(20261200, 20261212))
TRIAL_STEPS = 160


def features(value: int) -> tuple[int, ...]:
    return tuple((value >> i) & 1 for i in range(4))


def target_for(task: str, x: tuple[int, ...]) -> int:
    if task == "in_family_pair":
        return x[0] ^ x[2] ^ 1
    if task == "in_family_single":
        return x[1]
    if task == "unknown_xor_3":
        return x[0] ^ x[1] ^ x[2]
    if task == "unknown_xor_4":
        return x[0] ^ x[1] ^ x[2] ^ x[3]
    if task == "unknown_and":
        return x[0] & x[1]
    if task == "unknown_majority":
        return int(sum(x) >= 3)
    raise ValueError("invalid task")


def trial(seed: int, task: str, noise: float = .04) -> dict:
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "lab.sqlite")
        lab = AdaptiveRuleLearner(store, profile_id="evaluation",
                                  experiment_id="stress", noise=noise)
        successes, confidences, alarms = [], [], []
        for step in range(TRIAL_STEPS):
            x = features(rng.randrange(16))
            true_label = target_for(task, x)
            prediction = lab.predict(x)
            action = prediction["action"]
            if step >= 100:
                successes.append(int(action == true_label))
                confidences.append(prediction["confidence"])
                alarms.append(int(prediction["requires_review"]))
            # Only reported correctness is exposed to the learner.
            observed = int(action == true_label) ^ int(rng.random() < noise)
            assert lab.observe(x, action, observed, event_id="event_" + str(step))
        result = {
            "accuracy_last_60": statistics.mean(successes),
            "confidence_last_60": statistics.mean(confidences),
            "alarm_rate_last_60": statistics.mean(alarms),
            "final_requires_review": lab.predict(features(3))["requires_review"],
        }
        store.close()
        return result


def run() -> dict:
    tasks = (
        "in_family_pair", "in_family_single", "unknown_xor_3",
        "unknown_xor_4", "unknown_and", "unknown_majority"
    )
    raw = {task: [trial(seed, task) for seed in SEEDS] for task in tasks}
    high_noise = [trial(seed, "in_family_pair", .20) for seed in SEEDS]
    scores = {
        name: {
            "accuracy_last_60": round(statistics.mean(
                item["accuracy_last_60"] for item in runs
            ), 4),
            "confidence_last_60": round(statistics.mean(
                item["confidence_last_60"] for item in runs
            ), 4),
            "review_alarm_last_60": round(statistics.mean(
                item["alarm_rate_last_60"] for item in runs
            ), 4),
            "trials_flagged_at_end": sum(
                item["final_requires_review"] for item in runs
            ),
            "trials": len(runs),
        }
        for name, runs in {**raw, "in_family_20pct_noise": high_noise}.items()
    }
    # These are diagnostic checks, not evidence that the known hypothesis
    # library can generalize to arbitrary new logical families.
    gates = {
        "control_rules_are_learned": all(
            scores[k]["accuracy_last_60"] >= .85
            for k in ("in_family_pair", "in_family_single")
        ),
        "high_noise_still_learns": scores["in_family_20pct_noise"]["accuracy_last_60"] >= .75,
        "known_good_does_not_raise_permanent_alarm": all(
            scores[k]["trials_flagged_at_end"] <= 3
            for k in ("in_family_pair", "in_family_single")
        ),
        "incompatible_parity_sends_review_signal": sum(
            scores[k]["trials_flagged_at_end"]
            for k in ("unknown_xor_3", "unknown_xor_4")
        ) >= 14,
        "no_claim_of_out_of_family_generalization": all(
            scores[k]["accuracy_last_60"] < .85
            for k in ("unknown_xor_3", "unknown_xor_4")
        ),
    }
    report = {
        "experiment": "adaptive_rule_ood_and_noise_controls",
        "seeds": len(SEEDS),
        "observations_per_task": TRIAL_STEPS,
        "scores": scores,
        "gates": gates,
        "passed": all(gates.values()),
        "limits": (
            "Review alarm is a heuristic from recent mismatch, not OOD proof; "
            "correctness labels remain simulator-only, not neural evaluation."
        ),
    }
    print("ADAPTIVE_REASONING_STRESS=" + json.dumps(report, sort_keys=True))
    if not report["passed"]:
        raise AssertionError("predeclared stress gates failed")
    return report


if __name__ == "__main__":
    run()
