"""Offline, no-weights and no-cloud checks for the approved model import path."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from genesis.hf_backend import HuggingFaceBackend
from genesis.hf_import import import_approved_model
from genesis.hf_models import (
    APPROVED_MODELS, MANIFEST_NAME, ModelImportError, sha256_file,
    verify_local_model
)
from genesis import Genesis


def rejected(fn):
    try:
        fn()
    except ModelImportError:
        return
    raise AssertionError("unsafe model import was accepted")


def run():
    key = "qwen2.5-0.5b-instruct"
    spec = APPROVED_MODELS[key]
    planned = import_approved_model(key)
    assert planned["status"] == "plan_only" and not planned["downloaded"]
    rejected(lambda: import_approved_model("unapproved/model"))
    rejected(lambda: import_approved_model(key, execute=True, accept_license=False))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mock-model"
        root.mkdir()
        for name in ("config.json", "tokenizer_config.json", "model.safetensors"):
            (root / name).write_bytes(b"safe-test-" + name.encode())
        hashes = {n: sha256_file(root / n)
                  for n in ("config.json", "tokenizer_config.json", "model.safetensors")}
        # Simulate the approved digest in a fake fixture without downloading 1GB.
        with patch.dict(APPROVED_MODELS, {key: {**spec,
                         "weight_sha256": hashes["model.safetensors"]}}):
            manifest = {"schema_version": 1, "model_key": key,
                        "repo_id": spec["repo_id"], "revision": spec["revision"],
                        "license": spec["license"],
                        "weight_sha256": hashes["model.safetensors"], "files": hashes}
            (root / MANIFEST_NAME).write_text(json.dumps(manifest))
            assert verify_local_model(root, verify_hashes=True)["model_key"] == key
            backend = HuggingFaceBackend(model_dir=str(root))
            assert not backend.available()
            assert backend.generate("hello") is None
            active = HuggingFaceBackend(model_dir=str(root), enabled=True, max_calls=1)
            assert active.call_count == 0
            assert active.max_calls == 1
            (root / "config.json").write_text("tampered")
            rejected(lambda: verify_local_model(root, verify_hashes=True))
            (root / "config.json").write_bytes(b"safe-test-config.json")
            bad = dict(manifest, revision="main")
            (root / MANIFEST_NAME).write_text(json.dumps(bad))
            rejected(lambda: verify_local_model(root))
            bad = dict(manifest, files={**hashes, "../evil.py": "a" * 64})
            (root / MANIFEST_NAME).write_text(json.dumps(bad))
            rejected(lambda: verify_local_model(root))

    with tempfile.TemporaryDirectory() as tmp:
        with patch.dict(os.environ, {"GENESIS_GENERATOR": "huggingface",
                     "GENESIS_HF_ENABLE": "0", "GENESIS_HF_MODEL_DIR": tmp}):
            with Genesis(state_path=Path(tmp)/"test.db",
                         workspace=Path(tmp)/"ws") as model:
                assert model.cognition.backend.name == "huggingface"
                assert not model.cognition.backend.available()
    print("HUGGINGFACE_IMPORT=PASS")


if __name__ == "__main__":
    run()
