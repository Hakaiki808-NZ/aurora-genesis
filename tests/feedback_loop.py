"""Regression checks for the bounded Genesis cognitive feedback loop."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from genesis import Genesis
from genesis.backends import GeneratorBackend
from genesis.engine_boundary import EngineReceipt
from genesis.feedback_loop import CognitiveFeedbackLoop


def run() -> None:
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "model.sqlite3"
        workspace = Path(td) / "workspace"
        model = Genesis(state_path=db_path, workspace=workspace,
                        enable_ollama=False, profile_id="alpha")
        original = model.feedback_status()
        assert original["turns_observed"] == 0
        assert original["awareness_assessment"]["subjective_consciousness"] == "unknown_no_measurement"
        assert model.self_check()["checks"]["feedback_controller"]

        secret = "PRIVATE_SENTENCE_DO_NOT_LOG_827"
        output = model.respond("What is " + secret + "?")
        assert output
        status = model.feedback_status()
        assert status["turns_observed"] == 1
        assert status["cycles"] >= 1
        events = model.store.db.execute(
            "SELECT payload_json FROM cognitive_feedback_events WHERE profile_id=?",
            ("alpha",),
        ).fetchall()
        assert events and not any(secret in e["payload_json"] for e in events)
        assert all("rationale" not in e["payload_json"] for e in events)

        pred_id = model.feedback.predict("test_event", 0.75)
        try:
            model.feedback.resolve_prediction(pred_id, False, "")
        except ValueError:
            pass
        else:
            raise AssertionError("missing evidence reference accepted")
        # Not independently authenticated: results remain explicitly reported.
        assert model.feedback.resolve_prediction(pred_id, False, "fixture:outcome")
        assert not model.feedback.resolve_prediction(pred_id, True, "fixture:duplicate")
        reported = model.feedback_status()["prediction_tracking"]
        assert reported["resolved_reported"] == 1
        assert reported["reported_brier_score"] == 0.5625
        assert reported["independently_verified"] is False

        for bad in (-0.1, 1.1, float("nan"), float("inf")):
            try:
                model.feedback.predict("invalid", bad)
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe probability accepted")
        try:
            model.feedback.tick(max_events=10000)
        except ValueError:
            pass
        else:
            raise AssertionError("unbounded tick accepted")

        model.feedback.observe_health({"database": True, "model": False})
        one = model.feedback.tick(max_events=1)
        assert one["processed"] == 1 and one["remaining"] >= 1
        model.feedback.tick()
        assert model.feedback_status()["last_health"] == {
            "failed_checks": ["model"], "ok": False
        }

        # No Aurora action is executed: only an already accepted terminal
        # receipt is reflected, and duplicate reconciliation is idempotent.
        model.store.prepare_action("test-action", "tool",
                                   {"type": "tool", "name": "external"},
                                   engine_request_id="req-feedback")
        receipt = EngineReceipt(request_id="req-feedback", receipt_id="receipt-feedback",
                                status="FAILED", error="test only")
        result = model.reconcile_engine_receipt(receipt)
        assert result["accepted"] and not result["idempotent"]
        prior = model.feedback_status()["reported_engine_receipts"]
        assert prior == 1
        duplicate = model.reconcile_engine_receipt(receipt)
        assert duplicate["accepted"] and duplicate["idempotent"]
        assert model.feedback_status()["reported_engine_receipts"] == prior

        # One store may host multiple scoped observers without cross-read.
        other = CognitiveFeedbackLoop(model.store, profile_id="beta")
        assert other.status()["turns_observed"] == 0
        assert other.status()["prediction_tracking"]["total"] == 0
        assert not other.resolve_prediction(pred_id, True, "fixture:cross")
        other.observe_turn({"outcome": "failure"})
        other.tick()
        assert other.status()["reported_failures"] == 1
        assert model.feedback_status()["turns_observed"] == 1

        before = model.feedback_status()
        report = model.feedback_tick()
        assert report["status"]["cycles"] > before["cycles"]
        assert report["status"]["mode"] == "turn_driven_with_external_tick"
        model.close()

        class CaptureBackend(GeneratorBackend):
            name = "capture"
            def __init__(self):
                self.prompts = []
            def available(self):
                return True
            def generate(self, prompt):
                self.prompts.append(prompt)
                return "TEXT_ONLY_TEST_OUTPUT"

        capture = CaptureBackend()
        with Genesis(state_path=Path(td) / "capture.sqlite3",
                     workspace=workspace, backend=capture,
                     enable_ollama=False, profile_id="capture") as active:
            active.respond("Explain a hypothetical astronomy concept.")
            active.respond("Explain another hypothetical astronomy concept.")
            assert len(capture.prompts) >= 2
            assert "Runtime operational feedback" in capture.prompts[-1]
            assert "Previous observed turns: 1" in capture.prompts[-1]
            assert "not factual authority" in capture.prompts[-1]

        reopened = Genesis(state_path=db_path, workspace=workspace,
                           enable_ollama=False, profile_id="alpha")
        after = reopened.feedback_status()
        assert after["turns_observed"] == 1
        assert after["prediction_tracking"]["total"] == 1
        assert after["reported_engine_receipts"] == 1
        reopened.close()
    print("COGNITIVE_FEEDBACK=PASS")


if __name__ == "__main__":
    run()
