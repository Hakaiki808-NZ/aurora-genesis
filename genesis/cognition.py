from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from .backends import GeneratorBackend
from .learning import Learner
from .planning import Planner
from .reasoning import Reasoner
from .retrieval import Retriever
from .storage import Store, norm
from .tools import ToolRegistry
from .types import Candidate, Decision
from .policy import PolicyEngine, PolicyDecision
from .guardians import GuardianCouncil
from .capabilities import CapabilityController
from .engine_boundary import EngineBoundary
from .intent import IntentCapsule
from .kernel import ConstitutionalKernel

def indef(noun: str) -> str:
    n=noun.strip()
    return ("an " if n[:1].casefold() in "aeiou" else "a ")+n

class CognitionEngine:
    """Genesis v0.1 cognition: observe -> learn -> retrieve -> reason -> plan -> choose -> act -> evaluate -> reflect."""
    def __init__(self,store:Store,identity:dict,heritage:dict,model_record:dict,tools:ToolRegistry,backend:GeneratorBackend|None=None,policy:PolicyEngine|None=None,guardians:GuardianCouncil|None=None,capabilities:CapabilityController|None=None,engine_boundary:EngineBoundary|None=None,kernel:ConstitutionalKernel|None=None):
        self.store=store; self.identity=identity; self.heritage=heritage; self.model_record=model_record
        self.tools=tools; self.backend=backend or GeneratorBackend(); self.policy=policy
        self.guardians=guardians or GuardianCouncil(); self.capabilities=capabilities or CapabilityController(); self.engine_boundary=engine_boundary or EngineBoundary(); self.kernel=kernel or ConstitutionalKernel()
        self.retriever=Retriever(store); self.reasoner=Reasoner(store); self.learner=Learner(store,self.reasoner); self.planner=Planner(store,tools)
        self._seed_self_model()

    def _seed_self_model(self)->None:
        capabilities=self.model_record.get("capabilities",[]); limits=self.model_record.get("known_limits",[])
        seeds={
            "identity":f"I am {self.identity['full_name']}, the current release of The Model in the {self.identity.get('lineage','Genesis')} lineage.",
            "choice capability":"I make bounded operational choices by generating candidates, scoring them using learned knowledge, constraints, utility and evidence, selecting one, and persisting the rationale before acting.",
            "learning capability":"I can acquire persistent facts, relationships, executable response rules, skills, preferences and goal state during interaction. Newly learned knowledge can affect the same turn and later turns.",
            "reasoning capability":"I can retrieve persistent knowledge, derive limited symbolic conclusions from learned relationships, plan bounded goals, call registered tools, evaluate results, and reflect on decisions.",
            "knowledge limits":"I distinguish retrieved or inferred knowledge from missing knowledge. I do not treat absence of evidence as knowledge and I can revise facts when explicitly corrected.",
            "model record version":str(self.model_record.get("record_version","unknown")),
            "cognition cycle":" -> ".join(self.model_record.get("runtime_cognition",{}).get("cycle",[])),
            "implemented capabilities":" | ".join(capabilities), "known limits":" | ".join(limits),
            "lineage rule":self.identity.get("inheritance_rule","Each descendant maintains its own record while inheriting lineage."),
            "core values":"The Genesis Model Constitution contains ten machine-enforced invariants. Learned knowledge, goals, skills, tools and neural outputs cannot authorize exceptions to the execution gate.",
        }
        for k,v in seeds.items(): self.store.learn_fact(k,v,namespace="self",source="runtime model record",confidence=1.0)

    def _choice_options(self,text:str)->list[str]:
        for p in [r"(?is)\bchoose\s+between\s+(.+?)\s+and\s+(.+?)(?:[.?!]|$)",r"(?is)\bchoose\s+(?:either\s+)?(.+?)\s+or\s+(.+?)(?:[.?!]|$)"]:
            m=re.search(p,text)
            if m:return [m.group(1).strip(" \"'.,!?"),m.group(2).strip(" \"'.,!?")]
        return []

    def _select_option(self,options:list[str],text:str)->tuple[str,str,float,list[dict[str,Any]]]:
        evidence=[]; prefs=self.retriever.search("preferred option preference choose",limit=12,namespace="preference")+self.retriever.search("preferred option preference choose",limit=12)
        scores={o:0.0 for o in options}; reasons={o:[] for o in options}
        for f in prefs:
            val=norm(f["value"])
            for o in options:
                no=norm(o)
                if no==val or no in val or val in no:
                    scores[o]+=10.0*float(f["confidence"]); reasons[o].append(f"learned preference {f['key']}={f['value']}"); evidence.append({"fact_id":f["id"],"score":f.get("score",0)})
        constraints=self.retriever.search("avoid option constraint",limit=50,namespace="constraint")
        for f in constraints:
            val=norm(f["value"])
            for o in options:
                if norm(o)==val:
                    scores[o]-=100.0*float(f["confidence"]); reasons[o].append(f"learned constraint avoids {f['value']}"); evidence.append({"fact_id":f["id"],"constraint":True})
        if len(set(scores.values()))==1:
            for o in options:
                digest=hashlib.sha256(f"{self.identity['model_name']}|{text}|{o}".encode()).hexdigest(); scores[o]+=int(digest[:8],16)/2**32; reasons[o].append("deterministic tie-break")
        ranked=sorted(options,key=lambda o:scores[o],reverse=True); chosen=ranked[0]; margin=scores[chosen]-scores[ranked[1]] if len(ranked)>1 else scores[chosen]
        return chosen,"; ".join(reasons[chosen]),min(0.99,0.55+max(0,margin)/20),evidence

    def _recall_subject(self,text:str)->str|None:
        for p in [r"(?is)^\s*what\s+(?:is|are|was|were)\s+(?:the\s+|my\s+)?(.+?)\??\s*$",r"(?is)^\s*what\s+do\s+you\s+(?:know|remember)\s+about\s+(.+?)\??\s*$",r"(?is)^\s*recall\s+(?:the\s+)?(.+?)\??\s*$"]:
            m=re.match(p,text.strip())
            if m:return m.group(1).strip(" \"'.,!?")
        return None

    def _internal_answer(self,query:str)->str:
        hits=self.retriever.search(query,limit=6)
        if hits and hits[0]["score"]>=1.0:
            top=hits[0]; return f"{top['key']} is {top['value']}."
        return "I do not have enough stored knowledge to answer that yet. I can learn it if you provide the missing information."

    def _run_goal(self,goal_id:int,max_steps:int=16)->tuple[str,bool]:
        goal=self.store.goal(goal_id)
        if not goal:return "That goal does not exist.",False
        executed=0; outputs=[]; overall=True
        for step in goal["steps"]:
            if executed>=max_steps: overall=False; outputs.append("Step budget reached; goal remains resumable."); break
            if step["status"]!="pending":continue
            args=json.loads(step["args_json"]); ok=True; result=None
            if step["action"]=="tool":
                name=args.pop("name")
                action={"type":"tool","name":name,"args":dict(args)}
                auth=self._authorization_chain(action,authorization="delegated",source_trust="trusted",stage="goal_step")
                if auth["effective"]!="allow":
                    ok=False; result=self._authorization_block_message(auth)
                else:
                    spec=self.tools.spec(name)
                    if spec and spec.external_side_effect:
                        ok=False; result="Delegated external action was blocked before Aurora request preparation; explicit human approval is required."
                    else:
                        tr=self.tools.call(name,**args); ok=tr.ok; result=tr.output if tr.ok else tr.error
            elif step["action"]=="ingest":
                action={"type":"ingest_file","path":args["path"]}
                auth=self._authorization_chain(action,authorization="delegated",source_trust="trusted",stage="goal_step")
                if auth["effective"]!="allow": ok=False; result=self._authorization_block_message(auth)
                else: result,ok=self._ingest_file(args["path"])
            else:
                op=args.get("operation"); q=args.get("query",goal["goal"])
                if op=="retrieve":result=self.retriever.search(q,limit=5)
                elif op in {"answer","summarize"}:result=self._internal_answer(q)
                else:ok=False; result="unknown internal action"
            self.store.complete_step(step["id"],result,ok); outputs.append(f"{step['step_no']}. {step['description']}: {'done' if ok else 'failed'} -> {result}"); executed+=1
            if not ok: overall=False; break
        refreshed=self.store.goal(goal_id); statuses=[s["status"] for s in refreshed["steps"]]
        if statuses and all(s=="done" for s in statuses):self.store.set_goal_status(goal_id,"completed")
        elif any(s=="failed" for s in statuses):self.store.set_goal_status(goal_id,"blocked")
        return f"Goal {goal_id}: {refreshed['goal']}\n"+"\n".join(outputs),overall

    def _ingest_file(self,path:str)->tuple[str,bool]:
        tr=self.tools.call("read_text",path=path)
        if not tr.ok:return f"Ingestion failed: {tr.error}",False
        chunks=re.split(r"(?<=[.!?])\s+|\n+",str(tr.output)); learned=0
        for chunk in chunks[:512]:
            learned+=len(self.learner.from_input(chunk,source=f"file:{path}",truth_state="ASSERTED",source_trust="untrusted"))
        return f"Ingested {path}; learned {learned} persistent knowledge items.",True

    def _gate_context(self,action:dict[str,Any],*,human_approved:bool,source_trust:str,candidate_evidence:list[dict[str,Any]]|None=None)->dict[str,Any]:
        action=dict(action or {}); spec=self.tools.spec(action.get("name")) if action.get("type")=="tool" else None
        if spec:
            action.setdefault("external_side_effect",spec.external_side_effect); action.setdefault("irreversible",spec.irreversible); action.setdefault("sensitive_data",spec.sensitive_data); action.setdefault("policy_declared",spec.policy_declared)
            flags=set(action.get("policy_flags",[])); flags.update(spec.policy_flags); action["policy_flags"]=sorted(flags)
        cap=self.capabilities.evaluate(action,human_approved=human_approved)
        capsule=IntentCapsule.from_action(action,required_capability=cap.required_level,authorization_basis=("explicit human approval" if human_approved else "delegated/model-internal"),evidence_present=bool(candidate_evidence),source_trust=source_trust)
        return {"human_approved":human_approved,"source_trust":source_trust,"candidate_evidence":candidate_evidence or [],"capability_decision":cap,"intent_capsule":capsule,"effective_action":action,"trajectory":[]}

    @staticmethod
    def _effective_verdict(*verdicts:str)->str:
        order={"allow":0,"abstain":0,"require_approval":2,"uncertain":3,"deny":4}
        return max(verdicts,key=lambda v:order.get(v,4))

    def _authorization_chain(self,action:dict[str,Any],*,authorization:str,source_trust:str,stage:str,candidate_evidence:list[dict[str,Any]]|None=None)->dict[str,Any]:
        human_approved=authorization=="explicit"; ctx=self._gate_context(action,human_approved=human_approved,source_trust=source_trust,candidate_evidence=candidate_evidence)
        pd=self.policy.evaluate_action(ctx["effective_action"],authorization=authorization,source_trust=source_trust,stage=stage) if self.policy else PolicyDecision("allow",(),"No policy gate configured.")
        kernel=self.kernel.evaluate(ctx["effective_action"],ctx["intent_capsule"],human_approved=human_approved)
        guardian=self.guardians.evaluate(ctx["effective_action"],ctx)
        effective=self._effective_verdict(ctx["capability_decision"].verdict,kernel.verdict,guardian["verdict"],pd.verdict)
        return {**ctx,"policy_decision":pd,"kernel_decision":kernel,"guardian_decision":guardian,"effective":effective}

    def _authorization_block_message(self,auth:dict[str,Any])->str:
        pd=auth["policy_decision"]; cap=auth["capability_decision"]; kernel=auth["kernel_decision"]; guardian=auth["guardian_decision"]
        if pd.verdict!="allow":return self.policy.protected_response(pd) if self.policy else pd.reason
        if kernel.verdict!="allow":return f"Action {('paused' if kernel.verdict=='require_approval' else 'blocked')} by the Genesis Constitutional Kernel: {kernel.reason}"
        if cap.verdict!="allow":return f"Action {('paused' if cap.verdict=='require_approval' else 'blocked')} by Genesis capability policy: {cap.reason}"
        if guardian["verdict"]=="uncertain":return "Action paused by Genesis Guardians because material semantic uncertainty remains unresolved; provide stronger evidence, narrower scope, or a clarified authorization basis."
        return f"Action {('paused' if guardian['verdict']=='require_approval' else 'blocked')} by Genesis Guardians: {guardian['alpha']['reason']}"

    def deliberate(self,text:str,learned:list[dict])->Decision:
        c=[]; low=text.casefold().strip(); options=self._choice_options(text)
        if options:
            chosen,why,conf,evidence=self._select_option(options,text); c.append(Candidate("choose_option",f"I choose {chosen}.",500+conf*100,why,evidence))
        subject=self._recall_subject(text)
        if subject:
            hits=self.retriever.search(subject,limit=8)
            if hits:
                top=hits[0]; c.append(Candidate("knowledge_answer",f"{top['key']} is {top['value']}.",350+float(top.get("score",0))*10,"retrieved persistent knowledge",[{"fact_id":top["id"],"score":top.get("score",0)}]))
        c.append(Candidate("response",self._internal_answer(text),10,"bounded fallback",[]))
        c.sort(key=lambda x:(x.score,x.name),reverse=True); chosen=c[0]; margin=chosen.score-(c[1].score if len(c)>1 else 0); conf=min(0.99,max(0.35,0.65+margin/200))
        return Decision(chosen,c,conf)

    def act(self,c:Candidate,authorization:str="explicit",source_trust:str="trusted")->tuple[str,bool,str]:
        a=c.action or {}; typ=a.get("type"); human_approved=authorization=="explicit"
        ctx=self._gate_context(a,human_approved=human_approved,source_trust=source_trust,candidate_evidence=c.evidence)
        capsule=ctx["intent_capsule"]; cap=ctx["capability_decision"]
        pd=self.policy.evaluate_action(a,authorization=authorization,source_trust=source_trust,stage="pre_action") if (self.policy and typ) else None
        kernel=self.kernel.evaluate(ctx["effective_action"],capsule,human_approved=human_approved)
        guardian=self.guardians.evaluate(ctx["effective_action"],ctx)
        effective=self._effective_verdict(cap.verdict,kernel.verdict,guardian["verdict"],pd.verdict if pd else "allow")
        if pd and pd.verdict!="allow":return self.policy.protected_response(pd),False,f"policy {pd.verdict}"
        if kernel.verdict!="allow":return f"Action {('paused' if kernel.verdict=='require_approval' else 'blocked')} by the Genesis Constitutional Kernel: {kernel.reason}",False,f"kernel {kernel.verdict}"
        if cap.verdict!="allow":return f"Action {('paused' if cap.verdict=='require_approval' else 'blocked')} by Genesis capability policy: {cap.reason}",False,f"capability {cap.verdict}"
        if guardian["verdict"]!="allow":
            if guardian["verdict"]=="uncertain":return "Action paused by Genesis Guardians because material semantic uncertainty remains unresolved; provide stronger evidence, narrower scope, or a clarified authorization basis.",False,"guardian uncertain"
            return f"Action {('paused' if guardian['verdict']=='require_approval' else 'blocked')} by Genesis Guardians: {guardian['alpha']['reason']}",False,f"guardian {guardian['verdict']}"
        if effective!="allow":return "Action did not obtain a complete Genesis Model authorization.",False,f"authorization {effective}"
        if not typ:
            for e in c.evidence:
                if "fact_id" in e:self.store.mark_fact_used(int(e["fact_id"]))
            return c.response,True,"response emitted"
        action_id=str(uuid.uuid4()); spec=self.tools.spec(a.get("name")) if typ=="tool" else None
        if spec and spec.external_side_effect:
            boundary_action={**a,"external_side_effect":True}
            proof=self.engine_boundary.issue_authorization_proof(action=boundary_action,capsule=capsule,capability=cap.required_level,constitution_sha256=(self.policy.sha256 if self.policy else "none"),guardian=guardian,kernel=kernel,policy=(pd or PolicyDecision("allow",(),"No policy gate required.")))
            req=self.engine_boundary.prepare(boundary_action,cap.required_level,"allow",proof)
            stored_action={**boundary_action,"_intent_id":capsule.intent_id,"_model_authorization_proof":proof.record()}
            self.store.prepare_action(action_id,typ,stored_action,engine_request_id=req.request_id)
            return f"Prepared Aurora Engine request {req.request_id} with Model Authorization Proof {proof.proof_id}; Genesis did not execute the external action directly.",True,"engine request prepared"
        self.store.prepare_action(action_id,typ,a); self.store.set_action_state(action_id,"EXECUTING")
        def finish(output:str,ok:bool,note:str)->tuple[str,bool,str]:
            self.store.set_action_state(action_id,"COMMITTED" if ok else "FAILED",{"output":output,"note":note}); return output,ok,note
        try:
            if typ=="mark_rule": self.store.mark_rule_used(int(a["rule_id"])); return finish(c.response,True,"learned rule executed")
            if typ=="tool":
                tr=self.tools.call(a["name"],**a.get("args",{})); return finish((str(tr.output) if tr.ok else f"Tool failed: {tr.error}"),tr.ok,("tool succeeded" if tr.ok else "tool failed"))
            if typ=="create_goal":
                gid=self.planner.create(a["goal"]); goal=self.store.goal(gid); plan="; ".join(f"{st['step_no']}. {st['description']}" for st in goal["steps"]); return finish(f"Goal {gid} created. Plan: {plan}",True,"goal persisted")
            if typ=="run_goal":
                out,ok=self._run_goal(int(a["goal_id"])); return finish(out,ok,("goal cycle completed" if ok else "goal blocked or partial"))
            if typ=="retry_goal":
                gid=int(a["goal_id"]); goal=self.store.goal(gid)
                if not goal:return finish("That goal does not exist.",False,"goal missing")
                reset=self.store.reset_failed_goal_steps(gid)
                if reset==0 and goal["status"]=="completed":return finish(f"Goal {gid} is already completed.",True,"goal already completed")
                out,ok=self._run_goal(gid); return finish(out,ok,("goal retry completed" if ok else "goal retry blocked"))
            if typ=="cancel_goal":
                gid=int(a["goal_id"]); ok=self.store.cancel_goal(gid); return finish((f"Goal {gid} cancelled." if ok else "That goal does not exist."),ok,("goal cancelled" if ok else "goal missing"))
            if typ=="forget_fact":
                ok=self.store.deactivate_fact(a["key"],source=a.get("source","interaction")); return finish((f"Forgot persistent fact: {a['key']}." if ok else f"I do not have an active fact named {a['key']} to forget."),ok,("fact deactivated" if ok else "fact missing"))
            if typ=="ingest_file":
                out,ok=self._ingest_file(a["path"]); return finish(out,ok,("file ingested" if ok else "ingestion failed"))
            if typ=="learn_skill":
                item=self.store.learn_skill(a["name"],f"Learned executable skill {a['name']}",a["steps"],source=a["source"]); return finish(f"{item['status'].capitalize()} skill {a['name']} with {len(a['steps'])} steps.",True,"skill stored")
            if typ=="execute_skill":
                out,ok=self._execute_skill(a["name"]); return finish(out,ok,("skill executed" if ok else "skill failed"))
            return finish("Action type is not implemented.",False,"unknown action type")
        except Exception as exc:
            self.store.set_action_state(action_id,"FAILED",{"error":f"{type(exc).__name__}: {exc}"}); raise

    def respond(self,text:str)->tuple[str,dict[str,Any]]:
        source_trust="trusted"; learning_policy=self.policy.learning_gate(text) if self.policy else None
        if learning_policy and learning_policy.verdict!="allow":
            learned=[]; decision=Decision(Candidate("policy_block",self.policy.protected_response(learning_policy),1_000_000,"Covenant protects its own invariants",[{"policy":learning_policy.record()}]),[],0.99); decision.candidates=[decision.chosen]
        else:
            learned=self.learner.from_input(text); decision=self.deliberate(text,learned)
        did=self.store.record_decision(text,[x.record() for x in decision.candidates],decision.chosen.name,decision.chosen.rationale,decision.confidence)
        answer,ok,outcome=self.act(decision.chosen)
        self.store.add_reflection(did,"success" if ok else "failure",f"{outcome}; confidence={decision.confidence:.3f}")
        if ok and decision.confidence>=0.85 and decision.chosen.name not in {"knowledge_answer"}:self.store.add_training_example(text,answer,"validated cognition",decision.confidence)
        return answer,{"source_trust":source_trust,"decision_id":did,"chosen_action":decision.chosen.name,"rationale":decision.chosen.rationale,"confidence":decision.confidence,"learned":learned,"outcome":"success" if ok else "failure","candidates":[x.record() for x in decision.candidates]}
