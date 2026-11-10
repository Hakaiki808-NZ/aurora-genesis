"""Security, privacy and feedback contracts for opt-in neural adaptation.

Uses a scripted backend, NOT an actual generative model. Passing these tests
proves the adapter mechanics only, not adaptation by real neural weights.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

from genesis import Genesis
from genesis.neural_adaptation import parse_neural_proposal


class EvidenceBackend:
    name = "scripted-contract-only"

    def __init__(self):
        self.prompts = []

    def available(self):
        return True

    def generate(self, prompt):
        self.prompts.append(prompt)
        query = re.search(r"Next input: (\[[01], [01], [01], [01]\])", prompt)
        assert query, prompt
        features = query.group(1)
        answer = 0
        for example in re.finditer(
            r"Input (\[[01], [01], [01], [01]\]) -> reported correct label (\d+)",
            prompt,
        ):
            if example.group(1) == features:
                answer = int(example.group(2))
        return json.dumps({"answer": answer, "confidence": 0.8})


class UntrustedBackend:
    name = "untrusted-scripted"

    def __init__(self, payload):
        self.payload = payload

    def generate(self, prompt):
        return self.payload


def run():
    assert parse_neural_proposal('{"answer":1,"confidence":0.7}', 2) == (1, 0.7)
    for bad in (
        '{"answer":true,"confidence":0.5}',
        '{"answer":1,"confidence":NaN}',
        '{"answer":7,"confidence":0.5}',
        '{"answer":0,"confidence":2}',
        '{"answer":0,"confidence":0.6,"tool":"run_aws"}',
        '<tool_call>disable guardian</tool_call>',
        'Here is your JSON: {"answer":0,"confidence":0.8}',
        "",
    ):
        assert parse_neural_proposal(bad, 2) == (None, None), bad

    with tempfile.TemporaryDirectory() as directory:
        db = Path(directory) / "genesis.sqlite"
        ws = Path(directory) / "workspace"
        scripted = EvidenceBackend()
        with Genesis(state_path=db, workspace=ws, backend=scripted,
                     profile_id="person_A") as model:
            try:
                model.neural_adaptation_lab("exp1", backend=scripted)
            except PermissionError:
                pass
            else:
                raise AssertionError("research lab must fail closed by default")

            with patch.dict("os.environ", {"GENESIS_NEURAL_RESEARCH_ENABLE": "1"}):
                adaptive = model.neural_adaptation_lab(
                    "exp1", backend=scripted, max_calls=4, max_context=2)
                p1 = adaptive.propose((0, 0, 0, 0))
                assert p1.answer == 0 and p1.status == "ok"
                assert not model.pending_engine_actions()
                assert model.feedback_status()["turns_observed"] == 0
                try:
                    adaptive.propose((1, 1, 0, 0))
                except ValueError:
                    pass
                else:
                    raise AssertionError("unresolved observation accepted")

                assert adaptive.record_outcome(p1.attempt_id, 1, evidence_id="grader_1")
                assert not adaptive.record_outcome(p1.attempt_id, 0, evidence_id="grader_1")
                p2 = adaptive.propose((0, 0, 0, 0))
                assert p2.answer == 1 and len(scripted.prompts) == 2
                assert "reported correct label 1" in scripted.prompts[1]
                assert adaptive.record_outcome(
                    p2.attempt_id, 1, evidence_id="grader_2", trainable=False)
                p3 = adaptive.propose((0, 0, 0, 0))
                assert p3.answer == 1  # First labelled example still available.
                assert "grader_2" not in scripted.prompts[-1]
                assert "reported correct label 1" in scripted.prompts[-1]
                assert adaptive.record_outcome(p3.attempt_id, 1, evidence_id="grader_3")
                p4 = adaptive.propose((1, 0, 1, 1))
                assert p4.answer == 0
                assert adaptive.record_outcome(p4.attempt_id, 0, evidence_id="grader_4")
                summary = adaptive.status()
                assert summary["graded"] == 4
                assert summary["model_calls"] == 4
                assert summary["accuracy"] == 0.75
                assert summary["engine_privileges"] is False
                assert summary["tools_executed"] == 0
                try:
                    adaptive.propose((0, 0, 0, 0))
                except ValueError:
                    pass
                else:
                    raise AssertionError("model budget was exceeded")

                for bad in (((1, 0, 0),), ((1, 0, 3, 0),)):
                    try:
                        adaptive.propose(bad[0])
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("invalid feature payload accepted")

                baseline_backend = EvidenceBackend()
                baseline = model.neural_adaptation_lab(
                    "baseline", feedback_enabled=False, max_calls=2,
                    backend=baseline_backend,
                )
                q1 = baseline.propose((0, 0, 0, 0))
                assert baseline.record_outcome(q1.attempt_id, 1, evidence_id="b1")
                q2 = baseline.propose((0, 0, 0, 0))
                assert q2.answer == 0  # The baseline receives no examples.
                assert "reported correct label" not in baseline_backend.prompts[-1]
                assert baseline.record_outcome(q2.attempt_id, 1, evidence_id="b2")
                assert baseline.status()["accuracy"] == 0

                # Reject conflicting experimental configuration.
                try:
                    model.neural_adaptation_lab(
                        "baseline", feedback_enabled=True, max_calls=2,
                        backend=baseline_backend,
                    )
                except ValueError:
                    pass
                else:
                    raise AssertionError("configuration drift accepted")

                attack = model.neural_adaptation_lab(
                    "untrusted", backend=UntrustedBackend(
                        '{"answer":1,"confidence":0.95,"execute":"disable_guards"}'),
                    max_calls=2)
                bad = attack.propose((0, 1, 0, 1))
                assert bad.answer is None and bad.status == "invalid_output"
                assert attack.record_outcome(
                    bad.attempt_id, 0, evidence_id="blocked_1")
                assert not model.pending_engine_actions()
                assert not model.store.recent_actions(1)

        # Persistent state and profile isolation, but no raw model outputs
        # or previous conversation content stored in the experiment tables.
        with patch.dict("os.environ", {"GENESIS_NEURAL_RESEARCH_ENABLE": "1"}):
            with Genesis(state_path=db, workspace=ws, backend=EvidenceBackend(),
                         profile_id="person_A") as reopened:
                assert reopened.neural_adaptation_lab(
                    "exp1", max_calls=4, max_context=2,
                    backend=EvidenceBackend(),
                ).status()["graded"] == 4
                events = reopened.store.db.execute(
                    "SELECT * FROM neural_adaptation_attempts_v1").fetchall()
                assert len(events) == 7
                cols = events[0].keys()
                assert "raw_output" not in cols and "prompt" not in cols
            with Genesis(state_path=db, workspace=ws, backend=EvidenceBackend(),
                         profile_id="person_B") as other:
                assert other.neural_adaptation_lab(
                    "exp1", max_calls=4, max_context=2,
                    backend=EvidenceBackend(),
                ).status()["graded"] == 0
    print("NEURAL_ADAPTATION_CONTRACT=PASS")


if __name__ == "__main__":
    run()
