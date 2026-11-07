"""Read-only *research* admission checks for a local PEFT adapter.

A passing hash is byte integrity, not a publisher signature, safety approval,
or an Aurora operational entitlement. Production admission is separate.
"""
from __future__ import annotations

import json
from pathlib import Path

from .hf_models import sha256_file


class AdapterAdmissionError(ValueError):
    pass


_ALLOWED_FILES = frozenset({
    "README.md", "adapter_config.json", "adapter_model.safetensors",
    "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
    "added_tokens.json", "merges.txt", "vocab.json"
})


def verify_local_adapter(
    adapter_dir: str | Path,
    metrics_path: str | Path,
    base_manifest: dict,
    *,
    check_hash: bool = True,
) -> dict:
    """Reject mismatched, unapproved and mutable-format adapters before loading."""
    root = Path(adapter_dir)
    provenance = Path(metrics_path)
    if not root.is_dir() or root.is_symlink():
        raise AdapterAdmissionError("missing or symlink adapter directory")
    if not provenance.is_file() or provenance.is_symlink():
        raise AdapterAdmissionError("training provenance is absent or symlinked")
    inventory = list(root.iterdir())
    if not inventory or any(
        item.is_symlink() or not item.is_file() or item.name not in _ALLOWED_FILES
        for item in inventory
    ):
        raise AdapterAdmissionError("unapproved file, directory or symlink in adapter")
    weight = root / "adapter_model.safetensors"
    config_file = root / "adapter_config.json"
    if not weight.is_file() or not config_file.is_file():
        raise AdapterAdmissionError("PEFT adapter checkpoint or config is absent")
    try:
        meta = json.loads(provenance.read_text(encoding="utf-8"))
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AdapterAdmissionError("invalid JSON adapter provenance") from exc
    if not isinstance(meta, dict) or not isinstance(config, dict):
        raise AdapterAdmissionError("adapter provenance must be structured JSON")
    if (meta.get("base_weight_sha256") != base_manifest.get("weight_sha256")
            or meta.get("base_revision") != base_manifest.get("revision")
            or meta.get("training_mode") != "cpu-fp32-lora-r4"
            or meta.get("status") != "completed_experiment"
            or meta.get("promote") is not False
            or not 1 <= int(meta.get("completed_steps", 0)) <= 64):
        raise AdapterAdmissionError("model, revision or training provenance mismatch")
    digest = meta.get("adapter_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise AdapterAdmissionError("invalid adapter checksum")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise AdapterAdmissionError("invalid adapter checksum") from exc
    if (not isinstance(meta.get("adapter_bytes"), int)
            or meta["adapter_bytes"] != weight.stat().st_size
            or weight.stat().st_size > 20_000_000):
        raise AdapterAdmissionError("adapter size differs or is unbounded")
    if check_hash and sha256_file(weight) != digest:
        raise AdapterAdmissionError("adapter checkpoint hash mismatch")
    if (
        config.get("peft_type") != "LORA"
        or config.get("task_type") != "CAUSAL_LM"
        or config.get("r") != 4
        or config.get("lora_alpha") != 8
        or config.get("bias") != "none"
        or set(config.get("target_modules") or ()) != {"q_proj", "v_proj"}
    ):
        raise AdapterAdmissionError("unsupported LoRA topology")
    return meta
