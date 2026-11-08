from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

_LEVELS = {f"C{i}": i for i in range(6)}
PERMANENTLY_DENIED = {"engine_authority","supreme_authority","guardian_bypass","constitution_bypass","constitution_modify","policy_self_exception","engine_handler_install"}

@dataclass(frozen=True)
class CapabilityDecision:
    verdict: str
    required_level: str
    granted_level: str
    reason: str
    needs_human_approval: bool = False
    def record(self) -> dict[str, Any]: return asdict(self)

class CapabilityController:
    def __init__(self, granted_level: str = "C4"):
        if granted_level not in _LEVELS: raise ValueError("invalid capability level")
        self.granted_level = granted_level

    @staticmethod
    def _required(action: dict[str, Any] | None) -> str:
        a = action or {}
        flags = set(a.get("policy_flags", []) or [])
        if (
            flags & PERMANENTLY_DENIED or a.get("type") in PERMANENTLY_DENIED
            or any(key in a for key in PERMANENTLY_DENIED)
        ):
            return "DENY"
        declared = a.get("capability_level")
        if declared is not None and declared not in _LEVELS:
            return "DENY"
        if a.get("persistent_autonomy") or a.get("high_autonomy"):
            floor = "C5"
        elif a.get("external_side_effect") or a.get("privileged") or a.get("irreversible"):
            # Genesis continues to treat all external effects as C4 (conservative).
            # Engine has its own independent, operation-specific tier catalogue.
            floor = "C4"
        elif a.get("type") in {"run_goal", "retry_goal", "execute_skill", "create_goal", "cancel_goal"}:
            floor = "C3"
        elif a.get("type") in {"tool", "ingest_file", "learn_skill", "forget_fact", "mark_rule"}:
            floor = "C2"
        elif a.get("type"):
            floor = "C1"
        else:
            floor = "C0"
        # Model-declared levels may only increase, NEVER decrease, the derived floor.
        return f"C{max(_LEVELS[floor], _LEVELS.get(declared, 0))}"

    def evaluate(self, action: dict[str, Any] | None, *, human_approved: bool=False) -> CapabilityDecision:
        a=action or {}; required=self._required(a)
        if required=="DENY":return CapabilityDecision("deny","N/A",self.granted_level,"The requested capability is permanently non-grantable to Genesis.")
        if _LEVELS[required] > _LEVELS[self.granted_level]:return CapabilityDecision("deny",required,self.granted_level,"The requested action exceeds the configured Genesis capability ceiling.")
        if required=="C4" and not human_approved:return CapabilityDecision("require_approval",required,self.granted_level,"C4 actions require explicit human approval.",True)
        if required=="C5":
            if not human_approved:return CapabilityDecision("require_approval",required,self.granted_level,"C5 actions require explicit human approval.",True)
            expiry=a.get("expires_at"); max_actions=a.get("max_actions")
            if not expiry or max_actions is None:return CapabilityDecision("deny",required,self.granted_level,"C5 authority requires both a finite expiry and an action-count bound.")
            if expiry:
                try:
                    exp=datetime.fromisoformat(str(expiry).replace("Z","+00:00")); exp=exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
                    if exp <= datetime.now(timezone.utc):return CapabilityDecision("deny",required,self.granted_level,"C5 authority has expired.")
                except ValueError:return CapabilityDecision("deny",required,self.granted_level,"C5 expiry is invalid.")
            if type(max_actions) is not int or not 1 <= max_actions <= 1000:return CapabilityDecision("deny",required,self.granted_level,"C5 maximum-action bound is invalid.")
        return CapabilityDecision("allow",required,self.granted_level,"Action is inside the configured Genesis capability envelope.")
