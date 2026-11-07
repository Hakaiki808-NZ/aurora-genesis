"""Regression tests for Genesis Core and university-level add-on packs."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from genesis import Genesis
from genesis.knowledge_modules import KnowledgeModuleError

ROOT = Path(__file__).resolve().parent.parent
DEGREE = json.loads((ROOT / "examples" / "addons" / "physics-bsc-starter.json").read_text())
CS = json.loads((ROOT / "examples" / "addons" / "computer-science-bsc-starter.json").read_text())


def rejected(fn):
    try:
        fn()
    except KnowledgeModuleError:
        return
    raise AssertionError("expected KnowledgeModuleError")


def run():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state.sqlite3"
        workspace = Path(tmp) / "workspace"
        with Genesis(state_path=state, workspace=workspace, enable_ollama=False) as g:
            # The built-in Core is always present without installing a row.
            addons = g.list_addons()
            assert len(addons) == 1 and addons[0]["id"] == "genesis-core", addons
            assert addons[0]["protected"] and addons[0]["enabled"]
            assert not addons[0]["uninstallable"]
            assert g.list_knowledge_modules() == []

            rejected(lambda: g.uninstall_addon("genesis-core"))
            rejected(lambda: g.uninstall_knowledge_module("genesis-core"))
            rejected(lambda: g.enable_knowledge_module("genesis-core", False))
            rejected(lambda: g.set_addon_enabled("genesis-core", False))
            rejected(lambda: g.install_addon({**DEGREE, "id": "genesis-core"}))
            rejected(lambda: g.install_knowledge_module({**DEGREE, "id": "genesis-core"}))
            assert g.list_addons()[0]["enabled"]

            assert g.install_addon(DEGREE)["status"] == "installed"
            assert g.install_addon(CS)["status"] == "installed"
            addons = g.list_addons()
            assert len(addons) == 3 and sum(a["protected"] for a in addons) == 1, addons
            for addon in addons[1:]:
                assert addon["type"] == "university_curriculum"
                assert addon["programme"]["level"] == "bachelor"
                assert addon["uninstallable"]
            syllabus = g.addon_syllabus("physics-bsc-starter")
            assert len(syllabus["programme"]["units"]) == 6
            assert not syllabus["credential_issued"]
            assert not syllabus["proficiency_verified"]
            hits = g.search_knowledge_modules("electric fields Gauss law")
            assert hits and hits[0]["module_id"] == "physics-bsc-starter", hits
            ans = g.respond_with_trace("Explain electric fields and Gauss law")
            assert ans["trace"]["chosen_action"] == "module_knowledge", ans
            assert "Gauss" in ans["answer"] and "physics-bsc-starter" in ans["answer"]
            assert g.search_knowledge_modules("relational databases transactions")

            g.set_addon_enabled("physics-bsc-starter", False)
            assert not g.search_knowledge_modules("electric fields Gauss law")
            assert g.list_addons()[0]["enabled"]  # Core cannot be affected.
            g.set_addon_enabled("physics-bsc-starter", True)

            bad = copy.deepcopy(DEGREE)
            bad["programme"]["units"][0]["chapter_ids"].append("missing-chapter")
            rejected(lambda: g.install_addon(bad, replace=True))
            bad = copy.deepcopy(DEGREE)
            bad["programme"]["units"][0]["year"] = 9
            rejected(lambda: g.install_addon(bad, replace=True))
            bad = copy.deepcopy(DEGREE)
            bad["run_python"] = "print('should never execute')"
            rejected(lambda: g.install_addon(bad, replace=True))
            bad = copy.deepcopy(CS)
            bad["category"] = "knowledge"
            rejected(lambda: g.install_addon(bad, replace=True))

        # Persisted curriculum works after restart; Core is still present.
        with Genesis(state_path=state, workspace=workspace, enable_ollama=False) as g:
            assert len(g.list_addons()) == 3
            assert g.addon_syllabus("physics-bsc-starter")["programme"]["units"]
            assert g.uninstall_addon("physics-bsc-starter")["status"] == "uninstalled"
            assert len(g.list_addons()) == 2
            rejected(lambda: g.uninstall_addon("genesis-core"))

    from genesis.api import app
    paths = {route.path for route in app.routes}
    assert {"/addons", "/addons/{addon_id}/syllabus",
            "/addons/{addon_id}/status", "/addons/{addon_id}"}.issubset(paths)
    print("ADDONS_CORE_DEGREE_TRACK=PASS")


if __name__ == "__main__":
    run()
