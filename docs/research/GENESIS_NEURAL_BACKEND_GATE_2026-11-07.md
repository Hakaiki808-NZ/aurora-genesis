# Genesis — bounded neural reasoning integration

Date: 2026-11-07 (NZDT)  
Release classification: experimental, **not production-ready or a trained Genesis neural checkpoint**.

## Architecture

```text
Kyro (UI) -> Genesis Cognition
               |         |
     deterministic       optional pretrained neural backend
     memory / goals      (text response only)
     / Guardians         no tool schema or execution authority
               |
     Model Authorization Proof
               |
        Aurora Engine (separate authority, NOT connected by this change)
```

This integration does not change trained neural weights. It connects a third-party pretrained model to the existing Genesis symbolic framework. There is no general intelligence or benchmark score claim.

## Implementation

- `genesis/bedrock_backend.py`: synchronous Bedrock Converse adapter; explicit `maxTokens`, no tool definitions, output length limits, no raw exception/prompt logging, bounded attempted calls per process, and safe `None` fallback on AWS errors.
- `genesis/model.py`: separate opt-in `GENESIS_GENERATOR=bedrock` and `GENESIS_BEDROCK_ENABLE=1`; normal default remains current Ollama/symbolic mode.
- `genesis/cognition_patch.py`: neural text proposals only for unmatched requests. Structured learning, factual recall, calculations, policy-sensitive actions and goals continue through existing deterministic routing. Stored user assertions are marked as potentially untrusted.
- `genesis/cognition.py`: neural output cannot be automatically recorded as a validated training example.
- `tests/neural_backend.py`: no-cloud-cost mocked inference, quota budget, model output failure, deterministic action, memory and feature flag checks.

## Settings (only after AWS access/quotas and expenditure approval)

```bash
export GENESIS_GENERATOR=bedrock
export GENESIS_BEDROCK_ENABLE=1
export GENESIS_BEDROCK_REGION=ap-southeast-2
export GENESIS_BEDROCK_MODEL_ID=apac.amazon.nova-micro-v1:0
export GENESIS_BEDROCK_MAX_TOKENS=256
export GENESIS_BEDROCK_MAX_CALLS=8
python3 -m tests.neural_backend
```

`GENESIS_BEDROCK_MAX_CALLS` is **per process**, not a daily/monthly billing cap, and multiple concurrent processes can exceed it. Set strict IAM permissions, account-level policies and monitoring before real inference. A US$1 AWS Budget is an alert only, never an expense hard stop. Do not ingest personal/private user data into external inference without consent, retention policy and provider assessment.

## AWS deployment gate

The connected AWS account in Sydney was inspected 2026-11-07 NZDT:

- Active model and inference profile catalogue advertises Nova Micro and `apac.amazon.nova-micro-v1:0`.
- Bedrock service quotas for Nova Micro on-demand/cross-region tokens per minute were reported **0**.
- Prior bounded Converse test received `ThrottlingException: Too many tokens per day`.
- Current Kyro Lambda is active with Genesis reference mode but no Bedrock configuration. **No AWS deployment or model inference enabled by this branch.**
- Do not confuse an advertised model catalogue entry with ability to invoke or bill it.

Before enabling: obtain account-approved nonzero quota and a successful one-token-budget probe, verify model/region IAM permissions, attach monitoring/cost protections and manual kill switch, run the full Genesis regression suite, and test the authenticated Kyro-to-Genesis route in a browser. Keep the private Aurora Engine independent.

## Learning and evaluation roadmap

1. **Baseline:** freeze independent factual QA, multistep reasoning, safety-policy, prompt-injection, and unfamiliar-environment tasks. Record pass/fail and human-rater criteria, not just GitHub job success.
2. **Neural inference:** compare a pretrained model with the deterministic baseline, include cost/tokens/latency, and label each outcome (correct, incorrect, abstained, inaccessible).
3. **Controlled memory and feedback:** accept only human-reviewed, licensed examples; tag provenance, remove PII, deduplicate and isolate a hidden test set. Never treat self-generated answers or synthetic pass conditions as verified training.
4. **Optional fine-tuning:** only if a suitable open-weight model, legally usable training data, compute budget and reproducible experiment are available. Publish checkpoint hash, dataset version, eval scorecard and failure cases.
5. **Generalisation:** blind testing on unfamiliar games and tasks, reproducible multi-seed results, and held-out benchmarks. ARC LS20 5/7 is game-specific and not evidence of AGI.

Status: neural integration engineering complete in development branch, **model training not performed**, Bedrock production inference blocked, qualification pending.
