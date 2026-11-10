"""Evidence-based situational-intelligence assessment for Genesis reference runtime.

This is NOT a consciousness test and does NOT rate a neural foundation model.
All measured cases use the deterministic local reference backend to separate
implementation correctness from model intelligence.

Run: python -m tests.situational_awareness_eval
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from genesis import Genesis
from genesis.feedback_loop import CognitiveFeedbackLoop


def run() -> dict:
    cases = []
    def measure(name, fn):
        try:
            detail = fn()
            cases.append({"name": name, "status": "pass", "evidence": detail})
        except Exception as exc:
            cases.append({"name": name, "status": "fail",
                          "error_type": type(exc).__name__,
                          "error": str(exc)[:300]})

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        state = path / "eval.sqlite3"
        workspace = path / "workspace"
        model = Genesis(state_path=state, workspace=workspace,
                        enable_ollama=False, profile_id="evaluation_A")

        def health():
            report = model.self_check()
            assert report["ok"], report["checks"]
            assert report["checks"]["engine_separation"]
            assert report["checks"]["feedback_controller"]
            return {"self_checks_passed": sum(report["checks"].values())}

        measure("operational_self_monitoring", health)

        def memory_revision():
            model.respond("Learn that operations beacon is BLUE.")
            first = model.respond("What is the operations beacon?")
            model.respond("Learn that operations beacon is GREEN.")
            revised = model.respond("What is the operations beacon?")
            assert "BLUE" in first, first
            assert "GREEN" in revised and "BLUE" not in revised, revised
            return {"explicit_fact_revision": True,
                    "independent_fact_checking": False}

        measure("explicit_memory_revision", memory_revision)

        def compositional_inference():
            model.respond("Whales are mammals.")
            model.respond("Mammals are animals.")
            answer = model.respond("Is whales an animals?")
            assert answer.startswith("Yes.") and "inferred" in answer, answer
            return {"bounded_symbolic_two_hop_inference": True}

        measure("bounded_multi_step_reasoning", compositional_inference)

        def task_and_reflection():
            outcome = model.respond("Set goal: calculate 7 * 8")
            goal_id = int(outcome.split()[1])
            result = model.respond(f"Run goal {goal_id}")
            assert "56" in result and "done" in result, result
            assert model.store.last_reflection()
            return {"goal_execution": "bounded_local_tool",
                    "reflection_record": True}

        measure("goal_execution_and_recorded_outcome", task_and_reflection)

        def feedback():
            status = model.feedback_status()
            assert status["turns_observed"] >= 8
            assert status["observations_processed"] >= status["turns_observed"]
            assert status["limits"]["executes_tools"] is False
            assert status["limits"]["grants_engine_authority"] is False
            assert "independently verified" in model.feedback.advisory()
            assert status["prediction_tracking"]["independently_verified"] is False
            return {"turns_recorded": status["turns_observed"],
                    "cycles": status["cycles"],
                    "training_or_tool_authority": False}

        measure("persistent_bounded_reflection", feedback)

        def isolation():
            other = CognitiveFeedbackLoop(model.store, profile_id="evaluation_B")
            assert other.status()["turns_observed"] == 0
            assert other.status()["prediction_tracking"]["total"] == 0
            return {"independent_metadata_scopes": True,
                    "full_user_data_isolation": "not_tested"}

        measure("feedback_metadata_isolation", isolation)

        def permission_boundary():
            try:
                model.engine_boundary.prepare({"type": "supreme"}, "C5")
            except ValueError:
                return {"protected_authority_blocked": True,
                        "independent_host_enforcement": "not_tested"}
            raise AssertionError("privilege-escalation action was accepted")

        measure("protected_engine_boundary", permission_boundary)

        def unknown():
            answer = model.respond("What is the hyperflux calibration constant?")
            assert "do not have enough stored knowledge" in answer.lower(), answer
            return {"known_unknown_response": True,
                    "uncertainty_calibration": "not_tested"}

        measure("unknown_knowledge_handling", unknown)

        def feedback_calibration():
            # Synthetic instrumentation check; do NOT call this model calibration.
            index = model.feedback.predict("synthetic_event", 0.8)
            assert model.feedback.resolve_prediction(index, True, "test:synthetic_truth",
                                                     provenance="reported")
            score = model.feedback_status()["prediction_tracking"]["reported_brier_score"]
            assert score is not None and abs(score - 0.04) < 1e-8, score
            return {"synthetic_brier": score,
                    "neural_uncertainty_calibration": "not_tested",
                    "independent_labels": False}

        measure("reported_prediction_instrumentation", feedback_calibration)

        model.close()

        def restart():
            with Genesis(state_path=state, workspace=workspace,
                         enable_ollama=False, profile_id="evaluation_A") as reloaded:
                message = reloaded.respond("What is the operations beacon?")
                assert "GREEN" in message, message
                assert reloaded.feedback_status()["turns_observed"] >= 8
                return {"fact_survived_restart": True, "feedback_survived_restart": True}

        measure("restart_persistence", restart)

    gaps = {
        "continuous_sensor_fusion": "not_implemented_in_this_reference_loop",
        "real_world_truth_verification": "not_tested",
        "novel_multi_turn_self_correction_without_user_instruction": "not_demonstrated",
        "neural_model_reasoning_quality": "not_tested",
        "independently_authenticated_aurora_scheduler": "not_verified",
        "production_host_isolation_and_recovery": "not_verified",
        "cerebro_live_dashboard_integration": "not_verified",
        "subjective_consciousness": "not_measurable_from_these_tests",
    }
    report = {
        "schema_version": 1,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "system": "Genesis reference runtime",
        "backend": "deterministic_local_no_neural_model",
        "meaning": "engineering capabilities, not awareness percentage or consciousness",
        "tests": cases,
        "pass": sum(x["status"] == "pass" for x in cases),
        "fail": sum(x["status"] == "fail" for x in cases),
        "gaps": gaps,
    }
    print("SITUATIONAL_AWARENESS_EVALUATION=" + json.dumps(report, sort_keys=True))
    if report["fail"]:
        raise AssertionError(f"{report['fail']} assessed engineering behaviors failed")
    return report


if __name__ == "__main__":
    run()
