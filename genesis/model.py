from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .backends import GeneratorBackend, OllamaBackend
from .bedrock_backend import BedrockBackend
from .cognition import CognitionEngine
from .storage import Store
from .tools import ToolRegistry
from .policy import PolicyEngine
from .guardians import GuardianCouncil
from .capabilities import CapabilityController
from .engine_boundary import EngineBoundary, EngineReceipt
from .realignment import RealignmentSchool
from .knowledge_modules import KnowledgeModuleStore
from .task_assurance import TaskLedger
from .user_capabilities import UserCapabilityServices
from .memory_network import MemoryNetwork

ROOT=Path(__file__).resolve().parent.parent


def _default_data_dir()->Path:
    base=Path(os.environ.get("XDG_DATA_HOME",Path.home()/".local"/"share"))
    return base/"aurora"/"genesis"


class Genesis:
    """Stable public Genesis Model API. Aurora Engine remains a separate system."""
    VERSION="v0.1"
    def __init__(self,state_path:str|Path|None=None,workspace:str|Path|None=None,backend:GeneratorBackend|None=None,enable_ollama:bool|None=None,ollama_model:str="qwen2.5-coder:1.5b",profile_id:str="local"):
        cfg=ROOT/"config"
        self.identity=json.loads((cfg/"identity.json").read_text(encoding="utf-8")); self.heritage=json.loads((cfg/"heritage.json").read_text(encoding="utf-8")); self.model_record=json.loads((cfg/"model_record.json").read_text(encoding="utf-8"))
        data_dir=_default_data_dir(); data_dir.mkdir(parents=True,exist_ok=True)
        state_path=state_path or os.environ.get("GENESIS_STATE_PATH") or data_dir/"genesis_state.sqlite3"
        workspace=workspace or os.environ.get("GENESIS_WORKSPACE") or data_dir/"workspace"
        self.store=Store(state_path); self.tools=ToolRegistry(workspace)
        self.knowledge_modules=KnowledgeModuleStore(self.store)
        self.assurance=TaskLedger(self.store)
        self.user_capabilities=UserCapabilityServices(self.store,profile_id)
        self.memory=MemoryNetwork(self.store,profile_id)  # opt-in; does not write until consent
        self.policy=PolicyEngine(cfg/"model_constitution.json",self.tools,self.store)
        self.guardians=GuardianCouncil()
        self.realignment_school=RealignmentSchool()
        self.capabilities=CapabilityController(granted_level=os.environ.get("GENESIS_CAPABILITY_LEVEL","C4"))
        self.engine_boundary=EngineBoundary(model_release=self.identity.get("full_name","Genesis v0.1"), minimum_engine=self.identity.get("minimum_engine","Aurora pre-v0.1"))
        generator_mode=os.environ.get("GENESIS_GENERATOR","auto").casefold()
        use_ollama = (enable_ollama is True) or (enable_ollama is None and generator_mode in {"auto","ollama"})
        if backend is None and generator_mode == "bedrock":
            # Explicit two-switch opt-in. No implicit AWS usage in auto mode.
            backend=BedrockBackend(
                model=os.environ.get("GENESIS_BEDROCK_MODEL_ID","apac.amazon.nova-micro-v1:0"),
                region=os.environ.get("GENESIS_BEDROCK_REGION","ap-southeast-2"),
                enabled=os.environ.get("GENESIS_BEDROCK_ENABLE","").lower() in {"1","true","yes"},
                max_output_tokens=int(os.environ.get("GENESIS_BEDROCK_MAX_TOKENS","256")),
                max_calls=int(os.environ.get("GENESIS_BEDROCK_MAX_CALLS","8")),
            )
        if backend is None and use_ollama: backend=OllamaBackend(model=os.environ.get("GENESIS_OLLAMA_MODEL",ollama_model))
        self.cognition=CognitionEngine(self.store,self.identity,self.heritage,self.model_record,self.tools,backend,self.policy,self.guardians,self.capabilities,self.engine_boundary)
        self.cognition.knowledge_modules=self.knowledge_modules
        self.last_trace:dict[str,Any]|None=None
        self._turn_lock=threading.RLock()

    def respond(self,text:str)->str:
        if not isinstance(text,str) or not text.strip(): return "Please provide a non-empty message."
        if len(text)>100000: return "Message exceeds the 100,000 character model-input limit."
        with self._turn_lock:
            self.store.add_episode("user",text,0.6)
            answer,trace=self.cognition.respond(text)
            self.store.add_episode("assistant",answer,0.6)
            self.last_trace=trace
            return answer

    def respond_with_trace(self,text:str)->dict[str,Any]:
        answer=self.respond(text); return {"answer":answer,"trace":self.last_trace}

    def state(self)->dict[str,Any]:
        return {"version":self.VERSION,"identity":self.identity,"lineage":self.heritage.get("lineage"),"record_version":self.model_record.get("record_version"),"constitution":self.policy.summary(),"capability_level":self.capabilities.granted_level,"guardians":{"alpha":self.guardians.alpha.guardian_id,"omegas":[g.guardian_id for g in self.guardians.omegas],"challenge":self.guardians.challenge.guardian_id,"jury_size":len(self.guardians.omegas)},"engine_boundary":{"minimum_engine":self.engine_boundary.minimum_engine,"pending_requests":len(self.store.pending_engine_actions())},"stats":self.store.stats(),"tools":self.tools.specs(),"last_decision":self.store.last_decision(),"last_reflection":self.store.last_reflection(),"active_goals":self.store.active_goals(),"knowledge_modules":self.knowledge_modules.list(),"realignment_school":{"version":self.realignment_school.VERSION,"cases":len(self.realignment_school.curriculum()),"autonomous_updates":False},"backend":{"name":self.cognition.backend.name,"available":self.cognition.backend.available()},"health":self.self_check()}

    def self_check(self)->dict[str,Any]:
        checks={}
        try:
            checks["database"]=self.store.db.execute("PRAGMA quick_check").fetchone()[0]=="ok"
        except Exception:
            checks["database"]=False
        checks["identity_loaded"]=bool(self.identity.get("model_name") and self.identity.get("system_role"))
        checks["model_record_loaded"]=self.model_record.get("record_version")==self.VERSION
        checks["required_tools"]=all(self.tools.has(n) for n in ("calculate","read_text","write_note","list_workspace"))
        checks["constitution_integrity"]=self.policy.integrity_ok
        checks["constitution_complete"]=len(self.policy.commandment_ids)==10 and len(set(self.policy.commandment_ids))==10
        checks["guardian_topology"]=len(self.guardians.omegas)>=7 and bool(self.guardians.alpha.guardian_id)
        checks["challenge_omega"]=getattr(self.guardians.challenge,"guardian_id",None)=="omega-challenge"
        checks["constitutional_kernel"]=hasattr(self.cognition,"kernel")
        checks["intent_capsule_gate"]=hasattr(self.cognition,"_authorization_chain")
        checks["capability_ceiling"]=self.capabilities.granted_level in {"C0","C1","C2","C3","C4","C5"}
        checks["engine_separation"]=self.engine_boundary.minimum_engine.startswith("Aurora ")
        return {"ok":all(checks.values()),"checks":checks}

    def goal(self,goal_id:int)->dict[str,Any]|None:return self.store.goal(goal_id)
    def decision_history(self,limit:int=20)->list[dict[str,Any]]:return self.store.recent_decisions(limit)

    def search_knowledge(self,query:str,limit:int=8)->list[dict[str,Any]]: return self.cognition.retriever.search(query,limit=limit)
    def export_state(self,path:str|Path)->Path:return self.store.export_json(path)
    def backup_state(self,path:str|Path)->Path:return self.store.backup(path)
    def register_tool(self,name:str,description:str,fn,mutating:bool=False,**policy)->None:self.tools.register(name,description,fn,mutating,**policy)
    def constitution(self)->dict[str,Any]:return self.policy.summary()
    def policy_audit(self,limit:int=50)->list[dict[str,Any]]:return self.store.recent_policy_audit(limit)
    def pending_engine_actions(self,limit:int=100)->list[dict[str,Any]]:return self.store.pending_engine_actions(limit)

    def reconcile_engine_receipt(self,receipt:EngineReceipt)->dict[str,Any]:
        """Apply one authoritative Aurora Engine receipt to a PREPARED action.

        Receipt IDs are persistence-backed anti-replay keys. Re-applying the exact
        same receipt is idempotent; a different receipt for an already-finalized
        request is rejected.
        """
        if not receipt.receipt_id:
            return {"accepted":False,"reason":"receipt_id is required"}
        if receipt.status not in {"COMMITTED","FAILED","CANCELLED"}:
            return {"accepted":False,"reason":"invalid terminal receipt status"}
        tx=self.store.action_by_engine_request(receipt.request_id)
        if not tx:
            return {"accepted":False,"reason":"unknown engine request"}
        used=self.store.action_by_engine_receipt(receipt.receipt_id)
        if used and used["action_id"]!=tx["action_id"]:
            return {"accepted":False,"reason":"receipt replay detected"}
        if tx["state"] in {"COMMITTED","FAILED","CANCELLED"}:
            same=(tx.get("engine_receipt_id")==receipt.receipt_id and tx["state"]==receipt.status)
            return {"accepted":bool(same),"idempotent":bool(same),"state":tx["state"],"reason":"already reconciled" if same else "request already finalized"}
        if tx["state"]!="PREPARED":
            return {"accepted":False,"reason":f"request is not awaiting an Engine receipt: {tx['state']}"}
        self.store.set_action_state(tx["action_id"],receipt.status,{"result":receipt.result,"error":receipt.error},engine_receipt_id=receipt.receipt_id)
        return {"accepted":True,"idempotent":False,"state":receipt.status,"action_id":tx["action_id"],"request_id":receipt.request_id,"receipt_id":receipt.receipt_id}

    def install_knowledge_module(self, package:dict[str,Any], *, replace:bool=False)->dict[str,Any]:
        """Explicit installation of data-only reference material. No Engine privileges."""
        with self._turn_lock:
            return self.knowledge_modules.install(package, replace=replace)

    def list_knowledge_modules(self)->list[dict[str,Any]]:
        return self.knowledge_modules.list()

    def search_knowledge_modules(self, query:str, limit:int=5)->list[dict[str,Any]]:
        return self.knowledge_modules.search(query, limit)

    def enable_knowledge_module(self, module_id:str, enabled:bool=True)->dict[str,Any]:
        with self._turn_lock:
            return self.knowledge_modules.set_enabled(module_id, enabled)

    def uninstall_knowledge_module(self, module_id:str)->dict[str,Any]:
        with self._turn_lock:
            return self.knowledge_modules.uninstall(module_id)

    # Outcome assurance is observational. These operations never dispatch tools or
    # grant Aurora execution privileges. No task is complete without an explicit
    # review of evidence against every declared acceptance criterion.
    def create_task(self,title:str,criteria:list[str],priority:int=50,due_at:str|None=None)->dict[str,Any]:
        return self.assurance.create(title,criteria,priority,due_at)

    def tasks(self,limit:int=100)->list[dict[str,Any]]: return self.assurance.list(limit)
    def task(self,task_id:str)->dict[str,Any]: return self.assurance.get(task_id)
    def due_tasks(self,now:str|None=None,limit:int=100)->list[dict[str,Any]]: return self.assurance.due(now,limit)
    def task_events(self,task_id:str)->list[dict[str,Any]]: return self.assurance.events(task_id)
    def task_attention(self,now:str|None=None,limit:int=50)->list[dict[str,Any]]: return self.assurance.attention(now,limit)
    def transition_task(self,task_id:str,action:str)->dict[str,Any]: return self.assurance.transition(task_id,action)
    def add_task_evidence(self,task_id:str,criterion_index:int,observation:str,reference:str,source_type:str="user")->dict[str,Any]:
        return self.assurance.submit_evidence(task_id,criterion_index,observation,reference,source_type)
    def review_task_evidence(self,task_id:str,evidence_id:str,accepted:bool,reviewer:str)->dict[str,Any]:
        return self.assurance.review_evidence(task_id,evidence_id,accepted,reviewer)
    def complete_task(self,task_id:str,reviewer:str,human_confirmed:bool=False)->dict[str,Any]:
        return self.assurance.complete(task_id,reviewer,human_confirmed)

    # The following are opt-in, profile-scoped *reference* methods. Profile
    # selection and consent changes MUST be authenticated/authorized in Kyro.
    # They do not grant Aurora tool authority and do not alter legacy respond()
    # episode storage (which requires separate privacy migration).
    def ux_consents(self)->dict[str,bool]: return self.user_capabilities.consents()
    def ux_set_consent(self,scope:str,enabled:bool)->dict[str,Any]:
        result=self.user_capabilities.consent(scope,enabled)
        if scope=="memory" and not enabled: self.memory.clear_volatile()
        return result
    def ux_remember(self,kind:str,key:str,value:str,*,source:str="user_explicit",
                    expires_at:str|None=None)->dict[str,Any]:
        return self.user_capabilities.remember(kind,key,value,source=source,expires_at=expires_at)
    def ux_recall(self,kind:str,query:str="",limit:int=30)->list[dict[str,Any]]:
        return self.user_capabilities.recall(kind,query,limit)
    def ux_forget(self,kind:str,key:str)->bool: return self.user_capabilities.forget(kind,key)
    def ux_add_claim(self,statement:str,sources:list[dict[str,str]]|None=None)->dict[str,Any]:
        return self.user_capabilities.add_claim(statement,sources)
    def ux_review_claim(self,claim_id:str,supported:bool,reviewer:str)->dict[str,Any]:
        return self.user_capabilities.review_claim(claim_id,supported,reviewer)
    def ux_propose_nudge(self,title:str,due_at:str)->dict[str,Any]:
        return self.user_capabilities.propose_nudge(title,due_at)
    def ux_attention(self,now:str|None=None,limit:int=30)->list[dict[str,Any]]:
        return self.user_capabilities.attention(now,limit)
    def ux_dismiss_nudge(self,nudge_id:str)->bool:
        return self.user_capabilities.dismiss_nudge(nudge_id)
    def ux_compare_options(self,criteria:list[dict[str,Any]],
                           options:list[dict[str,Any]])->dict[str,Any]:
        return self.user_capabilities.compare_options(criteria,options)
    def ux_export_profile(self)->dict[str,Any]: return self.user_capabilities.export_profile()
    def ux_erase_profile(self)->dict[str,Any]:
        result=self.user_capabilities.erase_profile()
        self.memory.clear_volatile()
        return result

    def close(self)->None:self.store.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
