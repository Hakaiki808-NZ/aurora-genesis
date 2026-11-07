#!/usr/bin/env bash
set -euo pipefail
URL="http://127.0.0.1:${GENESIS_OSS_PORT:-8877}"
curl --fail --silent --show-error "$URL/health" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get("status")=="ok",d; print("HEALTH=PASS")'
# Must confirm the actual neural backend was used, not an HTTP 200 from symbolic fallback.
curl --fail --silent --show-error -X POST "$URL/chat" -H 'Content-Type: application/json' \
  --data '{"message":"Explain the purpose of a checksum.","trace":true}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("trace",{}).get("chosen_action")=="neural_answer",d; assert d.get("answer"),d; print("NEURAL_INFERENCE=PASS"); print("RESPONSE:",d["answer"][:250])'
