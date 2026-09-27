from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .backends import GeneratorBackend, OllamaBackend
from .cognition import CognitionEngine
from .storage import Store
from .tools import ToolRegistry
from .policy import PolicyEngine
from .guardians import GuardianCouncil
from .capabilities import CapabilityController
from .engine_boundary import EngineBoundary, EngineReceipt

ROOT=Path(__file__).resolve().parent.parent


def _default_data_dir()->Path:
    base=Path(os.environ.get("XDG_DATA_HOME",Path.home()/".local"/"share"))
    return base/"aurora"/"genesis"


class Genesis:
    """Stable public Genesis Model API. Aurora Engine remains a separate system."""
    VERSION="v0.1"
    def __init__(self,state_path:str|Path|None=None,workspace:str|Path|None=None,backend:GeneratorBackend|None=None,enable_ollama:bool|None=None,ollama_model:str="qwen2.5-coder:1.5b"):
        cfg=ROOT/"config"
        self.identity=json.loads((cfg/"identity.json").read_text(encoding="utf-8")); self.heritage=json.loads((cfg/"heritage.json").read_text(encoding="utf-8")); self.model_record=json.loads((cfg/"model_record.json").read_text(encoding="utf-8"))
        data_dir=_default_data_dir(); data_dir.mkdir(parents=True,exist_ok=True)
        state_path=state_path or os.environ.get("GENESIS_STATE_PATH") or data_dir/"genesis_state.sqlite3"
        workspace=workspace or os.environ.get("GENESIS_WORKSPACE") or data_dir/"workspace"
        self.store=Store(state_path); self.tools=ToolRegistry(workspace)
        self.policy=PolicyEngine(cfg/"model_constitution.json",self.tools,self.store)
        self.guardians=GuardianCouncil()
        self.capabilities=CapabilityController(granted_level=os.environ.get("GENESIS_CAPABILITY_LEVEL","C4"))
        self.engine_boundary=EngineBoundary(model_release=self.identity.get("full_name","Genesis v0.1"), minimum_engine=self.identity.get("minimum_engine","Aurora pre-v0.1"))
        generator_mode=os.environ.get("GENESIS_GENERATOR","auto").casefold()
        use_ollama = (enable_ollama is True) or (enable_ollama is None and generator_mode in {"auto","ollama"})
        if backend is None and use_ollama: backend=OllamaBackend(model=os.environ.get("GENESIS_OLLAMA_MODEL",ollama_model))
        self.cognition=CognitionEngine(self.store,self.identity,self.heritage,self.model_record,self.tools,backend,self.policy,self.guardians,self.capabilities,self.engine_boundary)
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
        return {"version":self.VERSION,"identity":self.identity,"lineage":self.heritage.get("lineage"),"record_version":self.model_record.get("record_version"),"constitution":self.policy.summary(),"capability_level":self.capabilities.granted_level,"guardians":{"alpha":self.guardians.alpha.guardian_id,"omegas":[g.guardian_id for g in self.guardians.omegas],"challenge":self.guardians.challenge.guardian_id,"jury_size":len(self.guardians.omegas)},"engine_boundary":{"minimum_engine":self.engine_boundary.minimum_engine,"pending_requests":len(self.store.pending_engine_actions())},"stats":self.store.stats(),"tools":self.tools.specs(),"last_decision":self.store.last_decision(),"last_reflection":self.store.last_reflection(),"active_goals":self.store.active_goals(),"backend":{"name":self.cognition.backend.name,"available":self.cognition.backend.available()},"health":self.self_check()}

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

    def close(self)->None:self.store.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
