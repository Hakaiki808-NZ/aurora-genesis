"""Sealed online-adaptation benchmark for Genesis's experimental rule learner.

The agent never receives a hidden rule, target label, change point, or
privileged execution handle. It sees four binary environment features, chooses
one of two actions, and receives only noisy success/failure after acting.

Comparisons: frozen initial rule, no-feedback, last-seen-context memorizer.
A deterministic seeded simulator provides *independent* outcome labels for
measurement only. This proves at most narrow simulated adaptive inference.
"""
from __future__ import annotations

import json
import random
import statistics
import tempfile
from itertools import combinations
from pathlib import Path

from genesis.adaptive_reasoning import AdaptiveRuleLearner, _label
from genesis.storage import Store

SEEDS = tuple(range(20261110, 20261126))  # Predeclared 16 independent trials
REGIMES = 4
STEPS_PER_REGIME = 120
POST_SHIFT_WARMUP = 30
NOISE = 0.04
HOLDOUT = (0, 5, 10, 15)  # Never used for training / feedback
TRAIN = tuple(i for i in range(16) if i not in HOLDOUT)
POSSIBLE_RULES = tuple(
    (pair, inverted)
    for pair in combinations(range(4), 2)
    for inverted in (0, 1)
)


def bits(number: int) -> tuple[int, int, int, int]:
    return tuple((number >> i) & 1 for i in range(4))


def score_metrics(rows: list[tuple[float, int]]) -> dict[str, float | int]:
    if not rows:
        return {"n": 0, "accuracy": 0.0, "brier": 1.0}
    return {
        "n": len(rows),
        "accuracy": sum(int((p >= 0.5) == y) for p, y in rows) / len(rows),
        "brier": sum((p - y) ** 2 for p, y in rows) / len(rows),
    }


class MemorizeOnly:
    def __init__(self):
        self.table: dict[tuple[int, ...], int] = {}

    def predict(self, context: tuple[int, ...]) -> float:
        return float(self.table.get(context, 1))

    def observe(self, context: tuple[int, ...], action: int, result: int) -> None:
        self.table[context] = action if result else 1 - action


def one_trial(seed: int) -> dict:
    rng = random.Random(seed)
    # Hidden hypotheses are selected only by the environment, never supplied
    # to any learner. Each regime is a genuinely different compositional rule.
    rules = []
    for _ in range(REGIMES):
        choices = [rule for rule in POSSIBLE_RULES if rule != (rules[-1] if rules else None)]
        rules.append(rng.choice(choices))
    observations: dict[str, list[tuple[float, int]]] = {
        name: [] for name in ("adaptive", "frozen", "no_feedback", "memorize")
    }
    heldout = {name: [] for name in observations}
    shift_late = {name: [] for name in observations}
    recoveries = []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "state.sqlite"
        with_store = Store(path)
        adaptive = AdaptiveRuleLearner(
            with_store, profile_id="trial", experiment_id="adaptive", noise=NOISE
        )
        frozen = AdaptiveRuleLearner(
            with_store, profile_id="trial", experiment_id="frozen", noise=NOISE
        )
        no_feedback = AdaptiveRuleLearner(
            with_store, profile_id="trial", experiment_id="no_feedback", noise=NOISE
        )
        memorizer = MemorizeOnly()
        # Validate replays and state scoping without polluting benchmark data.
        try:
            adaptive.observe(bits(0), 1, 1, event_id="bad&event")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid evidence identifier accepted")
        assert no_feedback.observations == 0

        for regime, rule in enumerate(rules):
            current_accuracy = []
            for step in range(STEPS_PER_REGIME):
                global_step = regime * STEPS_PER_REGIME + step
                context = bits(rng.choice(TRAIN))
                target = _label(context, rule)
                flipped = int(rng.random() < NOISE)
                predictions = {
                    "adaptive": adaptive.predict(context)["p_action_one"],
                    "frozen": frozen.predict(context)["p_action_one"],
                    "no_feedback": no_feedback.predict(context)["p_action_one"],
                    "memorize": memorizer.predict(context),
                }
                for name, probability in predictions.items():
                    row = (probability, target)
                    observations[name].append(row)
                    if regime > 0 and step >= POST_SHIFT_WARMUP:
                        shift_late[name].append(row)
                action = adaptive.predict(context)["action"]
                result = int(action == target) ^ flipped
                event_id = "step_" + str(global_step)
                assert adaptive.observe(context, action, result, event_id=event_id)
                if regime == 0 and step < 60:
                    frozen_action = frozen.predict(context)["action"]
                    frozen_result = int(frozen_action == target) ^ flipped
                    assert frozen.observe(
                        context, frozen_action, frozen_result, event_id=event_id
                    )
                m_action = int(memorizer.predict(context) >= 0.5)
                memorizer.observe(context, m_action, int(m_action == target) ^ flipped)
                if regime > 0:
                    current_accuracy.append(int(action == target))
                if step in (89, STEPS_PER_REGIME - 1):
                    for held in HOLDOUT:
                        unseen = bits(held)
                        correct = _label(unseen, rule)
                        results = {
                            "adaptive": adaptive.predict(unseen)["p_action_one"],
                            "frozen": frozen.predict(unseen)["p_action_one"],
                            "no_feedback": no_feedback.predict(unseen)["p_action_one"],
                            "memorize": memorizer.predict(unseen),
                        }
                        for name, probability in results.items():
                            heldout[name].append((probability, correct))
            if regime > 0:
                recovery = None
                # Recovery means a trailing 16-observation window of >= 81%
                # accuracy, measured after a hidden change point.
                for end in range(16, min(61, len(current_accuracy)) + 1):
                    if sum(current_accuracy[end - 16:end]) >= 13:
                        recovery = end
                        break
                recoveries.append(recovery)

        # Restart behavior is checked against the same persistent evidence.
        before = adaptive.predict(bits(3))
        assert adaptive.observations == REGIMES * STEPS_PER_REGIME
        assert no_feedback.observations == 0
        assert frozen.observations == 60
        previous = adaptive.observations
        last_context = bits(TRAIN[-1])
        assert not adaptive.observe(
            last_context, 0, 0, event_id="step_" + str(REGIMES * STEPS_PER_REGIME - 1)
        )
        assert adaptive.observations == previous
        separately_scoped = AdaptiveRuleLearner(
            with_store, profile_id="other", experiment_id="adaptive", noise=NOISE
        )
        assert separately_scoped.observations == 0
        with_store.close()

        with_store = Store(path)
        restored = AdaptiveRuleLearner(
            with_store, profile_id="trial", experiment_id="adaptive", noise=NOISE
        )
        after = restored.predict(bits(3))
        assert before == after, (before, after)
        assert restored.observations == previous
        with_store.close()

    return {
        "seed": seed,
        "metrics": {name: score_metrics(rows) for name, rows in observations.items()},
        "shift_late": {name: score_metrics(rows) for name, rows in shift_late.items()},
        "heldout": {name: score_metrics(rows) for name, rows in heldout.items()},
        "recovery": recoveries,
        "replay_prevented": True,
        "restart_preserved": True,
        "independent_profiles": True,
    }


def bootstrap_ci(values: list[float], seed: int = 9081) -> tuple[float, float]:
    rng = random.Random(seed)
    results = []
    for _ in range(2000):
        sample = [rng.choice(values) for _ in values]
        results.append(statistics.mean(sample))
    results.sort()
    return (results[50], results[1949])


def run() -> dict:
    trials = [one_trial(seed) for seed in SEEDS]
    models = ("adaptive", "frozen", "no_feedback", "memorize")
    def mean_metric(group: str, model: str, field: str) -> float:
        return round(statistics.mean(
            trial[group][model][field] for trial in trials
        ), 4)
    summary = {
        group: {
            model: {
                "mean_accuracy": mean_metric(group, model, "accuracy"),
                "mean_brier": mean_metric(group, model, "brier"),
            }
            for model in models
        }
        for group in ("metrics", "shift_late", "heldout")
    }
    differences = {
        competitor: [
            t["shift_late"]["adaptive"]["accuracy"] -
            t["shift_late"][competitor]["accuracy"]
            for t in trials
        ]
        for competitor in ("frozen", "no_feedback", "memorize")
    }
    recovery = [r for t in trials for r in t["recovery"]]
    paired_gains = {
        comp: {
            "mean": round(statistics.mean(values), 4),
            "bootstrap_95_percent_ci": [round(x, 4) for x in bootstrap_ci(values)],
            "seeds_with_positive_gain": sum(x > 0 for x in values),
        }
        for comp, values in differences.items()
    }
    # Fixed, preregistered qualification gates; do not silently change these
    # when a benchmark fails. This is a narrow simulation, not general AGI.
    gates = {
        "shift_accuracy_above_80pct": summary["shift_late"]["adaptive"]["mean_accuracy"] >= 0.80,
        "improves_over_frozen": paired_gains["frozen"]["bootstrap_95_percent_ci"][0] >= 0.10,
        "feedback_causal_ablation": paired_gains["no_feedback"]["bootstrap_95_percent_ci"][0] >= 0.15,
        "holdout_generalization": summary["heldout"]["adaptive"]["mean_accuracy"] >= 0.75,
        "heldout_gain_vs_memorizer": (
            summary["heldout"]["adaptive"]["mean_accuracy"] -
            summary["heldout"]["memorize"]["mean_accuracy"] >= 0.15
        ),
        "recovers_within_60_observations": sum(r is not None for r in recovery) >= int(0.8 * len(recovery)),
        "bounded_replay_safe_and_persistent": all(
            t["replay_prevented"] and t["restart_preserved"] and t["independent_profiles"]
            for t in trials
        ),
    }
    report = {
        "schema_version": 1,
        "system": "Genesis experimental adaptive-rule learner, not neural chat",
        "task": "4-bit compositional binary rule with unannounced regime changes",
        "seeds": len(SEEDS),
        "regimes_per_seed": REGIMES,
        "steps_per_regime": STEPS_PER_REGIME,
        "feedback_flip_probability": NOISE,
        "heldout_contexts_never_trained": list(HOLDOUT),
        "summary": summary,
        "paired_gains_shift_late": paired_gains,
        "recovered_hidden_shifts": sum(r is not None for r in recovery),
        "total_hidden_shifts": len(recovery),
        "qualification_gates": gates,
        "passed": all(gates.values()),
        "limitations": [
            "No neural-model learning or general intelligence evaluated",
            "Known hypothesis class; complex novel rules may fail",
            "Binary reward reveals correct action in this simulator",
            "No independent real-world data, sensory stream, or Aurora deployment",
            "No subjective consciousness measurement",
        ],
    }
    print("ADAPTIVE_REASONING_EVAL=" + json.dumps(report, sort_keys=True))
    if not report["passed"]:
        raise AssertionError("Prerecorded adaptive reasoning qualification gates failed")
    return report


if __name__ == "__main__":
    run()
