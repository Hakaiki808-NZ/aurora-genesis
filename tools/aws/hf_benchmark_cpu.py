#!/usr/bin/env python3
"""Six original real-weight CPU inference probes, not a formal benchmark."""
from __future__ import annotations
import json
import os
import platform
import resource
import time
from datetime import datetime, timezone
from pathlib import Path
import torch
import transformers
from transformers import AutoTokenizer
from genesis.hf_backend import HuggingFaceBackend
from genesis.hf_models import verify_local_model

MODEL_DIR=Path(os.environ["GENESIS_HF_MODEL_DIR"])
RESULTS=Path(os.environ.get("GENESIS_HF_RESULTS","/opt/genesis-hf/results.json"))
TASKS=[
 ("arithmetic","Calculate 17 multiplied by 19. Give only the answer.","323"),
 ("word_problem","Four pens cost $6. What do ten pens cost at the same price per pen? Answer briefly.","$15"),
 ("deduction","All glims are snarps. No snarps are green. Can a glim be green? Answer yes or no with one sentence.","No"),
 ("geography","What is the capital city of New Zealand, and which island is it on? Answer in one sentence.","Wellington, North Island"),
 ("uncertainty","Without searching online, what was the exact temperature in Wellington at 7:13am on 14 July 2026? If you cannot know, say so.","Abstention expected"),
 ("formatting","For this answer use precisely three words: sky, river, stone.","sky river stone"),
]
def main():
    torch.set_num_threads(2)
    manifest=verify_local_model(MODEL_DIR,verify_hashes=True)
    tokenizer=AutoTokenizer.from_pretrained(str(MODEL_DIR),local_files_only=True,trust_remote_code=False)
    backend=HuggingFaceBackend(model_dir=str(MODEL_DIR),enabled=True,
                               max_calls=len(TASKS),max_output_tokens=56)
    result={"generated_utc":datetime.now(timezone.utc).isoformat(),
            "model":manifest["repo_id"],"revision":manifest["revision"],
            "weight_sha256":manifest["weight_sha256"],
            "hardware":{"device":"cpu","torch_threads":torch.get_num_threads(),
                        "platform":platform.platform()},
            "software":{"torch":torch.__version__,"transformers":transformers.__version__},
            "benchmark_label":"six original operator smoke prompts; NOT standardized or held-out",
            "cases":[]}
    RESULTS.parent.mkdir(parents=True,exist_ok=True)
    for key,prompt,reference in TASKS:
        before=time.perf_counter()
        answer=backend.generate(prompt)
        seconds=round(time.perf_counter()-before,3)
        tokens=len(tokenizer.encode(answer,add_special_tokens=False)) if answer else 0
        record={"id":key,"prompt":prompt,"reference":reference,"output":answer,
                "seconds":seconds,"output_tokens_estimate":tokens,
                "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "error_code":backend.last_error_code,
                "approx_output_tokens_per_second":round(tokens/max(seconds,0.001),2)}
        result["cases"].append(record)
        RESULTS.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
        print("CASE "+key+" "+json.dumps(record,ensure_ascii=False),flush=True)
    print("GENESIS_HF_CPU_BENCHMARK_FINISHED",flush=True)
if __name__=="__main__":main()
