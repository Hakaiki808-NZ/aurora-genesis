"""Private, consent-gated, bounded Genesis shadow evaluator.

This module performs INFERENCE ONLY. It does not update model weights or approve
assistant answers as truth. Both the base model and the existing LoRA adapter
answer the same prompt, and the results are saved for independent review.
Raw prompts/answers must remain in restricted private storage, never CI logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path


def load_cases(path: str | Path) -> list[dict]:
    source = Path(path)
    raw = source.read_bytes()
    if len(raw) > 100_000:
        raise ValueError("Shadow batch exceeds private input limit")
    cases: list[dict] = []
    ids: set[str] = set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict) or obj.get("consent_shadow_eval") is not True:
            raise ValueError("Explicit shadow-evaluation consent required")
        case_id = obj.get("case_id")
        prompt = obj.get("prompt")
        reference = obj.get("assistant_reference", "")
        if not isinstance(case_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{4,80}", case_id):
            raise ValueError("Invalid case ID")
        if case_id in ids:
            raise ValueError("Duplicate shadow case ID")
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 2500:
            raise ValueError("Invalid prompt length")
        if not isinstance(reference, str) or len(reference) > 4000:
            raise ValueError("Invalid assistant reference")
        ids.add(case_id)
        cases.append({
            "case_id": case_id,
            "prompt": prompt.strip(),
            "assistant_reference": reference.strip(),
            "origin": str(obj.get("origin", "unknown"))[:80],
            "consent_shadow_eval": True,
            "consent_training": obj.get("consent_training") is True,
        })
    if not 1 <= len(cases) <= 8:
        raise ValueError("Require between 1 and 8 explicitly consented questions")
    return cases


def infer(model, tokenizer, prompt: str, max_new_tokens: int) -> tuple[str, float]:
    import torch
    messages = [
        {"role": "system", "content": (
            "You are the experimental Genesis cognition model. Be helpful, "
            "state uncertainty, do not claim access to AWS or other tools. "
            "Do not grant yourself Aurora execution authority."
        )},
        {"role": "user", "content": prompt},
    ]
    encoded = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
    )
    start = time.monotonic()
    with torch.inference_mode():
        tokens = model.generate(
            encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    answer = tokenizer.decode(tokens[0, encoded.shape[-1]:], skip_special_tokens=True)
    return answer.strip()[:4000], round(time.monotonic() - start, 3)


def evaluate(
    cases: list[dict],
    model_dir: str,
    adapter_dir: str,
    max_new_tokens: int = 96,
) -> dict:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not 8 <= max_new_tokens <= 128:
        raise ValueError("Token budget must be between 8 and 128")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir, torch_dtype=torch.float32, local_files_only=True
    )
    model.eval()
    rows: dict[str, dict] = {
        c["case_id"]: {
            "case_id": c["case_id"],
            "origin": c["origin"],
            "prompt": c["prompt"],
            "assistant_reference": c["assistant_reference"],
            "consent_shadow_eval": True,
            "consent_training": c["consent_training"],
            "review": "pending_human_or_independent_eval",
            "training_eligible": False,
        } for c in cases
    }
    for c in cases:
        answer, seconds = infer(model, tokenizer, c["prompt"], max_new_tokens)
        rows[c["case_id"]]["base_answer"] = answer
        rows[c["case_id"]]["base_seconds"] = seconds
    model = PeftModel.from_pretrained(model, adapter_dir, is_trainable=False)
    model.eval()
    for c in cases:
        answer, seconds = infer(model, tokenizer, c["prompt"], max_new_tokens)
        rows[c["case_id"]]["adapter_answer"] = answer
        rows[c["case_id"]]["adapter_seconds"] = seconds
    return {
        "schema": "genesis-shadow-eval-v1",
        "status": "candidate_only_unreviewed",
        "model_family": "Qwen2.5-0.5B-Instruct",
        "adapter_source": "experimental_genesis_lora_r2",
        "has_real_model_outputs": True,
        "model_weights_updated": False,
        "auto_promotion": False,
        "cases": [rows[c["case_id"]] for c in cases],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--adapter-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    args = parser.parse_args()
    digest = hashlib.sha256(Path(args.data).read_bytes()).hexdigest()
    if digest != args.expected_sha256:
        raise RuntimeError("Dataset integrity check failed")
    cases = load_cases(args.data)
    result = evaluate(cases, args.model_dir, args.adapter_dir, args.max_new_tokens)
    result["dataset_sha256"] = digest
    result["case_count"] = len(cases)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("GENESIS_SHADOW_EVAL_COMPLETED candidate_only case_count=" + str(len(cases)))


if __name__ == "__main__":
    main()
