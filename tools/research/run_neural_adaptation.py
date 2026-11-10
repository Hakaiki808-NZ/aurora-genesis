"""Real-backend Genesis neural adaptation benchmark (disabled by default).

Usage:
  python -m tools.research.run_neural_adaptation           # dry-run only
  GENESIS_NEURAL_RESEARCH_ENABLE=1 python -m tools.research.run_neural_adaptation \
      --execute --backend ollama --model qwen2.5-coder:1.5b

No provider calls occur unless --execute is supplied. Bedrock also requires
GENESIS_BEDROCK_ENABLE=1 and --approve-paid-inference. Synthetic labels are
computed independently, and withheld predictions are not fed back as examples.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
from pathlib import Path
from statistics import mean

from genesis import Genesis
from genesis.backends import OllamaBackend
from genesis.bedrock_backend import BedrockBackend

TASKS = {
    "xor3": lambda b: b[0] ^ b[1] ^ b[2],
    "xor4": lambda b: b[0] ^ b[1] ^ b[2] ^ b[3],
    "and": lambda b: b[0] & b[2],
    "majority3": lambda b: int(sum(b) >= 3),
    "exactly_two": lambda b: int(sum(b) == 2),
    "implication": lambda b: int((not b[0]) or b[1]),
    "conditional": lambda b: int((b[0] and b[1]) or (b[2] and not b[3])),
}
HOLDOUT = (0, 5, 10, 15)
TRAIN = tuple(x for x in range(16) if x not in HOLDOUT)
MAX_TOTAL_CALLS = 64


def bits(value: int) -> tuple[int, int, int, int]:
    return tuple((value >> index) & 1 for index in range(4))


def make_protocol(seed: int = 20261110, *, tasks: int = 1,
                  regimes: int = 2, train_per_regime: int = 6,
                  holdout_per_regime: int = 2, noise: float = 0.1) -> list[dict]:
    """All hidden rules and labels remain in the evaluator, never in prompts."""
    if not 1 <= tasks <= 2 or not 2 <= regimes <= 3:
        raise ValueError("task/regime budget exceeded")
    if not 4 <= train_per_regime <= 10 or not 1 <= holdout_per_regime <= 4:
        raise ValueError("train/heldout count budget exceeded")
    if not 0 <= noise <= 0.2:
        raise ValueError("noise budget exceeded")
    if 2 * tasks * regimes * (train_per_regime + holdout_per_regime) > MAX_TOTAL_CALLS:
        raise ValueError("total model-call budget exceeded")
    rng = random.Random(seed)
    scenarios = []
    for task_index in range(tasks):
        families = rng.sample(list(TASKS), regimes)
        entries = []
        for stage, family in enumerate(families):
            train_contexts = rng.sample(TRAIN, train_per_regime)
            withheld_contexts = rng.sample(HOLDOUT, holdout_per_regime)
            for local_step, value in enumerate(train_contexts + withheld_contexts):
                x = bits(value)
                truth = TASKS[family](x)
                is_holdout = local_step >= train_per_regime
                # Noise is only added to training feedback, not to the
                # independent label against which accuracy is measured.
                reported = (truth ^ int(rng.random() < noise)) if not is_holdout else truth
                entries.append({
                    "regime": stage, "features": x,
                    "true_label": int(truth), "reported_label": int(reported),
                    "holdout": is_holdout,
                })
        scenarios.append({"task_index": task_index, "events": entries,
                          "private_hidden_family_order": families})
    return scenarios


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "accuracy": None, "parse_rate": None, "brier": None}
    valid = [r for r in rows if r["answer"] is not None]
    return {
        "n": len(rows),
        "accuracy": round(mean(int(r["answer"] == r["truth"]) for r in rows), 4),
        "parse_rate": round(len(valid) / len(rows), 4),
        "brier": (round(mean(
            (r["confidence"] - int(r["answer"] == r["truth"])) ** 2
            for r in valid
        ), 4) if valid else None),
    }


def evaluate_protocol(protocol: list[dict], backend, *, max_context: int = 10) -> dict:
    """Run matched feedback/no-feedback arms with identical independent labels."""
    results = []
    with tempfile.TemporaryDirectory() as temp:
        # A research-only SQLite state store; experiments never reuse live
        # user data. Only the final aggregate report leaves this directory.
        with Genesis(state_path=Path(temp) / "lab.sqlite3",
                     workspace=Path(temp) / "workspace",
                     backend=backend, enable_ollama=False,
                     profile_id="neural_eval") as model:
            assert not model.pending_engine_actions()
            for scenario in protocol:
                for feedback_enabled in (False, True):
                    key = f"trial_{scenario['task_index']}_{int(feedback_enabled)}"
                    session = model.neural_adaptation_lab(
                        key, feedback_enabled=feedback_enabled,
                        choices=2, max_calls=len(scenario["events"]),
                        max_context=max_context, backend=backend,
                    )
                    observations = []
                    for index, event in enumerate(scenario["events"]):
                        proposal = session.propose(event["features"])
                        # An oracle computed this label before the model call.
                        # The model sees it only after answering, and only if
                        # trainable=True in the feedback-enabled arm.
                        assert session.record_outcome(
                            proposal.attempt_id, event["reported_label"],
                            evidence_id=f"grade_{index}",
                            trainable=not event["holdout"],
                        )
                        observations.append({
                            "regime": event["regime"],
                            "holdout": event["holdout"],
                            "truth": event["true_label"],
                            "answer": proposal.answer,
                            "confidence": proposal.confidence,
                        })
                    assert not model.pending_engine_actions()
                    results.append({
                        "task": scenario["task_index"],
                        "arm": "feedback" if feedback_enabled else "no_feedback",
                        "all": summarize(observations),
                        "heldout": summarize([r for r in observations if r["holdout"]]),
                        "post_shift": summarize([r for r in observations if r["regime"] > 0]),
                        "invalid_outputs": sum(r["answer"] is None for r in observations),
                        "session": session.status(),
                    })
    compare = []
    for task_index in sorted({r["task"] for r in results}):
        old = next(r for r in results if r["task"] == task_index and r["arm"] == "no_feedback")
        new = next(r for r in results if r["task"] == task_index and r["arm"] == "feedback")
        compare.append({
            "task": task_index,
            "heldout_accuracy_gain": round(
                new["heldout"]["accuracy"] - old["heldout"]["accuracy"], 4),
            "post_shift_accuracy_gain": round(
                new["post_shift"]["accuracy"] - old["post_shift"]["accuracy"], 4),
        })
    return {"arms": results, "paired_differences": compare}


def _backend(args, total_calls: int):
    if args.backend == "ollama":
        active = OllamaBackend(
            model=args.model, base_url=args.ollama_url,
            timeout=3.0, generation_timeout=90.0,
            max_output_tokens=128,
        )
        if not active.available():
            raise RuntimeError("requested Ollama model is not available locally")
        return active
    if not args.approve_paid_inference or os.environ.get("GENESIS_BEDROCK_ENABLE") != "1":
        raise PermissionError("paid inference requires explicit flag AND environment opt-in")
    # Per-request token and number-of-calls caps; costs can still be nonzero.
    active = BedrockBackend(
        model=args.model, region=args.region,
        enabled=True, max_output_tokens=128, max_calls=total_calls,
    )
    if not active.available():
        raise RuntimeError("Bedrock backend is unavailable or quota-gated")
    return active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("ollama", "bedrock"), default="ollama")
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--region", default="ap-southeast-2")
    parser.add_argument("--approve-paid-inference", action="store_true")
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--tasks", type=int, default=1)
    parser.add_argument("--regimes", type=int, default=2)
    parser.add_argument("--train-per-regime", type=int, default=6)
    parser.add_argument("--holdout-per-regime", type=int, default=2)
    parser.add_argument("--noise", type=float, default=0.1)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    protocol = make_protocol(
        args.seed, tasks=args.tasks, regimes=args.regimes,
        train_per_regime=args.train_per_regime,
        holdout_per_regime=args.holdout_per_regime, noise=args.noise,
    )
    total_calls = sum(len(task["events"]) for task in protocol) * 2
    # Never serialize hidden families or outcome labels to the model.
    report = {
        "schema": 1, "provider": args.backend, "model": args.model,
        "execute": bool(args.execute),
        "call_cap": total_calls,
        "independent_oracle": "synthetic_hidden_rules",
        "hidden_regime_changes": args.regimes - 1,
        "heldout_feedback_leakage": False,
        "noise": args.noise,
        "neural_weights_updated": False,
        "aurora_execution": False,
    }
    if not args.execute:
        report["result"] = "dry_run_no_model_calls"
    else:
        if os.environ.get("GENESIS_NEURAL_RESEARCH_ENABLE") != "1":
            raise PermissionError("GENESIS_NEURAL_RESEARCH_ENABLE=1 required")
        backend = _backend(args, total_calls)
        report["result"] = evaluate_protocol(protocol, backend)
        report["validation"] = (
            "real_generation_attempted_measurements_are_not_general_AGI_proof"
        )
    output = json.dumps(report, sort_keys=True)
    print("NEURAL_ADAPTIVE_REAL_MODEL_EVAL=" + output)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
