#!/usr/bin/env python3
"""Reproducible, opt-in deployment of the isolated Kyro knowledge service.

Default: validate AWS CloudFormation only. Provision/update only with --apply.
Requires AWS credentials for the intended account/region and boto3.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cloud/knowledge-service/index.py"
TEMPLATE = ROOT / "cloud/knowledge-service/template.json"


def build_template():
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    template["Resources"]["KnowledgeFunction"]["Properties"]["Code"]["ZipFile"] = (
        SOURCE.read_text(encoding="utf-8")
    )
    result = json.dumps(template)
    if len(result.encode("utf-8")) > 51200:
        raise ValueError("inline CloudFormation exceeds 51200-byte limit")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="ap-southeast-2")
    parser.add_argument("--stack", default="kyro-knowledge-standard-v1-dev")
    parser.add_argument("--api-id", required=True)
    parser.add_argument("--jwt-authorizer-id", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    cf = boto3.client("cloudformation", region_name=args.region)
    body = build_template()
    params = [
        {"ParameterKey": "ApiId", "ParameterValue": args.api_id},
        {"ParameterKey": "JwtAuthorizerId", "ParameterValue": args.jwt_authorizer_id},
    ]
    cf.validate_template(TemplateBody=body)
    if not args.apply:
        print("VALIDATED; no AWS resources changed. Pass --apply to deploy.")
        return
    try:
        current = cf.describe_stacks(StackName=args.stack)["Stacks"][0]
        if current["StackStatus"].endswith("ROLLBACK_COMPLETE"):
            raise RuntimeError("Stack is rolled back; inspect/fix before retrying")
        update = True
    except ClientError as exc:
        if "does not exist" not in str(exc):
            raise
        update = False
    kwargs = {
        "StackName": args.stack,
        "TemplateBody": body,
        "Capabilities": ["CAPABILITY_IAM"],
        "Parameters": params,
        "Tags": [{"Key": "System", "Value": "Genesis"},
                 {"Key": "Stage", "Value": "private-alpha"}],
    }
    if update:
        try:
            result = cf.update_stack(**kwargs)
            print("UPDATE_STARTED", result["StackId"])
        except ClientError as exc:
            if "No updates are to be performed" not in str(exc):
                raise
            print("NO_CHANGE")
    else:
        result = cf.create_stack(**kwargs)
        print("CREATE_STARTED", result["StackId"])
    print("Wait for CloudFormation completion; then run live auth and retrieval smoke tests.")


if __name__ == "__main__":
    main()
