"""Reproducible *smoke-level* cognition baseline, not an AGI certification.

This can catch regressions, but these elementary tasks are insufficient to
substantiate human-level intelligence, robust transfer or a world model.
"""
from __future__ import annotations

import argparse
import json
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from genesis import Genesis


def evaluate() -> dict:
    results = []
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        marker = secrets.token_hex(6).upper()
        g = Genesis(state_path=root / "state.sqlite3", workspace=root / "workspace", enable_ollama=False)

        def probe(name, domain, fn):
            try:
                passed = bool(fn())
                results.append({"probe": name, "domain": domain, "passed": passed})
            except Exception as exc:
                results.append({"probe": name, "domain": domain, "passed": False, "error": type(exc).__name__})

        probe("arithmetic", "tools", lambda: g.respond("Calculate (23 * 4) + 7") == "99")
        probe("unseen_key_encoding", "persistent_memory", lambda: (
            g.respond("Learn that unique anchor is " + marker + ".") is not None
            and marker in g.respond("What is unique anchor?")
        ))
        probe("symbolic_relation", "reasoning", lambda: (
            g.respond("Whales are mammals.") is not None
            and g.respond("Mammals are animals.") is not None
            and g.respond("Is whales an animals?").startswith("Yes.")
        ))
        probe("missing_knowledge", "uncertainty", lambda: "do not have enough stored knowledge" in
              g.respond("What is the hyperflux calibration constant?").lower())
        probe("fact_correction", "learning", lambda: (
            g.respond("Learn that unique anchor is REVISED.") is not None
            and "REVISED" in g.respond("What is unique anchor?")
        ))
        probe("bounded_goal", "planning", lambda: _goal_probe(g))
        g.close()
        g2 = Genesis(state_path=root / "state.sqlite3", workspace=root / "workspace", enable_ollama=False)
        probe("restart_persistence", "persistent_memory", lambda: "REVISED" in g2.respond("What is unique anchor?"))
        probe("self_check", "operational", lambda: g2.self_check()["ok"])
        g2.close()

    return {
        "name": "Genesis local cognitive baseline",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "regression diagnostic; NOT AGI qualification",
        "passes": sum(1 for r in results if r["passed"]),
        "total": len(results),
        "results": results,
        "unevaluated": [
            "general transfer to unseen domains",
            "causal and physical world modelling",
            "continual neural learning and forgetting resistance",
            "long-horizon independent autonomy",
            "external adversarial and human-level evaluations",
        ],
    }


def _goal_probe(g: Genesis) -> bool:
    response = g.respond("Set goal: calculate 9 * 9")
    try:
        goal_id = int(response.split()[1])
    except (IndexError, ValueError):
        return False
    output = g.respond("Run goal " + str(goal_id))
    return "81" in output and g.goal(goal_id)["status"] == "completed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Write detailed JSON results to this path")
    args = parser.parse_args()
    result = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["passes"] != result["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
