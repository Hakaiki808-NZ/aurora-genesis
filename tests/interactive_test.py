"""Regression tests for typed Genesis interactive action selection.

This tests action validity and environmental feedback, not ARC puzzle solving.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from genesis import Genesis
from tests.arc_agi3_probe import parse_action


def run() -> None:
    with tempfile.TemporaryDirectory() as td:
        model = Genesis(
            state_path=Path(td) / "state.sqlite3",
            workspace=Path(td) / "workspace",
            enable_ollama=False,
        )
        try:
            frames = ("[[0,0],[0,0]]", "[[0,1],[0,0]]", "[[0,1],[1,0]]", "[[0,1],[1,1]]")
            actions = {"ACTION1", "ACTION2", "ACTION3", "ACTION4"}
            for idx in range(3):
                d = model.decide_game_action("new-game", frames[idx], sorted(actions))
                assert d["action"] is not None, d
                assert parse_action(__import__("json").dumps(d["action"]), actions) is not None, d
                assert d["action"]["action_type"] == f"ACTION{idx+1}", d
                assert d["policy"] == "explore-v1"
                blocked = model.decide_game_action("new-game", frames[idx], sorted(actions))
                assert blocked["action"] is None and blocked["reason"] == "awaiting_environment_feedback", blocked
                feedback = model.observe_game_outcome("new-game", frames[idx+1], "NOT_FINISHED")
                assert feedback["recorded"] and feedback["changed_observation"] is True

            # A session for another game is isolated from the first.
            other = model.decide_game_action("another-game", frames[0], ["ACTION2"])
            assert other["action"] == {"action_type": "ACTION2"}, other
            model.observe_game_outcome("another-game", frames[0], "NOT_FINISHED")
            history = model.game_history("new-game")
            assert history["steps_issued"] == 3
            assert history["observation_changes_by_action"] == {"ACTION1": 1, "ACTION2": 1, "ACTION3": 1}
            assert len(history["outcomes"]) == 3
            assert model.game_history("another-game")["steps_issued"] == 1

            # ACTION6 requires bounded coordinates; no unsupported action may escape.
            click = model.decide_game_action("click-game", frames[0], ["ACTION6", "FOO"])
            assert parse_action(__import__("json").dumps(click["action"]), {"ACTION6"}) is not None
            assert click["action"] == {"action_type": "ACTION6", "x": 32, "y": 32}
            assert model.decide_game_action("no-actions", frames[0], ["FOO"])["action"] is None

            # The gameplay observation must not be routed through declarative learning.
            assert model.store.get_fact("You") is None

            # The original natural-language and constitutional checks remain available.
            assert model.self_check()["ok"]
        finally:
            model.close()
    print("INTERACTIVE_ACTION_API=PASS")


if __name__ == "__main__":
    run()
