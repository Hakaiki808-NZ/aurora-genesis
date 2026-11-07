"""Experimental Genesis neural text adapter for the private Kyro AWS workspace.

This calls a *pretrained external* Bedrock model, not a Genesis-trained
foundation model. No tools or Aurora execution are exposed. Disabled by default.
"""
import json
import os
import time
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

MODEL_ID = os.environ.get("GENESIS_NEURAL_MODEL_ID", "apac.amazon.nova-micro-v1:0")
REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
BUDGET_TABLE = os.environ.get("GENESIS_NEURAL_BUDGET_TABLE", "")
ISSUER = os.environ.get("GENESIS_INTERNAL_ISSUER", "")
AUDIENCE = os.environ.get("GENESIS_INTERNAL_AUDIENCE", "")
MAX_ATTEMPTS = max(1, min(24, int(os.environ.get("GENESIS_NEURAL_MAX_ATTEMPTS", "12"))))
MAX_TOKENS = max(8, min(256, int(os.environ.get("GENESIS_NEURAL_MAX_TOKENS", "128"))))
ENABLED = os.environ.get("GENESIS_NEURAL_ENABLED") == "1"


def reply(status, data):
    return {"statusCode": status,
            "headers": {"content-type": "application/json; charset=utf-8",
                        "cache-control": "no-store",
                        "x-content-type-options": "nosniff"},
            "body": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}


def budget_attempt():
    if not BUDGET_TABLE:
        return False
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ttl = int(time.time()) + 3 * 86400
    try:
        # Count attempted calls, including model failures. Cross-invocation
        # atomic check stops parallel or recycled workers from bypassing caps.
        boto3.client("dynamodb", region_name=REGION).update_item(
            TableName=BUDGET_TABLE,
            Key={"day": {"S": day}},
            UpdateExpression="SET expires = :ttl ADD attempts :one",
            ConditionExpression="attribute_not_exists(attempts) OR attempts < :cap",
            ExpressionAttributeValues={
                ":one": {"N": "1"},
                ":cap": {"N": str(MAX_ATTEMPTS)},
                ":ttl": {"N": str(ttl)},
            },
        )
        return True
    except ClientError:
        return False


def handler(event, context):
    if not isinstance(event, dict):
        return reply(400, {"error": "invalid_event"})
    if event.get("action") == "status":
        return reply(200, {
            "adapter": "genesis-neural-text-v0",
            "enabled": ENABLED,
            "model": MODEL_ID,
            "source": "external_pretrained_bedrock",
            "max_output_tokens": MAX_TOKENS,
            "max_daily_attempts": MAX_ATTEMPTS,
            "aurora_execution": "not_attached",
        })
    if not ENABLED:
        return reply(503, {"error": "neural_gate_closed", "reason": "Bedrock quota and cost gates are not yet cleared"})
    if event.get("version") != "2.0" or event.get("rawPath") != "/api/chat":
        return reply(403, {"error": "invalid_internal_request"})
    rc = event.get("requestContext") or {}
    if (rc.get("http") or {}).get("method") != "POST":
        return reply(405, {"error": "method_not_allowed"})
    claims = (((rc.get("authorizer") or {}).get("jwt") or {}).get("claims") or {})
    if (not ISSUER or not AUDIENCE or claims.get("iss") != ISSUER or
            claims.get("aud") != AUDIENCE or claims.get("token_use") != "id" or
            not str(claims.get("sub", "")).startswith("private-alpha:")):
        return reply(403, {"error": "invalid_internal_context"})
    try:
        body = event.get("body") or ""
        if not isinstance(body, str) or len(body.encode("utf-8")) > 8000:
            return reply(413, {"error": "message_too_large"})
        data = json.loads(body)
        prompt = data.get("message")
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 1800:
            return reply(422, {"error": "message_must_be_1_to_1800_characters"})
    except (TypeError, ValueError):
        return reply(400, {"error": "invalid_json"})
    if not budget_attempt():
        return reply(429, {"error": "daily_attempt_limit_or_budget_store_unavailable"})
    try:
        client = boto3.client(
            "bedrock-runtime", region_name=REGION,
            config=Config(connect_timeout=2, read_timeout=14,
                          retries={"mode": "standard", "max_attempts": 1}),
        )
        value = client.converse(
            modelId=MODEL_ID,
            system=[{"text": "You are the experimental neural text component of Genesis. "
                      "You are a pretrained external model, not a trained Genesis foundation model. "
                      "Answer carefully; say when you do not know. You have no tools or execution authority."}],
            messages=[{"role": "user", "content": [{"text": prompt.strip()}]}],
            inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.2},
        )
        blocks = value.get("output", {}).get("message", {}).get("content", [])
        answer = "\n".join(b["text"] for b in blocks if isinstance(b, dict) and isinstance(b.get("text"), str)).strip()
        if not answer:
            return reply(503, {"error": "empty_model_response"})
        return reply(200, {
            "answer": answer[:4096],
            "model": MODEL_ID,
            "source": "external_pretrained_bedrock",
            "experimental": True,
        })
    except Exception:
        # No user prompt, token or exception details are logged.
        return reply(503, {"error": "model_inference_unavailable"})
