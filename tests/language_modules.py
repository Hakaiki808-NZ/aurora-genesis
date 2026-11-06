"""Free language pack integration and Unicode retrieval tests."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from genesis import Genesis
from genesis.knowledge_modules import KnowledgeModuleError, _terms

ROOT = Path(__file__).resolve().parent.parent
PACKS = [
    json.loads((ROOT / "examples" / "modules" / f"{name}.json").read_text(encoding="utf-8"))
    for name in ("spanish-basics", "te-reo-maori-basics")
]


def rejects(call):
    try:
        call()
    except KnowledgeModuleError:
        return
    raise AssertionError("invalid module unexpectedly accepted")


def run():
    assert "tēnā" in _terms("Tēnā koe")
    assert "kōrua" in _terms("Tēnā kōrua")
    assert "gracias" in _terms("Muchas gracias")
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "state.sqlite3"
        ws = Path(tmp) / "workspace"
        with Genesis(state_path=db, workspace=ws, enable_ollama=False) as model:
            for pack in PACKS:
                assert model.install_knowledge_module(pack)["status"] == "installed"
            catalogue = {m["module_id"]: m for m in model.list_knowledge_modules()}
            assert catalogue["spanish-basics"]["category"] == "language"
            assert catalogue["spanish-basics"]["language_tag"] == "es"
            assert catalogue["te-reo-maori-basics"]["language_tag"] == "mi"
            assert all(m["is_free"] and m["distribution"] == "open" for m in catalogue.values())

            spanish = model.search_knowledge_modules("Spanish gracias por favor")
            assert spanish and spanish[0]["module_id"] == "spanish-basics"
            assert spanish[0]["is_free"] and spanish[0]["language_tag"] == "es"
            maori = model.search_knowledge_modules("te reo Māori greeting tēnā koe")
            assert maori and maori[0]["module_id"] == "te-reo-maori-basics", maori
            macron = model.search_knowledge_modules("tēnā kōrua")
            assert macron and macron[0]["module_id"] == "te-reo-maori-basics", macron
            assert "kōrua" in macron[0]["excerpt"]
            answer = model.respond_with_trace("Explain te reo Māori greeting tēnā koe")
            assert answer["trace"]["chosen_action"] == "module_knowledge", answer
            assert "te-reo-maori-basics" in answer["answer"]

            invalid = copy.deepcopy(PACKS[0])
            invalid.pop("language_tag")
            rejects(lambda: model.install_knowledge_module(invalid))
            invalid = copy.deepcopy(PACKS[0])
            invalid["language_tag"] = "../wrong"
            rejects(lambda: model.install_knowledge_module(invalid))
            invalid = copy.deepcopy(PACKS[0])
            invalid["category"] = "executable"
            rejects(lambda: model.install_knowledge_module(invalid))
            invalid = copy.deepcopy(PACKS[0])
            invalid["category"] = ["language"]
            rejects(lambda: model.install_knowledge_module(invalid))
            invalid = copy.deepcopy(PACKS[0])
            invalid["category"] = "knowledge"
            rejects(lambda: model.install_knowledge_module(invalid))

            model.enable_knowledge_module("te-reo-maori-basics", False)
            assert not model.search_knowledge_modules("tēnā kōrua")
            model.enable_knowledge_module("te-reo-maori-basics", True)
            assert model.search_knowledge_modules("tēnā kōrua")

        with Genesis(state_path=db, workspace=ws, enable_ollama=False) as model:
            assert model.search_knowledge_modules("tēnā kōrua")
            assert model.list_knowledge_modules()[1]["category"] == "language"
            assert model.uninstall_knowledge_module("te-reo-maori-basics")["status"] == "uninstalled"
            assert not model.search_knowledge_modules("tēnā kōrua")
            assert model.search_knowledge_modules("Spanish gracias por favor")

    print("LANGUAGE_MODULES=PASS")


if __name__ == "__main__":
    run()
