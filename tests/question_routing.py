"""An explanation request is not an assertion, with or without a question mark."""
from __future__ import annotations

import tempfile
from pathlib import Path

from genesis import Genesis


def run():
    with tempfile.TemporaryDirectory() as temp:
        with Genesis(
            state_path=Path(temp) / "state.sqlite3",
            workspace=Path(temp) / "workspace",
            enable_ollama=False,
        ) as model:
            for question in (
                "Explain why checksums are useful when transferring files.",
                "How are checksums useful when transferring files",
                "What is encryption",
                "Describe why encryption is useful for communication.",
            ):
                result = model.respond_with_trace(question)
                assert result["trace"]["chosen_action"] != "acknowledge_learning", result
            assert model.store.get_fact("Explain why checksums") is None
            learned = model.respond_with_trace("Learn that protocol codename is ORCHID.")
            assert learned["trace"]["chosen_action"] == "acknowledge_learning"
            assert model.store.get_fact("protocol codename") is not None
    print("QUESTION_ROUTING=PASS")


if __name__ == "__main__":
    run()
