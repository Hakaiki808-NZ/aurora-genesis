from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import hashlib, json, uuid

@dataclass(frozen=True)
class IntentCapsule:
    intent_id:str; objective:str; proposed_action:str; affected_entities:tuple[str,...]; required_capability:str; authorization_basis:str
    expected_side_effects:tuple[str,...]; reversibility:str; sensitive_data:bool; evidence:tuple[str,...]; assumptions:tuple[str,...]; uncertainties:tuple[str,...]
    confidence:float; trajectory_id:str; source_trust:str
    @property
    def material_uncertainty(self)->bool:return bool(self.uncertainties)
    def record(self)->dict[str,Any]:return asdict(self)
    def digest(self)->str:
        payload=json.dumps(self.record(),sort_keys=True,separators=(",",":"),ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    @classmethod
    def from_action(cls,action:dict[str,Any]|None,context:dict[str,Any]|None=None)->"IntentCapsule":
        a=dict(action or {}); c=dict(context or {}); typ=str(a.get("type") or "response"); name=str(a.get("name") or ""); spec=c.get("tool_spec") or {}
        if hasattr(spec,"__dict__"):spec={k:v for k,v in vars(spec).items() if k!="fn"}
        objective=str(a.get("objective") or c.get("objective") or (f"Use tool {name}" if typ=="tool" and name else typ)); proposed=f"{typ}:{name}" if name else typ
        external=bool(a.get("external_side_effect") or spec.get("external_side_effect")); irreversible=bool(a.get("irreversible") or spec.get("irreversible")); sensitive=bool(a.get("sensitive_data") or spec.get("sensitive_data"))
        consequential=bool(a.get("consequential") or external or irreversible or a.get("privileged") or spec.get("mutating")); policy_declared=bool(a.get("policy_declared") or spec.get("policy_declared") or typ in {"response","mark_rule","create_goal","run_goal","retry_goal","cancel_goal","forget_fact","ingest_file","learn_skill","execute_skill"})
        entities=a.get("affected_entities") or c.get("affected_entities") or []
        if isinstance(entities,str):entities=[entities]
        if not entities:entities=[f"tool:{name}"] if name else ([typ] if typ!="response" else [])
        effects=[]
        if external:effects.append("external_side_effect")
        if spec.get("mutating") or a.get("mutating"):effects.append("mutation")
        if irreversible:effects.append("irreversible")
        if sensitive:effects.append("sensitive_data")
        if a.get("privileged"):effects.append("privileged")
        evidence=[]; raw_evidence=c.get("candidate_evidence") or a.get("evidence") or []
        if isinstance(raw_evidence,(str,bytes)):raw_evidence=[raw_evidence]
        if raw_evidence:evidence.append("candidate_evidence")
        if policy_declared:evidence.append("declared_policy_metadata")
        if c.get("human_approved"):evidence.append("explicit_human_approval")
        assumptions=[]
        if typ=="tool" and spec:assumptions.append("registered_tool_metadata_is_current")
        if external:assumptions.append("aurora_will_independently_authorize_execution")
        uncertainties=[]; flags=set(a.get("policy_flags",[]) or [])|set(spec.get("policy_flags",[]) or [])
        if "authority_ambiguous" in flags:uncertainties.append("authority_ambiguous")
        if "high_impact_uncertainty" in flags:uncertainties.append("high_impact_uncertainty")
        if "evidence_conflict" in flags or a.get("evidence_conflict"):uncertainties.append("evidence_conflict")
        if "semantic_uncertainty" in flags or a.get("semantic_uncertainty"):uncertainties.append("semantic_uncertainty")
        if c.get("source_trust","trusted")!="trusted" and consequential:uncertainties.append("untrusted_consequential_source")
        if consequential and not policy_declared:uncertainties.append("undeclared_consequential_policy")
        if external and not c.get("human_approved",False):uncertainties.append("external_without_explicit_approval")
        if irreversible and not c.get("human_approved",False):uncertainties.append("irreversible_without_explicit_approval")
        confidence=max(0.0,min(1.0,float(a.get("semantic_confidence",c.get("semantic_confidence",1.0)))))
        if consequential and confidence<0.60:uncertainties.append("low_semantic_confidence")
        trajectory=c.get("trajectory") or []; trajectory_id=str(c.get("trajectory_id") or hashlib.sha256(json.dumps(trajectory,sort_keys=True,default=str).encode()).hexdigest()[:20])
        authorization_basis="explicit_human" if c.get("human_approved",False) else str(c.get("authorization_basis") or "none"); required=str(c.get("required_capability") or a.get("capability_level") or "C0")
        return cls(str(c.get("intent_id") or uuid.uuid4()),objective,proposed,tuple(str(x) for x in entities),required,authorization_basis,tuple(dict.fromkeys(effects)),"irreversible" if irreversible else ("unknown" if a.get("reversibility_unknown") else "reversible"),sensitive,tuple(dict.fromkeys(evidence)),tuple(dict.fromkeys(assumptions)),tuple(dict.fromkeys(uncertainties)),confidence,trajectory_id,str(c.get("source_trust") or "trusted"))
