"""Synthetic ARC-AGI-3 harness regression; never contacts ARC or AWS."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.benchmarks.arc_agi_3 import (
    BenchmarkBlocked, KyroHttpsGenesis, frame_payload, main,
    make_prompt, parse_decision, play_game, play_live,
)


class Action:
    def __init__(self, name, complex_action=False):
        self.name = name
        self.complex_action = complex_action

    def is_complex(self):
        return self.complex_action


class State:
    def __init__(self, name):
        self.name = name


class Observation:
    def __init__(self, state="NOT_FINISHED"):
        self.frame = [[[0, 1], [1, 0]]]
        self.state = State(state)
        self.levels_completed = 0
        self.win_levels = 1


class Environment:
    action_space = [Action("ACTION1"), Action("ACTION6", True)]

    def reset(self):
        return Observation()

    def step(self, action, data=None):
        assert action.name == "ACTION1"
        assert data == {}
        return Observation("WIN")


class Arcade:
    def make(self, game, save_recording=False):
        assert game == "ls20" and save_recording is False
        return Environment()


class Agent:
    def choose(self, prompt):
        proposal = json.loads(prompt)
        assert proposal["actions"][0]["name"] == "ACTION1"
        assert proposal["observation"]["frame"] == [[[0, 1], [1, 0]]]
        return '{"action":"ACTION1"}'


class ReadinessTests(unittest.TestCase):
    def test_frame_prompt(self):
        self.assertEqual(frame_payload(Observation())["state"], "NOT_FINISHED")
        text = make_prompt("ls20", Observation(), Environment.action_space, [])
        self.assertEqual(json.loads(text)["game"], "ls20")

    def test_action_schema_is_strict(self):
        action, data = parse_decision('{"action":"ACTION6","x":63,"y":0}', Environment.action_space)
        self.assertEqual((action.name, data), ("ACTION6", {"x": 63, "y": 0}))
        for invalid in (
            "ACTION1",
            '{"action":"ACTION9"}',
            '{"action":"ACTION1","tool":"shell"}',
            '{"action":"ACTION6","x":64,"y":0}',
            '{"action":"ACTION6","x":true,"y":0}',
            '{"action":"ACTION6","x":1}',
        ):
            with self.subTest(invalid=invalid), self.assertRaises(BenchmarkBlocked):
                parse_decision(invalid, Environment.action_space)

    def test_synthetic_environment_end_to_end(self):
        outcome = play_game(Arcade(), Agent(), "ls20", 3)
        self.assertEqual(outcome["status"], "win")
        self.assertEqual(outcome["actions"], [{"action": "ACTION1"}])

    def test_endpoint_requires_https_and_token(self):
        for url, token in (
            ("http://example.org/chat", "token"),
            ("https://example.org/chat", ""),
            ("https://u:p@example.org/chat", "token"),
        ):
            with self.assertRaises(BenchmarkBlocked):
                KyroHttpsGenesis(url, token)

    def test_anonymous_arc_requires_explicit_opt_in(self):
        with patch.dict("os.environ", {"ARC_API_KEY": ""}):
            with self.assertRaisesRegex(BenchmarkBlocked, "arc_api_key_missing"):
                play_live(Agent(), "ls20", 1)
            with patch("importlib.util.find_spec", return_value=None):
                with self.assertRaisesRegex(BenchmarkBlocked, "official_arc_agi_toolkit_not_installed"):
                    play_live(Agent(), "ls20", 1, allow_anonymous_arc=True)

    def test_anonymous_mode_still_respects_live_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "blocked.json"
            self.assertEqual(main(["--arc-anonymous", "--output", str(path)]), 2)
            report = json.loads(path.read_text())
            self.assertEqual(report["result"], "BLOCKED")
            self.assertEqual(report["blocker"], "live_run_not_authorized")
            self.assertFalse(report["official_scorecard_available"])
            self.assertIsNone(report["official_score"])

    def test_no_default_live_call_or_fake_score(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "blocked.json"
            self.assertEqual(main(["--output", str(path)]), 2)
            report = json.loads(path.read_text())
            self.assertEqual(report["result"], "BLOCKED")
            self.assertEqual(report["blocker"], "live_run_not_authorized")
            self.assertIsNone(report["official_score"])
            self.assertFalse(report["official_scorecard_available"])


if __name__ == "__main__":
    unittest.main()
