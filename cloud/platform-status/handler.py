"""Authenticated read-only AWS status of Kyro, Genesis, and Aurora.

No model prompts, tool execution, user data, IAM modifications or resource writes.
This is a deployment inventory, not a full reliability or end-to-end login proof.
"""
from __future__ import annotations

import json
import os
import time


def response(status,body):
    return {"statusCode":status,
            "headers":{"content-type":"application/json","cache-control":"no-store",
                       "x-content-type-options":"nosniff"},
            "body":json.dumps(body,separators=(",",":"))}


def handler(event,context):
    request=event.get("requestContext") if isinstance(event,dict) else None
    claims=((request or {}).get("authorizer") or {}).get("jwt",{}).get("claims",{})
    if (not isinstance(claims,dict)
            or claims.get("iss")!=os.environ.get("KYRO_JWT_ISSUER")
            or claims.get("aud")!=os.environ.get("KYRO_JWT_AUDIENCE")
            or claims.get("token_use")!="id"
            or not claims.get("sub")):
        return response(401,{"error":"Kyro authentication required"})
    try:
        if int(claims.get("exp",0))<=time.time():
            return response(401,{"error":"Session expired"})
    except (ValueError,TypeError):
        return response(401,{"error":"Malformed session"})
    if (event.get("rawPath")!="/api/v3/platform/status" or
            event.get("requestContext",{}).get("http",{}).get("method")!="GET"):
        return response(404,{"error":"Unknown platform route"})
    import boto3
    region="ap-southeast-2"
    lamb=boto3.client("lambda",region_name=region)
    s3=boto3.client("s3",region_name=region)
    codebuild=boto3.client("codebuild",region_name=region)
    events=boto3.client("events",region_name=region)
    names=[
       "kyro-v3-core-dev","agk-kyro-beta",
       "aurora-cloud-v1-controller-dev","aurora-cloud-v1-motor-dev",
       "aurora-cloud-v1-angel-dev",
       "genesis-neural-inference-dev"
    ]
    services={}
    for name in names:
        try:
            r=lamb.get_function_configuration(FunctionName=name)
            services[name]={"deployed":r.get("State")=="Active",
                            "update":r.get("LastUpdateStatus")}
        except Exception:
            services[name]={"deployed":False}
    def active(name):
        return services.get(name,{}).get("deployed",False)
    project="genesis-controlled-cpu-lora-dev"
    build_status="unverified"
    try:
        ids=codebuild.list_builds_for_project(projectName=project,
                                             sortOrder="DESCENDING").get("ids",[])[:1]
        if ids:
            builds=codebuild.batch_get_builds(ids=ids).get("builds",[])
            build_status=builds[0].get("buildStatus","unknown") if builds else "unknown"
    except Exception:
        pass
    schedule_state="unverified"
    try:
        rule=events.describe_rule(Name="genesis-autotrain-approved-datasets-dev")
        schedule_state=rule.get("State","unknown")
    except Exception:
        pass
    bucket=os.environ["GENESIS_ARTIFACT_BUCKET"]
    key="genesis/hf/qwen2p5-0p5b-instruct/training/cpu-lora-r2/adapter/adapter_model.safetensors"
    adapter_stored=False
    try:
        obj=s3.head_object(Bucket=bucket,Key=key)
        adapter_stored=obj.get("ServerSideEncryption")=="AES256" and obj.get("ContentLength",0)>0
    except Exception:
        pass
    neural_active=active("genesis-neural-inference-dev")
    return response(200,{
        "classification":"private_alpha_research",
        "kyro":{"interface":"deployed","core_api":"active" if active("kyro-v3-core-dev") else "unavailable",
                "login":"configured_not_user_verified"},
        "genesis":{"reference_lambda":"active" if active("agk-kyro-beta") else "unavailable",
                   "trained_adapter_private":adapter_stored,
                   "experimental_neural_api":"active" if neural_active else "not_deployed",
                   "neural_quality":"not_production_qualified"},
        "aurora":{"engine":"C1_restricted_online" if
                    all(active(n) for n in ("aurora-cloud-v1-controller-dev",
                                            "aurora-cloud-v1-motor-dev",
                                            "aurora-cloud-v1-angel-dev")) else "incomplete",
                  "execution":"disabled_for_model"},
        "training":{"daily_check":schedule_state,
                    "latest_build":build_status,
                    "automatic_promotion":False},
        "overall":"private_alpha_partial",
        "security":"Model text never grants Aurora execution permission"
    })
