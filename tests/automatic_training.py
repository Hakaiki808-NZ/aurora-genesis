"""No-cloud regression for approved, bounded automatic LoRA build admission."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path

from tools.aws.genesis_autotrain_controller import (
    TrainingBlocked, validate_manifest, validated_training_data, cost_gate
)


def denied(fn):
    try:
        fn()
    except TrainingBlocked:
        return
    raise AssertionError("unapproved automatic training passed safeguards")


def run():
    now=dt.datetime(2026,11,7,2,0,tzinfo=dt.timezone.utc)
    root=Path(__file__).resolve().parents[1]
    dataset=(root/"genesis/training/data/genesis_evidence_operations_v1.jsonl").read_bytes()
    prefix="genesis/training/automation"
    manifest={
        "schema":"genesis-auto-train-v1","approved":True,
        "source_license":"original-project-authored",
        "user_conversation_data":False,
        "dataset_key":prefix+"/datasets/evidence-operations-v1.jsonl",
        "dataset_sha256":hashlib.sha256(dataset).hexdigest(),
        "max_steps":8,"expires_utc":"2026-11-20T00:00:00Z"
    }
    assert validate_manifest(manifest,prefix=prefix,now=now)["max_steps"]==8
    assert validated_training_data(dataset,manifest["dataset_sha256"])==60
    denied(lambda:validated_training_data(dataset+b"!",manifest["dataset_sha256"]))
    denied(lambda:validate_manifest({**manifest,"approved":False},prefix=prefix,now=now))
    denied(lambda:validate_manifest({**manifest,"user_conversation_data":True},prefix=prefix,now=now))
    denied(lambda:validate_manifest({**manifest,"source_license":"user-uploaded-unreviewed"},prefix=prefix,now=now))
    denied(lambda:validate_manifest({**manifest,"dataset_key":"../outside.jsonl"},prefix=prefix,now=now))
    denied(lambda:validate_manifest({**manifest,"max_steps":200},prefix=prefix,now=now))
    denied(lambda:validate_manifest({**manifest,"expires_utc":"2026-11-06T00:00:00Z"},prefix=prefix,now=now))
    denied(lambda:validate_manifest({**manifest,"dataset_sha256":"abc"},prefix=prefix,now=now))
    denied(lambda:cost_gate("19.8","10.0"))
    denied(lambda:cost_gate("not-a-cost","10.0"))
    assert cost_gate("-0.0000000033","10.0")=="0"
    denied(lambda:cost_gate("-3.0","10.0"))
    assert cost_gate("0.5","10.0")=="0.5"
    print("AUTOMATIC_TRAINING_PLAN=PASS")


if __name__=="__main__":
    run()
