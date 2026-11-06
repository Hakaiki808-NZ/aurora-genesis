from __future__ import annotations

from fastapi import FastAPI, Query, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
import hmac
import os
from pydantic import BaseModel, Field

from .model import Genesis
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
