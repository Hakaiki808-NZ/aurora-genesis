"""No-cloud-cost checks for privately hosted, open-weight Ollama inference."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from genesis.backends import OllamaBackend
from genesis import Genesis


class FakeHTTP:
    def __init__(self, content):
        self.content = json.dumps(content).encode("utf-8")

    def read(self, limit=-1):
        return self.content[:limit] if limit >= 0 else self.content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def run():
    calls = []
    model_installed = False

    def fake_open(request, timeout=0):
        nonlocal model_installed
        url = request.full_url
        calls.append((url, timeout, request.data))
        if url.endswith("/api/tags"):
            names = [{"name": "qwen2.5-coder:1.5b"}] if model_installed else []
            return FakeHTTP({"models": names})
        if url.endswith("/api/generate"):
            payload = json.loads(request.data)
            assert payload["model"] == "qwen2.5-coder:1.5b"
            assert payload["stream"] is False
            assert payload["options"]["num_predict"] == 32
            return FakeHTTP({"response": "A neural response."})
        raise AssertionError(url)

    with patch("genesis.backends.urllib.request.urlopen", side_effect=fake_open), patch("genesis.backends.time.monotonic", side_effect=[10.0, 11.0, 17.0, 18.0]):
        backend = OllamaBackend(
            base_url="http://ollama:11434", max_output_tokens=32,
            generation_timeout=60.0,
        )
        assert backend.available() is False
        model_installed = True
        assert backend.available() is False  # 5-second negative cache
        assert backend.available() is True  # Model appears without restarting Genesis
        assert backend.generate("Explain why tests matter") == "A neural response."
        assert any(c[0].endswith("/api/generate") for c in calls)

    with patch("genesis.backends.urllib.request.urlopen", side_effect=lambda req, timeout=0: FakeHTTP(
        {"models": [{"name": "qwen2.5-coder:1.5b"}]} if req.full_url.endswith("/api/tags") else {"response": "From self-hosted model"}
    )):
        # Demonstrate Genesis cognition can consume an OSS backend.
        with tempfile.TemporaryDirectory() as location:
            backend = OllamaBackend(max_output_tokens=32)
            with Genesis(state_path=Path(location) / "state.db", workspace=Path(location) / "workspace", backend=backend) as genesis:
                response = genesis.respond_with_trace("Explain the purpose of a checksum.")
                assert response["answer"] == "From self-hosted model", response
                assert response["trace"]["chosen_action"] == "neural_answer", response
                assert genesis.respond("Calculate 7 * 9") == "63"

    for options in ({"max_output_tokens": 0}, {"generation_timeout": 1000}, {"base_url": "invalid://foo"}):
        try:
            OllamaBackend(**options)
            raise AssertionError("Unsafe/invalid backend configuration accepted")
        except ValueError:
            pass
    print("OSS_BACKEND=PASS")


if __name__ == "__main__":
    run()
