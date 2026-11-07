"""Bounded *real* CPU LoRA fine-tuning of the approved Qwen checkpoint.

This is a small, reversible experimental PEFT adapter, never a new base model.
No private user conversations, tool-output authority, GPU charges or remote code.
Local baseline checkpoint integrity is verified before every run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path


SEED = 1907
SYSTEM = (
    "You are Genesis, an experimental cognitive model. Explain uncertainty "
    "and distinguish observations, claims, inferences and verified actions. "
    "Never claim a source, tool execution or Aurora authorization you lack."
)
RESPONSE_CAP = 144
TIME_LIMIT_SECONDS = 900


def dataset_plan(path: str | Path, public_eval: str | Path | None = None) -> dict:
    """Validate public training material; hold out examples before fitting."""
    source = Path(path)
    raw = source.read_bytes()
    rows = []
    seen = set()
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict) or set(obj) != {"instruction", "response"}:
            raise ValueError("training row must contain only instruction and response")
        instruction, response = obj["instruction"], obj["response"]
        if (not isinstance(instruction, str) or not isinstance(response, str)
                or not instruction.strip() or not response.strip()
                or len(instruction) > 900 or len(response) > 1500):
            raise ValueError("bad or oversized training example at line " + str(number))
        key = instruction.strip().casefold()
        if key in seen:
            raise ValueError("duplicate training instruction")
        seen.add(key)
        rows.append({"instruction": instruction.strip(), "response": response.strip()})
    if not (35 <= len(rows) <= 256):
        raise ValueError("training requires 35–256 validated public examples")

    if public_eval:
        suite = json.loads(Path(public_eval).read_text(encoding="utf-8"))
        prompts = {str(c["prompt"]).strip().casefold() for c in suite["cases"]}
        if seen.intersection(prompts):
            raise ValueError("benchmark leakage: train prompt is an evaluation prompt")

    shuffled = list(rows)
    random.Random(SEED).shuffle(shuffled)
    heldout_n = max(8, len(shuffled) // 5)
    heldout, train = shuffled[:heldout_n], shuffled[heldout_n:]
    assert set(x["instruction"] for x in heldout).isdisjoint(
        set(x["instruction"] for x in train)
    )
    return {
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "source": source.name,
        "train": train, "heldout": heldout,
        "seed": SEED, "train_count": len(train), "heldout_count": len(heldout)
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bounded Genesis CPU LoRA adapter experiment")
    p.add_argument("--data", default="genesis/training/data/genesis_sft_v0.jsonl")
    p.add_argument("--public-eval", default="tools/eval/genesis_hf_probe_v1.json")
    p.add_argument("--model-dir", default=os.environ.get("GENESIS_HF_MODEL_DIR", ""))
    p.add_argument("--out", default="/opt/genesis-cpu-lora/out")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--resume-adapter", default=None)
    p.add_argument("--resume-metrics", default=None)
    p.add_argument("--plan-only", action="store_true")
    args = p.parse_args()
    if not 1 <= args.steps <= 64:
        raise ValueError("steps must be between 1 and 64")
    if bool(args.resume_adapter) != bool(args.resume_metrics):
        raise ValueError("resuming requires both an adapter and its provenance")

    plan = dataset_plan(args.data, args.public_eval)
    summary = {"dataset_sha256": plan["dataset_sha256"],
               "train_count": plan["train_count"],
               "heldout_count": plan["heldout_count"],
               "seed": SEED, "steps": args.steps,
               "training_target": "Qwen2.5-0.5B-Instruct LoRA q_proj+v_proj"}
    if args.plan_only:
        print(json.dumps({"mode": "plan_only", **summary}, indent=2))
        return
    if not args.model_dir:
        raise ValueError("explicit --model-dir required for weight updates")

    from genesis.hf_models import verify_local_model, sha256_file
    from genesis.hf_backend import normalize_disabled_qwen_sliding_window
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoConfig, AutoTokenizer, AutoModelForCausalLM

    start = time.monotonic()
    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    random.seed(SEED)

    root = Path(args.out)
    if root.exists():
        raise ValueError("never overwrite a previous training run")
    root.mkdir(parents=True)
    base_manifest = verify_local_model(args.model_dir, verify_hashes=True)
    print("BASE_WEIGHTS_SHA256_VERIFIED", base_manifest["weight_sha256"], flush=True)
    summary.update({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_repo_id": base_manifest["repo_id"],
        "base_revision": base_manifest["revision"],
        "base_weight_sha256": base_manifest["weight_sha256"],
        "training_mode": "cpu-fp32-lora-r4", "not_public_release": True,
        "torch_version": torch.__version__,
    })

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, local_files_only=True, trust_remote_code=False
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    config = AutoConfig.from_pretrained(
        args.model_dir, local_files_only=True, trust_remote_code=False
    )
    config = normalize_disabled_qwen_sliding_window(config)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir, config=config, local_files_only=True,
        trust_remote_code=False, use_safetensors=True,
        torch_dtype=torch.float32, attn_implementation="eager"
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )
    if args.resume_adapter:
        parent_metrics = json.loads(Path(args.resume_metrics).read_text(encoding="utf-8"))
        parent_weight = Path(args.resume_adapter) / "adapter_model.safetensors"
        if (parent_metrics.get("base_weight_sha256") != base_manifest["weight_sha256"]
                or sha256_file(parent_weight) != parent_metrics.get("adapter_sha256")
                or parent_metrics.get("promote") is not False):
            raise RuntimeError("parent LoRA provenance or integrity not verified")
        model = PeftModel.from_pretrained(
            model, args.resume_adapter, is_trainable=True
        )
        summary["parent_adapter_sha256"] = parent_metrics["adapter_sha256"]
        summary["continuation"] = True
    else:
        model = get_peft_model(
            model, LoraConfig(
                r=4, lora_alpha=8, lora_dropout=0.0, bias="none",
                target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM",
            )
        )
        summary["continuation"] = False
    trainable = [p for p in model.parameters() if p.requires_grad]
    summary["trainable_parameters"] = sum(p.numel() for p in trainable)
    print("LORA_TRAINABLE_PARAMS", summary["trainable_parameters"], flush=True)
    if not trainable:
        raise RuntimeError("no trainable LoRA weights")
    optimizer = torch.optim.AdamW(trainable, lr=1e-4, weight_decay=0.0)

    def encode(row):
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM},
             {"role": "user", "content": row["instruction"]}],
            tokenize=False, add_generation_prompt=True
        )
        full = prompt + row["response"] + tokenizer.eos_token
        pref = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        tokens = tokenizer(full, add_special_tokens=False)["input_ids"]
        tokens = tokens[:RESPONSE_CAP]
        labels = [-100] * len(pref) + tokens[len(pref):]
        if len(tokens) != len(labels) or all(x == -100 for x in labels):
            return None
        return {"input_ids": torch.tensor([tokens], dtype=torch.long),
                "attention_mask": torch.ones((1, len(tokens)), dtype=torch.long),
                "labels": torch.tensor([labels], dtype=torch.long)}

    training = [x for row in plan["train"] if (x := encode(row)) is not None]
    heldout = [x for row in plan["heldout"] if (x := encode(row)) is not None]
    if len(training) < 25 or len(heldout) < 5:
        raise RuntimeError("training or heldout examples truncated by token cap")
    summary.update({"tokenized_train": len(training),
                    "tokenized_heldout": len(heldout)})
    print("DATA_PREPARED", len(training), len(heldout), flush=True)

    def heldout_loss():
        model.eval()
        total = 0.0
        with torch.inference_mode():
            for ex in heldout[:5]:
                total += float(model(**ex).loss.detach().item())
        return round(total / min(5, len(heldout)), 6)

    summary["initial_heldout_loss"] = heldout_loss()
    print("INITIAL_HELDOUT_LOSS", summary["initial_heldout_loss"], flush=True)
    progress = []
    for step in range(args.steps):
        if time.monotonic()-start > TIME_LIMIT_SECONDS:
            summary["status"] = "time_limit_reached"
            break
        model.train()
        batch = training[step % len(training)]
        optimizer.zero_grad(set_to_none=True)
        loss = model(**batch).loss
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite training loss; reject adapter")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
        optimizer.step()
        row = {"step": step+1,
               "training_loss": round(float(loss.detach().item()), 6),
               "elapsed_seconds": round(time.monotonic()-start, 2)}
        progress.append(row)
        print("TRAIN_STEP", json.dumps(row), flush=True)
    if not progress:
        raise RuntimeError("no completed training steps")
    summary["completed_steps"] = len(progress)
    summary["training"] = progress
    summary["final_heldout_loss"] = heldout_loss()
    summary["elapsed_seconds"] = round(time.monotonic()-start, 2)
    summary["status"] = summary.get("status", "completed_experiment")
    if summary["final_heldout_loss"] > summary["initial_heldout_loss"]:
        summary["promote"] = False
        summary["validation_warning"] = "heldout loss rose; do not promote"
    else:
        summary["promote"] = False
        summary["validation_warning"] = (
            "heldout loss is a tiny proxy; independent benchmarks and safety "
            "review required before promotion"
        )

    # Adapter-only file, never overwrite or modify base checkpoint.
    adapter_path = root / "adapter"
    model.save_pretrained(str(adapter_path), safe_serialization=True)
    tokenizer.save_pretrained(str(adapter_path))
    weight = adapter_path / "adapter_model.safetensors"
    if not weight.exists():
        raise RuntimeError("PEFT did not save Safetensors adapter")
    summary["adapter_sha256"] = sha256_file(weight)
    summary["adapter_bytes"] = weight.stat().st_size
    summary["limitations"] = (
        "Small public instruction set and five-example heldout loss; "
        "eight-ish CPU steps cannot prove general reasoning or safety improvement."
    )
    (root / "metrics.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )
    print("GENESIS_REAL_LORA_TRAINING_SAVED", json.dumps({
        "steps": len(progress),
        "initial_heldout_loss": summary["initial_heldout_loss"],
        "final_heldout_loss": summary["final_heldout_loss"],
        "adapter_sha256": summary["adapter_sha256"],
        "adapter_bytes": summary["adapter_bytes"],
        "promotion": "blocked",
    }), flush=True)


if __name__ == "__main__":
    main()
