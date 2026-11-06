"""Authenticated local research interface for Genesis.

This app deliberately refuses to start without a strong access token. It must
not be exposed directly to public networks; it is not a production identity
or multi-tenant authorization system.
"""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from genesis import Genesis

STATIC = Path(__file__).resolve().parent / "static"


def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.environ.get("KYRO_ACCESS_TOKEN", "")
    if len(expected) < 24:
        raise HTTPException(status_code=503, detail="Kyro authentication is not configured")
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Authentication required")
    supplied = authorization[len(prefix):]
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid credentials")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(os.environ.get("KYRO_ACCESS_TOKEN", "")) < 24:
        raise RuntimeError("KYRO_ACCESS_TOKEN must contain at least 24 characters")
    # Genesis remains the cognitive Model. The Aurora Engine is NOT embedded.
    model = Genesis(enable_ollama=os.environ.get("GENESIS_GENERATOR", "none").lower() == "ollama")
    app.state.genesis = model
    try:
        yield
    finally:
        model.close()


app = FastAPI(
    title="Kyro Local Alpha",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def hardening_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )
    return response


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=16000)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/assets/app.js")
def javascript():
    return FileResponse(STATIC / "app.js", media_type="application/javascript")


@app.get("/assets/style.css")
def stylesheet():
    return FileResponse(STATIC / "style.css", media_type="text/css")


@app.get("/api/status", dependencies=[Depends(require_token)])
def status():
    g = app.state.genesis
    return {
        "service": "kyro-local-alpha",
        "model": "Genesis",
        "model_version": g.VERSION,
        "model_health": g.self_check(),
        "aurora_attached": False,
        "public_deployment_qualified": False,
    }


@app.post("/api/chat", dependencies=[Depends(require_token)])
def chat(req: ChatRequest):
    # Do not expose Genesis traces or Engine credentials in a user-facing route.
    return {"answer": app.state.genesis.respond(req.message)}
