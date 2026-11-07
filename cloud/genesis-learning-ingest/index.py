"""Private opt-in event capture and bounded shadow evaluation scheduling.

No public HTTP route, no Aurora execution, no weight updates, no auto-promotion.
Invokers require AWS IAM permission to call this Lambda.
"""
import boto3
import datetime
import hashlib
import json
import os
import re
import time

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
TABLE = os.environ["GENESIS_LEARNING_TABLE"]
BUCKET = os.environ["GENESIS_TRAINING_BUCKET"]
PROJECT = os.environ["GENESIS_SHADOW_PROJECT"]
MAX_RUNS = 3
MAX_BATCH = 8
DDB = boto3.client("dynamodb", region_name=REGION)
S3 = boto3.client("s3", region_name=REGION)
BUILDS = boto3.client("codebuild", region_name=REGION)


def outcome(status, **details):
    return {"ok": status == "ok", "status": status, **details}


def text_field(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValueError("invalid_input")
    text = value.strip()
    text = re.sub(r"\bAKIA[A-Z0-9]{16}\b", "[redacted-key]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{16,}\b", "[redacted-secret]", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[redacted-email]", text)
    return text


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{4,80}", value):
        raise ValueError("invalid_identifier")
    return value


def attr(item, name, default=""):
    value = item.get(name, {})
    return value.get("S", default) if isinstance(value, dict) else default


def capture(event):
    if event.get("consent_shadow_eval") is not True:
        return outcome("consent_required")
    source = event.get("origin")
    if source not in ("chatgpt_explicit_opt_in", "kyro_explicit_opt_in"):
        return outcome("untrusted_source")
    try:
        session = identifier(event.get("session_id"))
        case_id = identifier(event.get("case_id"))
        prompt = text_field(event.get("prompt"), 2500)
        answer = event.get("assistant_reference", "")
        if answer:
            answer = text_field(answer, 4000)
        elif not isinstance(answer, str):
            raise ValueError("invalid_reference")
    except ValueError as exc:
        return outcome(str(exc))
    now = datetime.datetime.now(datetime.timezone.utc)
    item = {
        "pk": {"S": "SESSION#" + session},
        "sk": {"S": "QUESTION#" + case_id},
        "prompt": {"S": prompt},
        "assistant_reference": {"S": answer},
        "reference_status": {"S": "assistant_unverified"},
        "origin": {"S": source},
        "consent_shadow_eval": {"BOOL": True},
        "consent_training": {"BOOL": event.get("consent_training") is True},
        "shadow_status": {"S": "queued"},
        "alignment_review": {"S": "pending_review"},
        "created_utc": {"S": now.isoformat()},
        "expires_at": {"N": str(int(now.timestamp()) + 90 * 86400)},
    }
    try:
        DDB.put_item(
            TableName=TABLE,
            Item=item,
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
        return outcome("ok", case_id=case_id, stage="captured_unreviewed")
    except DDB.exceptions.ConditionalCheckFailedException:
        return outcome("duplicate_event")


def delete(event):
    try:
        session = identifier(event.get("session_id"))
        case_id = identifier(event.get("case_id"))
    except ValueError:
        return outcome("invalid_identifier")
    # The caller must authenticate and authorize the request before invoking
    # this IAM-only Lambda. Do not expose this action to a public route.
    DDB.delete_item(
        TableName=TABLE,
        Key={
            "pk": {"S": "SESSION#" + session},
            "sk": {"S": "QUESTION#" + case_id},
        },
    )
    # S3 datasets and result artifacts require separate deletion workflow.
    return outcome("ok", deletion_scope="event_only", downstream_erasure_required=True)


def shadow_cycle():
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    items = DDB.scan(
        TableName=TABLE,
        Limit=200,
        FilterExpression="begins_with(pk, :p) AND #s = :q",
        ExpressionAttributeNames={"#s": "shadow_status"},
        ExpressionAttributeValues={":p": {"S": "SESSION#"}, ":q": {"S": "queued"}},
    ).get("Items", [])
    cases = []
    selected = []
    for item in items:
        if item.get("consent_shadow_eval", {}).get("BOOL") is not True:
            continue
        q = attr(item, "prompt")
        case_id = attr(item, "sk").replace("QUESTION#", "", 1)
        if not q or not case_id:
            continue
        selected.append(item)
        cases.append({
            "case_id": case_id,
            "prompt": q,
            "assistant_reference": attr(item, "assistant_reference"),
            "origin": attr(item, "origin", "unknown"),
            "consent_shadow_eval": True,
            "consent_training": item.get("consent_training", {}).get("BOOL") is True,
        })
        if len(cases) >= MAX_BATCH:
            break
    if len(cases) < 2:
        return outcome("no_new_batch", queued=len(cases))
    raw = "".join(json.dumps(c, ensure_ascii=False, separators=(",", ":")) + "\n" for c in cases).encode()
    digest = hashlib.sha256(raw).hexdigest()
    lock = {"pk": {"S": "CONTROL#shadow"}, "sk": {"S": "RUN#" + today}}
    try:
        DDB.put_item(
            TableName=TABLE, Item=lock,
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
    except DDB.exceptions.ConditionalCheckFailedException:
        return outcome("daily_lock_already_used")
    try:
        DDB.update_item(
            TableName=TABLE,
            Key={"pk": {"S": "CONTROL#shadow"}, "sk": {"S": "LIFETIME"}},
            UpdateExpression="ADD runs :one",
            ConditionExpression="attribute_not_exists(runs) OR runs < :max",
            ExpressionAttributeValues={":one": {"N": "1"}, ":max": {"N": str(MAX_RUNS)}},
        )
    except DDB.exceptions.ConditionalCheckFailedException:
        return outcome("evaluation_run_cap_reached", max_runs=MAX_RUNS)
    key = "genesis/training/automation/datasets/shadow-" + digest[:16] + ".jsonl"
    run_id = today.replace("-", "") + "-" + digest[:12]
    S3.put_object(Bucket=BUCKET, Key=key, Body=raw, ServerSideEncryption="AES256", ContentType="application/x-ndjson")
    launched = BUILDS.start_build(
        projectName=PROJECT,
        environmentVariablesOverride=[
            {"name": "SHADOW_DATA_KEY", "value": key, "type": "PLAINTEXT"},
            {"name": "SHADOW_DATA_SHA256", "value": digest, "type": "PLAINTEXT"},
            {"name": "SHADOW_RUN_ID", "value": run_id, "type": "PLAINTEXT"},
        ],
    )
    for item in selected:
        DDB.update_item(
            TableName=TABLE,
            Key={"pk": item["pk"], "sk": item["sk"]},
            UpdateExpression="SET shadow_status = :s, evaluation_id = :v",
            ConditionExpression="shadow_status = :old",
            ExpressionAttributeValues={
                ":s": {"S": "submitted"}, ":v": {"S": run_id},
                ":old": {"S": "queued"},
            },
        )
    return outcome("ok", stage="shadow_build_submitted", case_count=len(cases), run_id=run_id,
                   build_id=launched["build"]["id"], auto_promotion=False)


def handler(event, context):
    if not isinstance(event, dict):
        return outcome("invalid_event")
    # Only AWS-IAM-authorized direct invocations. No API Gateway HTTP request.
    if any(k in event for k in ("requestContext", "rawPath", "headers")):
        return outcome("private_iam_only")
    try:
        action = event.get("action")
        if action == "ingest":
            return capture(event)
        if action == "delete_event":
            return delete(event)
        if action == "shadow_cycle":
            return shadow_cycle()
        if action == "status":
            return outcome("ok", stage="private_capture_ready", max_shadow_builds=MAX_RUNS,
                           model_weight_updates=False, direct_iam_only=True)
        return outcome("unsupported_action")
    except Exception:
        return outcome("service_error")
