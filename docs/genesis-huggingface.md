# Genesis × Hugging Face open-weight integration

**Status (2026-11-07):** Experimental opt-in code path. No pretrained weights downloaded,
no GPU instance provisioned, no fine-tuning run launched, no production deployment.

## Model selection and licence

| Candidate | Role | Licence |
| --- | --- | --- |
| [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) | Local adapter smoke tests | Apache-2.0 |
| [Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) | First parameter-efficient fine-tuning candidate | Apache-2.0 |

Re-verify upstream model cards and immutable revision hashes before downloading;
review third-party assets and licenses before redistributing any weights.
Do not interpret the project Apache-2.0 licence as automatically relicensing
third-party checkpoints.

## Trust boundaries

Kyro -> Genesis cognition -> optional local HuggingFaceBackend -> text proposal only.
Genesis's policy, guardians, authorization proofs and tool path remain separate.
Aurora owns operational execution. The adapter has **no engine authority**, tool
schemas, filesystem write interface, or external inference API.

## Safe, offline-by-default setup

The backend has two explicit switches. Neither is enabled automatically.
Loading a model requires memory beyond the current AWS t3.small server, so
**do not enable it there**. Provision a separately authorized, GPU-capable runtime
only after quota, data, security and cost gates are satisfied.

1. On an appropriately sized controlled development machine install optional
   dependencies (not part of default production requirements):
   python -m pip install "transformers>=4.51" accelerate torch safetensors huggingface_hub
2. Review the upstream revision and cache the pinned weight files in a separate,
   approved download step:
   hf download Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca
   This was the upstream model revision inspected on 2026-11-07; re-check
   before use. Download requires internet/storage.
3. Set GENESIS_GENERATOR=huggingface and GENESIS_HF_ENABLE=1 only in the
   isolated runtime, together with GENESIS_HF_REVISION=c1899de289a04d12100db370d81485cdf75e47ca.
   Default model is Qwen/Qwen3-0.6B.
4. Run python -m tests.huggingface_backend (offline mocks).
5. For approved 1.7B evaluation, set GENESIS_HF_MODEL_ID=Qwen/Qwen3-1.7B,
   select its own pinned revision, and cache it in advance.

Supported bounds: GENESIS_HF_MAX_TOKENS (1-256; default 128) and
GENESIS_HF_MAX_CALLS (1-25 per process; default 8).
Generation is deterministic and capped; failed calls consume the per-process
allowance. Available() is not proof weights are cached or GPU exists.
Model loading uses local_files_only=True, trust_remote_code=False and an immutable
pinned 40-character revision. No Hub networking occurs on the inference path.
Do not ingest private user data into training without consent and governance.

## AWS and training gate

Account observations from Sydney, 2026-11-07:
- One running t3.small; not appropriate for this 0.6B+ inference or training.
- EC2 G/VT on-demand GPU quota: **0 vCPU**; an existing increase
  request for **4 vCPU** is at CASE_OPENED (not yet usable).
- Existing US$1 Zero-Spend Budget is an **alert**, not a hard cap.
- Earlier bounded 1,123-parameter Lambda training checkpoint is not an LLM.

Before paid LoRA/QLoRA fine-tuning: verify open-weight licence and pinned
revision, obtain provenance-tracked, human-reviewed training and holdout datasets,
ensure nonzero GPU quota, set an operational hard stop/termination plan and
independent spend checks within the user's US$30 authorization,
establish least-privilege execution, and run held-out evaluations.
No autonomous billing or ongoing job is started by this integration.

## Acceptance gates

- No network, model weights, or GPU needed for default and unit-test paths.
- Cannot enable without explicit generator mode and enable switch.
- Unknown model IDs rejected; unpinned model load rejected.
- Model output is untrusted text; calculations/tool decisions remain under
  Genesis's deterministic/policy paths.
- Actual GPU-based quality, safety and fine-tuning evaluation **not yet passed**.
