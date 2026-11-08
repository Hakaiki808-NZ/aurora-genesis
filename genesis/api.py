from __future__ import annotations

import hmac
import os
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .model import Genesis
from .knowledge_modules import KnowledgeModuleError
from .task_assurance import TaskError

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
@app.get("/neural/status")
def neural_status():
    backend = model.cognition.backend
    if backend.name == "neurol":
        backend.available()
        return backend.status()
    return {"name": backend.name, "neurol_selected": False}

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

# Public discovery is read-only; mutations reuse the private module admin gate.
@app.get("/addons")
def addons(): return {"addons":model.list_addons()}

@app.get("/addons/catalog")
def addons_catalog():
    catalogue = Path(__file__).resolve().parent.parent / "examples" / "addons" / "catalog.json"
    return json.loads(catalogue.read_text(encoding="utf-8"))

@app.get("/addons/{addon_id}/syllabus")
def addon_syllabus(addon_id:str):
    try: return model.addon_syllabus(addon_id)
    except KnowledgeModuleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.post("/addons")
def install_addon(req:ModuleInstallRequest,_admin:None=Depends(require_module_admin)):
    try: return model.install_addon(req.package,replace=req.replace)
    except KnowledgeModuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/addons/{addon_id}/status")
def set_addon_status(addon_id:str,req:ModuleStatusRequest,
                     _admin:None=Depends(require_module_admin)):
    try: return model.set_addon_enabled(addon_id,req.enabled)
    except KnowledgeModuleError as exc:
        raise HTTPException(status_code=409 if addon_id=="genesis-core" else 404,
                            detail=str(exc)) from exc

@app.delete("/addons/{addon_id}")
def remove_addon(addon_id:str,_admin:None=Depends(require_module_admin)):
    try: return model.uninstall_addon(addon_id)
    except KnowledgeModuleError as exc:
        raise HTTPException(status_code=409 if addon_id=="genesis-core" else 404,
                            detail=str(exc)) from exc


# Task assurance routes are intentionally control-plane only. Kyro must keep
# GENESIS_CONTROL_TOKEN server-side and authenticate the actual end-user before
# using these endpoints. If no strong token is configured, routes are disabled.
def require_task_control(x_genesis_control_token: str | None = Header(default=None, alias="X-Genesis-Control-Token")):
    expected=os.environ.get("GENESIS_CONTROL_TOKEN","")
    if len(expected)<32:
        raise HTTPException(status_code=503,detail="task control disabled: set GENESIS_CONTROL_TOKEN (32+ chars)")
    if not x_genesis_control_token or not hmac.compare_digest(expected,x_genesis_control_token):
        raise HTTPException(status_code=401,detail="invalid task control credential")
    return True


@app.exception_handler(TaskError)
async def task_error_handler(request,exc:TaskError):
    return JSONResponse(status_code=404 if "not found" in str(exc) else 400,
                        content={"detail":str(exc)})


class TaskCreate(BaseModel):
    title:str=Field(min_length=1,max_length=240)
    criteria:list[str]=Field(min_length=1,max_length=20)
    priority:int=Field(default=50,ge=0,le=100)
    due_at:str|None=None


class TaskTransition(BaseModel):
    action:str=Field(min_length=1,max_length=24)


class TaskEvidence(BaseModel):
    criterion_index:int=Field(ge=0)
    observation:str=Field(min_length=1,max_length=2000)
    reference:str=Field(min_length=1,max_length=1000)
    source_type:str="user"


class TaskEvidenceReview(BaseModel):
    accepted:bool
    reviewer:str=Field(min_length=1,max_length=120)


class TaskCompletion(BaseModel):
    reviewer:str=Field(min_length=1,max_length=120)
    human_confirmed:bool=False


@app.post("/tasks",dependencies=[Depends(require_task_control)])
def create_task(req:TaskCreate):
    return model.create_task(req.title,req.criteria,req.priority,req.due_at)


@app.get("/tasks",dependencies=[Depends(require_task_control)])
def list_tasks(limit:int=Query(default=100,ge=1,le=500)):
    return {"tasks":model.tasks(limit)}


@app.get("/tasks/due",dependencies=[Depends(require_task_control)])
def due_tasks(limit:int=Query(default=100,ge=1,le=500)):
    # Pull-only reminder feed; no background worker or unsolicited notification.
    return {"tasks":model.due_tasks(limit=limit),"automated_notifications":False}


@app.get("/tasks/attention",dependencies=[Depends(require_task_control)])
def task_attention(limit:int=Query(default=50,ge=1,le=100)):
    return {"items":model.task_attention(limit=limit),
            "mode":"pull_only","automated_notifications":False}


@app.get("/tasks/{task_id}",dependencies=[Depends(require_task_control)])
def get_task(task_id:str):
    return model.task(task_id)


@app.get("/tasks/{task_id}/events",dependencies=[Depends(require_task_control)])
def task_events(task_id:str):
    return {"events":model.task_events(task_id)}


@app.post("/tasks/{task_id}/transition",dependencies=[Depends(require_task_control)])
def transition_task(task_id:str,req:TaskTransition):
    return model.transition_task(task_id,req.action)


@app.post("/tasks/{task_id}/evidence",dependencies=[Depends(require_task_control)])
def add_task_evidence(task_id:str,req:TaskEvidence):
    return model.add_task_evidence(task_id,req.criterion_index,req.observation,
                                   req.reference,req.source_type)


@app.post("/tasks/{task_id}/evidence/{evidence_id}/review",dependencies=[Depends(require_task_control)])
def review_task_evidence(task_id:str,evidence_id:str,req:TaskEvidenceReview):
    # Kyro must require explicit human review; a caller string is not identity proof.
    return model.review_task_evidence(task_id,evidence_id,req.accepted,req.reviewer)


@app.post("/tasks/{task_id}/complete",dependencies=[Depends(require_task_control)])
def complete_task(task_id:str,req:TaskCompletion):
    # Human-attested is not the same thing as independently machine-verified.
    return model.complete_task(task_id,req.reviewer,req.human_confirmed)
