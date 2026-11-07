"""Private Kyro research-only Genesis neural inference Lambda.

Image contains SHA-verified local Qwen base and experimental LoRA r2.
Does NOT expose execution tools, AWS admin powers, autonomous agents, or
changes to Aurora. API Gateway JWT authentication and DynamoDB usage limits.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path


_MODEL = None


def _reply(status: int, data: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store, private",
            "x-content-type-options": "nosniff",
            "referrer-policy": "no-referrer",
        },
        "body": json.dumps(data, separators=(",", ":"), ensure_ascii=False),
    }


def _principal(event):
    if not isinstance(event, dict):
        return None
    request=event.get("requestContext") or {}
    auth=request.get("authorizer") or {}
    jwt=auth.get("jwt") or {}
    claims=jwt.get("claims") or {}
    if (
        not isinstance(claims, dict)
        or claims.get("iss") != os.environ.get("KYRO_JWT_ISSUER")
        or claims.get("aud") != os.environ.get("KYRO_JWT_AUDIENCE")
        or claims.get("token_use") != "id"
        or not isinstance(claims.get("sub"), str)
        or len(claims["sub"]) > 150
    ):
        return None
    try:
        if int(claims["exp"]) < time.time():
            return None
    except (KeyError, ValueError, TypeError):
        return None
    return claims["sub"]


def _backend():
    global _MODEL
    if _MODEL is None:
        import torch
        torch.set_num_threads(2)
        from genesis.hf_backend import HuggingFaceBackend
        base=HuggingFaceBackend(
            model_dir="/var/task/model",
            enabled=True,
            adapter_enabled=True,
            adapter_dir="/var/task/adapter",
            adapter_metrics="/var/task/adapter-metrics.json",
            max_calls=25,
            max_output_tokens=96,
        )
        if not base.available():
            raise RuntimeError("verified experimental model unavailable")
        _MODEL=base
    # The quota below is the actual cross-container usage bound. The
    # local adapter's 25-call counter is not a billing limit.
    if _MODEL.call_count>=_MODEL.max_calls:
        _MODEL.call_count=0
    return _MODEL


def _charge_quota(subject):
    """Before inference: at most 80 monthly total and 10 daily per user.

    An attempted request counts even if the model later fails.
    """
    import boto3
    from botocore.exceptions import ClientError
    now=dt.datetime.now(dt.timezone.utc)
    yearmonth=now.strftime("%Y-%m")
    day=now.strftime("%Y-%m-%d")
    table=os.environ["GENESIS_NEURAL_LIMITS_TABLE"]
    ddb=boto3.client("dynamodb",region_name=os.environ.get("AWS_REGION","ap-southeast-2"))
    keyhash=hashlib.sha256(subject.encode("utf-8")).hexdigest()[:32]
    records=[
        ("GLOBAL#GENESIS","MONTH#"+yearmonth,80),
        ("USER#"+keyhash,"DAY#"+day,10),
    ]
    for pk,sk,cap in records:
        try:
            ddb.update_item(
                TableName=table,
                Key={"pk":{"S":pk},"sk":{"S":sk}},
                UpdateExpression="SET expires_at=:expiry ADD requests :increment",
                ConditionExpression="attribute_not_exists(requests) OR requests < :cap",
                ExpressionAttributeValues={
                    ":increment":{"N":"1"},
                    ":cap":{"N":str(cap)},
                    ":expiry":{"N":str(int((now+dt.timedelta(days=40)).timestamp()))},
                },
            )
        except ClientError as e:
            if e.response.get("Error",{}).get("Code")=="ConditionalCheckFailedException":
                return False
            raise
    return True


def lambda_handler(event, context):
    if not _principal(event):
        return _reply(401,{"error":"Authenticated Kyro identity required"})
    path=str(event.get("rawPath",""))
    method=(event.get("requestContext",{}).get("http",{}) or {}).get("method","")
    if method=="GET" and path=="/api/v3/neural/status":
        return _reply(200,{
            "service":"genesis-neural-research",
            "status":"candidate_inference_available",
            "base":"Qwen2.5-0.5B-Instruct",
            "adapter":"experimental LoRA round 2",
            "test_status":"research_only_not_production_qualified",
            "model_loaded":_MODEL is not None,
            "aurora_execution":"disabled",
            "training":"independent candidate-only automation",
            "limits":{"monthly_total_requests":80,"daily_per_user":10},
        })
    if method!="POST" or path!="/api/v3/neural/chat":
        return _reply(404,{"error":"Unknown neural research route"})
    if event.get("isBase64Encoded"):
        return _reply(400,{"error":"Unsupported request encoding"})
    raw=event.get("body")
    if not isinstance(raw,str) or len(raw.encode("utf-8"))>5500:
        return _reply(400,{"error":"Request body missing or too large"})
    try:
        data=json.loads(raw)
    except (ValueError,TypeError):
        return _reply(400,{"error":"Malformed JSON request"})
    text=data.get("message") if isinstance(data,dict) else None
    if not isinstance(text,str) or not 1<=len(text.strip())<=2500:
        return _reply(400,{"error":"Message must be 1–2500 characters"})
    try:
        if not _charge_quota(_principal(event)):
            return _reply(429,{"error":"Research inference quota reached"})
    except Exception:
        return _reply(503,{"error":"Quota service unavailable. Inference disabled."})
    try:
        from genesis import Genesis
        backend=_backend()
        # Isolate user session/memory per invocation. No cross-tenant persistence,
        # workspace writes only to a disposable /tmp directory.
        with tempfile.TemporaryDirectory(prefix="genesis-private-") as tmp:
            with Genesis(
                state_path=Path(tmp)/"genesis.sqlite3",
                workspace=Path(tmp)/"workspace",
                backend=backend,
                profile_id="serverless-private"
            ) as model:
                response=model.respond_with_trace(text.strip())
        return _reply(200,{
            "service":"genesis-neural-research",
            "model":"Qwen2.5-0.5B-Instruct + unpromoted LoRA r2",
            "answer":response["answer"],
            "chosen_action":response["trace"].get("chosen_action"),
            "experimental":True,
            "aurora_execution":"disabled",
            "disclaimer":"Experimental model: facts and important decisions require verification.",
        })
    except Exception:
        # No raw errors, user messages or tokens in logs.
        return _reply(503,{"error":"Experimental Genesis inference unavailable"})
