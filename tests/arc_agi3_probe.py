"""ARC-AGI-3 compatibility probe for the public Genesis reference implementation.

Strictly record invalid actions. Never substitute a random move and call it Genesis.
This is exploratory testing, not an ARC Prize verified benchmark.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from genesis import Genesis


def parse_action(text: str, allowed: set[str]) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
    except (TypeError, ValueError):
        return None
    if isinstance(obj, dict) and set(obj) == {"actions"}:
        items = obj["actions"]
        obj = items[0] if isinstance(items, list) and len(items) == 1 else None
    if not isinstance(obj, dict):
        return None
    action = obj.get("action_type")
    if not isinstance(action, str) or action not in allowed:
        return None
    if action == "ACTION6":
        if set(obj) != {"action_type", "x", "y"}:
            return None
        if not all(type(obj[k]) is int and 0 <= obj[k] <= 63 for k in ("x", "y")):
            return None
    elif set(obj) != {"action_type"}:
        return None
    return obj


def observed_frame(observation: Any) -> str:
    raw = getattr(observation, "frame", observation)
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    return json.dumps(raw, separators=(",", ":"), default=str)[:16000]


def genesis_action(model: Genesis, frame: str, allowed: set[str]) -> dict[str, Any]:
    prompt = (
        "You are exploring an unknown ARC-AGI-3 environment. "
        "Learn its rules through observations and actions. "
        "Available actions: " + ", ".join(sorted(allowed)) + ". "
        'Return ONLY JSON like {"action_type":"ACTION1"} or '
        '{"action_type":"ACTION6","x":32,"y":32}. '
        "Observation (frame): " + frame
    )
    response = model.respond_with_trace(prompt)
    action = parse_action(response["answer"], allowed)
    return {
        "valid_action": action is not None,
        "action": action,
        "model_output_excerpt": response["answer"][:500],
        "trace_available": isinstance(response.get("trace"), dict),
    }


def probe(offline: bool, game_id: str, max_actions: int) -> dict[str, Any]:
    report: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "test": "ARC-AGI-3 Genesis reference compatibility",
        "mode": "synthetic-format-test" if offline else "official-public-game-exploration",
        "game": None if offline else game_id,
        "verified_arc_prize_score": None,
        "aurora": "private engine unavailable in public code",
        "kyro": "runnable interface unavailable in public code",
        "actions_taken": 0,
    }
    with tempfile.TemporaryDirectory() as directory:
        with Genesis(
            state_path=Path(directory) / "state.sqlite3",
            workspace=Path(directory) / "workspace",
            enable_ollama=False,
        ) as model:
            report["genesis_version"] = model.VERSION
            report["backend"] = "built-in reference; Ollama disabled"
            report["self_check"] = model.self_check()
            if offline:
                frame = json.dumps([[0] * 64 for _ in range(64)], separators=(",", ":"))
                decision = genesis_action(model, frame, {"ACTION1", "ACTION2"})
                report["first_decision"] = decision
                report["status"] = "action_ready" if decision["valid_action"] else "no_valid_action"
                report["note"] = "Synthetic grid, NOT an ARC-AGI-3 game or score"
                return report
            try:
                import arc_agi
                from arcengine import GameAction, GameState
            except ImportError as exc:
                report.update(status="sdk_missing", error=str(exc))
                return report
            try:
                arc = arc_agi.Arcade()
                env = arc.make(game_id)
                if env is None:
                    report["status"] = "environment_unavailable"
                    return report
                observation = env.reset()
                if observation is None:
                    report["status"] = "no_observation"
                    return report
                allowed = {action.name for action in env.action_space}
                report["allowed_actions"] = sorted(allowed)
                for step in range(max_actions):
                    decision = genesis_action(model, observed_frame(observation), allowed)
                    if step == 0:
                        report["first_decision"] = decision
                    if not decision["valid_action"]:
                        report["status"] = "no_valid_action"
                        break
                    act = decision["action"]
                    data = {k: act[k] for k in ("x", "y") if k in act}
                    observation = env.step(GameAction[act["action_type"]], data=data)
                    report["actions_taken"] += 1
                    if observation is None:
                        report["status"] = "observation_failed"
                        break
                    if observation.state == GameState.WIN:
                        report["status"] = "game_won"
                        break
                    if observation.state == GameState.GAME_OVER:
                        report["status"] = "game_over"
                        break
                else:
                    report["status"] = "action_budget_reached"
                card = arc.get_scorecard()
                if card is not None:
                    report["exploratory_score"] = getattr(card, "score", None)
            except Exception as exc:
                report.update(status="runtime_error", error=f"{type(exc).__name__}: {str(exc)[:400]}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--game", default="ls20")
    parser.add_argument("--max-actions", type=int, default=3)
    parser.add_argument("--out", default="arc-agi3-probe.json")
    opts = parser.parse_args()
    if not 1 <= opts.max_actions <= 50:
        parser.error("max actions must be 1 through 50")
    result = probe(opts.offline, opts.game, opts.max_actions)
    Path(opts.out).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    if result.get("status") in {"sdk_missing", "environment_unavailable", "no_observation", "runtime_error"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
