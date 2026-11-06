"""Bounded public LS20 visual reasoning experiment.

Runs only on visual frames exposed by the official SDK. The planner is
public-game-specific, informed by public LS20 descriptions, and NOT a
blind/general-purpose ARC benchmark entry. A failed game is a failed game.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import arc_agi
from arcengine import GameAction, GameState

from genesis.visual_navigation import LS20VisualPlanner
from tests.arc_agi3_probe import observed_frame, parse_action


def run(max_actions: int) -> dict:
    arc = arc_agi.Arcade()
    env = arc.make("ls20")
    if env is None:
        raise RuntimeError("Public LS20 environment could not be opened")
    obs = env.reset()
    planner = LS20VisualPlanner()
    allowed = {item.name for item in env.action_space}
    results: dict = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "game": "ls20",
        "policy": "ls20-vision-v1",
        "evaluation": "public exploratory, game-aware; not a verified or blind AGI benchmark",
        "result": "not_started",
        "allowed_actions": sorted(allowed),
        "max_actions": max_actions,
        "actions_taken": 0,
        "levels_completed": getattr(obs, "levels_completed", 0),
        "win_levels": getattr(obs, "win_levels", None),
        "action_trace": [],
        "level_progress": [],
    }
    previous_level = getattr(obs, "levels_completed", 0)
    for index in range(max_actions):
        decision = planner.decide(observed_frame(obs),
                                  int(getattr(obs, "levels_completed", 0)),
                                  allowed)
        move = decision.get("action")
        if move is None:
            results["result"] = "planner_abstained"
            results["stop_reason"] = decision
            break
        valid = parse_action(json.dumps(move), allowed)
        if valid is None:
            results["result"] = "invalid_action"
            results["stop_reason"] = decision
            break
        obs = env.step(GameAction[valid["action_type"]],
                       data={k:valid[k] for k in ("x","y") if k in valid})
        results["actions_taken"] += 1
        if obs is None:
            results["result"] = "no_observation"
            break
        level = getattr(obs, "levels_completed", previous_level)
        results["levels_completed"] = level
        if level != previous_level:
            results["level_progress"].append(
                {"action_number":index+1,"from":previous_level,"to":level})
            previous_level = level
        results["action_trace"].append({
            "step": index+1, "action": valid["action_type"],
            "reason":decision.get("reason"),
            "position":decision.get("position"),
            "target":decision.get("objective"),
            "route_length":decision.get("route_len"),
            "levels_completed":level,
        })
        if obs.state == GameState.WIN:
            results["result"] = "won"
            break
        if obs.state == GameState.GAME_OVER:
            results["result"] = "game_over"
            break
    else:
        results["result"] = "action_budget_exhausted"
    card = arc.get_scorecard()
    results["exploratory_score"] = getattr(card, "score", None)
    results["last_game_state"] = obs.state.name if obs else None
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-actions", type=int, default=100)
    parser.add_argument("--out", default="ls20-visual-result.json")
    args = parser.parse_args()
    if not 1 <= args.max_actions <= 500:
        parser.error("actions must be between 1 and 500")
    result = run(args.max_actions)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("LS20_RESULT "+json.dumps({k:v for k,v in result.items() if k != "action_trace"}))
    print("LS20_TRACE_HEAD "+json.dumps(result["action_trace"][:35]))
    print("LS20_TRACE_TAIL "+json.dumps(result["action_trace"][-12:]))
    # Don't let the CI job say 'passed the game' merely because it ran.
    # The JSON result is the authoritative outcome.


if __name__ == "__main__":
    main()
