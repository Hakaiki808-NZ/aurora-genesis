"""Zero-cost, zero-download tests for Genesis's opt-in Hugging Face adapter."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from genesis import Genesis
from genesis.huggingface_backend import HuggingFaceBackend


class FakeGenerator:
    def __init__(self, answer="An untrusted text proposal.", invalid=False):
        self.calls = []
        self.answer = answer
        self.invalid = invalid

    def __call__(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if self.invalid:
            return [{"generated_text": []}]
        return [{"generated_text": self.answer}]


def run():
    fake = FakeGenerator()
    backend = HuggingFaceBackend(generator=fake)
    assert not backend.available()
    assert backend.generate("Hello") is None and not fake.calls

    active = HuggingFaceBackend(enabled=True, generator=fake, max_calls=2, max_output_tokens=24)
    assert active.available()
    assert active.generate("Describe provenance") == "An untrusted text proposal."
    assert fake.calls[0][1]["max_new_tokens"] == 24
    assert fake.calls[0][1]["return_full_text"] is False
    assert "cannot run tools" in fake.calls[0][0][0]["content"].lower()
    assert active.generate("Again")
    assert active.generate("Third call") is None
    assert len(fake.calls) == 2 and not active.available()

    assert HuggingFaceBackend(enabled=True, generator=FakeGenerator(invalid=True)).generate("Q") is None
    for kwargs in ({"model_id": "unknown/model"}, {"max_calls": 0}, {"max_output_tokens": 999}):
        try:
            HuggingFaceBackend(**kwargs)
            raise AssertionError("Unsafe configuration accepted")
        except ValueError:
            pass

    with tempfile.TemporaryDirectory() as d:
        fake = FakeGenerator("A neural answer.")
        backend = HuggingFaceBackend(enabled=True, generator=fake)
        with patch.dict(os.environ, {"GENESIS_GENERATOR": "none"}):
            with Genesis(state_path=Path(d)/"state.sqlite", workspace=Path(d)/"workspace", backend=backend) as g:
                out = g.respond_with_trace("Explain the purpose of checksum verification.")
                assert out["answer"] == "A neural answer.", out
                assert out["trace"]["chosen_action"] == "neural_answer", out
                before = len(fake.calls)
                assert g.respond("Calculate 7 * 9") == "63"
                assert len(fake.calls) == before  # Deterministic tool path unchanged.

    with tempfile.TemporaryDirectory() as d:
        with patch.dict(os.environ, {
            "GENESIS_GENERATOR": "huggingface",
            "GENESIS_HF_ENABLE": "0",
            "GENESIS_HF_MODEL_ID": "Qwen/Qwen3-0.6B",
        }):
            with Genesis(state_path=Path(d)/"state.sqlite", workspace=Path(d)/"workspace") as g:
                assert g.cognition.backend.name == "huggingface"
                assert not g.cognition.backend.available()
    print("HUGGINGFACE_BACKEND=PASS")


if __name__ == "__main__":
    run()
