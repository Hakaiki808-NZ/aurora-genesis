"""Explicit, bounded offline training. Never ingests chat history automatically."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import unicodedata

import numpy as np

from .core import Adam, Config, NeuralCore, VOCAB, canonical, encode

MAX_DATA_BYTES = 2 * 1024 * 1024


def load_dataset(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_DATA_BYTES+1)
    if len(raw) > MAX_DATA_BYTES:
        raise ValueError("dataset exceeds 2 MiB research limit")
    data = json.loads(raw)
    if data.get("format") != "genesis-neurol-corpus-v1":
        raise ValueError("invalid corpus format")
    documents = data.get("documents")
    if not isinstance(documents, list) or not 3 <= len(documents) <= 2000:
        raise ValueError("invalid document count")
    splits = {name: [] for name in ("train", "validation", "test")}
    seen, groups = set(), {}
    for row in documents:
        if not isinstance(row, dict) or row.get("split") not in splits:
            raise ValueError("explicit split required")
        if row.get("training_allowed") is not True or row.get("reviewed") is not True:
            raise ValueError("review and training permission required for every document")
        if any(not isinstance(row.get(key), str) or not row[key].strip()
               for key in ("source", "license", "group", "text")):
            raise ValueError("source, license, group and text required")
        text = row["text"]
        if not 2 <= len(text.encode("utf-8")) <= 4096:
            raise ValueError("document length must be 2..4096 bytes")
        normal = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        if normal in seen:
            raise ValueError("duplicate text across corpus")
        seen.add(normal)
        group, split = row["group"], row["split"]
        if group in groups and groups[group] != split:
            raise ValueError("document group crosses splits")
        groups[group] = split
        splits[split].append(text)
    if any(not docs for docs in splits.values()):
        raise ValueError("train, validation and test must all be non-empty")
    return splits, hashlib.sha256(raw).hexdigest()


def evaluate(model, texts):
    loss_sum, count = 0.0, 0
    for text in texts:
        ids = np.array(encode(text), dtype=np.int64)
        for start in range(0, len(ids)-1, 256):
            segment = ids[start:start+257]
            loss, _ = model.loss_and_gradients(segment[:-1][None], segment[1:][None], backward=False)
            loss_sum += loss*(len(segment)-1)
            count += len(segment)-1
    return loss_sum/count


def unigram_loss(train, test):
    counts = np.ones(VOCAB)
    for text in train:
        np.add.at(counts, encode(text)[1:], 1)
    logp = np.log(counts/counts.sum())
    tokens = [token for text in test for token in encode(text)[1:]]
    return float(-logp[tokens].mean())


def train(dataset, output, *, steps=600, batch_size=8, length=48, rate=0.003,
          config=Config(), report_path=None):
    for value, lower, upper in ((steps, 1, 5000), (batch_size, 1, 32), (length, 2, 256)):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError("invalid training budget")
    splits, dataset_sha = load_dataset(dataset)
    tokens = np.array([token for text in splits["train"] for token in encode(text)], dtype=np.int64)
    if len(tokens) <= length:
        raise ValueError("training corpus too short for sequence length")
    start = time.monotonic()
    model = NeuralCore(config)
    optimizer = Adam(model, rate)
    rng = np.random.default_rng(config.seed+1)
    initial = evaluate(model, splits["validation"])
    best_loss, best_step = initial, 0
    best = {k: w.copy() for k, w in model.weights.items()}
    history = []
    for step in range(1, steps+1):
        starts = rng.integers(0, len(tokens)-length, size=batch_size)
        batch = tokens[starts[:, None]+np.arange(length+1)]
        loss, grads = model.loss_and_gradients(batch[:, :-1], batch[:, 1:])
        optimizer.update(grads)
        if step % max(1, steps//10) == 0 or step == steps:
            validation = evaluate(model, splits["validation"])
            history.append({"step": step, "batch_loss": loss, "validation_loss": validation})
            if validation < best_loss:
                best_loss, best_step = validation, step
                best = {k: w.copy() for k, w in model.weights.items()}
    model.weights = best
    # Test is touched only after checkpoint selection on validation.
    test_loss = evaluate(model, splits["test"])
    baseline = unigram_loss(splits["train"], splits["test"])
    learning_passed = bool(best_loss < initial*0.95 and test_loss < baseline)
    report = {
        "format": "genesis-neurol-evaluation-v1", "stage": "experimental_candidate",
        "architecture": "byte_embedding_reset_before_gru_softmax", "pretrained_weights": False,
        "parameters": model.parameter_count, "dataset_sha256": dataset_sha,
        "documents": {k: len(v) for k, v in splits.items()},
        "steps": steps, "best_validation_step": best_step, "seed": config.seed,
        "batch_size": batch_size, "sequence_length": length, "learning_rate": rate,
        "initial_validation_loss": initial, "best_validation_loss": best_loss,
        "test_loss": test_loss, "test_unigram_loss": baseline,
        "learning_check_passed": learning_passed, "history": history,
        "elapsed_seconds": round(time.monotonic()-start, 3), "runtime": "local_numpy_cpu",
        "numpy_version": np.__version__, "cloud_spend_usd": 0,
        "limitations": "Small synthetic corpus; no evidence of general reasoning, instruction following, semantic safety, or production readiness. Split separation detects exact normalized duplicates and shared groups, not semantic leakage.",
    }
    digest = model.save(output, report)
    restored, _, restored_digest = NeuralCore.load(output, expected_sha256=digest)
    if restored_digest != digest or any(not np.array_equal(w, restored.weights[k]) for k, w in model.weights.items()):
        raise RuntimeError("checkpoint round-trip failed")
    report["checkpoint_sha256"] = digest
    report["checkpoint_roundtrip_verified"] = True
    report["samples"] = {p: restored.generate(p, max_new_bytes=96) for p in ("Genesis ", "Aurora ", "Kyro ")}
    if report_path:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical(report)+b"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    training = sub.add_parser("train")
    training.add_argument("--dataset", required=True)
    training.add_argument("--output", required=True)
    training.add_argument("--report", required=True)
    training.add_argument("--steps", type=int, default=600)
    training.add_argument("--batch-size", type=int, default=8)
    training.add_argument("--length", type=int, default=48)
    training.add_argument("--rate", type=float, default=0.003)
    training.add_argument("--seed", type=int, default=1907)
    training.add_argument("--profile", choices=("prototype", "million"), default="prototype")
    initialize = sub.add_parser("initialize", help="create an untrained, digest-pinned research checkpoint")
    initialize.add_argument("--output", required=True)
    initialize.add_argument("--seed", type=int, default=1907)
    initialize.add_argument("--profile", choices=("prototype", "million"), default="million")
    generation = sub.add_parser("generate")
    generation.add_argument("--checkpoint", required=True)
    generation.add_argument("--sha256", required=True)
    generation.add_argument("--prompt", required=True)
    generation.add_argument("--max-new-bytes", type=int, default=128)
    args = parser.parse_args()
    if args.command == "train":
        config = Config.million(args.seed) if args.profile == "million" else Config(seed=args.seed)
        report = train(args.dataset, args.output, steps=args.steps,
                       batch_size=args.batch_size, length=args.length,
                       rate=args.rate, config=config, report_path=args.report)
        print(json.dumps(report, indent=2))
    elif args.command == "initialize":
        config = Config.million(args.seed) if args.profile == "million" else Config(seed=args.seed)
        model = NeuralCore(config)
        metadata = {"stage": "initialized_untrained", "learning_check_passed": False,
                    "parameters": model.parameter_count, "pretrained_weights": False,
                    "profile": args.profile, "seed": config.seed}
        digest = model.save(args.output, metadata)
        restored, restored_metadata, restored_digest = NeuralCore.load(args.output, expected_sha256=digest)
        if restored_digest != digest or restored.parameter_count != model.parameter_count or restored_metadata != metadata:
            raise RuntimeError("initialized checkpoint round-trip failed")
        print(json.dumps({"stage": metadata["stage"], "parameters": model.parameter_count,
                          "checkpoint_sha256": digest, "roundtrip_verified": True,
                          "enabled_for_inference": False}, indent=2))
    else:
        model, _, _ = NeuralCore.load(args.checkpoint, expected_sha256=args.sha256)
        print(model.generate(args.prompt, max_new_bytes=args.max_new_bytes))


if __name__ == "__main__":
    main()
