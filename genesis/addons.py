"""Genesis add-on catalogue.

The Core record describes built-in Genesis runtime capabilities, not a mutable
knowledge pack. Optional add-ons use the existing data-only knowledge store.
No installed content may become system instructions, tools, weights, policy, or
Aurora execution authority.
"""
from __future__ import annotations

from typing import Any

from .knowledge_modules import KnowledgeModuleError, KnowledgeModuleStore

CORE_ID = "genesis-core"
CORE_FEATURES = (
    "conversation_orchestration",
    "model_memory_interface",
    "source_attributed_knowledge_retrieval",
    "semantic_policy_boundary",
    "guardian_integration",
    "addon_lifecycle",
    "response_traceability",
)


class AddonManager:
    """Core is code-owned, always present, and not stored in uninstallable rows."""

    def __init__(self, modules: KnowledgeModuleStore):
        self.modules = modules

    @staticmethod
    def core() -> dict[str, Any]:
        return {
            "id": CORE_ID,
            "title": "Genesis Core",
            "type": "core",
            "version": "v0.1",
            "installed": True,
            "enabled": True,
            "protected": True,
            "uninstallable": False,
            "distribution": "bundled",
            "capabilities": list(CORE_FEATURES),
            "notes": "Built-in interfaces; does not imply an independently trained model.",
        }

    def list(self) -> list[dict[str, Any]]:
        addons = [self.core()]
        for mod in self.modules.list():
            item = dict(mod)
            item["id"] = item.pop("module_id")
            item["type"] = ("university_curriculum"
                            if item.get("category") == "degree_track" else
                            "language" if item.get("category") == "language" else
                            "knowledge")
            item["installed"] = True
            item["protected"] = False
            item["uninstallable"] = True
            addons.append(item)
        return addons

    def get(self, addon_id: str) -> dict[str, Any]:
        for item in self.list():
            if item["id"] == addon_id:
                return item
        raise KnowledgeModuleError("unknown addon")

    def install(self, package: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
        if not isinstance(package, dict) or package.get("id") == CORE_ID:
            raise KnowledgeModuleError("Genesis Core is reserved and cannot be replaced")
        return self.modules.install(package, replace=replace)

    def set_enabled(self, addon_id: str, enabled: bool) -> dict[str, Any]:
        if addon_id == CORE_ID:
            if not enabled:
                raise KnowledgeModuleError("Genesis Core cannot be disabled")
            return {"id": CORE_ID, "enabled": True, "protected": True}
        return self.modules.set_enabled(addon_id, enabled)

    def uninstall(self, addon_id: str) -> dict[str, Any]:
        if addon_id == CORE_ID:
            raise KnowledgeModuleError("Genesis Core cannot be uninstalled")
        return self.modules.uninstall(addon_id)

    def syllabus(self, addon_id: str) -> dict[str, Any]:
        addon = self.get(addon_id)
        if addon.get("category") != "degree_track":
            raise KnowledgeModuleError("addon is not a university curriculum")
        return {
            "id": addon_id,
            "programme": addon["programme"],
            "credential_issued": False,
            "proficiency_verified": False,
            "notice": ("Educational reference content only. Installing a pack "
                       "is not a university degree, accreditation or proof of competence."),
        }
