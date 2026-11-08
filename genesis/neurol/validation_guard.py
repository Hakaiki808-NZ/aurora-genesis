"""Validation-only checkpoint guard for experimental Neurol training.

A rising validation curve can be unavoidable on small data. This guard prevents
deteriorating steps from replacing the best recorded weights. It does not
claim that the validation metric itself can be forced to improve monotonically.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class ValidationGuard:
    initial: float
    patience: int = 5
    min_delta: float = 1e-4
    max_regression: float = 0.05
    regression_patience: int = 2
    best: float = 0.0
    best_step: int = 0
    stalls: int = 0
    regressions: int = 0
    stop_reason: str | None = None

    def __post_init__(self):
        if not isinstance(self.initial, (int, float)) or not math.isfinite(self.initial):
            raise ValueError("initial validation loss must be finite")
        if type(self.patience) is not int or self.patience < 1:
            raise ValueError("patience must be a positive integer")
        if type(self.regression_patience) is not int or self.regression_patience < 1:
            raise ValueError("regression_patience must be a positive integer")
        if not 0 <= self.min_delta < 1 or not 0 <= self.max_regression <= 1:
            raise ValueError("invalid checkpoint guard threshold")
        self.best = float(self.initial)

    def observe(self, step: int, validation: float) -> bool:
        """Return True iff validation strictly improves the saved best weights.

        Stop decisions are expressed through `stop_reason`. Never inspects test.
        """
        if self.stop_reason is not None:
            raise RuntimeError("validation guard already stopped")
        if type(step) is not int or step < 1:
            raise ValueError("step must be a positive integer")
        if not isinstance(validation, (int, float)) or not math.isfinite(validation):
            self.stop_reason = "non_finite_validation"
            return False
        if validation < self.best - self.min_delta:
            self.best = float(validation)
            self.best_step = step
            self.stalls = self.regressions = 0
            return True
        self.stalls += 1
        self.regressions = (
            self.regressions + 1
            if validation > self.best * (1 + self.max_regression)
            else 0
        )
        if self.regressions >= self.regression_patience:
            self.stop_reason = "validation_regression"
        elif self.stalls >= self.patience:
            self.stop_reason = "early_stopping"
        return False
