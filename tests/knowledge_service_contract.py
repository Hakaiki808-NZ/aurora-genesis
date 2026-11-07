"""Dependency-free contract tests for the invited Kyro knowledge service.

Run: python -m unittest tests.knowledge_service_contract
No AWS credentials or outbound requests are needed.
"""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cloud" / "knowledge-service" / "index.py"
TEMPLATE = ROOT / "cloud" / "knowledge-service" / "template.json"


def load_handler():
    boto3 = types.ModuleType("boto3")
    boto3.dynamodb = types.ModuleType("boto3.dynamodb")
    boto3.dynamodb.conditions = types.ModuleType("boto3.dynamodb.conditions")
    boto3.dynamodb.conditions.Key = object
    botocore = types.ModuleType("botocore")
    botocore.exceptions = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        response = {"Error": {"Code": "Mock"}}

    botocore.exceptions.ClientError = ClientError
    spec = importlib.util.spec_from_file_location("kyro_knowledge_contract", SOURCE)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "boto3": boto3,
        "boto3.dynamodb": boto3.dynamodb,
        "boto3.dynamodb.conditions": boto3.dynamodb.conditions,
        "botocore": botocore,
        "botocore.exceptions": botocore.exceptions,
    }):
        spec.loader.exec_module(module)
    return module


def event(path, params=None, authenticated=True):
    return {
        "rawPath": "/api/v3/knowledge/" + path,
        "queryStringParameters": params or {},
        "requestContext": {
            "http": {"method": "GET"},
            "authorizer": {"jwt": {"claims": {"sub": "contract-test"}}}
            if authenticated else {},
        },
    }


class KnowledgeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = load_handler()

    def body(self, response):
        return json.loads(response["body"])

    def test_unauthenticated_rejected(self):
        self.assertEqual(self.service.handler(event("sources", authenticated=False), None)["statusCode"], 401)

    def test_source_catalog(self):
        r = self.service.handler(event("sources"), None)
        self.assertEqual(r["statusCode"], 200)
        self.assertEqual(set(self.body(r)["sources"]), {"openalex", "wikidata", "crossref"})

    def test_training_disabled(self):
        r = self.service.handler(event("training/status"), None)
        self.assertEqual(self.body(r)["weights_training"], "disabled")

    def test_personal_data_rejected(self):
        with self.assertRaises(ValueError):
            self.service._validate_query("research bob@example.com")

    def test_upstream_normalization_no_abstracts(self):
        with patch.object(self.service, "_fetch_json", return_value={
            "message": {"items": [{"DOI": "10.1000/demo", "title": ["Study"],
                                   "abstract": "DO NOT PERSIST"}]}
        }):
            rows = self.service._remote("crossref", "research", 1)
        self.assertEqual(len(rows), 1)
        self.assertNotIn("abstract", json.dumps(rows))
        self.assertFalse(rows[0]["training_eligible"])

    def test_live_search_is_bounded_and_cached(self):
        rows = [{"source": "openalex", "title": "Research", "training_eligible": False}]
        with patch.object(self.service, "_quota") as quota, \
             patch.object(self.service, "_remote", return_value=rows) as remote, \
             patch.object(self.service, "_save_metadata", return_value=1) as saved:
            r = self.service.handler(event("search", {"source": "openalex", "q": "research",
                                                      "limit": "1"}), None)
        self.assertEqual(r["statusCode"], 200)
        quota.assert_called_once()
        remote.assert_called_once_with("openalex", "research", 1)
        saved.assert_called_once()

    def test_invalid_source_rejected(self):
        with patch.object(self.service, "_quota") as quota:
            r = self.service.handler(event("search", {"source": "http://127.0.0.1",
                                                      "q": "research"}), None)
        self.assertEqual(r["statusCode"], 400)
        quota.assert_not_called()

    def test_infrastructure_security(self):
        infra = json.loads(TEMPLATE.read_text())
        resources = infra["Resources"]
        self.assertEqual(resources["KnowledgeRoute"]["Properties"]["AuthorizationType"], "JWT")
        table = resources["KnowledgeTable"]["Properties"]
        self.assertEqual(table["BillingMode"], "PAY_PER_REQUEST")
        self.assertTrue(table["PointInTimeRecoverySpecification"]["PointInTimeRecoveryEnabled"])
        self.assertTrue(table["TimeToLiveSpecification"]["Enabled"])
        self.assertEqual(resources["KnowledgeFunction"]["Properties"]["ReservedConcurrentExecutions"], 2)


if __name__ == "__main__":
    unittest.main()
