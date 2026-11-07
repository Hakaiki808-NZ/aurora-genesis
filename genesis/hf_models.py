"""Audited, revision-pinned Hugging Face model catalogue and local file checks.

This is model DATA, never an Aurora execution permission or a Kyro credential.
Do not accept executable model repository code or pickle weight formats.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

MANIFEST_NAME = "genesis-hf-manifest.json"

# Curated starting point already used by Genesis's experimental QLoRA trainer.
# Commit and safetensors hash are taken from the model's Hugging Face files page.
APPROVED_MODELS = {
    "qwen2.5-0.5b-instruct": {
        "repo_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "c89bee90d9f811437d9735454613c35b4a3c4dc8",
        "license": "apache-2.0",
        "weight_file": "model.safetensors",
        "weight_sha256": "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe",
        "task": "text-generation",
    },
}
SAFE_NAMES = frozenset({
    "README.md", "LICENSE", "config.json", "generation_config.json",
    "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
    "vocab.json", "merges.txt", "model.safetensors",
})


class ModelImportError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_local_model(directory: str | Path, *, verify_hashes: bool = False) -> dict:
    """Reject unapproved, incomplete or modified on-disk model snapshots.

    verify_hashes=True scans all files including the weights before first load.
    A manifest is a local integrity record, NOT a publisher signature.
    """
    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        raise ModelImportError("model directory is missing or a symlink")
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ModelImportError("approved model manifest missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ModelImportError("invalid model manifest") from exc
    if not isinstance(manifest, dict):
        raise ModelImportError("invalid model manifest")
    spec = APPROVED_MODELS.get(manifest.get("model_key"))
    if spec is None:
        raise ModelImportError("model is not in the approved catalogue")
    for key in ("repo_id", "revision", "license", "weight_sha256"):
        if manifest.get(key) != spec[key]:
            raise ModelImportError("model metadata does not match approved revision")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ModelImportError("file inventory is missing")
    if not {"config.json", "tokenizer_config.json", spec["weight_file"]} <= set(files):
        raise ModelImportError("model configuration, tokenizer or weights missing")
    if files[spec["weight_file"]] != spec["weight_sha256"]:
        raise ModelImportError("weight digest does not match approved checkpoint")
    for name, expected_hash in files.items():
        if name not in SAFE_NAMES or not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ModelImportError("unexpected file or invalid digest")
        try:
            int(expected_hash, 16)
        except ValueError as exc:
            raise ModelImportError("invalid digest") from exc
        file = root / name
        if not file.is_file() or file.is_symlink():
            raise ModelImportError("required model file is missing or a symlink")
        if verify_hashes and sha256_file(file) != expected_hash:
            raise ModelImportError("model file failed SHA-256 integrity check")
    return manifest
