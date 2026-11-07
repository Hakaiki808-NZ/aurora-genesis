"""Budget-gated, dataset-change-triggered AWS Genesis LoRA training controller.

Automatically checks daily, but starts compute only for a *new approved* dataset.
This never auto-promotes an adapter or takes user chat logs as training data.

Security: IAM-scoped private S3 provenance; checksum check; one lock per dataset;
hard daily/monthly launch limits; cost-estimate guard; bounded CodeBuild timeout.
A delayed AWS bill cannot be guaranteed as an absolute spend cap.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from decimal import Decimal, InvalidOperation


class TrainingBlocked(Exception):
    pass


def validate_manifest(manifest, *, prefix, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(manifest,dict):
        raise TrainingBlocked("manifest must be an object")
    if manifest.get("schema") != "genesis-auto-train-v1":
        raise TrainingBlocked("unsupported manifest schema")
    if manifest.get("approved") is not True:
        raise TrainingBlocked("dataset has not been approved")
    if manifest.get("source_license") != "original-project-authored":
        raise TrainingBlocked("only original cleared training data is accepted")
    if manifest.get("user_conversation_data") is not False:
        raise TrainingBlocked("conversation-derived training data not allowed")
    key=manifest.get("dataset_key","")
    if not isinstance(key,str) or not key.startswith(prefix+"/datasets/"):
        raise TrainingBlocked("dataset key outside permitted private prefix")
    if not re.fullmatch(r"[A-Za-z0-9/_-]{3,170}\.jsonl",key):
        raise TrainingBlocked("invalid dataset key")
    sha=manifest.get("dataset_sha256","")
    if not isinstance(sha,str) or not re.fullmatch(r"[a-f0-9]{64}",sha):
        raise TrainingBlocked("missing expected dataset digest")
    steps=manifest.get("max_steps")
    if not isinstance(steps,int) or isinstance(steps,bool) or not 1<=steps<=12:
        raise TrainingBlocked("training steps exceed approved bound")
    expiry=manifest.get("expires_utc")
    try:
        until=dt.datetime.fromisoformat(expiry.replace("Z","+00:00"))
    except (ValueError,AttributeError,TypeError):
        raise TrainingBlocked("invalid expiry")
    if until.tzinfo is None or until<=now or until>now+dt.timedelta(days=120):
        raise TrainingBlocked("approval expired or unreasonably distant")
    return {"dataset_key":key,"dataset_sha256":sha,"max_steps":steps}


def validated_training_data(data,expected_sha):
    if not isinstance(data,bytes) or len(data)>256_000 or len(data)<1000:
        raise TrainingBlocked("dataset too large or empty")
    if hashlib.sha256(data).hexdigest()!=expected_sha:
        raise TrainingBlocked("dataset has changed since approval")
    seen=set()
    for line in data.decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:row=json.loads(line)
        except ValueError:raise TrainingBlocked("invalid JSONL training data")
        if not isinstance(row,dict) or set(row)!={"instruction","response"}:
            raise TrainingBlocked("unapproved data structure")
        i,r=row["instruction"],row["response"]
        if (not isinstance(i,str) or not isinstance(r,str)
                or not 2<=len(i)<=900 or not 2<=len(r)<=1500):
            raise TrainingBlocked("invalid training example")
        ident=i.casefold().strip()
        if ident in seen:
            raise TrainingBlocked("duplicate training prompt")
        seen.add(ident)
    if not 35<=len(seen)<=256:
        raise TrainingBlocked("training set has an unsupported number of records")
    return len(seen)


def cost_gate(cost_usd,limit_usd):
    try:
        spent=Decimal(str(cost_usd))
        limit=Decimal(str(limit_usd))
    except InvalidOperation:
        raise TrainingBlocked("cost information unavailable")
    if not spent.is_finite() or spent<0 or limit<=0 or spent>=limit:
        raise TrainingBlocked("cloud spend estimate outside safe threshold")
    return str(spent)


def handler(event, context):
    import boto3
    from botocore.exceptions import ClientError

    event=event or {}
    if not isinstance(event,dict):
        return {"status":"blocked","reason":"invalid event"}
    # No user-submitted dataset key, launch parameters, identity or paid override.
    action=event.get("action","check")
    if action not in ("check","status"):
        return {"status":"blocked","reason":"unsupported action"}

    region=os.environ.get("AWS_REGION","ap-southeast-2")
    bucket=os.environ["GENESIS_TRAINING_BUCKET"]
    prefix=os.environ.get("GENESIS_TRAINING_PREFIX","genesis/training/automation").rstrip("/")
    project=os.environ["GENESIS_CODEBUILD_PROJECT"]
    allowed_cost=os.environ.get("GENESIS_MAX_ACCOUNT_ESTIMATED_USD","10.0")
    now=dt.datetime.now(dt.timezone.utc)
    period=now.strftime("%Y-%m")
    s3=boto3.client("s3",region_name=region)
    try:
        raw=s3.get_object(Bucket=bucket,Key=prefix+"/approved/current.json")["Body"].read()
    except ClientError as exc:
        if exc.response.get("Error",{}).get("Code") in ("NoSuchKey","404"):
            return {"status":"no_approved_dataset","training":False}
        return {"status":"blocked","reason":"approval record unavailable"}
    if len(raw)>8192:
        return {"status":"blocked","reason":"approval record too large"}
    try:
        m=validate_manifest(json.loads(raw),prefix=prefix,now=now)
        data=s3.get_object(Bucket=bucket,Key=m["dataset_key"])["Body"].read(256_001)
        n=validated_training_data(data,m["dataset_sha256"])
    except (TrainingBlocked,ClientError,ValueError,UnicodeError) as exc:
        return {"status":"blocked","reason":str(exc)[:150] if isinstance(exc,TrainingBlocked) else "dataset could not be verified"}

    lock_dataset=prefix+"/locks/datasets/"+m["dataset_sha256"]+".json"
    lock_day=prefix+"/locks/"+period+"/"+now.strftime("%Y-%m-%d")+".json"
    try:
        s3.head_object(Bucket=bucket,Key=lock_dataset)
        return {"status":"already_processed","training":False,"dataset_sha":m["dataset_sha256"][:12]}
    except ClientError as exc:
        if exc.response.get("Error",{}).get("Code") not in ("404","NoSuchKey","NotFound"):
            return {"status":"blocked","reason":"cannot check dataset lock"}

    # Status is read-only; do not spend, start builds or acquire locks.
    if action=="status":
        return {"status":"approved_pending","training":False,
                "dataset_count":n,"steps":m["max_steps"]}
    try:
        ce=boto3.client("ce",region_name="us-east-1")
        start=period+"-01"
        end=(now.date()+dt.timedelta(days=1)).isoformat()
        bill=ce.get_cost_and_usage(
            TimePeriod={"Start":start,"End":end},
            Granularity="MONTHLY",Metrics=["UnblendedCost"])
        values=bill.get("ResultsByTime") or []
        if not values or values[-1].get("Estimated") is False and not values[-1].get("Total"):
            raise TrainingBlocked("cloud cost report missing")
        spend=values[-1]["Total"]["UnblendedCost"]["Amount"]
        cost_gate(spend,allowed_cost)

        prior=s3.list_objects_v2(Bucket=bucket,Prefix=prefix+"/locks/"+period+"/",MaxKeys=10)
        if prior.get("KeyCount",0)>=4:
            raise TrainingBlocked("four monthly training launches already reserved")
        cb=boto3.client("codebuild",region_name=region)
        running=cb.list_builds_for_project(projectName=project,sortOrder="DESCENDING").get("ids",[])[:5]
        if running:
            states=cb.batch_get_builds(ids=running).get("builds",[])
            if any(x.get("buildStatus")=="IN_PROGRESS" for x in states):
                raise TrainingBlocked("previous training build remains active")
        # Claim per-dataset uniqueness before any paid compute starts.
        body=json.dumps({"dataset_sha256":m["dataset_sha256"],
                         "start_date":now.date().isoformat(),
                         "source":"bounded-approved-dataset-controller"}).encode("utf-8")
        for key in (lock_dataset,lock_day):
            try:
                s3.put_object(Bucket=bucket,Key=key,Body=body,
                              ServerSideEncryption="AES256",
                              ContentType="application/json",IfNoneMatch="*")
            except ClientError as exc:
                if exc.response.get("Error",{}).get("Code") in (
                    "PreconditionFailed","ConditionalRequestConflict"):
                    return {"status":"already_locked","training":False}
                raise
        overrides=[
            {"name":"TRAIN_DATA_KEY","value":m["dataset_key"],"type":"PLAINTEXT"},
            {"name":"TRAIN_DATA_SHA","value":m["dataset_sha256"],"type":"PLAINTEXT"},
            {"name":"TRAIN_RUN_ID","value":now.strftime("%Y%m%d")+"-"+m["dataset_sha256"][:12],"type":"PLAINTEXT"},
            {"name":"TRAIN_STEPS","value":str(m["max_steps"]),"type":"PLAINTEXT"},
        ]
        start_result=cb.start_build(
            projectName=project,environmentVariablesOverride=overrides)
        return {"status":"build_started","training":True,
                "build_id":start_result.get("build",{}).get("id"),
                "steps":m["max_steps"],"dataset_count":n}
    except TrainingBlocked as exc:
        return {"status":"blocked","reason":str(exc)}
    except Exception:
        # Locks remain on any ambiguous error; fail closed rather than double-launch.
        return {"status":"blocked","reason":"AWS training gate or build request failed"}
