"""Invite-only Kyro public-metadata knowledge service.

Independent from Aurora, and not a model-training or weights endpoint.
Public metadata remains untrusted RAG reference material.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

TABLE = None
SOURCES = {
    "openalex": {
        "label": "OpenAlex",
        "license": "CC0 metadata",
        "terms": "https://help.openalex.org/api/",
        "content": "Bibliographic metadata only; no full-text works",
    },
    "wikidata": {
        "label": "Wikidata",
        "license": "CC0 structured data",
        "terms": "https://www.wikidata.org/wiki/Wikidata:Licensing",
        "content": "Entity names and descriptions only",
    },
    "crossref": {
        "label": "Crossref",
        "license": "Public bibliographic metadata (no abstracts)",
        "terms": "https://www.crossref.org/documentation/retrieve-metadata/",
        "content": "Title, DOI and publication metadata only",
    },
}
_WORD = re.compile(r"[a-z0-9]{3,}", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)
_PHONE = re.compile(r"\+?\d[\d\s()-]{9,}\d")
_STOP = {"the", "and", "for", "from", "about", "with", "what", "does", "which"}


def _db():
    global TABLE
    if TABLE is None:
        TABLE = boto3.resource("dynamodb").Table(os.environ["KNOWLEDGE_TABLE"])
    return TABLE


def _reply(status, body):
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
        },
        "body": json.dumps(body, ensure_ascii=False, separators=(",", ":")),
    }


def _terms(value):
    return list(dict.fromkeys(
        w.lower() for w in _WORD.findall(value)
        if w.lower() not in _STOP
    ))[:8]


def _query_params(event):
    params = event.get("queryStringParameters")
    return params if isinstance(params, dict) else {}


def _validate_query(raw):
    if not isinstance(raw, str):
        raise ValueError("query must be text")
    value = " ".join(raw.split())
    if not 2 <= len(value) <= 120:
        raise ValueError("query length must be between 2 and 120 characters")
    if _EMAIL.search(value) or _PHONE.search(value):
        raise ValueError("do not send personal information to external knowledge sources")
    if not _terms(value):
        raise ValueError("query must contain searchable words")
    return value


def _fetch_json(url):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "KyravantraKnowledge/0.1 (https://github.com/Hakaiki808-NZ/aurora-genesis)",
        },
    )
    # The URL is generated only from three hard-coded hosts, never from user input.
    with urlopen(request, timeout=5) as resp:
        if resp.status != 200:
            raise RuntimeError("upstream non-200 response")
        payload = resp.read(200_001)
        if len(payload) > 200_000:
            raise RuntimeError("upstream response too large")
    return json.loads(payload)


def _clean(value, length=240):
    return " ".join(str(value or "").split())[:length]


def _record(source, external_id, title, url, detail=""):
    external_id, title = _clean(external_id, 300), _clean(title, 240)
    if not external_id or not title or not isinstance(url, str):
        return None
    if not url.startswith("https://"):
        return None
    return {
        "source": source,
        "external_id": external_id,
        "title": title,
        "url": url[:500],
        "detail": _clean(detail, 300),
        "license": SOURCES[source]["license"],
        "trust": "untrusted_public_metadata",
        "training_eligible": False,
    }


def _remote(source, query, limit):
    if source == "openalex":
        qs = urlencode({"search": query, "per-page": limit, "select": "id,title,doi,publication_year"})
        rows = _fetch_json("https://api.openalex.org/works?" + qs).get("results", [])
        return [r for x in rows if (r := _record(
            source, x.get("id"), x.get("title"), x.get("id") or "",
            str(x.get("publication_year") or ""),
        ))]
    if source == "wikidata":
        qs = urlencode({"action": "wbsearchentities", "search": query,
                        "language": "en", "limit": limit, "format": "json"})
        rows = _fetch_json("https://www.wikidata.org/w/api.php?" + qs).get("search", [])
        return [r for x in rows if (r := _record(
            source, x.get("id"), x.get("label"),
            "https://www.wikidata.org/wiki/" + _clean(x.get("id"), 24),
            x.get("description", ""),
        ))]
    if source == "crossref":
        qs = urlencode({"query.title": query, "rows": limit, "select": "DOI,title,URL,published"})
        rows = _fetch_json("https://api.crossref.org/works?" + qs).get("message", {}).get("items", [])
        return [r for x in rows if (r := _record(
            source, x.get("DOI"), (x.get("title") or [""])[0],
            "https://doi.org/" + _clean(x.get("DOI"), 300),
            "",
        ))]
    raise ValueError("source not approved")


def _quota(sub):
    subject = hashlib.sha256(sub.encode("utf-8")).hexdigest()[:24]
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        _db().update_item(
            Key={"pk": "QUOTA#" + day, "sk": subject},
            UpdateExpression="SET #n = if_not_exists(#n, :zero) + :one, expires_at = :expires",
            ConditionExpression="attribute_not_exists(#n) OR #n < :limit",
            ExpressionAttributeNames={"#n": "requests"},
            ExpressionAttributeValues={
                ":zero": 0, ":one": 1, ":limit": 30,
                ":expires": int(time.time()) + 172800,
            },
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise PermissionError("daily external-query limit reached") from exc
        raise


def _save_metadata(records):
    expires = int(time.time()) + 30 * 86400
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    with _db().batch_writer(overwrite_by_pkeys=["pk", "sk"]) as batch:
        for record in records[:5]:
            digest = hashlib.sha256(
                (record["source"] + ":" + record["external_id"]).encode("utf-8")
            ).hexdigest()[:32]
            doc = dict(record)
            doc.update({
                "pk": "SOURCE#" + record["source"],
                "sk": "DOC#" + digest,
                "expires_at": expires,
                "ingested_at": now,
            })
            batch.put_item(Item=doc)
            for word in _terms(record["title"] + " " + record["detail"])[:8]:
                batch.put_item(Item={
                    "pk": "TERM#" + word,
                    "sk": "HIT#" + record["source"] + "#" + digest,
                    "title": record["title"],
                    "url": record["url"],
                    "source": record["source"],
                    "external_id": record["external_id"],
                    "license": record["license"],
                    "trust": record["trust"],
                    "training_eligible": False,
                    "expires_at": expires,
                })
            count += 1
    return count


def _cache_search(query, limit):
    hits = {}
    now = int(time.time())
    for word in _terms(query)[:4]:
        resp = _db().query(
            KeyConditionExpression=Key("pk").eq("TERM#" + word),
            Limit=40,
        )
        for item in resp.get("Items", []):
            if item.get("expires_at", 0) <= now:
                continue
            key = item["sk"]
            if key not in hits:
                hits[key] = {k: item[k] for k in (
                    "source", "external_id", "title", "url", "license",
                    "trust", "training_eligible",
                ) if k in item}
                hits[key]["score"] = 0
            hits[key]["score"] += 1
    return sorted(hits.values(), key=lambda x: (-x["score"], x["title"]))[:limit]


def handler(event, context):
    # API Gateway validates the Cognito JWT; reject direct/unauthorized calls too.
    claims = (((event.get("requestContext") or {}).get("authorizer") or {})
              .get("jwt") or {}).get("claims") or {}
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        return _reply(401, {"error": "authentication_required"})
    method = (event.get("requestContext") or {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    if method != "GET" or "/knowledge/" not in path:
        return _reply(405, {"error": "unsupported_method_or_route"})
    operation = path.rsplit("/knowledge/", 1)[-1].strip("/")
    params = _query_params(event)
    if operation == "health":
        return _reply(200, {"service": "genesis-public-metadata", "status": "operational",
                            "training": "disabled", "schema": "knowledge-v1"})
    if operation == "sources":
        return _reply(200, {"sources": SOURCES, "training": "disabled",
                            "access": "invite-only", "data_class": "public_metadata"})
    if operation == "training/status":
        return _reply(200, {"weights_training": "disabled", "reason": "requires reviewed data rights, "
                            "evaluation, rollback and explicit cost gating"})
    if operation not in {"search", "cache/search"}:
        return _reply(404, {"error": "unknown_route"})
    try:
        query = _validate_query(params.get("q"))
        limit = int(params.get("limit", "3"))
        if not 1 <= limit <= 5:
            raise ValueError("limit must be 1 to 5")
        if operation == "cache/search":
            return _reply(200, {"results": _cache_search(query, limit), "mode": "local_cache"})
        source = params.get("source", "openalex")
        if source not in SOURCES:
            raise ValueError("source must be openalex, wikidata or crossref")
        _quota(subject)
        records = _remote(source, query, limit)
        count = _save_metadata(records)
        return _reply(200, {"results": records, "source": source, "cached": count,
                            "mode": "live_public_metadata", "training": "disabled"})
    except PermissionError as exc:
        return _reply(429, {"error": str(exc)})
    except (TypeError, ValueError) as exc:
        return _reply(400, {"error": str(exc)})
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, json.JSONDecodeError):
        return _reply(502, {"error": "upstream_source_unavailable"})
    except ClientError:
        return _reply(503, {"error": "knowledge_store_unavailable"})
