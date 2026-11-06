"""One-shot Genesis GPU trainer launcher and independent cost/runtime watchdog."""
import datetime
import json
import os
import boto3
from botocore.exceptions import ClientError

REGION = "ap-southeast-2"
RUN_TAG = "genesis-qwen2p5-05b-v0"
MAX_AGE_SECONDS = 3 * 3600
LIMIT_SPOT_PRICE = "1.00"


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _disable_rule():
    boto3.client("events", region_name=REGION).disable_rule(
        Name=os.environ["SCHEDULE_RULE_NAME"]
    )


def _user_data():
    sha = os.environ["GENESIS_SOURCE_SHA"]
    return """#!/bin/bash
set -Eeuo pipefail
shutdown -h +180 >/dev/null 2>&1 || true
trap 'shutdown -h now || poweroff' EXIT
export GENESIS_SOURCE_SHA="%s"
curl --retry 3 --max-time 60 -fsSL \\
  "https://raw.githubusercontent.com/Hakaiki808-NZ/aurora-genesis/%s/tools/aws/run_genesis_qlora.sh" \\
  | bash
""" % (sha, sha)


def _gpu_quota(code):
    try:
        data = boto3.client("service-quotas", region_name=REGION).get_service_quota(
            ServiceCode="ec2", QuotaCode=code
        )
        return data["Quota"]["Value"]
    except ClientError:
        return 0


def _known_gpu_instances(ec2):
    reservations = ec2.describe_instances(Filters=[
        {"Name": "tag:GenesisTrainingRun", "Values": [RUN_TAG]},
    ]).get("Reservations", [])
    return [i for r in reservations for i in r.get("Instances", [])]


def _cost_constrained_launch(ec2, mode):
    tags = [
        {"Key": "Name", "Value": "genesis-qwen-finetune-once"},
        {"Key": "GenesisTrainingRun", "Value": RUN_TAG},
        {"Key": "Project", "Value": "Genesis"},
        {"Key": "Environment", "Value": "development"},
        {"Key": "TrainingMaxHours", "Value": "3"},
    ]
    params = {
        "ClientToken": "genesis-finetune-qwen05b-once-20261107",
        "ImageId": os.environ["GPU_AMI_ID"],
        "InstanceType": "g4dn.xlarge",
        "MinCount": 1,
        "MaxCount": 1,
        "SubnetId": os.environ["GPU_SUBNET_ID"],
        "SecurityGroupIds": [os.environ["GPU_SECURITY_GROUP_ID"]],
        "IamInstanceProfile": {"Name": os.environ["GPU_INSTANCE_PROFILE_NAME"]},
        "UserData": _user_data(),
        "InstanceInitiatedShutdownBehavior": "terminate",
        "MetadataOptions": {"HttpEndpoint": "enabled", "HttpTokens": "required"},
        "BlockDeviceMappings": [{
            "DeviceName": "/dev/sda1",
            "Ebs": {
                "VolumeType": "gp3", "VolumeSize": 50,
                "DeleteOnTermination": True, "Encrypted": True,
            },
        }],
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": tags},
            {"ResourceType": "volume", "Tags": tags},
        ],
    }
    if mode == "spot":
        params["InstanceMarketOptions"] = {
            "MarketType": "spot",
            "SpotOptions": {
                "SpotInstanceType": "one-time",
                "MaxPrice": LIMIT_SPOT_PRICE,
                "InstanceInterruptionBehavior": "terminate",
            },
        }
    response = ec2.run_instances(**params)
    return response["Instances"][0]["InstanceId"]


def lambda_handler(event, context):
    event = event or {}
    ec2 = boto3.client("ec2", region_name=REGION)
    now = _now()
    existing = _known_gpu_instances(ec2)
    if existing:
        inst = existing[0]
        age_seconds = (now - inst["LaunchTime"]).total_seconds()
        state = inst["State"]["Name"]
        if state in ("running", "pending", "stopping", "stopped"):
            if age_seconds > MAX_AGE_SECONDS:
                if not event.get("dry_run"):
                    ec2.terminate_instances(InstanceIds=[inst["InstanceId"]])
                return {
                    "status": "deadline_terminate", "state": state,
                    "instance_id": inst["InstanceId"], "age_seconds": int(age_seconds),
                }
            return {
                "status": "running_or_initializing", "state": state,
                "instance_id": inst["InstanceId"], "age_seconds": int(age_seconds),
            }
        if state in ("terminated", "shutting-down"):
            if not event.get("dry_run"):
                _disable_rule()
            return {"status": "completed_or_terminated", "state": state}
    deadline = datetime.datetime.fromisoformat(os.environ["AUTOSTART_DEADLINE_UTC"])
    if now > deadline:
        if not event.get("dry_run"):
            _disable_rule()
        return {"status": "approval_window_expired_no_gpu_launched"}

    spot = _gpu_quota("L-3819A6DF")
    on_demand = _gpu_quota("L-DB2E81BA")
    mode = "spot" if spot >= 4 else ("on-demand" if on_demand >= 4 else None)
    if not mode or event.get("dry_run"):
        return {
            "status": "quota_pending" if not mode else "quota_ready_dry_run",
            "spot_vcpus": spot, "on_demand_vcpus": on_demand, "launch_mode": mode,
        }
    s3 = boto3.client("s3", region_name=REGION)
    bucket = os.environ["LOCK_BUCKET"]
    lock_key = os.environ["LOCK_KEY"]
    try:
        s3.put_object(
            Bucket=bucket, Key=lock_key,
            Body=json.dumps({"run": RUN_TAG, "time_utc": now.isoformat(), "mode": mode}).encode(),
            IfNoneMatch="*", ServerSideEncryption="AES256",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in (
            "PreconditionFailed", "ConditionalRequestConflict"
        ):
            return {"status": "launch_already_claimed"}
        raise
    try:
        instance_id = _cost_constrained_launch(ec2, mode)
        print(json.dumps({"launched": instance_id, "market": mode}))
        return {
            "status": "launched", "instance_id": instance_id,
            "market": mode, "max_hours": 3,
        }
    except Exception:
        s3.delete_object(Bucket=bucket, Key=lock_key)
        raise
