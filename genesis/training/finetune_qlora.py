#!/usr/bin/env python3
"""Genesis bounded experimental QLoRA fine-tune on a licensed open-weight base model.

Run only on an approved CUDA GPU. This creates a PEFT adapter, not a new
general-purpose foundation model. No tool permissions are embedded in weights.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
    set_seed,
)

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
BASE_REVISION = "c89bee90d9f811437d9735454613c35b4a3c4dc8"
BASE_LICENSE = "Apache-2.0"
SEED = 1907
MAX_LENGTH = 384
SYSTEM = (
    "You are Genesis, an experimental reasoning component. Distinguish verified "
    "observations from interpretation, explain uncertainty, and never claim to "
    "have operational authorization unless a trusted external tool confirms it."
)


class GenesisDataset(Dataset):
    def __init__(self, rows, tokenizer):
        self.records = []
        for row in rows:
            prompt_messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": row["instruction"]},
            ]
            prompt = tokenizer.apply_chat_template(
                prompt_messages, tokenize=False, add_generation_prompt=True
            )
            full = prompt + row["response"].strip() + tokenizer.eos_token
            prompt_tokens = tokenizer(prompt, add_special_tokens=False)["input_ids"]
            full_tokens = tokenizer(full, add_special_tokens=False)["input_ids"]
            if len(prompt_tokens) >= MAX_LENGTH - 4:
                continue
            full_tokens = full_tokens[:MAX_LENGTH]
            labels = [-100] * len(prompt_tokens) + full_tokens[len(prompt_tokens):]
            if all(label == -100 for label in labels):
                continue
            self.records.append({
                "input_ids": full_tokens,
                "attention_mask": [1] * len(full_tokens),
                "labels": labels,
            })
        if not self.records:
            raise RuntimeError("No nonempty dataset examples after tokenization")

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        return self.records[idx]


class PadBatch:
    def __init__(self, pad_id):
        self.pad_id = pad_id

    def __call__(self, rows):
        n = max(len(x["input_ids"]) for x in rows)
        return {
            "input_ids": torch.tensor([
                r["input_ids"] + [self.pad_id] * (n - len(r["input_ids"]))
                for r in rows
            ], dtype=torch.long),
            "attention_mask": torch.tensor([
                r["attention_mask"] + [0] * (n - len(r["attention_mask"]))
                for r in rows
            ], dtype=torch.long),
            "labels": torch.tensor([
                r["labels"] + [-100] * (n - len(r["labels"]))
                for r in rows
            ], dtype=torch.long),
        }


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU unavailable: refusing unexpectedly slow CPU training")
    max_steps = min(80, max(1, int(os.environ.get("GENESIS_MAX_STEPS", "60"))))
    data_file = Path(os.environ.get(
        "GENESIS_DATASET", "genesis/training/data/genesis_sft_v0.jsonl"
    ))
    output_dir = Path(os.environ.get("GENESIS_OUTPUT", "/tmp/genesis-finetune"))
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_data = data_file.read_bytes()
    rows = [json.loads(line) for line in raw_data.decode("utf-8").splitlines()
            if line.strip()]
    for row in rows:
        if (not isinstance(row.get("instruction"), str)
                or not isinstance(row.get("response"), str)
                or not row["instruction"].strip()
                or not row["response"].strip()):
            raise ValueError("Invalid data row")
    if len(rows) < 20:
        raise ValueError("Insufficient examples for a held-out evaluation")
    random.Random(SEED).shuffle(rows)
    validation_count = max(5, len(rows) // 5)
    validation_rows, training_rows = rows[:validation_count], rows[validation_count:]

    set_seed(SEED)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, revision=BASE_REVISION, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        revision=BASE_REVISION,
        quantization_config=quant,
        torch_dtype=torch.float16,
        device_map={"": 0},
        trust_remote_code=False,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(model, LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    ))
    train_dataset = GenesisDataset(training_rows, tokenizer)
    eval_dataset = GenesisDataset(validation_rows, tokenizer)

    args = TrainingArguments(
        output_dir=str(output_dir / "trainer"),
        max_steps=max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        per_device_eval_batch_size=1,
        learning_rate=1e-4,
        warmup_steps=min(4, max_steps // 4),
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        fp16=True,
        gradient_checkpointing=True,
        eval_strategy="steps",
        eval_steps=min(20, max_steps),
        save_strategy="steps",
        save_steps=min(20, max_steps),
        save_total_limit=1,
        logging_steps=5,
        report_to="none",
        dataloader_num_workers=0,
        remove_unused_columns=False,
        seed=SEED,
        data_seed=SEED,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=PadBatch(tokenizer.pad_token_id),
    )
    initial_metrics = trainer.evaluate(metric_key_prefix="initial")
    train_metrics = trainer.train().metrics
    final_metrics = trainer.evaluate(metric_key_prefix="final")
    adapter_dir = output_dir / "adapter"
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "experimental",
        "base_model": BASE_MODEL,
        "base_revision": BASE_REVISION,
        "base_license": BASE_LICENSE,
        "dataset_sha256": hashlib.sha256(raw_data).hexdigest(),
        "training_examples": len(train_dataset),
        "heldout_examples": len(eval_dataset),
        "max_steps": max_steps,
        "seed": SEED,
        "lora_rank": 8,
        "quantization": "NF4 / fp16",
        "initial": initial_metrics,
        "training": train_metrics,
        "final": final_metrics,
        "limitations": (
            "Small synthetic instruction dataset; performance and safety not "
            "established beyond recorded held-out evaluation."
        ),
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "completed",
        "initial_eval_loss": initial_metrics.get("initial_loss"),
        "final_eval_loss": final_metrics.get("final_loss"),
        "adapter_dir": str(adapter_dir),
    }))


if __name__ == "__main__":
    main()
