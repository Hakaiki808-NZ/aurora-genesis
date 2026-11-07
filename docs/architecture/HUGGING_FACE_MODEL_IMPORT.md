# Genesis Hugging Face model/weights integration (experimental)

**Status:** opt-in import and offline CPU inference implementation; NOT downloaded or deployed by this change.

## Standards supported and deliberately distinct

- **Safetensors:** data-only model-weight files; do not import pickle-based `.bin`, `.pt`, `.pth` or unknown executable formats.
- **Transformers:** `config.json`, tokenizer files, generation configuration and `AutoModelForCausalLM` for supported architectures.
- **Hugging Face Hub:** versioned snapshots pinned to an immutable commit SHA; selective downloads.
- **PEFT/LoRA:** existing experimental QLoRA training emits `adapter_model.safetensors` and `adapter_config.json`. Adapter loading into the live Genesis backend is **not yet enabled**; base-model compatibility, evaluation and signing are required first.
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

## Boundaries and acceptance gates

**Kyro:** may expose approved model selection and telemetry in a future authenticated admin UI; does not ingest weights into the browser.

**Genesis:** retains policy, knowledge modules, provenance and optional text-generation adapters. Model output is an unverified suggestion, not evidence of a valid action or a trained Genesis foundation model.

**Aurora:** retains execution authority, resource containment, admission, accounting and rollback; production acceptance must be implemented independently of Genesis model output.

**Unfinished gates:** full model download and real CPU generation smoke test, resource measurements, signed model admission, per-tenant model isolation, license review, adapter compatibility checks and held-out quality/security evaluations. No AWS deployment, GPU training or inference spending is authorized by this change.

## Source material

- HF Transformers loading models: https://huggingface.co/docs/transformers/models
- Hub snapshot downloads: https://huggingface.co/docs/huggingface_hub/en/package_reference/file_download
- HF PEFT checkpoint format: https://huggingface.co/docs/peft/main/developer_guides/checkpoint
- Qwen model files/license: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct
- GGUF/llama.cpp: https://huggingface.co/docs/transformers/main/en/community_integrations/llama_cpp
