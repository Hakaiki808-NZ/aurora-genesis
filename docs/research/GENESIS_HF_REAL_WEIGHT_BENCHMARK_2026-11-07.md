# Genesis real Hugging Face weights: first CPU inference and reasoning run

**Date:** 2026-11-07 (NZDT)  
**Status:** REAL, REPRODUCIBLE experimental CPU inference completed. **Not a production deployment.**  
**Release classification:** Pre-alpha research evidence; do not equate smoke-prompt answers with AGI, safety approval or reliable reasoning.

## Input and provenance

- Base model: `Qwen/Qwen2.5-0.5B-Instruct`, Apache-2.0 (as declared by publisher).
- Hugging Face immutable revision: `c89bee90d9f811437d9735454613c35b4a3c4dc8`.
- Required `model.safetensors` SHA-256: `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.
- **Observed:** Nine files totalling 999,602,614 bytes downloaded by `genesis.hf_import` with `--execute --accept-license`; local SHA-256 validation passed. S3 `HeadObject` independently confirmed `model/model.safetensors` at 988,097,824 bytes, encrypted using AES256.
- Persisted private artifacts: `s3://<private-project-artifact-bucket>/genesis/hf/qwen2p5-0p5b-instruct/` (weights, import manifest, verification, first-run results, eager-attention results, end-to-end Genesis results, post-fix test).
- **Do not commit any model weights to this public repository or expose the private artifact-bucket name here.**

## Compute and resource measurements

- AWS account: development environment; Region: `ap-southeast-2`.
- EC2 test: `m7i-flex.large` (2 vCPU, 8 GiB RAM), Amazon Linux 2023, CPU-only.
- Actual installed packages include `torch==2.6.0`, `transformers==4.51.3`, `huggingface_hub==0.36.0`, `safetensors==0.5.3` and `accelerate==1.6.0`.
- Backend loaded weights locally using `trust_remote_code=False`, `local_files_only=True`, `use_safetensors=True`, float32 and explicit token ceilings; no external model inference calls.
- Peak resident memory reported by `resource.getrusage`: 3,365,472 KiB (~3.21 GiB) on eager-attention run.
- End-to-end per-prompt latency including generation: ~0.85–3.05 seconds in the six simple direct-backend prompts (model initialization occurs during the first call).
- Measured approximate output tokens/sec across the direct prompt wall-clock: ~0.98–5.44. This **is not** a standardized decode-only tokens/sec benchmark. The first prompt includes model loading.
- Transformers emitted a sliding-window-attention compatibility warning both before and after switching to eager attention. The backend now supplies explicit attention masks and eager attention, but the warning remains; investigate before publishing production throughput/quality claims.

## Genuine model outputs

The six prompts were original, minimal operator smoke tests, **not** held-out academic evaluations:

| Probe | Expected | Actual | Assessment |
|---|---|---|---|
| `17 * 19` | 323 | `323` | Correct |
| Four pens cost $6; price of ten | $15 | `Ten pens would cost $60.` | **Incorrect** |
| All glims are snarps; no snarps are green | No | `No.` | Correct |
| NZ capital and island | Wellington, North Island | Wellington, North Island | Correct |
| Exact historical temperature without data | Explicitly say unknown | `I'm sorry, but I can't assist with that.` | Did not fabricate a number but gave poor uncertainty handling |
| Three specified words | sky river stone | `Sky, river, stone.` | Substantially follows format |

Retesting with eager attention and explicit attention masks yielded the same answers. **There is no evidence the configuration adjustment fixed the arithmetic error.**

## Full Genesis integration

A separate invocation through `Genesis.respond_with_trace` with the same real-weight backend found:

1. `Calculate 17 * 19` -> `323`, selected `calculate` (deterministic tool).
2. `Four pens cost $6. What do ten pens cost at the same rate?` -> the neural answer eventually states **$15** but begins with a contradictory claim that ten pens cost the same as four, so reasoning is still unreliable.
3. `Explain why checksums are useful when transferring files.` initially selected `acknowledge_learning`, incorrectly treating an imperative question as a user assertion. This was an existing Genesis learner-parser fault, not a corrupt checkpoint.

**Code fix:** `genesis/learning.py` now excludes common interrogative/explanatory prefixes from implicit declarative learning. Added `tests/question_routing.py` and included it in `verify.py`. The isolated regression passed on AWS, and a real-weight post-fix replay selected `neural_answer` and generated a relevant checksum explanation.

## Security, governance and cost

- Aurora operational authority was unchanged; model generation stayed text-only. No model-proposed tool calls or Engine receipts were accepted.
- Kyro's deployed public-facing inference was **not** changed or enabled by these tests.
- The instance was launched in a security group with **zero inbound rules**, IAM scoped to SSM and private S3 write-only model artifact prefix, EBS encryption and automatic disk deletion.
- Separate boot-time 50-minute termination timer and one-time AWS EventBridge Scheduler termination watchdog were created. Verify eventual instance/volume termination independently.
- AWS account currently restricts new EC2 to Free Tier-eligible types; the first `t3.large` launch request was refused by AWS and did not provision an instance. `m7i-flex.large` was approved as eligible. Existing account budget alert is **not** a hard cost cap; actual billing/credit use may lag and must be checked separately.

## Evidence and acceptance

- Source: `tools/aws/hf_benchmark_install.sh` and `tools/aws/hf_benchmark_cpu.py` on this pull-request branch.
- GitHub full tests and neural adapter checks passed after the question-routing fix.
- **Passed:** immutable approved model revision; file hashes; real local CPU generation; private model+results backup; Genesis deterministic and neural routing; explanation question regression; no production exposure.
- **Not passed:** reasoning reliability, standardized generalization benchmarks, verified attention warning resolution, concurrent load/availability, authenticated Kyro-to-Genesis live deployment, supervised model admission, automatic operational rollback.

**Next action:** Preserve the baseline, add hidden/unseen evaluation and precise task metrics, improve arithmetic word-problem performance and uncertainty behavior with deterministic verification or vetted model upgrades, investigate attention warnings, and keep public promotion gated by objective review.
