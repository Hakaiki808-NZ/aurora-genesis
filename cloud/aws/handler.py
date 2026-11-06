"""Authenticated AWS Lambda research test adapter for the public Genesis reference model.

This is NOT Aurora and cannot perform externally privileged engine actions.
Each API Gateway JWT subject has separate short-lived, encrypted S3 state.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from genesis import Genesis

S3 = boto3.client("s3")
STATE_BUCKET = os.environ["STATE_BUCKET"]
MAX_MESSAGE = 2000
MAX_STATE = 5 * 1024 * 1024

def reply(status, obj):
    return {
        "statusCode": status,
        "headers": {
            "Cache-Control": "no-store",
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
        },
        "body": json.dumps(obj, ensure_ascii=False),
    }

def lambda_handler(event, context):
    claims = (((event or {}).get("requestContext") or {}).get("authorizer") or {}).get("jwt", {}).get("claims", {})
    subject = claims.get("sub")
    if not isinstance(subject, str) or len(subject) < 8 or len(subject) > 160:
        return reply(401, {"error": "Authenticated identity required"})
    method = ((event or {}).get("requestContext") or {}).get("http", {}).get("method", "")
    route = (event or {}).get("rawPath", "")
    if method == "GET" and route == "/api/status":
        with tempfile.TemporaryDirectory() as tmp:
            with Genesis(state_path=Path(tmp)/"state.sqlite3", workspace=Path(tmp)/"workspace", enable_ollama=False) as model:
                return reply(200, {
                    "service": "kyro-genesis-cloud-research-beta",
                    "model": "Genesis",
                    "model_version": model.VERSION,
                    "model_health": model.self_check(),
                    "aurora_attached": False,
                    "public_deployment_qualified": False,
                    "persistence": "per-user encrypted S3, seven-day test retention",
                    "model_generation": "deterministic reference, no hosted LLM",
                })
    if not (method == "POST" and route == "/api/chat"):
        return reply(404, {"error": "Not found"})

    raw = (event or {}).get("body") or ""
    if (event or {}).get("isBase64Encoded"):
        return reply(400, {"error": "Unsupported body encoding"})
    if len(raw.encode("utf-8")) > 12000:
        return reply(413, {"error": "Request exceeds test limit"})
    try:
        body = json.loads(raw)
        message = body.get("message")
    except (ValueError, AttributeError):
        return reply(400, {"error": "Expected JSON object"})
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE:
        return reply(422, {"error": "Message must be 1–2000 characters"})

    key = "test-state/" + hashlib.sha256(subject.encode("utf-8")).hexdigest() + ".sqlite3"
    etag = None
    try:
        saved = S3.get_object(Bucket=STATE_BUCKET, Key=key)
        if saved.get("ContentLength", 0) > MAX_STATE:
            return reply(413, {"error": "Stored research state exceeds test limit"})
        prior = saved["Body"].read(MAX_STATE + 1)
        if len(prior) > MAX_STATE:
            return reply(413, {"error": "Stored research state exceeds test limit"})
        etag = saved["ETag"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
            prior = None
        else:
            return reply(503, {"error": "Research state unavailable"})
    try:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "genesis.sqlite3"
            if prior is not None:
                state.write_bytes(prior)
            with Genesis(state_path=state, workspace=Path(tmp)/"workspace", enable_ollama=False) as model:
                if not model.self_check().get("ok"):
                    return reply(503, {"error": "Genesis self-check failed"})
                answer = model.respond(message)
                backup = Path(tmp) / "consistent-backup.sqlite3"
                model.backup_state(backup)
            payload = backup.read_bytes()
        if len(payload) > MAX_STATE:
            return reply(413, {"error": "Research state has reached the size limit"})
        kwargs = {
            "Bucket": STATE_BUCKET,
            "Key": key,
            "Body": payload,
            "ContentType": "application/vnd.sqlite3",
            "ServerSideEncryption": "AES256",
            "IfMatch": etag,
        } if etag else {
            "Bucket": STATE_BUCKET,
            "Key": key,
            "Body": payload,
            "ContentType": "application/vnd.sqlite3",
            "ServerSideEncryption": "AES256",
            "IfNoneMatch": "*",
        }
        try:
            S3.put_object(**kwargs)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("PreconditionFailed", "ConditionalRequestConflict", "412", "409"):
                return reply(409, {"error": "Another message updated this session. Please retry."})
            return reply(503, {"error": "Research state could not be saved"})
        return reply(200, {"answer": answer, "model": "Genesis", "aurora_attached": False})
    except Exception:
        # Do not disclose internal traces, sensitive metadata, or model content.
        return reply(500, {"error": "Cloud research request failed"})
