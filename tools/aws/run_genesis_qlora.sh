#!/bin/bash
# Genesis GPU fine-tune bootstrap; intended for one disposable GPU EC2 instance.
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export PYTHONUNBUFFERED=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export HF_HUB_DISABLE_TELEMETRY=1
export WANDB_DISABLED=true
export TRANSFORMERS_NO_ADVISORY_WARNINGS=1
AWS_DEFAULT_REGION="ap-southeast-2"
OUTPUT_BUCKET="aurora-genesis-dev-foundation-artifactbucket-3zbfubklmplx"
PREFIX="genesis/finetune/qwen2p5-0p5b-v0"
MAX_SECONDS=9000
MAX_STEPS=60
REPO="https://github.com/Hakaiki808-NZ/aurora-genesis.git"
# The immutable source SHA is supplied by the launch controller.
SOURCE_SHA="${GENESIS_SOURCE_SHA:?Missing pinned source commit}"

mkdir -p /opt/genesis /opt/genesis/output
exec > >(tee -a /var/log/genesis-gpu-training.log) 2>&1
shutdown -h +180 >/dev/null 2>&1 || true
cleanup() {
  set +e
  trap - EXIT
  date -u +"UTC finish: %Y-%m-%dT%H:%M:%SZ"
  if command -v aws >/dev/null 2>&1; then
    aws s3 cp /var/log/genesis-gpu-training.log "s3://$OUTPUT_BUCKET/$PREFIX/logs/training.log" || true
    if [ -d /opt/genesis/output/adapter ]; then
      aws s3 cp /opt/genesis/output/adapter "s3://$OUTPUT_BUCKET/$PREFIX/adapter/" --recursive || true
    fi
    if [ -f /opt/genesis/output/metrics.json ]; then
      aws s3 cp /opt/genesis/output/metrics.json "s3://$OUTPUT_BUCKET/$PREFIX/metrics.json" || true
    fi
  fi
  shutdown -h now || poweroff || true
}
trap cleanup EXIT

date -u +"UTC begin: %Y-%m-%dT%H:%M:%SZ"
nvidia-smi
cd /opt/genesis
git clone "$REPO" project
cd project
git checkout "$SOURCE_SHA"
/opt/pytorch/bin/python -m pip install --no-cache-dir -r genesis/training/requirements_qlora.txt

export GENESIS_MAX_STEPS="$MAX_STEPS"
export GENESIS_DATASET="/opt/genesis/project/genesis/training/data/genesis_sft_v0.jsonl"
export GENESIS_OUTPUT="/opt/genesis/output"
timeout --signal=TERM --kill-after=30s "$MAX_SECONDS" /opt/pytorch/bin/python genesis/training/finetune_qlora.py
echo "Training command completed."
