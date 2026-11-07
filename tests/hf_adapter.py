"""Offline adapter admission gates: byte integrity, topology and provenance."""
from __future__ import annotations
import hashlib
import json
import tempfile
from pathlib import Path

from genesis.hf_adapter import AdapterAdmissionError, verify_local_adapter
from genesis.hf_backend import HuggingFaceBackend


def rejected(fn):
    try:
        fn()
    except AdapterAdmissionError:
        return
    raise AssertionError("invalid adapter incorrectly admitted")


def run():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)
        ad=p/"adapter"
        ad.mkdir()
        weights=b"synthetic inert adapter weights, not real model"
        (ad/"adapter_model.safetensors").write_bytes(weights)
        config={"peft_type":"LORA","task_type":"CAUSAL_LM","r":4,"lora_alpha":8,
                "target_modules":["q_proj","v_proj"],"bias":"none"}
        (ad/"adapter_config.json").write_text(json.dumps(config))
        base={"weight_sha256":"a"*64,"revision":"pinned-revision"}
        metrics={"base_weight_sha256":"a"*64,"base_revision":"pinned-revision",
                 "training_mode":"cpu-fp32-lora-r4",
                 "status":"completed_experiment","completed_steps":8,
                 "promote":False,
                 "adapter_sha256":hashlib.sha256(weights).hexdigest(),
                 "adapter_bytes":len(weights)}
        manifest=p/"metrics.json"
        manifest.write_text(json.dumps(metrics))
        assert verify_local_adapter(ad,manifest,base)["completed_steps"]==8
        assert not HuggingFaceBackend(
            model_dir=str(p),enabled=False,adapter_enabled=True,
            adapter_dir=str(ad),adapter_metrics=str(manifest)
        ).available()
        try:
            HuggingFaceBackend(adapter_enabled=True,enabled=True)
            raise AssertionError("incomplete adapter enable accepted")
        except ValueError:
            pass

        (ad/"adapter_model.safetensors").write_bytes(b"modified!")
        rejected(lambda: verify_local_adapter(ad,manifest,base))
        (ad/"adapter_model.safetensors").write_bytes(weights)
        (ad/"run.py").write_text("print('never load')")
        rejected(lambda: verify_local_adapter(ad,manifest,base))
        (ad/"run.py").unlink()
        (ad/"adapter_config.json").write_text(json.dumps({**config,"r":64}))
        rejected(lambda: verify_local_adapter(ad,manifest,base))
        (ad/"adapter_config.json").write_text(json.dumps(config))
        rejected(lambda: verify_local_adapter(
            ad,manifest,{"weight_sha256":"b"*64,"revision":"pinned-revision"}
        ))
        manifest.write_text(json.dumps({**metrics,"status":"failed"}))
        rejected(lambda: verify_local_adapter(ad,manifest,base))
        manifest.write_text(json.dumps(metrics))
        assert verify_local_adapter(ad,manifest,base,check_hash=True)
    print("HF_ADAPTER_ADMISSION=PASS")


if __name__=="__main__":
    run()
