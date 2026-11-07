#!/usr/bin/env bash
# Isolated and bounded AWS CPU model import/benchmark. Do not use on shared hosts.
set -Eeuo pipefail
test -n "$GENESIS_HF_S3_BUCKET"
test -n "$GENESIS_HF_S3_PREFIX"
test -n "$GENESIS_HF_EXPECTED_COMMIT"
BASE=/opt/genesis-hf
REPO="$BASE/repo"
MODEL="$BASE/model"
LOG="$BASE/install.log"
S3="s3://$GENESIS_HF_S3_BUCKET/$GENESIS_HF_S3_PREFIX"
mkdir -p "$BASE"
exec > >(tee -a "$LOG") 2>&1
trap 'status=$?; echo "EXIT_STATUS=$status"; aws s3 cp "$LOG" "$S3/install.log" --sse AES256 || true' EXIT
echo "START_UTC=$(date -u +%FT%TZ)"
free -h
df -h /
dnf -y install git python3-pip
git clone --depth 1 --branch feature/genesis-huggingface-model-import https://github.com/Hakaiki808-NZ/aurora-genesis.git "$REPO"
actual_commit="$(git -C "$REPO" rev-parse HEAD)"
test "$actual_commit" = "$GENESIS_HF_EXPECTED_COMMIT" || { echo "Checkout changed; refusing to run unpinned code"; exit 1; }
python3 -m venv "$BASE/venv"
"$BASE/venv/bin/python" -m pip install -q --upgrade pip
"$BASE/venv/bin/python" -m pip install -q --no-cache-dir torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
"$BASE/venv/bin/python" -m pip install -q --no-cache-dir transformers==4.51.3 huggingface_hub==0.36.0 safetensors==0.5.3 accelerate==1.6.0 hf_xet
echo "DEPENDENCIES_INSTALLED_UTC=$(date -u +%FT%TZ)"
export HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false
export GENESIS_HF_MODEL_DIR="$MODEL"
export GENESIS_HF_RESULTS="$BASE/results.json"
export PYTHONPATH="$REPO"
cd "$REPO"
"$BASE/venv/bin/python" -m genesis.hf_import import --model qwen2.5-0.5b-instruct --destination "$MODEL" --execute --accept-license
"$BASE/venv/bin/python" -m genesis.hf_import verify --model qwen2.5-0.5b-instruct --destination "$MODEL" > "$BASE/verification.json"
echo "WEIGHTS_IMPORTED_AND_VERIFIED_UTC=$(date -u +%FT%TZ)"
"$BASE/venv/bin/python" -u tools/aws/hf_benchmark_cpu.py
aws s3 cp "$BASE/verification.json" "$S3/verification.json" --sse AES256
aws s3 cp "$BASE/results.json" "$S3/results.json" --sse AES256
aws s3 cp "$MODEL/" "$S3/model/" --recursive --exclude ".cache/*" --no-progress --sse AES256
echo "WEIGHTS_AND_RESULTS_STORED_IN_PRIVATE_S3_UTC=$(date -u +%FT%TZ)"
