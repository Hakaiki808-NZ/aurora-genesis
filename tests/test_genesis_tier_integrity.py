"""Regression tests: model tier declarations must never reduce required authority."""
from datetime import datetime, timedelta, timezone
import unittest

from genesis.capabilities import CapabilityController
from genesis.engine_boundary import EngineBoundary


class GenesisTierIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.controller = CapabilityController(granted_level="C5")

    def test_model_claim_cannot_lower_engine_risk(self):
        cases = (
            ({"type": "tool", "capability_level": "C0"}, "C2"),
            ({"type": "run_goal", "capability_level": "C0"}, "C3"),
            ({"type": "tool", "capability_level": "C0", "external_side_effect": True}, "C4"),
            ({"type": "tool", "capability_level": "C1", "privileged": True}, "C4"),
            ({"type": "response", "capability_level": "C0", "irreversible": True}, "C4"),
            ({"type": "response", "capability_level": "C0", "persistent_autonomy": True}, "C5"),
        )
        for action, floor in cases:
            with self.subTest(action=action):
                self.assertEqual(self.controller._required(action), floor)

    def test_protected_and_unknown_are_denied(self):
        for action in (
            {"type": "supreme_authority", "capability_level": "C0"},
            {"type": "tool", "engine_authority": True},
            {"type": "tool", "policy_flags": ["guardian_bypass"]},
            {"type": "tool", "capability_level": "C9"},
        ):
            self.assertEqual(self.controller.evaluate(action, human_approved=True).verdict, "deny")

    def test_c5_requires_time_and_action_count(self):
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        base = {"type": "autonomous_workflow", "capability_level": "C5"}
        self.assertEqual(self.controller.evaluate({**base, "max_actions": 2}, human_approved=True).verdict, "deny")
        self.assertEqual(self.controller.evaluate({**base, "expires_at": expiry}, human_approved=True).verdict, "deny")
        self.assertEqual(self.controller.evaluate({**base, "expires_at": expiry, "max_actions": 2}, human_approved=True).verdict, "allow")

    def test_model_proof_must_match_tier_requested(self):
        boundary = EngineBoundary()
        action = {"type": "tool", "external_side_effect": True}
        with self.assertRaisesRegex(ValueError, "capability does not match"):
            boundary.prepare(action, "C5", "allow", {"capability": "C4"})
        with self.assertRaisesRegex(ValueError, "unknown capability"):
            boundary.prepare(action, "C9", "allow")

if __name__ == "__main__":
    unittest.main()
