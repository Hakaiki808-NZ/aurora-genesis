"""Overlapping C/B/A standards must remain orthogonal to execution authority."""
import unittest
from genesis.standards import StandardsRegistry, _STANDARDS, _BY_ALIAS
from genesis.capabilities import CapabilityController


class StandardsOverlapTests(unittest.TestCase):
    def test_unique_milestones_and_aliases(self):
        self.assertEqual(len(_STANDARDS), 14)
        self.assertEqual(len(_BY_ALIAS), 16)
        self.assertEqual([s.rank for s in _STANDARDS], list(range(14)))

    def test_exact_boundaries(self):
        self.assertTrue(StandardsRegistry.equivalent("C5", "B1"))
        self.assertTrue(StandardsRegistry.equivalent("B5", "A1"))
        self.assertEqual(StandardsRegistry.lookup("C5").canonical, "C5/B1")
        self.assertEqual(StandardsRegistry.lookup("A1").canonical, "B5/A1")
        self.assertEqual(StandardsRegistry.compare("C4", "B1"), -1)
        self.assertEqual(StandardsRegistry.compare("B4", "A1"), -1)
        self.assertEqual(StandardsRegistry.compare("B5", "A1"), 0)
        self.assertEqual(StandardsRegistry.compare("A2", "A1"), 1)

    def test_series_and_hypothetical_boundary(self):
        summary = StandardsRegistry.summary()
        self.assertEqual(summary["minimum_series"], [f"C{i}" for i in range(6)])
        self.assertEqual(summary["achievable_series"], [f"B{i}" for i in range(1, 6)])
        self.assertEqual(summary["frontier_series"], [f"A{i}" for i in range(1, 6)])
        self.assertEqual(summary["hypothetical_labels"], ["A2", "A3", "A4", "A5"])
        self.assertEqual(summary["current_frontier_reference"], "B5/A1")
        self.assertEqual(summary["attainment_state"], "UNVERIFIED")
        self.assertEqual(summary["execution_authority"], "NONE")

    def test_unverified_by_default(self):
        for entry in StandardsRegistry.catalogue():
            self.assertEqual(entry["evidence_state"], "UNVERIFIED")
            requirement = StandardsRegistry.evidence_requirements(entry["aliases"][0])
            self.assertEqual(requirement["status"], "NOT_QUALIFIED")
            self.assertFalse(requirement["grants_engine_privileges"])
            self.assertEqual(len(requirement["required_evidence"]), 4)

    def test_never_accepts_unknown_label(self):
        for value in ("B0", "B6", "A0", "A6", "C6", "E1", "", "c5", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                StandardsRegistry.lookup(value)

    def test_standards_do_not_expand_existing_execution_ceiling(self):
        controller = CapabilityController(granted_level="C1")
        for name in ("B1", "B5", "A1", "A5"):
            standard = StandardsRegistry.lookup(name)
            self.assertGreaterEqual(standard.rank, 5)
            # Standards labels are not execution-policy capabilities.
            self.assertEqual(controller.evaluate({
                "type": "tool", "capability_level": name
            }, human_approved=True).verdict, "deny")

    def test_framework_visible_in_genesis_state(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from genesis import Genesis
        with TemporaryDirectory() as tmp:
            model = Genesis(state_path=Path(tmp)/"model.db",
                            workspace=Path(tmp)/"ws", enable_ollama=False)
            try:
                result = model.state()
                self.assertTrue(result["health"]["checks"]["standards_overlap"])
                self.assertEqual(result["standards_framework"]["milestone_count"], 14)
                self.assertEqual(result["standards_framework"]["attainment_state"], "UNVERIFIED")
            finally:
                model.close()


if __name__ == "__main__":
    unittest.main()
