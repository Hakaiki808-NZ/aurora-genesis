"""No-network tests for the opt-in general-purpose model baseline."""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from genesis import Genesis
from genesis.general_baseline import DEFAULT_MODEL, GeneralOllamaBackend


class OllamaStub:
    def __init__(self):
        self.chat_requests = []
        self.installed = True

    def __call__(self, request, timeout=1):
        if request.full_url.endswith("/api/tags"):
            data = {"models": [{"name": DEFAULT_MODEL}] if self.installed else []}
        elif request.full_url.endswith("/api/chat"):
            payload = json.loads(request.data)
            self.chat_requests.append(payload)
            data = {"message": {"role": "assistant", "content": "Ice is less dense than water."}}
        else:
            raise AssertionError("Unexpected network request")
        return io.BytesIO(json.dumps(data).encode("utf-8"))


def run():
    for invalid in ["https://127.0.0.1:11434", "http://remote.example:11434",
                    "http://127.0.0.1:11434/other"]:
        try:
            GeneralOllamaBackend(base_url=invalid)
            raise AssertionError("Untrusted endpoint accepted")
        except ValueError:
            pass

    try:
        GeneralOllamaBackend(model="not-reviewed:latest")
        raise AssertionError("Unreviewed model accepted")
    except ValueError:
        pass

    stub = OllamaStub()
    with patch("genesis.general_baseline.urllib.request.urlopen", side_effect=stub):
        backend = GeneralOllamaBackend(max_output_tokens=42, max_calls=2)
        assert backend.available()
        assert backend.generate("Why does ice float?") == "Ice is less dense than water."
        assert backend.call_count == 1
        sent = stub.chat_requests[0]
        assert sent["model"] == DEFAULT_MODEL
        assert not sent["think"] and not sent["stream"]
        assert sent["options"]["num_predict"] == 42
        assert [m["role"] for m in sent["messages"]] == ["system", "user"]
        assert "cannot execute tools" in sent["messages"][0]["content"]
        backend.remember("Why does ice float?", "It is less dense.")
        assert backend.generate("And why?")
        followup = stub.chat_requests[-1]["messages"]
        assert [m["role"] for m in followup] == ["system", "user", "assistant", "user"]
        assert backend.generate("Too many") is None
        assert backend.last_error_code == "CALL_LIMIT"
        assert len(stub.chat_requests) == 2
        backend.clear_context()
        assert not backend._history
        assert backend.generate("x" * 6001) is None

        stub.installed = False
        assert not GeneralOllamaBackend().available()
        stub.installed = True

        with tempfile.TemporaryDirectory() as d:
            neural = GeneralOllamaBackend(max_calls=10)
            with Genesis(state_path=Path(d) / "state.db", workspace=Path(d) / "ws", backend=neural) as model:
                response = model.respond_with_trace("Explain why ice floats on water.")
                assert response["trace"]["chosen_action"] == "neural_answer", response
                assert response["answer"] == "Ice is less dense than water.", response
                n = len(stub.chat_requests)
                assert model.respond("Calculate 7 * 9") == "63"
                assert len(stub.chat_requests) == n
                assert model.self_check()["ok"]

    print("GENERAL_BASELINE=PASS (mock transport only, real model not tested)")


if __name__ == "__main__":
    run()
