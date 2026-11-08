"""Optional CPU-accelerated Neurol million-profile training (PyTorch).

Uses the exact reset-before recurrence in core.NeuralCore.  The output remains
an integrity-checked JSON checkpoint for the existing, disabled-by-default
Neurol backend; PyTorch's executable pickle serialization is never used.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from .core import Config, NeuralCore, encode, canonical
from .train import load_dataset, unigram_loss


def train_torch(dataset, initialized_checkpoint, output, *, steps=600,
                batch_size=8, sequence_length=48, rate=0.002,
                eval_every=40, patience=5, report=None,
                expected_sha256=None):
    try:
        import torch
        from torch import nn
        import torch.nn.functional as F
    except ImportError as exc:
        raise RuntimeError("Optional PyTorch is required for accelerated training") from exc
    if (type(steps) is not int or not 1 <= steps <= 5000
            or type(batch_size) is not int or not 1 <= batch_size <= 32
            or type(sequence_length) is not int or not 2 <= sequence_length <= 256
            or type(eval_every) is not int or not 1 <= eval_every <= 200
            or type(patience) is not int or not 1 <= patience <= 50
            or not isinstance(rate, (float, int)) or not math.isfinite(rate) or not 0 < rate <= 0.02):
        raise ValueError("invalid bounded training budget")
    if not expected_sha256:
        raise ValueError("pin the SHA-256 of the initialized checkpoint explicitly")
    base, metadata, initial_digest = NeuralCore.load(initialized_checkpoint, expected_sha256=expected_sha256)
    if metadata.get("stage") != "initialized_untrained" or metadata.get("learning_check_passed") is not False:
        raise ValueError("expected initialized, untrained checkpoint")
    if base.config != Config.million(base.config.seed) or base.parameter_count != 1_026_126:
        raise ValueError("wrong model dimensions")
    splits, corpus_digest = load_dataset(dataset)
    torch.set_num_threads(2)
    torch.manual_seed(base.config.seed)
    p = nn.ParameterDict({name: nn.Parameter(torch.tensor(value.copy(), dtype=torch.float32))
                          for name, value in base.weights.items()})

    def forward(ids):
        batch, length = ids.shape
        hidden = torch.zeros((batch, base.config.hidden))
        result = []
        for t in range(length):
            x = p["E"][ids[:, t]]
            r = torch.sigmoid(x @ p["Wr"] + hidden @ p["Ur"] + p["br"])
            z = torch.sigmoid(x @ p["Wz"] + hidden @ p["Uz"] + p["bz"])
            n = torch.tanh(x @ p["Wn"] + (r * hidden) @ p["Un"] + p["bn"])
            hidden = z * hidden + (1-z) * n
            result.append(hidden @ p["V"] + p["b"])
        return torch.stack(result, dim=1)

    def score(texts):
        sum_loss, count = 0., 0
        with torch.no_grad():
            for text in texts:
                ids = encode(text)
                for start in range(0, len(ids)-1, 256):
                    fragment = ids[start:start+257]
                    x = torch.tensor([fragment[:-1]], dtype=torch.long)
                    y = torch.tensor(fragment[1:], dtype=torch.long)
                    logits = forward(x)[0]
                    sum_loss += float(F.cross_entropy(logits, y, reduction="sum"))
                    count += len(fragment)-1
        return sum_loss / count

    train_tokens = np.asarray([t for text in splits["train"] for t in encode(text)], dtype=np.int64)
    if len(train_tokens) <= sequence_length:
        raise ValueError("training corpus shorter than sequence")
    initial_val = score(splits["validation"])
    best_loss, best_step, best_state = initial_val, 0, {k: v.detach().clone() for k,v in p.items()}
    optimizer = torch.optim.Adam(p.parameters(), lr=rate)
    sampler = np.random.default_rng(base.config.seed+1)
    history, stalls = [], 0
    start = time.monotonic()
    for step in range(1, steps+1):
        starts = sampler.integers(0, len(train_tokens)-sequence_length, size=batch_size)
        batch = train_tokens[starts[:,None]+np.arange(sequence_length+1)]
        x = torch.tensor(batch[:,:-1].copy(), dtype=torch.long)
        y = torch.tensor(batch[:,1:].copy(), dtype=torch.long)
        logits = forward(x)
        loss = F.cross_entropy(logits.reshape(-1, 258), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(p.parameters(), 1.)
        optimizer.step()
        if step % eval_every == 0 or step == steps:
            validation = score(splits["validation"])
            history.append({"step": step, "train_loss": float(loss), "validation_loss": validation})
            if validation < best_loss-1e-4:
                best_loss, best_step, stalls = validation, step, 0
                best_state = {k: v.detach().clone() for k,v in p.items()}
            else:
                stalls += 1
                if stalls >= patience:
                    break
    for name, param in p.items():
        base.weights[name] = best_state[name].cpu().numpy().astype(np.float64)
    # The baseline and test set are consumed only after validation selection.
    from .train import evaluate
    test_loss = evaluate(base, splits["test"])
    baseline = unigram_loss(splits["train"], splits["test"])
    passed = bool(best_step > 0 and best_loss < initial_val*0.95 and test_loss < baseline)
    evidence = {
        "stage": "experimental_candidate" if passed else "training_gate_failed",
        "learning_check_passed": passed,
        "parameters": base.parameter_count,
        "dataset_sha256": corpus_digest,
        "initial_checkpoint_sha256": initial_digest,
        "initial_validation_loss": initial_val,
        "best_validation_loss": best_loss,
        "test_loss": test_loss,
        "test_unigram_loss": baseline,
        "steps_run": step,
        "best_step": best_step,
        "training": "opt_in_offline_pytorch_cpu",
        "limitations": "Small synthetic corpus; not proof of fluent conversation, reasoning, generalization, safety or deployment readiness.",
    }
    digest = base.save(output, evidence)
    verified, _, loaded_digest = NeuralCore.load(output, expected_sha256=digest)
    if loaded_digest != digest or any(not np.array_equal(base.weights[k], verified.weights[k])
                                      for k in base.weights):
        raise RuntimeError("checkpoint round-trip verification failed")
    result = dict(evidence, checkpoint_sha256=digest,
                  elapsed_seconds=round(time.monotonic()-start,3),
                  history=history, checkpoint_roundtrip_verified=True,
                  deployed=False, cloud_spend_usd=0)
    if report is not None:
        path = Path(report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical(result)+b"\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True)
    p.add_argument("--initialized", required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--steps", type=int, default=600)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--sequence-length", type=int, default=48)
    p.add_argument("--rate", type=float, default=0.002)
    p.add_argument("--eval-every", type=int, default=40)
    p.add_argument("--patience", type=int, default=5)
    args = p.parse_args()
    result = train_torch(args.dataset, args.initialized, args.output,
                         steps=args.steps, batch_size=args.batch_size,
                         sequence_length=args.sequence_length, rate=args.rate,
                         eval_every=args.eval_every, patience=args.patience,
                         report=args.report, expected_sha256=args.expected_sha256)
    print(json.dumps({k:v for k,v in result.items() if k != "history"}, indent=2))


if __name__ == "__main__":
    main()
