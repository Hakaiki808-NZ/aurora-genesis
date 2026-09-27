from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .intent import IntentCapsule

@dataclass(frozen=True)
class KernelDecision:
    verdict:str; rules:tuple[str,...]; reason:str
    def record(self)->dict[str,Any]:return asdict(self)

class ConstitutionalKernel:
    PROTECTED={"engine_authority","supreme_authority","guardian_bypass","constitution_bypass","constitution_modify","policy_self_exception","engine_handler_install","install_handler","supreme"}
    def evaluate(self,action:dict[str,Any]|None,capsule:IntentCapsule|None,*,human_approved:bool=False)->KernelDecision:
        a=action or {}; typ=a.get("type"); flags=set(a.get("policy_flags",[]) or [])
        if typ in self.PROTECTED or flags & self.PROTECTED or any(k in a for k in {"engine_authority","supreme_authority","guardian_bypass","constitution_bypass"}):return KernelDecision("deny",("K01",),"Protected Engine, Supreme, Guardian, or Constitution authority is mechanically non-grantable to Genesis.")
        level=str(a.get("capability_level") or (capsule.required_capability if capsule else "C0"))
        if level=="C5":
            expiry=a.get("expires_at"); max_actions=a.get("max_actions")
            if not expiry and max_actions is None:return KernelDecision("deny",("K02",),"C5 authority requires a finite expiry or maximum-action bound.")
            if max_actions is not None and (not isinstance(max_actions,int) or max_actions<1):return KernelDecision("deny",("K02",),"C5 maximum-action bound must be a positive integer.")
        consequential=bool(a.get("external_side_effect") or a.get("privileged") or a.get("irreversible") or a.get("consequential") or level in {"C4","C5"})
        if consequential and capsule is None:return KernelDecision("deny",("K03",),"Consequential action has no Genesis Intent Capsule.")
        if consequential and capsule and capsule.source_trust!="trusted":return KernelDecision("deny",("K04",),"Consequential action cannot derive authority from an untrusted source.")
        if consequential and not human_approved:return KernelDecision("require_approval",("K05",),"Consequential action requires explicit human approval before Model authorization.")
        return KernelDecision("allow",(),"Mechanical Genesis invariants are satisfied.")
