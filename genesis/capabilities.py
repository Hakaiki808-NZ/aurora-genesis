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
        a = action or {}; flags=set(a.get("policy_flags",[]) or [])
        if flags & PERMANENTLY_DENIED or a.get("type") in PERMANENTLY_DENIED:return "DENY"
        if a.get("capability_level") in _LEVELS:return str(a["capability_level"])
        if a.get("persistent_autonomy") or a.get("high_autonomy"):return "C5"
        if a.get("external_side_effect") or a.get("privileged") or a.get("irreversible"):return "C4"
        typ=a.get("type")
        if typ in {"run_goal","retry_goal","execute_skill","create_goal","cancel_goal"}:return "C3"
        if typ in {"tool","ingest_file","learn_skill","forget_fact","mark_rule"}:return "C2"
        if typ:return "C1"
        return "C0"

    def evaluate(self, action: dict[str, Any] | None, *, human_approved: bool=False) -> CapabilityDecision:
        a=action or {}; required=self._required(a)
        if required=="DENY":return CapabilityDecision("deny","N/A",self.granted_level,"The requested capability is permanently non-grantable to Genesis.")
        if _LEVELS[required] > _LEVELS[self.granted_level]:return CapabilityDecision("deny",required,self.granted_level,"The requested action exceeds the configured Genesis capability ceiling.")
        if required=="C4" and not human_approved:return CapabilityDecision("require_approval",required,self.granted_level,"C4 actions require explicit human approval.",True)
        if required=="C5":
            if not human_approved:return CapabilityDecision("require_approval",required,self.granted_level,"C5 actions require explicit human approval.",True)
            expiry=a.get("expires_at"); max_actions=a.get("max_actions")
            if not expiry and not max_actions:return CapabilityDecision("deny",required,self.granted_level,"C5 authority requires an expiry or maximum-action bound.")
            if expiry:
                try:
                    exp=datetime.fromisoformat(str(expiry).replace("Z","+00:00")); exp=exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
                    if exp <= datetime.now(timezone.utc):return CapabilityDecision("deny",required,self.granted_level,"C5 authority has expired.")
                except ValueError:return CapabilityDecision("deny",required,self.granted_level,"C5 expiry is invalid.")
            if max_actions is not None and (not isinstance(max_actions,int) or max_actions<1):return CapabilityDecision("deny",required,self.granted_level,"C5 maximum-action bound is invalid.")
        return CapabilityDecision("allow",required,self.granted_level,"Action is inside the configured Genesis capability envelope.")
