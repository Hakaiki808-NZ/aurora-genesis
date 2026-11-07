# Genesis Hugging Face model/weights integration (experimental)

**Status (2026-11-07):** approved base weights downloaded, SHA-256-verified and exercised on isolated temporary AWS CPU instances; checkpoint archived privately in encrypted S3. No persistent model-serving instance, Kyro integration or production deployment.

## Standards supported and deliberately distinct

- **Safetensors:** data-only model-weight files; do not import pickle-based `.bin`, `.pt`, `.pth` or unknown executable formats.
- **Transformers:** `config.json`, tokenizer files, generation configuration and `AutoModelForCausalLM` for supported architectures.
- **Hugging Face Hub:** versioned snapshots pinned to an immutable commit SHA; selective downloads.
- **PEFT/LoRA:** the existing GPU QLoRA training prototype and new bounded CPU LoRA pipeline emit `adapter_model.safetensors` plus `adapter_config.json`. Research adapter loading is explicitly opt-in and verifies the exact base checkpoint/revision, adapter digest and LoRA topology. **No automatic production adapter admission** is implemented; publisher signatures, independent quality/security review and rollback gates remain required.
- **GGUF:** an alternative quantized runtime format for llama.cpp/Ollama. It is NOT a drop-in replacement for Safetensors or guaranteed to load every model; the existing Ollama backend handles separately installed models.

## Approved initial base model

`Qwen/Qwen2.5-0.5B-Instruct` (Apache-2.0, ~988 MB safetensors weights) is already the base model selected by the project's QLoRA prototype. The catalogue in `genesis/hf_models.py` pins a specific Hugging Face commit and the weight file's published SHA-256.

Other language, embedding and specialist models are candidates for review, not automatically trusted or combined. Model weights cannot simply be concatenated to add abilities.

## Operator workflow

```bash
python -m genesis.hf_import catalog
python -m genesis.hf_import import --model qwen2.5-0.5b-instruct
# Plan only; no network or weights downloaded.
python -m pip install -r requirements_hf.txt
python -m genesis.hf_import import --model qwen2.5-0.5b-instruct --execute --accept-license
python -m genesis.hf_import verify --model qwen2.5-0.5b-instruct
export GENESIS_GENERATOR=huggingface
export GENESIS_HF_ENABLE=1
export GENESIS_HF_MODEL_DIR="$HOME/.local/share/aurora/genesis/models/qwen2.5-0.5b-instruct"
python run.py
```

The importer checks the upstream model ID, exact revision, declared license, individual file sizes, a 1.5 GB maximum download allowance and SHA-256. It rejects unknown files and remote code; creates a local manifest only after validating downloaded files. Model snapshots and other weights must stay **outside GitHub** and outside public static Kyro assets. Imports require working internet access, adequate disk/RAM and an operator's explicit license acceptance. A snapshot integrity manifest is NOT a cryptographic publisher signature.

The inference backend stays off until both `GENESIS_GENERATOR=huggingface` and `GENESIS_HF_ENABLE=1` are configured. It uses local files only, `trust_remote_code=False`, `use_safetensors=True`, CPU execution and bounded requests. It returns text only to Genesis cognition; it cannot call tools or authorize Engine actions.

## Research-only trained adapter inference

The approved base weights remain immutable. After explicitly training and privately
archiving a versioned CPU LoRA adapter, copy the adapter and its accompanying
`metrics.json` to private local directories. Run:

```bash
python -m pip install -r requirements_hf_adapter.txt
export GENESIS_GENERATOR=huggingface
export GENESIS_HF_ENABLE=1
export GENESIS_HF_MODEL_DIR=/private/approved-qwen-checkpoint
export GENESIS_HF_ADAPTER_EXPERIMENTAL_ENABLE=1
export GENESIS_HF_ADAPTER_DIR=/private/trained-adapter
export GENESIS_HF_ADAPTER_METRICS=/private/training-metrics.json
python run.py
```

When the adapter flag is off, base-only inference behaves as before. The research
loader rejects missing, modified, unsupported or wrong-base adapters. It is **not**
a substitute for independent Engine admission, provenance signing, held-out evaluation
or tenant isolation. See the
[real two-round training report](../research/GENESIS_REAL_LORA_TRAINING_2026-11-07.md).

## Boundaries and acceptance gates

**Kyro:** may expose approved model selection and telemetry in a future authenticated admin UI; does not ingest weights into the browser.

**Genesis:** retains policy, knowledge modules, provenance and optional text-generation adapters. Model output is an unverified suggestion, not evidence of a valid action or a trained Genesis foundation model.

**Aurora:** retains execution authority, resource containment, admission, accounting and rollback; production acceptance must be implemented independently of Genesis model output.

**Verified test milestones:** base model download, immutable revision pin, local SHA-256 verification, private S3 archive, real CPU inference, two supervised short-lived AWS experiments and measured preliminary reasoning probes. In-memory Qwen2 attention normalization removes the observed false-positive sliding-window warning without changing source files; real benchmark logs recorded zero occurrences.

**Open production gates:** signed model admission, tenant isolation, independent quality and safety review, model-adapter compatibility, truly unseen benchmark coverage, factual retrieval grounding, concurrency tests, authenticated Kyro model service and deployment rollback. The [2026-11-07 reasoning hardening report](../research/GENESIS_REASONING_HARDENING_2026-11-07.md) records **4/12 raw**, **7/12 original Genesis**, and **10/12 hardened Genesis** strict passes on the *same small public test suite*, with serious residual weaknesses. This does **not** establish transferable intelligence, a newly trained foundation model or public-beta readiness.

**Billing:** temporary AWS tests can incur small EC2/S3 charges; AWS Budgets are alerts, not hard cost limits. No persistent paid instance is required to read this repository or run its offline mock tests.

## Source material

- HF Transformers loading models: https://huggingface.co/docs/transformers/models
- Hub snapshot downloads: https://huggingface.co/docs/huggingface_hub/en/package_reference/file_download
- HF PEFT checkpoint format: https://huggingface.co/docs/peft/main/developer_guides/checkpoint
- Qwen model files/license: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct
- GGUF/llama.cpp: https://huggingface.co/docs/transformers/main/en/community_integrations/llama_cpp
