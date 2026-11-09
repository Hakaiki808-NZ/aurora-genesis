"""Regression checks for the temporary Kyro expansion gate."""
import unittest
from tools.check_kyro_freeze import freeze_violation

class FreezeTest(unittest.TestCase):
    def test_backend_changes_are_untouched(self):
        self.assertIsNone(freeze_violation(["genesis/api.py"], "feat(genesis): health", ""))

    def test_new_kyro_features_rejected(self):
        self.assertIsNotNone(freeze_violation(["web/kyro/v3/new-suite.js"], "feat(kyro): add suite", ""))

    def test_maintenance_needs_exception(self):
        self.assertIsNotNone(freeze_violation(["cloud/public-beta-web/app.js"], "fix(kyro): repair login", ""))

    def test_maintenance_with_explicit_exception(self):
        self.assertIsNone(freeze_violation(["cloud/public-beta-web/app.js"], "fix(kyro): repair login", "Kyro-freeze-exception: stabilization"))

    def test_marker_does_not_allow_features(self):
        self.assertIsNotNone(freeze_violation(["cloud/public-site-v1/index.html"], "feat: redesign", "Kyro-freeze-exception: stabilization"))

if __name__ == "__main__":
    unittest.main()
