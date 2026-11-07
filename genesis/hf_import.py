"""Explicit, bounded Hugging Face snapshot import for Genesis.

Default is catalogue/plan only. No network, spending or weight downloads unless
an operator explicitly runs import --execute --accept-license.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from .hf_models import (
    APPROVED_MODELS, MANIFEST_NAME, ModelImportError, SAFE_NAMES,
    sha256_file, verify_local_model,
)

MAX_IMPORT_BYTES = 1_500_000_000  # one ~1 GB baseline plus tokenizer metadata


def default_models_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "aurora" / "genesis" / "models"


def import_approved_model(key: str, *, destination: str | Path | None = None,
                          execute: bool = False, accept_license: bool = False,
                          max_bytes: int = MAX_IMPORT_BYTES, api=None,
                          downloader=None) -> dict:
    spec = APPROVED_MODELS.get(key)
    if not spec:
        raise ModelImportError("model not approved: use catalog to see known models")
    dest = Path(destination) if destination else default_models_dir() / key
    plan = {"model_key": key, "repo_id": spec["repo_id"],
            "revision": spec["revision"], "license": spec["license"],
            "destination": str(dest), "execute": execute}
    if not execute:
        return {**plan, "status": "plan_only", "downloaded": False}
    if not accept_license:
        raise ModelImportError("explicit --accept-license required")
    if not 1 <= max_bytes <= MAX_IMPORT_BYTES:
        raise ModelImportError("import size must be between 1 and 1500000000 bytes")
    if dest.exists() or dest.is_symlink():
        raise ModelImportError("destination exists; never overwrite an installed model")
    if api is None or downloader is None:
        try:
            from huggingface_hub import HfApi, snapshot_download
        except ImportError as exc:
            raise ModelImportError("install optional requirements_hf.txt first") from exc
        api = api or HfApi()
        downloader = downloader or snapshot_download

    info = api.model_info(spec["repo_id"], revision=spec["revision"],
                          files_metadata=True, token=False)
    if info.sha != spec["revision"]:
        raise ModelImportError("hub revision does not match the pinned commit")
    card = getattr(info, "card_data", None)
    license_id = (card.get("license") if isinstance(card, dict)
                  else getattr(card, "license", None))
    if str(license_id).lower() != spec["license"]:
        raise ModelImportError("model card license is missing or changed")
    selected = {}
    for item in info.siblings:
        name = item.rfilename
        if name not in SAFE_NAMES:
            continue
        size = getattr(item, "size", None)
        if not isinstance(size, int) or size < 0:
            raise ModelImportError("hub did not supply file size; cannot enforce cap")
        selected[name] = size
    if not {"config.json", "tokenizer_config.json", spec["weight_file"]} <= set(selected):
        raise ModelImportError("expected safetensors checkpoint or tokenizer missing")
    if sum(selected.values()) > max_bytes:
        raise ModelImportError("snapshot exceeds configured download size cap")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".genesis-hf-", dir=dest.parent))
    try:
        # Only known, non-executable text/config and safetensors files.
        downloader(repo_id=spec["repo_id"], revision=spec["revision"],
                   local_dir=str(stage), allow_patterns=sorted(selected),
                   token=False, max_workers=2)
        hashes = {}
        for name, expected_size in selected.items():
            file = stage / name
            if file.is_symlink() or not file.is_file() or file.stat().st_size != expected_size:
                raise ModelImportError("download incomplete or unexpected file size")
            hashes[name] = sha256_file(file)
        if hashes[spec["weight_file"]] != spec["weight_sha256"]:
            raise ModelImportError("weight SHA-256 did not match approved source")
        manifest = {"schema_version": 1, "model_key": key,
                    "repo_id": spec["repo_id"], "revision": spec["revision"],
                    "license": spec["license"],
                    "weight_sha256": spec["weight_sha256"],
                    "files": hashes}
        (stage / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        verify_local_model(stage, verify_hashes=True)
        if dest.exists():
            raise ModelImportError("destination became occupied during download")
        stage.rename(dest)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {**plan, "status": "imported", "downloaded": True,
            "bytes": sum(selected.values()), "files": len(selected)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Genesis approved HF model importer")
    parser.add_argument("action", choices=("catalog", "import", "verify"))
    parser.add_argument("--model", default="qwen2.5-0.5b-instruct")
    parser.add_argument("--destination")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--accept-license", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "catalog":
            result = {"models": APPROVED_MODELS, "downloads": False}
        elif args.action == "verify":
            path = args.destination or default_models_dir() / args.model
            result = {"status": "verified", "manifest":
                      verify_local_model(path, verify_hashes=True)}
        else:
            result = import_approved_model(
                args.model, destination=args.destination, execute=args.execute,
                accept_license=args.accept_license
            )
        print(json.dumps(result, indent=2))
    except ModelImportError as exc:
        parser.exit(2, f"Genesis HF import blocked: {exc}\n")


if __name__ == "__main__":
    main()
