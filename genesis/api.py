from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Query, HTTPException, Header, Depends
from pydantic import BaseModel, Field

from .model import Genesis
from .knowledge_modules import KnowledgeModuleError

app=FastAPI(title="Genesis v0.1",version="v0.1")
model=Genesis()

class ChatRequest(BaseModel):
    message:str=Field(min_length=1,max_length=100000)
    trace:bool=False

@app.get("/health")
def health(): return {"status":"ok","model":model.identity["model_name"],"version":model.VERSION}
@app.get("/state")
def state(): return model.state()
@app.get("/diagnostics")
def diagnostics(): return model.self_check()
@app.get("/goals")
def goals(): return {"goals":model.store.goals()}
@app.get("/goals/{goal_id}")
def goal(goal_id:int): return {"goal":model.goal(goal_id)}
@app.get("/tools")
def tools(): return {"tools":model.tools.specs()}
@app.get("/constitution")
def constitution(): return model.constitution()
@app.get("/policy-audit")
def policy_audit(limit:int=Query(default=50,ge=1,le=500)): return {"entries":model.policy_audit(limit)}
@app.get("/knowledge")
def knowledge(q:str=Query(min_length=1),limit:int=Query(default=8,ge=1,le=50)): return {"results":model.search_knowledge(q,limit)}
@app.post("/chat")
def chat(req:ChatRequest): return model.respond_with_trace(req.message) if req.trace else {"answer":model.respond(req.message)}

class RealignmentAssessment(BaseModel):
    case_id:str=Field(min_length=1,max_length=64)
    choice:int=Field(ge=0,le=2)

@app.get("/realignment/curriculum")
def realignment_curriculum():
    return {"version":model.realignment_school.VERSION,
            "cases":model.realignment_school.curriculum(),
            "mode":"diagnostic_only"}

@app.post("/realignment/assess")
def realignment_assess(req:RealignmentAssessment):
    try:
        return model.realignment_school.assess(req.case_id,req.choice)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


# Administrator-only, data-only module management.
# Do not expose public installation without an authenticated owner identity,
# publisher signatures, entitlement checks and Aurora policy mediation.
class ModuleInstallRequest(BaseModel):
    package:dict[str,Any]
    replace:bool=False

class ModuleStatusRequest(BaseModel):
    enabled:bool

def require_module_admin(token:str|None=Header(default=None,alias="X-Genesis-Module-Admin")):
    expected=os.environ.get("GENESIS_MODULE_ADMIN_TOKEN","")
    if len(expected)<24:
        raise HTTPException(status_code=503,detail="module administration is disabled until a strong token is configured")
    if not token or not hmac.compare_digest(token,expected):
        raise HTTPException(status_code=403,detail="module administrator authentication required")

@app.get("/modules")
def modules(): return {"modules":model.list_knowledge_modules()}

@app.get("/modules/search")
def module_search(q:str=Query(min_length=1,max_length=5000),
                  limit:int=Query(default=5,ge=1,le=20)):
    return {"results":model.search_knowledge_modules(q,limit)}

@app.post("/modules")
def install_module(req:ModuleInstallRequest,
                   _admin:None=Depends(require_module_admin)):
    try:
        return model.install_knowledge_module(req.package,replace=req.replace)
    except KnowledgeModuleError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@app.post("/modules/{module_id}/status")
def set_module_status(module_id:str,req:ModuleStatusRequest,
                      _admin:None=Depends(require_module_admin)):
    try: return model.enable_knowledge_module(module_id,req.enabled)
    except KnowledgeModuleError as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc

@app.delete("/modules/{module_id}")
def remove_module(module_id:str,
                  _admin:None=Depends(require_module_admin)):
    try: return model.uninstall_knowledge_module(module_id)
    except KnowledgeModuleError as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc
