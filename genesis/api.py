from __future__ import annotations

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from .model import Genesis

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
