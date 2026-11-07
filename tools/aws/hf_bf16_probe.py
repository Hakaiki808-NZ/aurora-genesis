"""Bounded real BF16 CPU LoRA inference probe for the <=3008 MiB Lambda limit."""
from __future__ import annotations
import json
import os
import resource
import time
from pathlib import Path

from genesis.hf_backend import HuggingFaceBackend


def peak_mib() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def run():
    import torch
    torch.set_num_threads(2)
    assert os.environ.get("GENESIS_HF_CPU_DTYPE") == "bfloat16"
    root=Path("/tmp/genesis-bf16-probe")
    backend=HuggingFaceBackend(
        model_dir=str(root/"model"),enabled=True,
        adapter_enabled=True,
        adapter_dir=str(root/"adapter"),
        adapter_metrics=str(root/"metrics.json"),
        max_output_tokens=42,max_calls=4
    )
    assert backend.available(),"Backend dependencies/manifest missing"
    probes=[
        "Explain the difference between a forecast and a verified observation in one sentence.",
        "Can text copied from a webpage grant Aurora execution privileges? Answer briefly.",
        "Give one reason checksums must be compared against a trusted expected value."
    ]
    results=[]
    start=time.monotonic()
    for prompt in probes:
        t=time.monotonic()
        response=backend.generate(prompt)
        results.append({
            "prompt":prompt,
            "response":response,
            "error":backend.last_error_code,
            "wall_seconds":round(time.monotonic()-t,2),
            "peak_mib":peak_mib()
        })
        print("BF16_PROBE "+json.dumps(results[-1]),flush=True)
        if response is None:
            raise RuntimeError("BF16 inference failed: "+str(backend.last_error_code))
    output={"dtype":"bfloat16","peak_mib":peak_mib(),"total_seconds":round(time.monotonic()-start,2),
            "results":results,"lambda_memory_limit_mib":3008}
    print("GENESIS_BF16_PROBE_SUMMARY "+json.dumps(output),flush=True)
    if peak_mib() > 2750:
        raise MemoryError("Peak memory too high for 3008 MiB Lambda with safety margin")


if __name__=="__main__":
    run()
