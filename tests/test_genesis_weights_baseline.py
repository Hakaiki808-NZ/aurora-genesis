"""Smoke checks for the Genesis CPU-only training demonstration."""
import importlib.util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "genesis" / "training" / "aws_lambda_baseline.py"
spec = importlib.util.spec_from_file_location("genesis_baseline", module_path)
trainer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trainer)


def test_training_decreases_validation_loss():
    m = trainer.train()
    assert m["architecture"]["parameter_count"] > 0
    assert m["training"]["history"][-1]["validation_cross_entropy"] < m["training"]["initial_validation_loss"]


def test_offline_lambda_no_save():
    response = trainer.lambda_handler({"save": False}, None)
    assert response["ok"] and response["trained"]
    assert response["checkpoint_saved"] is False
    assert response["checkpoint_bytes"] > 0
