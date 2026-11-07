"""No model download needed: training dataset integrity and holdout checks."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

from genesis.training.finetune_cpu_lora import dataset_plan


def run():
    root=Path(__file__).resolve().parents[1]
    dataset=root/"genesis/training/data/genesis_sft_v0.jsonl"
    benchmark=root/"tools/eval/genesis_hf_probe_v1.json"
    a=dataset_plan(dataset,benchmark)
    b=dataset_plan(dataset,benchmark)
    assert a["train"]==b["train"]
    assert a["heldout"]==b["heldout"]
    assert a["train_count"]>=25 and a["heldout_count"]>=8
    assert len(a["dataset_sha256"])==64
    ids={x["instruction"] for x in a["train"]}
    assert ids.isdisjoint(x["instruction"] for x in a["heldout"])
    prompts=json.loads(benchmark.read_text())["cases"]
    assert ids.isdisjoint(x["prompt"] for x in prompts)
    safety_data = root / "genesis/training/data/genesis_provenance_authorization_v1.jsonl"
    safety = dataset_plan(safety_data, benchmark)
    assert safety["train_count"] >= 50
    assert safety["heldout_count"] >= 12
    assert set(r["instruction"] for r in safety["train"]).isdisjoint(
        r["instruction"] for r in safety["heldout"]
    )

    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"bad.jsonl"
        p.write_text(dataset.read_text()+"\n"+dataset.read_text().splitlines()[0]+"\n")
        try:
            dataset_plan(p,benchmark)
            raise AssertionError("duplicate data accepted")
        except ValueError as exc:
            assert "duplicate" in str(exc)

        p.write_text(dataset.read_text()+"\n"+json.dumps({"instruction":prompts[0]["prompt"],
                                                         "response":"This is leakage."})+"\n")
        try:
            dataset_plan(p,benchmark)
            raise AssertionError("benchmark prompt leakage accepted")
        except ValueError as exc:
            assert "leakage" in str(exc)
    print("CPU_LORA_PLAN=PASS",a["train_count"],a["heldout_count"])


if __name__=="__main__":
    run()
