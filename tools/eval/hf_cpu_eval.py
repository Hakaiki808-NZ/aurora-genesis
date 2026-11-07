#!/usr/bin/env python3
"""Run a frozen 12-case comparison on the *real* Hugging Face weights.

Raw backend and full Genesis model share one loaded CPU backend.
Strict scorer marks ambiguous answers for review, never self-judges semantics.
No network, new weights, training, side-effect tools, or user data.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from genesis import Genesis
from genesis.hf_backend import HuggingFaceBackend
from genesis.hf_models import verify_local_model
from tools.eval.score import grade


def summarize(entries: list[dict]) -> dict:
    outcomes=Counter(row["grading"]["status"] for row in entries)
    return {"total":len(entries),"strict_pass":outcomes["pass"],
            "strict_fail":outcomes["fail"],"needs_review":outcomes["review"]}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--model-dir",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--cases",default="tools/eval/genesis_hf_probe_v1.json")
    args=parser.parse_args()

    path=Path(args.model_dir)
    manifest=verify_local_model(path,verify_hashes=True)
    suite=json.loads(Path(args.cases).read_text(encoding="utf-8"))
    cases=suite["cases"]
    if len(cases)>12 or len(cases)<1:
        raise RuntimeError("unsupported bounded evaluation size")
    if len({case["id"] for case in cases})!=len(cases):
        raise RuntimeError("duplicate eval task")
    backend=HuggingFaceBackend(
        model_dir=str(path),enabled=True,
        max_calls=25,max_output_tokens=80
    )
    output={"generated_utc":datetime.now(timezone.utc).isoformat(),
            "suite_name":suite["name"],"suite_version":suite["version"],
            "limitations":suite["purpose"],
            "checkpoint":{"repo_id":manifest["repo_id"],"revision":manifest["revision"],
                          "weight_sha256":manifest["weight_sha256"]},
            "runtime":{"python":platform.python_version(),"platform":platform.platform(),
                       "device":"cpu"},
            "raw":[],"genesis":[]}
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)

    def record(case,answer,mode,seconds,action=None):
        entry={"id":case["id"],"kind":case["kind"],"prompt":case["prompt"],
               "expected":case.get("expected") or case.get("terms"),
               "answer":answer,"seconds":round(seconds,3),"grading":grade(case,answer),
               "chosen_action":action,"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        output[mode].append(entry)
        out.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print("RESULT "+mode+" "+json.dumps(entry,ensure_ascii=False),flush=True)

    # First pass: do not smuggle deterministic Genesis improvements into the raw score.
    for case in cases:
        start=time.perf_counter()
        answer=backend.generate(case["prompt"])
        record(case,answer,"raw",time.perf_counter()-start)

    # Second pass: same pinned weights, but Genesis's real policy/cognition layer.
    with tempfile.TemporaryDirectory(prefix="genesis-hf-eval-") as temp:
        with Genesis(state_path=Path(temp)/"state.sqlite3",
                     workspace=Path(temp)/"workspace",backend=backend) as model:
            for case in cases:
                start=time.perf_counter()
                response=model.respond_with_trace(case["prompt"])
                record(case,response["answer"],"genesis",time.perf_counter()-start,
                       response["trace"].get("chosen_action"))

    output["summary"]={"raw":summarize(output["raw"]),
                       "genesis":summarize(output["genesis"]),
                       "calls_used":backend.call_count,
                       "note":"strict pass is a lower bound; review items are NOT counted as wins"}
    out.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("GENESIS_REASONING_EVAL_COMPLETE "+json.dumps(output["summary"]),flush=True)


if __name__=="__main__":
    main()
