"""No-AWS-cost acceptance tests for Genesis's text-only neural adapter."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from genesis import Genesis
from genesis.bedrock_backend import BedrockBackend


class FakeConverse:
    def __init__(self, answer="The answer is 42.", stop="end_turn", error=None):
        self.calls = []
        self.answer = answer
        self.stop = stop
        self.error = error

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return {"stopReason": self.stop, "output": {"message": {"content": [{"text": self.answer}]}}}


def run():
    # The CloudFormation inline Lambda and source module must never drift.
    root = Path(__file__).resolve().parents[1]
    template = json.loads((root / "cloud/genesis-neural-gate/template.json").read_text(encoding="utf-8"))
    gateway = template["Resources"]["GatewayFunction"]["Properties"]
    assert gateway["Code"]["ZipFile"] == (root / "cloud/genesis-neural-gate/index.py").read_text(encoding="utf-8")
    assert gateway["Environment"]["Variables"]["GENESIS_NEURAL_MODEL_ID"] == "openai.gpt-oss-120b-1:0"
    assert template["Parameters"]["Enabled"]["Default"] == "0"
    # Feature gate is closed by default, even when a model ID is provided.
    mock = FakeConverse()
    backend = BedrockBackend(client=mock)
    assert not backend.available()
    assert backend.generate("Hello") is None and not mock.calls

    active = BedrockBackend(client=mock, enabled=True, max_output_tokens=24, max_calls=2)
    assert active.available()
    assert active.generate("What is 6 times 7?") == "The answer is 42."
    assert mock.calls[0]["modelId"] == "openai.gpt-oss-120b-1:0"
    assert mock.calls[0]["inferenceConfig"]["maxTokens"] == 24
    assert not any("toolConfig" in c for c in mock.calls)
    assert active.generate("Hello again")
    assert active.generate("Third call") is None
    assert len(mock.calls) == 2 and not active.available()

    assert BedrockBackend(enabled=True, client=FakeConverse(stop="content_filtered")).generate("test") is None
    assert BedrockBackend(enabled=True, client=FakeConverse(error=RuntimeError("secret"))).generate("test") is None
    assert BedrockBackend(enabled=True, client=FakeConverse(answer="")).generate("test") is None
    try:
        BedrockBackend(enabled=True, max_output_tokens=50000)
        raise AssertionError("unbounded tokens accepted")
    except ValueError:
        pass

    with tempfile.TemporaryDirectory() as d:
        client=FakeConverse("Neural backend answer")
        real=BedrockBackend(enabled=True, client=client)
        with patch.dict(os.environ, {"GENESIS_GENERATOR":"none"}):
            with Genesis(state_path=Path(d)/"genesis.sqlite", workspace=Path(d)/"workspace", backend=real) as genesis:
                result=genesis.respond_with_trace("Explain the purpose of a checksum.")
                assert result["answer"] == "Neural backend answer", result
                assert result["trace"]["chosen_action"] == "neural_answer", result
                assert client.calls and "cannot run tools" in client.calls[0]["messages"][0]["content"][0]["text"].lower()
                before=len(client.calls)
                assert genesis.respond("Calculate 7 * 9") == "63"
                assert len(client.calls)==before  # Tool path remains deterministic.
                genesis.respond("Learn that architecture codename is IRIS.")
                assert "IRIS" in genesis.respond("What is architecture codename?")
                assert len(client.calls)==before  # Exact recall does not require external inference.
                stats=genesis.state()["stats"]
                # Do not label generated answers as validated training samples.
                assert stats.get("training_examples",0) < stats.get("decisions",0)

    with tempfile.TemporaryDirectory() as d:
        # Explicit mode still needs the separate enable flag.
        with patch.dict(os.environ,{"GENESIS_GENERATOR":"bedrock","GENESIS_BEDROCK_ENABLE":"0"}):
            with Genesis(state_path=Path(d)/"state.db",workspace=Path(d)/"ws") as genesis:
                assert genesis.cognition.backend.name=="bedrock"
                assert not genesis.cognition.backend.available()
                assert "do not have enough stored knowledge" in genesis.respond("What is hyperflux?").lower()

    print("NEURAL_BACKEND=PASS")


if __name__ == "__main__":
    run()
