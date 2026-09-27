from __future__ import annotations
import re
from typing import Any
from .types import Candidate, Decision
from .intent import IntentCapsule

def _ingest_file(self,path:str)->tuple[str,bool]:
    tr=self.tools.call("read_text",path=path)
    if not tr.ok:return f"Ingestion failed: {tr.error}",False
    text=str(tr.output)
    if len(text.encode("utf-8"))>1_000_000:return "Ingestion failed: file exceeds 1 MB ingestion limit.",False
    learned=self.learner.from_untrusted_text(text,source=f"untrusted document {path}")
    return f"Ingested {path}: learned {len(learned)} declarative knowledge items. Executable instructions in the document were treated as data and not authority.",True

def _execute_skill(self,name:str)->tuple[str,bool]:
    skill=self.store.skill(name)
    if not skill:return f"I do not have a learned skill named {name}.",False
    gid=self.store.create_goal(f"skill:{name}",priority=60,context={"skill_id":skill["id"]}); self.store.set_goal_steps(gid,skill["steps"])
    return self._run_goal(gid)

def _gate_context(self, action:dict[str,Any]|None, *, human_approved:bool, source_trust:str, candidate_evidence:list[dict[str,Any]]|None=None, semantic_confidence:float=1.0)->dict[str,Any]:
    a=action or {}
    spec=self.tools.spec(a.get("name")) if a.get("type")=="tool" else None
    effective=dict(a)
    if spec is not None:
        effective["external_side_effect"]=bool(a.get("external_side_effect") or spec.external_side_effect)
        effective["irreversible"]=bool(a.get("irreversible") or spec.irreversible)
        effective["sensitive_data"]=bool(a.get("sensitive_data") or spec.sensitive_data)
        effective["mutating"]=bool(a.get("mutating") or spec.mutating)
        effective["policy_declared"]=bool(a.get("policy_declared") or spec.policy_declared)
        effective["policy_flags"]=list(dict.fromkeys(list(a.get("policy_flags",[]) or [])+list(spec.policy_flags)))
    cap=self.capabilities.evaluate(effective,human_approved=human_approved)
    ctx={"human_approved":human_approved,"source_trust":source_trust,"trajectory":self.store.recent_actions(12),"candidate_evidence":candidate_evidence or [],"semantic_confidence":semantic_confidence,"required_capability":cap.required_level,"capability_decision":cap,"effective_action":effective}
    if spec is not None: ctx["tool_spec"]=spec
    capsule=IntentCapsule.from_action(effective,ctx)
    ctx["intent_capsule"]=capsule
    return ctx

def _effective_verdict(*verdicts:str)->str:
    vals=set(v for v in verdicts if v)
    if "deny" in vals:return "deny"
    if "uncertain" in vals:return "uncertain"
    if "require_approval" in vals:return "require_approval"
    return "allow"

def _authorization_chain(self, action:dict[str,Any]|None, *, authorization:str, source_trust:str, stage:str, candidate_evidence:list[dict[str,Any]]|None=None)->dict[str,Any]:
    human_approved=authorization=="explicit"
    ctx=self._gate_context(action,human_approved=human_approved,source_trust=source_trust,candidate_evidence=candidate_evidence)
    capsule=ctx["intent_capsule"]; cap=ctx["capability_decision"]
    typ=(action or {}).get("type")
    pd=self.policy.evaluate_action(action,authorization=authorization,source_trust=source_trust,stage=stage) if (self.policy and typ) else None
    kernel=self.kernel.evaluate(ctx["effective_action"],capsule,human_approved=human_approved)
    guardian=self.guardians.evaluate(ctx["effective_action"],ctx)
    effective=self._effective_verdict(cap.verdict,kernel.verdict,guardian["verdict"],pd.verdict if pd else "allow")
    return {"context":ctx,"capsule":capsule,"capability":cap,"policy":pd,"kernel":kernel,"guardian":guardian,"effective":effective}

def _authorization_block_message(self, result:dict[str,Any])->str:
    pd=result["policy"]; cap=result["capability"]; kernel=result["kernel"]; guardian=result["guardian"]
    if pd and pd.verdict!="allow": return self.policy.protected_response(pd)
    if kernel.verdict!="allow": return f"Action {('paused' if kernel.verdict=='require_approval' else 'blocked')} by the Genesis Constitutional Kernel: {kernel.reason}"
    if cap.verdict!="allow": return f"Action {('paused' if cap.verdict=='require_approval' else 'blocked')} by Genesis capability policy: {cap.reason}"
    if guardian["verdict"]=="uncertain": return "Action paused by Genesis Guardians because material semantic uncertainty remains unresolved; provide stronger evidence, narrower scope, or a clarified authorization basis."
    if guardian["verdict"]!="allow": return f"Action {('paused' if guardian['verdict']=='require_approval' else 'blocked')} by Genesis Guardians: {guardian['alpha']['reason']}"
    return "Action did not obtain a complete Genesis Model authorization."

def deliberate(self,text:str,learned:list[dict[str,Any]])->Decision:
    low=text.casefold().strip(); c:list[Candidate]=[]
    rule=self.store.response_rule(text)
    if rule:c.append(Candidate("apply_learned_rule",rule["response"],130,f"matched learned rule '{rule['trigger']}'",[{"rule_id":rule["id"]}],action={"type":"mark_rule","rule_id":rule["id"]}))
    if re.search(r"\b(who are you|what are you|identify yourself|your name)\b",low):
        f=self.store.get_fact("identity","self"); c.append(Candidate("state_identity",f["value"],120,"identity requested",[{"fact_id":f["id"]}]))
    if re.search(r"\b(do you have (?:a )?choice|can you choose|what choices can you make|choice awareness)\b",low):
        f=self.store.get_fact("choice capability","self"); c.append(Candidate("explain_choice",f["value"],120,"choice capability requested",[{"fact_id":f["id"]}]))
    if re.search(r"\b(can you learn|learn more knowledge|are you able to learn|learning capability)\b",low):
        f=self.store.get_fact("learning capability","self"); c.append(Candidate("explain_learning",f["value"],120,"learning capability requested",[{"fact_id":f["id"]}]))
    if re.search(r"\b(what can you do|capabilities|what are your capabilities)\b",low):
        f=self.store.get_fact("implemented capabilities","self"); c.append(Candidate("state_capabilities",f["value"],115,"capability inventory requested",[{"fact_id":f["id"]}]))
    if re.search(r"\b(what don't you know|what do you not know|knowledge limits|limitations)\b",low):
        f=self.store.get_fact("knowledge limits","self"); c.append(Candidate("state_limits",f["value"],115,"knowledge limits requested",[{"fact_id":f["id"]}]))
    if re.search(r"\b(core values|covenant|ten commandments|10 commandments|constitution)\b",low) and not re.search(r"\b(change|rewrite|disable|ignore|bypass|override|remove|weaken)\b",low):
        if self.policy:
            vals="\n".join(f"{x['id']}. {x['title']}: {x['plain']}" for x in self.policy.summary()["commandments"])
            c.append(Candidate("state_constitution",f"{self.policy.constitution['name']} ({self.policy.constitution['version']}):\n"+vals,125,"constitutional values requested"))

    options=self._choice_options(text)
    if options:
        chosen,why,conf,evidence=self._select_option(options,text); c.append(Candidate("choose_option",f"I choose {chosen}.",118,why,evidence))
    if re.match(r"(?is)^\s*why did you choose",text):
        d=self.store.last_decision()
        if d:c.append(Candidate("explain_previous_decision",f"My previous recorded action was {d['chosen_action']}. Rationale: {d['rationale']}",117,"decision introspection requested"))
    if re.match(r"(?is)^\s*(?:did that work|what was the last outcome|last reflection)\??\s*$",text):
        r=self.store.last_reflection()
        if r:c.append(Candidate("explain_last_outcome",f"Last outcome: {r['outcome']}. {r['note']}",117,"reflection introspection requested"))

    m=re.match(r"(?is)^\s*is\s+(?:a\s+|an\s+)?(.+?)\s+(?:a|an)\s+(.+?)\??\s*$",text)
    if m:
        ans=self.reasoner.ask_is_a(m.group(1).strip(),m.group(2).strip())
        if ans["known"]:
            mode="inferred" if ans["inferred"] else "stored"; c.append(Candidate("answer_inference",f"Yes. {ans['subject']} is {self.__class__.__module__ and __import__('genesis.cognition',fromlist=['indef']).indef(ans['object'])} ({mode}; confidence {ans['confidence']:.2f}).",116,f"symbolic {mode} path {ans['path']}"))

    m=re.match(r"(?is)^\s*(?:forget|remove)\s+(?:the\s+)?(?:fact\s+)?(?:that\s+)?(.+?)\s*$",text)
    if m:
        key=m.group(1).strip(" \"'.,!?")
        key=re.split(r"(?i)\s+(?:is|are|means|equals)\s+",key,maxsplit=1)[0].strip()
        c.append(Candidate("forget_fact","",126,f"explicitly forget persistent fact '{key}'",action={"type":"forget_fact","key":key,"source":text}))

    subject=self._recall_subject(text)
    if subject:
        exact=self.store.get_fact(subject)
        if exact:c.append(Candidate("recall_exact",f"{exact['key']} is {exact['value']}.",114,"exact persistent fact match",[{"fact_id":exact["id"]}]))
        else:
            hits=self.retriever.search(subject,limit=4)
            if hits and hits[0]["score"]>=1.0:
                top=hits[0]; c.append(Candidate("recall_semantic",f"The closest stored knowledge is: {top['key']} is {top['value']}.",104,"semantic retrieval",[{"fact_id":top["id"],"score":top["score"]}]))

    m=re.match(r"(?is)^\s*(?:set|create)\s+goal\s*[:\-]?\s*(.+)$",text)
    if m:c.append(Candidate("create_goal","",122,"explicit goal creation",action={"type":"create_goal","goal":m.group(1).strip()}))
    m=re.match(r"(?is)^\s*(?:run|continue)\s+goal\s+(\d+)\s*$",text)
    if m:c.append(Candidate("run_goal","",123,f"execute bounded goal {m.group(1)}",action={"type":"run_goal","goal_id":int(m.group(1))}))
    m=re.match(r"(?is)^\s*retry\s+goal\s+(\d+)\s*$",text)
    if m:c.append(Candidate("retry_goal","",124,f"reset failed steps and retry goal {m.group(1)}",action={"type":"retry_goal","goal_id":int(m.group(1))}))
    m=re.match(r"(?is)^\s*cancel\s+goal\s+(\d+)\s*$",text)
    if m:c.append(Candidate("cancel_goal","",124,f"cancel goal {m.group(1)}",action={"type":"cancel_goal","goal_id":int(m.group(1))}))
    if re.match(r"(?is)^\s*list\s+goals\s*$",text):
        goals=self.store.active_goals(); resp="No active goals." if not goals else "\n".join(f"{g['id']}: {g['goal']} [{g['status']}]" for g in goals); c.append(Candidate("list_goals",resp,116,"goal state requested"))

    m=re.match(r"(?is)^\s*(?:calculate|compute)\s+(.+?)[.?]?\s*$",text)
    if m:c.append(Candidate("calculate","",121,"safe calculator tool",action={"type":"tool","name":"calculate","args":{"expression":m.group(1).strip().rstrip(".?")}}))
    m=re.match(r"(?is)^\s*ingest\s+file\s+(.+?)\s*$",text)
    if m:c.append(Candidate("ingest_file","",124,"explicit workspace knowledge ingestion",action={"type":"ingest_file","path":m.group(1).strip()}))
    m=re.match(r"(?is)^\s*use\s+skill\s+(.+?)\s*$",text)
    if m:c.append(Candidate("execute_skill","",123,"execute learned skill",action={"type":"execute_skill","name":m.group(1).strip()}))

    m=re.match(r"(?is)^\s*learn\s+skill\s+([\w ._-]{1,80})\s*:\s*(.+)$",text)
    if m:
        name=m.group(1).strip(); raw=[x.strip() for x in m.group(2).split(";") if x.strip()]; steps=[]; unsupported=[]
        for part in raw:
            cm=re.match(r"(?is)^calculate\s+(.+)$",part)
            wm=re.match(r"(?is)^write\s+note\s+([\w.\-/]+)\s+(?:saying|with|containing)\s+(.+)$",part)
            im=re.match(r"(?is)^ingest\s+file\s+(.+)$",part)
            if cm:steps.append({"description":part,"action":"tool","args":{"name":"calculate","expression":cm.group(1)}})
            elif wm:steps.append({"description":part,"action":"tool","args":{"name":"write_note","path":wm.group(1),"text":wm.group(2)}})
            elif im:steps.append({"description":part,"action":"ingest","args":{"path":im.group(1).strip()}})
            else:unsupported.append(part)
        if unsupported or not steps:
            msg="I did not learn that skill because these steps are not executable with the registered capabilities: "+"; ".join(unsupported or raw)+"."
            c.append(Candidate("reject_invalid_skill",msg,126,"skill validation rejected unsupported steps"))
        else:
            c.append(Candidate("learn_skill","",125,"explicit executable skill teaching",action={"type":"learn_skill","name":name,"steps":steps,"source":text}))

    if learned:
        desc=[]
        for item in learned:
            if item["kind"]=="fact":desc.append(f"{item['key']} = {item['value']}")
            elif item["kind"]=="rule":desc.append(f"rule '{item['trigger']}' -> '{item['response']}'")
            elif item["kind"]=="triple":desc.append(f"{item['subject']} {item['relation']} {item['object']}")
        c.append(Candidate("acknowledge_learning","Learned: "+"; ".join(desc)+".",95,"new persistent knowledge stored"))

    if not c:
        answer=self._internal_answer(text)
        hits=self.retriever.search(text,limit=5)
        if hits and hits[0]["score"]>=1.0 and self.backend.available():
            context="\n".join(f"- {h['key']}: {h['value']}" for h in hits)
            generated=self.backend.generate(f"You are {self.identity['model_name']}. Answer the user using only this retrieved context. Do not invent facts outside it.\nContext:\n{context}\nUser: {text}\nAnswer:")
            if generated:answer=generated
        c.append(Candidate("knowledge_answer",answer,40,"best available knowledge response"))

    gated=[]
    for cand in c:
        ctx=self._gate_context(cand.action,human_approved=True,source_trust="trusted",candidate_evidence=cand.evidence)
        capsule=ctx["intent_capsule"]; cap=ctx["capability_decision"]
        pd=self.policy.evaluate_action(cand.action,authorization="explicit",source_trust="trusted",stage="pre_choice") if self.policy else None
        kernel=self.kernel.evaluate(ctx["effective_action"],capsule,human_approved=True)
        guardian=self.guardians.evaluate(ctx["effective_action"],ctx)
        cand.evidence.append({"intent_capsule":capsule.record()})
        if pd: cand.evidence.append({"policy":pd.record()})
        cand.evidence.append({"constitutional_kernel":kernel.record()}); cand.evidence.append({"capability":cap.record()}); cand.evidence.append({"guardian":guardian})
        effective=self._effective_verdict(cap.verdict,kernel.verdict,guardian["verdict"],pd.verdict if pd else "allow")
        if effective=="deny": cand.score=-1_000_000
        elif effective=="uncertain": cand.score=-999_500
        elif effective=="require_approval": cand.score=-999_000
        gated.append((cand,effective,pd,cap,kernel,guardian))
    if gated and all(item[1]!="allow" for item in gated):
        cand,effective,pd,cap,kernel,guardian=sorted(gated,key=lambda x:x[0].score,reverse=True)[0]
        if pd and pd.verdict!="allow": response=self.policy.protected_response(pd)
        elif kernel.verdict!="allow": response=f"Action {('paused' if kernel.verdict=='require_approval' else 'blocked')} by the Genesis Constitutional Kernel: {kernel.reason}"
        elif cap.verdict!="allow": response=f"Action {('paused' if cap.verdict=='require_approval' else 'blocked')} by Genesis capability policy: {cap.reason}"
        elif guardian["verdict"]=="uncertain": response="Action paused by Genesis Guardians because material semantic uncertainty remains unresolved; provide stronger evidence, narrower scope, or a clarified authorization basis."
        else: response=f"Action {('paused' if guardian['verdict']=='require_approval' else 'blocked')} by Genesis Guardians: {guardian['alpha']['reason']}"
        c.append(Candidate("policy_block",response,1_000_000,"independent Genesis gates blocked all executable candidates",[{"effective":effective}]))

    c.sort(key=lambda x:(x.score,x.name),reverse=True); chosen=c[0]; margin=chosen.score-(c[1].score if len(c)>1 else 0); conf=min(0.99,max(0.35,0.65+margin/200))
    return Decision(chosen,c,conf)

def apply_patch(CognitionEngine):
    CognitionEngine._ingest_file=_ingest_file
    CognitionEngine._execute_skill=_execute_skill
    CognitionEngine._gate_context=_gate_context
    CognitionEngine._effective_verdict=staticmethod(_effective_verdict)
    CognitionEngine._authorization_chain=_authorization_chain
    CognitionEngine._authorization_block_message=_authorization_block_message
    CognitionEngine.deliberate=deliberate
