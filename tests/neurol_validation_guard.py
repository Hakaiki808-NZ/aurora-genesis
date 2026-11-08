"""Standard-library tests for Neurol validation-only checkpoint protection."""
import unittest
from genesis.neurol.validation_guard import ValidationGuard


class ValidationGuardTests(unittest.TestCase):
    def test_best_is_never_overwritten_by_regression(self):
        guard = ValidationGuard(initial=3., patience=5)
        self.assertTrue(guard.observe(40, 2.))
        self.assertEqual(guard.best_step, 40)
        self.assertFalse(guard.observe(80, 2.11))
        self.assertFalse(guard.observe(120, 2.12))
        self.assertEqual(guard.stop_reason, "validation_regression")
        self.assertEqual(guard.best_step, 40)
        self.assertEqual(guard.best, 2.)

    def test_isolated_noise_does_not_stop_improving_training(self):
        guard = ValidationGuard(initial=3.)
        self.assertTrue(guard.observe(40, 2.))
        self.assertFalse(guard.observe(80, 2.12))
        self.assertFalse(guard.observe(120, 2.01))
        self.assertIsNone(guard.stop_reason)
        self.assertTrue(guard.observe(160, 1.95))
        self.assertEqual(guard.regressions, 0)
        self.assertEqual(guard.stalls, 0)

    def test_plateau_stops_and_nonfinite_fails_closed(self):
        guard = ValidationGuard(initial=2., patience=2)
        self.assertFalse(guard.observe(40, 2.))
        self.assertFalse(guard.observe(80, 2.))
        self.assertEqual(guard.stop_reason, "early_stopping")
        with self.assertRaises(RuntimeError):
            guard.observe(120, 1.)
        guard = ValidationGuard(initial=2.)
        self.assertFalse(guard.observe(40, float("nan")))
        self.assertEqual(guard.stop_reason, "non_finite_validation")

    def test_bad_configuration_rejected(self):
        for kwargs in ({"initial":float("inf")},
                       {"initial":2., "patience":0},
                       {"initial":2., "regression_patience":0},
                       {"initial":2., "max_regression":-0.1}):
            with self.assertRaises(ValueError):
                ValidationGuard(**kwargs)


if __name__ == "__main__":
    unittest.main()
