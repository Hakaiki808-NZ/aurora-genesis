"""Kyro invite-only seven-capability beta. Lambda Python 3.12, stdlib+boto3.

All caller identity comes from API Gateway's Cognito JWT authorizer; this
function must NEVER be exposed through an unprotected Function URL or route.
This service stores *only* the beta control-plane records. It does not execute
tools, retrain Genesis, or control Aurora.
"""
from __future__ import annotations

import json
import math
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError

TABLE = os.environ["CAPABILITIES_TABLE"]
EXPECTED_ISSUER = os.environ["CAPABILITIES_ISSUER"]
db = boto3.client("dynamodb")
SCOPES = {
    "tasks": "TASK#",
    "memory": "MEM#memory#",
    "personalization": "MEM#preference#",
    "proactive": "NUDGE#",
    "provenance": "CLAIM#",
}
MAX_ITEMS = 250


class BadInput(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def timestamp(value):
    if not isinstance(value, str) or len(value) > 80:
        raise BadInput("A timezone-aware ISO timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except (ValueError, OverflowError) as exc:
        raise BadInput("A timezone-aware ISO timestamp is required") from exc


def string(v, field, length=500):
    if not isinstance(v, str) or not v.strip() or len(v) > length:
        raise BadInput(f"{field} must have 1-{length} characters")
    return v.strip()


def valid_scope(scope):
    if scope not in SCOPES:
        raise BadInput("Unknown capability scope")
    return scope


def reply(code, value):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store",
                    "Vary": "Authorization", "X-Content-Type-Options": "nosniff"},
        "body": json.dumps(value, ensure_ascii=False, allow_nan=False)
    }


def record(pk, sk):
    raw = db.get_item(TableName=TABLE, Key={"pk": {"S": pk}, "sk": {"S": sk}},
                      ConsistentRead=True).get("Item")
    if not raw:
        return None
    item = json.loads(raw["v"]["S"])
    item["_revision"] = int(raw["revision"]["N"])
    return item


def write(pk, sk, item, old=None):
    item = {k: v for k, v in item.items() if not k.startswith("_")}
    rev = 1 if old is None else int(old["_revision"]) + 1
    args = {"TableName": TABLE,
            "Item": {"pk": {"S": pk}, "sk": {"S": sk},
                     "revision": {"N": str(rev)},
                     "v": {"S": json.dumps(item, ensure_ascii=False, allow_nan=False)}}}
    if old is None:
        args["ConditionExpression"] = "attribute_not_exists(pk)"
    else:
        args["ConditionExpression"] = "#rev = :old"
        args["ExpressionAttributeNames"] = {"#rev": "revision"}
        args["ExpressionAttributeValues"] = {":old": {"N": str(old["_revision"])}}
    try:
        db.put_item(**args)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise BadInput("This record changed; refresh and retry", 409) from exc
        raise
    return item


def listing(pk, prefix=""):
    out = []
    args = {"TableName": TABLE, "KeyConditionExpression": "pk = :pk",
            "ExpressionAttributeValues": {":pk": {"S": pk}},
            "ConsistentRead": True, "Limit": 100}
    if prefix:
        args["KeyConditionExpression"] += " AND begins_with(sk, :pre)"
        args["ExpressionAttributeValues"][":pre"] = {"S": prefix}
    while True:
        resp = db.query(**args)
        out += [{"sk": row["sk"]["S"], **json.loads(row["v"]["S"]),
                 "_revision": int(row["revision"]["N"])} for row in resp.get("Items", [])]
        if len(out) > MAX_ITEMS:
            raise BadInput("Beta record limit reached; export or remove old records", 429)
        if not resp.get("LastEvaluatedKey"):
            break
        args["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return out


def remove(pk, sk):
    db.delete_item(TableName=TABLE, Key={"pk": {"S": pk}, "sk": {"S": sk}})


def consented(pk, scope):
    entry = record(pk, "CONSENT#" + valid_scope(scope))
    return bool(entry and entry.get("enabled") is True)


def need(pk, scope):
    if not consented(pk, scope):
        raise BadInput(f"{scope} is disabled; enable it in Privacy controls first", 403)


def parse_body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise BadInput("Base64 payloads are not supported")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 24000:
        raise BadInput("Request body too large", 413)
    try:
        value = json.loads(raw)
    except ValueError as exc:
        raise BadInput("Malformed JSON") from exc
    if not isinstance(value, dict):
        raise BadInput("JSON object required")
    return value


def summary(row):
    return {k: v for k, v in row.items() if k not in ("_revision", "sk")}


def decision(data):
    criteria = data.get("criteria")
    options = data.get("options")
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 12:
        raise BadInput("Provide 1-12 weighted criteria")
    if not isinstance(options, list) or not 2 <= len(options) <= 20:
        raise BadInput("Provide 2-20 options")
    weights = {}
    for item in criteria:
        if not isinstance(item, dict):
            raise BadInput("Invalid criterion")
        name = string(item.get("name"), "criterion", 100)
        weight = item.get("weight")
        if name in weights or type(weight) not in (int, float) or not math.isfinite(weight) or not 0 <= weight <= 100:
            raise BadInput("Weights must be unique finite values between 0 and 100")
        weights[name] = float(weight)
    total = sum(weights.values())
    if total <= 0:
        raise BadInput("At least one positive weight is required")
    compared = []
    seen = set()
    for item in options:
        if not isinstance(item, dict) or not isinstance(item.get("scores"), dict):
            raise BadInput("Each option requires scores")
        name = string(item.get("name"), "option", 120)
        if name in seen or set(item["scores"]) != set(weights):
            raise BadInput("Each unique option must score every criterion")
        seen.add(name)
        contribution = {}
        for criterion, weight in weights.items():
            rating = item["scores"][criterion]
            if type(rating) not in (int, float) or not math.isfinite(rating) or not 0 <= rating <= 5:
                raise BadInput("Ratings must be between 0 and 5")
            contribution[criterion] = round(float(rating) * weight / total, 6)
        compared.append({"name": name, "score_out_of_5": round(sum(contribution.values()), 6),
                         "contributions": contribution})
    compared.sort(key=lambda x: (-x["score_out_of_5"], x["name"].casefold()))
    return {"ranking": compared, "method": "user_supplied_weighted_sum", "auto_action": False,
            "caveat": "Scores are subjective estimates, not verified outcomes."}


def dispatch(event, pk, route, method):
    data = parse_body(event) if method == "POST" else {}
    query = event.get("queryStringParameters") or {}
    if method == "GET" and route == "/status":
        return {"name": "Kyro capabilities", "stage": "invite_only_beta",
                "consents": {s: consented(pk, s) for s in SCOPES},
                "autonomous_execution": False, "independently_verified": False}
    if method == "GET" and route == "/consents":
        return {"consents": {s: consented(pk, s) for s in SCOPES}}
    if method == "POST" and route == "/consents":
        scope = valid_scope(data.get("scope"))
        enabled = data.get("enabled")
        if type(enabled) is not bool:
            raise BadInput("enabled must be a boolean")
        sk = "CONSENT#" + scope
        old = record(pk, sk)
        write(pk, sk, {"scope": scope, "enabled": enabled, "changed_at": now()}, old)
        if not enabled:
            for item in listing(pk, SCOPES[scope]):
                remove(pk, item["sk"])
        return {"scope": scope, "enabled": enabled,
                "deleted_scope": "capabilities_beta_only"}
    if method == "GET" and route == "/memory":
        kind = query.get("kind", "memory")
        if kind not in ("memory", "preference"):
            raise BadInput("Unknown memory kind")
        scope = "memory" if kind == "memory" else "personalization"
        need(pk, scope)
        return {"items": [summary(x) for x in listing(pk, SCOPES[scope])
                          if x.get("expires_at") is None or x["expires_at"] > now()]}
    if method == "POST" and route == "/memory":
        kind = data.get("kind")
        if kind not in ("memory", "preference"):
            raise BadInput("Unknown memory kind")
        scope = "memory" if kind == "memory" else "personalization"
        need(pk, scope)
        key = string(data.get("key"), "key", 100)
        value = string(data.get("value"), "value", 2000)
        due = timestamp(data["expires_at"]) if data.get("expires_at") else None
        if due and due <= now():
            raise BadInput("Expiry must be in the future")
        sk = f"MEM#{kind}#{key}"
        old = record(pk, sk)
        out = {"kind": kind, "key": key, "value": value,
               "source": "user_explicit", "expires_at": due, "updated_at": now()}
        write(pk, sk, out, old)
        return out
    if method == "POST" and route == "/memory/forget":
        kind = data.get("kind")
        if kind not in ("memory", "preference"):
            raise BadInput("Unknown memory kind")
        key = string(data.get("key"), "key", 100)
        remove(pk, f"MEM#{kind}#{key}")
        return {"removed_from": "beta_capabilities_table", "kind": kind, "key": key}
    if method == "POST" and route == "/nudges":
        need(pk, "proactive")
        title = string(data.get("title"), "title", 240)
        due = timestamp(data.get("due_at"))
        uid = uuid.uuid4().hex
        out = {"id": uid, "title": title, "due_at": due, "state": "PENDING"}
        write(pk, "NUDGE#" + uid, out)
        return out
    if method == "GET" and route == "/attention":
        need(pk, "proactive")
        nudges = [summary(x) for x in listing(pk, "NUDGE#")
                  if x.get("state") == "PENDING" and x.get("due_at", "") <= now()]
        tasks = []
        if consented(pk, "tasks"):
            tasks = [summary(x) for x in listing(pk, "TASK#")
                     if x.get("status") not in ("COMPLETED_ATTESTED", "CANCELLED")
                     and (x.get("status") in ("BLOCKED", "REVIEW")
                          or x.get("due_at") and x["due_at"] <= now())]
        return {"nudges": nudges, "tasks": tasks, "delivery": "pull_only"}
    if method == "POST" and route == "/nudges/dismiss":
        need(pk, "proactive")
        uid = string(data.get("id"), "id", 64)
        sk = "NUDGE#" + uid
        old = record(pk, sk)
        if not old:
            raise BadInput("Reminder not found", 404)
        old["state"] = "DISMISSED"
        return write(pk, sk, old, old)
    if method == "GET" and route == "/claims":
        need(pk, "provenance")
        return {"claims": [summary(x) for x in listing(pk, "CLAIM#")]}
    if method == "POST" and route == "/claims":
        need(pk, "provenance")
        statement = string(data.get("statement"), "statement", 2400)
        sources = data.get("sources", [])
        if not isinstance(sources, list) or len(sources) > 8:
            raise BadInput("Maximum 8 source references")
        refs = [string(x, "source reference", 1000) for x in sources]
        uid = uuid.uuid4().hex
        out = {"id": uid, "statement": statement, "sources": refs,
               "status": "SOURCES_LISTED_UNCHECKED" if refs else "UNSUPPORTED",
               "independently_verified": False, "reviewed_by": None}
        write(pk, "CLAIM#" + uid, out)
        return out
    if method == "POST" and route == "/claims/review":
        need(pk, "provenance")
        uid = string(data.get("id"), "id", 64)
        accepted = data.get("supported")
        if type(accepted) is not bool:
            raise BadInput("supported must be boolean")
        sk = "CLAIM#" + uid
        old = record(pk, sk)
        if not old:
            raise BadInput("Claim not found", 404)
        if old["status"] not in ("SOURCES_LISTED_UNCHECKED", "UNSUPPORTED"):
            raise BadInput("Claim already reviewed", 409)
        old["status"] = "HUMAN_ATTESTED_SUPPORT" if accepted else "HUMAN_DISPUTED"
        old["reviewed_by"] = pk
        return write(pk, sk, old, old)
    if method == "POST" and route == "/decisions/compare":
        return decision(data)
    if method == "GET" and route == "/tasks":
        need(pk, "tasks")
        return {"tasks": [summary(x) for x in listing(pk, "TASK#")]}
    if method == "POST" and route == "/tasks":
        need(pk, "tasks")
        title = string(data.get("title"), "title", 240)
        criteria = data.get("criteria")
        if not isinstance(criteria, list) or not 1 <= len(criteria) <= 20:
            raise BadInput("Provide 1-20 success criteria")
        criteria = [string(s, "criterion", 300) for s in criteria]
        due = timestamp(data["due_at"]) if data.get("due_at") else None
        uid = uuid.uuid4().hex
        task = {"id": uid, "title": title, "criteria": criteria, "due_at": due,
                "status": "DRAFT", "evidence": [], "created_at": now(),
                "completion_basis": "not_complete"}
        write(pk, "TASK#" + uid, task)
        return task
    if route.startswith("/tasks/") and method == "POST":
        need(pk, "tasks")
        uid = string(data.get("id"), "id", 64)
        sk = "TASK#" + uid
        old = record(pk, sk)
        if not old:
            raise BadInput("Task not found", 404)
        status = old["status"]
        if route == "/tasks/transition":
            action = data.get("action")
            states = {"approve": (["DRAFT"], "APPROVED"),
                      "start": (["APPROVED", "BLOCKED"], "WORKING"),
                      "review": (["WORKING"], "REVIEW"),
                      "revise": (["REVIEW"], "WORKING"),
                      "block": (["APPROVED", "WORKING", "REVIEW"], "BLOCKED"),
                      "cancel": (["DRAFT", "APPROVED", "WORKING", "REVIEW", "BLOCKED"], "CANCELLED")}
            if action not in states or status not in states[action][0]:
                raise BadInput("Invalid task transition", 409)
            if action == "review" and not old["evidence"]:
                raise BadInput("Evidence required before review", 409)
            old["status"] = states[action][1]
        elif route == "/tasks/evidence":
            if status != "WORKING":
                raise BadInput("Evidence requires WORKING state", 409)
            index = data.get("criterion_index")
            if type(index) is not int or not 0 <= index < len(old["criteria"]):
                raise BadInput("Invalid criterion index")
            if len(old["evidence"]) >= 40:
                raise BadInput("Maximum 40 evidence entries")
            old["evidence"].append({"id": uuid.uuid4().hex, "criterion_index": index,
                                    "observation": string(data.get("observation"), "observation", 1000),
                                    "reference": string(data.get("reference"), "reference", 800),
                                    "review_state": "PENDING", "reviewed_by": None})
        elif route == "/tasks/review":
            if status != "REVIEW":
                raise BadInput("Evidence review requires REVIEW state", 409)
            eid = string(data.get("evidence_id"), "evidence_id", 64)
            accepted = data.get("accepted")
            if type(accepted) is not bool:
                raise BadInput("accepted must be boolean")
            target = next((x for x in old["evidence"] if x["id"] == eid), None)
            if target is None or target["review_state"] != "PENDING":
                raise BadInput("Evidence not pending", 409)
            target["review_state"] = "ACCEPTED" if accepted else "REJECTED"
            target["reviewed_by"] = pk
        elif route == "/tasks/complete":
            if status != "REVIEW" or data.get("human_confirmed") is not True:
                raise BadInput("Explicit review and confirmation required", 409)
            covered = {x["criterion_index"] for x in old["evidence"]
                       if x["review_state"] == "ACCEPTED"}
            if covered != set(range(len(old["criteria"]))):
                raise BadInput("All success criteria need accepted evidence", 409)
            old["status"] = "COMPLETED_ATTESTED"
            old["completion_basis"] = "human_attestation"
            old["completed_at"] = now()
        else:
            raise BadInput("Unknown task operation", 404)
        old["updated_at"] = now()
        return write(pk, sk, old, old)
    if method == "GET" and route == "/export":
        return {"scope": "capabilities_beta_table_only",
                "items": [summary(x) for x in listing(pk)],
                "legacy_genesis_included": False}
    if method == "POST" and route == "/erase":
        if data.get("confirm") != "ERASE_MY_BETA_DATA":
            raise BadInput("Explicit beta-data deletion confirmation required", 409)
        items = listing(pk)
        for item in items:
            remove(pk, item["sk"])
        return {"deleted_items": len(items), "scope": "capabilities_beta_table_only",
                "caveat": "Existing Kyro/Genesis data, provider logs, and AWS backups are outside this deletion."}
    raise BadInput("Endpoint not found", 404)


def lambda_handler(event, context):
    try:
        claims = (((event.get("requestContext") or {}).get("authorizer") or {})
                  .get("jwt") or {}).get("claims") or {}
        if not claims or claims.get("iss") != EXPECTED_ISSUER:
            raise BadInput("Authenticated Kyro session required", 401)
        sub = claims.get("sub")
        if not isinstance(sub, str) or not 1 <= len(sub) <= 128:
            raise BadInput("Authenticated user subject missing", 401)
        if claims.get("token_use") not in ("id", "access"):
            raise BadInput("Invalid token type", 401)
        pk = "UX#" + sub
        method = (event.get("requestContext") or {}).get("http", {}).get("method", "")
        raw_path = event.get("rawPath") or ""
        prefix = "/api/v3/capabilities"
        if not raw_path.startswith(prefix):
            raise BadInput("Unknown route", 404)
        route = unquote(raw_path[len(prefix):]) or "/"
        if not route.startswith("/") or ".." in route or "//" in route:
            raise BadInput("Invalid route", 404)
        if method not in ("GET", "POST"):
            raise BadInput("Unsupported method", 405)
        return reply(200, dispatch(event, pk, route, method))
    except BadInput as exc:
        return reply(exc.status, {"error": str(exc)})
    except ClientError as exc:
        # Fail closed, never expose AWS internal messages or caller records.
        print("DynamoDB operation failed", exc.response.get("Error", {}).get("Code", "unknown"))
        return reply(503, {"error": "The beta storage service is unavailable"})
    except Exception as exc:
        print("Kyro capability error", type(exc).__name__)
        return reply(500, {"error": "Internal capability service error"})
