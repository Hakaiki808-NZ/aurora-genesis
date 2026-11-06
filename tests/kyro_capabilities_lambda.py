"""Offline smoke tests for Kyro seven-capability Lambda with fake DynamoDB."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path


class FakeClientError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}
        super().__init__(code)


class FakeDynamo:
    def __init__(self):
        self.data = {}

    def get_item(self, TableName, Key, ConsistentRead=False):
        key = (Key["pk"]["S"], Key["sk"]["S"])
        return {"Item": self.data[key]} if key in self.data else {}

    def put_item(self, TableName, Item, ConditionExpression, **kwargs):
        key = (Item["pk"]["S"], Item["sk"]["S"])
        existing = self.data.get(key)
        if ConditionExpression == "attribute_not_exists(pk)" and existing is not None:
            raise FakeClientError("ConditionalCheckFailedException")
        if ConditionExpression == "#rev = :old":
            old = kwargs["ExpressionAttributeValues"][":old"]["N"]
            if existing is None or existing["revision"]["N"] != old:
                raise FakeClientError("ConditionalCheckFailedException")
        self.data[key] = Item.copy()

    def query(self, TableName, KeyConditionExpression, ExpressionAttributeValues,
              ConsistentRead=False, Limit=100, **kwargs):
        pk = ExpressionAttributeValues[":pk"]["S"]
        prefix = ExpressionAttributeValues.get(":pre", {}).get("S", "")
        out = [v for (p, sk), v in sorted(self.data.items())
               if p == pk and sk.startswith(prefix)]
        return {"Items": out}

    def delete_item(self, TableName, Key):
        self.data.pop((Key["pk"]["S"], Key["sk"]["S"]), None)


def run():
    fake = FakeDynamo()
    botomod = types.ModuleType("boto3")
    botomod.client = lambda name: fake
    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.ClientError = FakeClientError
    old = {name: sys.modules.get(name) for name in ("boto3", "botocore", "botocore.exceptions")}
    sys.modules.update({"boto3": botomod, "botocore": botocore, "botocore.exceptions": exceptions})
    os.environ["CAPABILITIES_TABLE"] = "fake-dynamo"
    os.environ["CAPABILITIES_ISSUER"] = "https://expected"
    try:
        path = Path(__file__).resolve().parent.parent / "tools" / "aws" / "kyro_capabilities_lambda.py"
        spec = importlib.util.spec_from_file_location("kyro_capabilities_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def call(route, method="GET", payload=None, user="alice", authenticated=True):
            claims = {"sub": user, "iss": "https://expected", "token_use": "id"} if authenticated else {}
            event = {"rawPath": "/api/v3/capabilities" + route,
                     "requestContext": {"http": {"method": method},
                                        "authorizer": {"jwt": {"claims": claims}}}}
            if payload is not None:
                event["body"] = json.dumps(payload)
            result = module.lambda_handler(event, None)
            return result["statusCode"], json.loads(result["body"])

        assert call("/status", authenticated=False)[0] == 401
        status, initial = call("/status")
        assert status == 200 and not any(initial["consents"].values())
        assert call("/memory", "POST", {"kind": "memory", "key": "x", "value": "y"})[0] == 403
        for scope in module.SCOPES:
            assert call("/consents", "POST", {"scope": scope, "enabled": True})[0] == 200
        assert all(call("/consents")[1]["consents"].values())
        assert call("/memory", "POST", {"kind": "memory", "key": "project", "value": "alpha"})[0] == 200
        assert call("/memory", "POST", {"kind": "preference", "key": "theme", "value": "light"})[0] == 200
        assert call("/memory?kind=preference")[0] == 400  # actual query is separate
        assert call("/memory")[1]["items"][0]["value"] == "alpha"
        assert call("/memory", user="bob")[0] == 403
        assert call("/consents", "POST", {"scope": "memory", "enabled": True}, user="bob")[0] == 200
        assert call("/memory", user="bob")[1]["items"] == []
        assert call("/memory", "POST", {"kind": "memory", "key": "project", "value": "bob"}, user="bob")[0] == 200
        assert call("/memory", user="alice")[1]["items"][0]["value"] == "alpha"

        task = call("/tasks", "POST", {"title": "Ship beta", "criteria": ["Health", "User review"]})[1]
        tid = task["id"]
        assert task["status"] == "DRAFT"
        assert call("/tasks/complete", "POST", {"id": tid, "human_confirmed": True})[0] == 409
        assert call("/tasks/transition", "POST", {"id": tid, "action": "approve"})[0] == 200
        assert call("/tasks/transition", "POST", {"id": tid, "action": "start"})[0] == 200
        assert call("/tasks/transition", "POST", {"id": tid, "action": "review"})[0] == 409
        for i in (0, 1):
            e = call("/tasks/evidence", "POST", {"id": tid, "criterion_index": i,
                "observation": "Test result", "reference": "test://reference"})[1]
            assert e["evidence"][-1]["review_state"] == "PENDING"
        assert call("/tasks/transition", "POST", {"id": tid, "action": "review"})[0] == 200
        assert call("/tasks/complete", "POST", {"id": tid, "human_confirmed": True})[0] == 409
        task = call("/tasks")[1]["tasks"][0]
        for e in task["evidence"]:
            assert call("/tasks/review", "POST", {"id": tid, "evidence_id": e["id"], "accepted": True})[0] == 200
        assert call("/tasks/complete", "POST", {"id": tid, "human_confirmed": True})[1]["completion_basis"] == "human_attestation"
        assert call("/tasks/transition", "POST", {"id": tid, "action": "start"})[0] == 409
        assert call("/tasks", user="bob")[0] == 403

        claim = call("/claims", "POST", {"statement": "Test assertion",
                        "sources": ["https://example.org"]})[1]
        assert claim["status"] == "SOURCES_LISTED_UNCHECKED" and claim["independently_verified"] is False
        reviewed = call("/claims/review", "POST", {"id": claim["id"], "supported": True})[1]
        assert reviewed["status"] == "HUMAN_ATTESTED_SUPPORT"
        assert reviewed["independently_verified"] is False
        assert call("/claims/review", "POST", {"id": claim["id"], "supported": False})[0] == 409

        nudge = call("/nudges", "POST", {"title": "Follow-up", "due_at": "2020-01-01T00:00:00Z"})[1]
        assert call("/attention")[1]["nudges"][0]["id"] == nudge["id"]
        assert call("/nudges/dismiss", "POST", {"id": nudge["id"]})[0] == 200
        assert call("/attention")[1]["nudges"] == []

        d = call("/decisions/compare", "POST",
                 {"criteria": [{"name": "quality", "weight": 3}, {"name": "cost", "weight": 1}],
                  "options": [{"name": "A", "scores": {"quality": 5, "cost": 1}},
                              {"name": "B", "scores": {"quality": 2, "cost": 5}}]})[1]
        assert d["ranking"][0]["name"] == "A" and not d["auto_action"]
        assert call("/decisions/compare", "POST",
                    {"criteria": [{"name": "bad", "weight": float("nan")}],
                     "options": []})[0] == 400
        assert call("/not-a-valid-action", "POST", {})[0] == 404

        export = call("/export")[1]
        assert export["scope"] == "capabilities_beta_table_only"
        assert not export["legacy_genesis_included"]
        assert call("/consents", "POST", {"scope": "memory", "enabled": False})[0] == 200
        assert call("/memory")[0] == 403
        assert call("/consents", "POST", {"scope": "memory", "enabled": True})[0] == 200
        assert call("/memory")[1]["items"] == []
        assert call("/erase", "POST", {"confirm": "wrong"})[0] == 409
        assert call("/erase", "POST", {"confirm": "ERASE_MY_BETA_DATA"})[0] == 200
        assert call("/status")[1]["consents"]["memory"] is False
        assert call("/memory", user="bob")[1]["items"][0]["value"] == "bob"
    finally:
        for k, oldvalue in old.items():
            if oldvalue is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = oldvalue
    print("KYRO_CAPABILITIES_LAMBDA=PASS")


if __name__ == "__main__":
    run()
