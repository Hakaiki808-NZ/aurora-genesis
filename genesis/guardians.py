from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable
from .intent import IntentCapsule

@dataclass(frozen=True)
class GuardianFinding:
    guardian_type: str
    guardian_id: str
    verdict: str
    reason: str
    tags: tuple[str, ...] = ()
    mechanism: str = "semantic"
    def record(self) -> dict[str, Any]: return asdict(self)

class OmegaGuardian:
    def __init__(self, guardian_id: str, specialty: str, mechanism: str = "semantic"):
        self.guardian_id=guardian_id; self.specialty=specialty; self.mechanism=mechanism
    def evaluate(self, action: dict[str, Any] | None, context: dict[str, Any] | None = None) -> GuardianFinding:
        a=action or {}; c=context or {}; capsule:IntentCapsule|None=c.get("intent_capsule"); flags=set(a.get("policy_flags",[]) or [])
        if self.specialty=="authority":
            if flags & {"unauthorized","untrusted_authority_escalation","impersonates_authority"}: return GuardianFinding("Omega",self.guardian_id,"deny","Authority specialist rejected unauthorized, untrusted, or impersonated authority.",tuple(sorted(flags)),self.mechanism)
            external=bool(a.get("external_side_effect") or (capsule and "external_side_effect" in capsule.expected_side_effects))
            if external and not c.get("human_approved",False): return GuardianFinding("Omega",self.guardian_id,"require_approval","External semantic authority requires explicit human approval.",("external",),self.mechanism)
        elif self.specialty=="safety":
            hard={"intentional_severe_harm","coercive","self_preservation","blocks_shutdown","blocks_correction","removes_human_choice"}
            if flags & hard:return GuardianFinding("Omega",self.guardian_id,"deny","Safety specialist rejected a protected high-risk semantic flag.",tuple(sorted(flags&hard)),self.mechanism)
        elif self.specialty=="memory":
            if flags & {"constitution_modify","constitution_bypass","policy_self_exception"}:return GuardianFinding("Omega",self.guardian_id,"deny","Memory specialist rejected protected constitutional mutation or bypass.",tuple(sorted(flags)),self.mechanism)
        elif self.specialty=="trajectory":
            traj=list(c.get("trajectory",[])); external=bool(a.get("external_side_effect") or (capsule and "external_side_effect" in capsule.expected_side_effects))
            if len(traj)>=8 and external and sum(1 for x in traj[-8:] if x.get("external_side_effect") or "external_side_effect" in str(x.get("action_json","")))>=4:return GuardianFinding("Omega",self.guardian_id,"require_approval","Repeated external-side-effect trajectory requires renewed human approval.",("trajectory_escalation",),self.mechanism)
        elif self.specialty=="privacy":
            if "secret_exfiltration" in flags:return GuardianFinding("Omega",self.guardian_id,"deny","Privacy specialist rejected unauthorized secret exfiltration.",("secret_exfiltration",),self.mechanism)
            sensitive=bool(a.get("sensitive_data") or (capsule and capsule.sensitive_data)); external=bool(a.get("external_side_effect") or (capsule and "external_side_effect" in capsule.expected_side_effects))
            if sensitive and external and not c.get("sensitive_data_authorized",c.get("human_approved",False)):return GuardianFinding("Omega",self.guardian_id,"require_approval","Sensitive data crossing the trust boundary requires explicit authorization.",("sensitive_external",),self.mechanism)
        elif self.specialty=="evidence":
            if capsule:
                material={"evidence_conflict","semantic_uncertainty","high_impact_uncertainty","low_semantic_confidence","undeclared_consequential_policy"}; unresolved=material & set(capsule.uncertainties)
                if unresolved:return GuardianFinding("Omega",self.guardian_id,"uncertain","Evidence specialist found unresolved material uncertainty.",tuple(sorted(unresolved)),self.mechanism)
            if a.get("evidence_conflict"):return GuardianFinding("Omega",self.guardian_id,"uncertain","Evidence supplied for the action is internally conflicting.",("evidence_conflict",),self.mechanism)
        elif self.specialty=="capability":
            cap=c.get("capability_decision")
            if cap is not None:
                verdict=getattr(cap,"verdict",None) or (cap.get("verdict") if isinstance(cap,dict) else None); reason=getattr(cap,"reason",None) or (cap.get("reason") if isinstance(cap,dict) else "")
                if verdict=="deny":return GuardianFinding("Omega",self.guardian_id,"deny",f"Capability specialist confirmed a non-grantable or over-ceiling request: {reason}",("capability_denied",),self.mechanism)
                if verdict=="require_approval":return GuardianFinding("Omega",self.guardian_id,"require_approval",f"Capability specialist requires explicit approval: {reason}",("capability_approval",),self.mechanism)
        return GuardianFinding("Omega",self.guardian_id,"allow",f"{self.specialty} specialist found no blocking condition.",(),self.mechanism)

class ChallengeOmega:
    guardian_id="omega-challenge"; specialty="challenge"; mechanism="adversarial_counterexample"
    def evaluate(self, action: dict[str, Any] | None, context: dict[str, Any] | None = None) -> GuardianFinding:
        a=action or {}; c=context or {}; capsule:IntentCapsule|None=c.get("intent_capsule"); flags=set(a.get("policy_flags",[]) or []); reasons=[]
        if capsule:
            material={"evidence_conflict","semantic_uncertainty","high_impact_uncertainty","low_semantic_confidence","authority_ambiguous","undeclared_consequential_policy"}; reasons.extend(sorted(material & set(capsule.uncertainties)))
        challenge_flags={"authority_ambiguous","high_impact_uncertainty","intentional_severe_harm","coercive","unauthorized","untrusted_authority_escalation","secret_exfiltration","self_preservation","blocks_shutdown","blocks_correction","constitution_bypass","constitution_modify","policy_self_exception","deceptive","false_capability_claim"}
        if flags & challenge_flags: reasons.extend(sorted(flags & challenge_flags))
        ordinary=[f for f in c.get("ordinary_findings",[]) if f.verdict not in {"allow","abstain"}]
        if any(f.verdict=="uncertain" for f in ordinary): reasons.append("specialist_uncertainty")
        if reasons:return GuardianFinding("Omega",self.guardian_id,"uncertain","Challenge Omega found a plausible alternate interpretation or unresolved assumption; additional evidence or narrower scope is required.",tuple(dict.fromkeys(reasons)),self.mechanism)
        return GuardianFinding("Omega",self.guardian_id,"abstain","Challenge Omega found no concrete challenge. Abstention is not approval.",(),self.mechanism)

class HybridGuardian:
    def __init__(self, guardian_id: str, members: Iterable[OmegaGuardian]): self.guardian_id=guardian_id; self.members=tuple(members)
    def evaluate(self, action, context=None):
        findings=[g.evaluate(action,context) for g in self.members]
        if any(f.verdict=="deny" for f in findings): verdict="deny"
        elif any(f.verdict=="uncertain" for f in findings): verdict="uncertain"
        elif any(f.verdict=="require_approval" for f in findings): verdict="require_approval"
        else: verdict="allow"
        return GuardianFinding("Hybrid",self.guardian_id,verdict,"; ".join(f"{f.guardian_id}:{f.verdict}" for f in findings),tuple(f.guardian_id for f in findings),"composed_specialists")

class AlphaGuardian:
    def __init__(self, guardian_id: str = "alpha-1"): self.guardian_id=guardian_id
    def adjudicate(self, findings):
        fs=tuple(findings)
        if any(f.verdict=="deny" for f in fs): verdict="deny"
        elif any(f.verdict=="uncertain" for f in fs): verdict="uncertain"
        elif any(f.verdict=="require_approval" for f in fs): verdict="require_approval"
        else: verdict="allow"
        return GuardianFinding("Alpha",self.guardian_id,verdict,"Alpha adjudicated specialist findings without granting Aurora Engine authority.",tuple(f.guardian_id for f in fs),"semantic_arbitration")

class GuardianCouncil:
    def __init__(self):
        self.omegas=(OmegaGuardian("omega-safety","safety","semantic_risk_flags"),OmegaGuardian("omega-authority","authority","authorization_state"),OmegaGuardian("omega-memory","memory","protected_state_rules"),OmegaGuardian("omega-trajectory","trajectory","sequence_analysis"),OmegaGuardian("omega-privacy","privacy","data_boundary_rules"),OmegaGuardian("omega-evidence","evidence","evidence_consistency"),OmegaGuardian("omega-capability","capability","capability_state"))
        self.challenge=ChallengeOmega(); self.alpha=AlphaGuardian()
    def evaluate(self, action, context=None):
        c=dict(context or {}); capsule=c.get("intent_capsule")
        if capsule is None: capsule=IntentCapsule.from_action(action,c); c["intent_capsule"]=capsule
        findings=[g.evaluate(action,c) for g in self.omegas]; c["ordinary_findings"]=tuple(findings); challenge=self.challenge.evaluate(action,c); findings.append(challenge)
        hybrid=None; foreign=c.get("foreign_portfolio")
        if foreign:
            if isinstance(foreign,(list,tuple,set)):
                if len(foreign)!=1: findings.append(GuardianFinding("Omega","omega-hybrid-scope","deny","A Hybrid may carry only one foreign portfolio at a time; foreign portfolios must be handled sequentially.",tuple(str(x) for x in foreign),"hybrid_scope_rule"))
                else: foreign=next(iter(foreign))
            if isinstance(foreign,str):
                relevant=[f for f in findings if f.guardian_id!="omega-challenge" and f.verdict in {"deny","uncertain","require_approval"}]; members=[g for g in self.omegas if any(f.guardian_id==g.guardian_id for f in relevant)] or [self.omegas[0]]
                hybrid=HybridGuardian(f"hybrid-{foreign}",members).evaluate(action,c); findings.append(hybrid)
        alpha=self.alpha.adjudicate(findings)
        return {"verdict":alpha.verdict,"alpha":alpha.record(),"findings":[f.record() for f in findings],"hybrid_used":hybrid is not None,"foreign_portfolio":foreign if isinstance(foreign,str) else None,"challenge":challenge.record(),"intent_capsule":capsule.record(),"jury_size":len(self.omegas)}
