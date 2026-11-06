"""Genesis v0 experimental character-level neural language-model trainer.

A short, bounded AWS Lambda CPU job. No third-party packages or model downloads.
This demonstrates training and checkpointing, NOT a production language model.
"""
import gzip
import hashlib
import json
import math
import os
import random
import time

TRAIN_LINES = [
    "genesis observes evidence and revises beliefs when evidence changes.",
    "genesis distinguishes observation from interpretation and uncertainty.",
    "genesis can ask for clarification when a request is ambiguous.",
    "genesis builds a working understanding from verifiable information.",
    "genesis plans actions while aurora controls execution authority.",
    "genesis reports uncertainty instead of inventing observations.",
    "genesis stores knowledge with source provenance and confidence.",
    "genesis tests predictions against outcomes and learns from errors.",
]
VALIDATION_LINES = [
    "genesis checks observations before changing its beliefs.",
    "genesis learns from evidence and describes uncertainty.",
]
SEED = 1907
EMBED_DIM = 8
HIDDEN_DIM = 20
EPOCHS = 4
MAX_TRAIN_CHARS = 3500
LEARNING_RATE = 0.05


def build_corpus():
    train = ("\n".join(TRAIN_LINES) + "\n") * 5
    valid = "\n".join(VALIDATION_LINES) + "\n"
    train = train[:MAX_TRAIN_CHARS]
    vocab = sorted(set(train + valid))
    stoi = {ch: i for i, ch in enumerate(vocab)}
    return train, valid, vocab, stoi


def initialize(n, rng):
    rand = lambda: rng.uniform(-0.08, 0.08)
    return {
        "E": [[rand() for _ in range(EMBED_DIM)] for _ in range(n)],
        "W1": [[rand() for _ in range(HIDDEN_DIM)] for _ in range(EMBED_DIM * 2)],
        "b1": [0.0] * HIDDEN_DIM,
        "W2": [[rand() for _ in range(n)] for _ in range(HIDDEN_DIM)],
        "b2": [0.0] * n,
    }


def forward(p, a, b):
    x = p["E"][a] + p["E"][b]
    h = [math.tanh(p["b1"][j] + sum(x[i] * p["W1"][i][j]
          for i in range(len(x)))) for j in range(HIDDEN_DIM)]
    logits = [p["b2"][j] + sum(h[k] * p["W2"][k][j]
              for k in range(HIDDEN_DIM)) for j in range(len(p["b2"]))]
    m = max(logits)
    exp = [math.exp(v - m) for v in logits]
    denom = sum(exp)
    return x, h, [v / denom for v in exp]


def loss_on_text(p, text, stoi):
    ids = [stoi[c] for c in text]
    total = 0.0
    for pos in range(2, len(ids)):
        _, _, prob = forward(p, ids[pos-2], ids[pos-1])
        total += -math.log(max(prob[ids[pos]], 1e-12))
    return total / max(1, len(ids) - 2)


def training_step(p, a, b, target, rate):
    x, h, prob = forward(p, a, b)
    loss = -math.log(max(prob[target], 1e-12))
    prob[target] -= 1.0
    dh = [sum(p["W2"][k][j] * prob[j] for j in range(len(prob)))
          * (1.0 - h[k] * h[k]) for k in range(HIDDEN_DIM)]
    dx = [sum(p["W1"][i][k] * dh[k] for k in range(HIDDEN_DIM))
          for i in range(len(x))]
    for k in range(HIDDEN_DIM):
        wk = p["W2"][k]
        for j in range(len(prob)):
            wk[j] -= rate * h[k] * prob[j]
    for j in range(len(prob)):
        p["b2"][j] -= rate * prob[j]
    for i in range(len(x)):
        wi = p["W1"][i]
        for k in range(HIDDEN_DIM):
            wi[k] -= rate * x[i] * dh[k]
    for k in range(HIDDEN_DIM):
        p["b1"][k] -= rate * dh[k]
    for i in range(EMBED_DIM):
        p["E"][a][i] -= rate * dx[i]
        p["E"][b][i] -= rate * dx[i + EMBED_DIM]
    return loss


def train():
    train_text, valid_text, vocab, stoi = build_corpus()
    p = initialize(len(vocab), random.Random(SEED))
    ids = [stoi[c] for c in train_text]
    before = loss_on_text(p, valid_text, stoi)
    histories = []
    for epoch in range(EPOCHS):
        loss = 0.0
        for pos in range(2, len(ids)):
            loss += training_step(p, ids[pos-2], ids[pos-1], ids[pos], LEARNING_RATE)
        histories.append({
            "epoch": epoch + 1,
            "train_cross_entropy": round(loss / (len(ids) - 2), 5),
            "validation_cross_entropy": round(loss_on_text(p, valid_text, stoi), 5),
        })
    count = (len(vocab) * EMBED_DIM + EMBED_DIM * 2 * HIDDEN_DIM +
             HIDDEN_DIM + HIDDEN_DIM * len(vocab) + len(vocab))
    return {
        "format": "genesis-char-mlp-v0",
        "kind": "experimental_neural_language_model",
        "limitations": "Tiny demonstration. Not a foundation model or general-purpose language understanding.",
        "architecture": {
            "context_chars": 2, "embedding_dim": EMBED_DIM,
            "hidden_dim": HIDDEN_DIM, "vocab_size": len(vocab),
            "parameter_count": count,
        },
        "vocabulary": vocab, "weights": p,
        "training": {
            "seed": SEED, "epochs": EPOCHS, "learning_rate": LEARNING_RATE,
            "train_chars": len(train_text),
            "validation_chars": len(valid_text),
            "initial_validation_loss": round(before, 5),
            "history": histories,
            "corpus": "bundled-original-genesis-example-text",
        },
    }


def lambda_handler(event, context):
    event = event or {}
    if event.get("action", "train") != "train":
        return {"ok": False, "reason": "unsupported action"}
    start = time.monotonic()
    model = train()
    raw = json.dumps(model, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=6, mtime=0)
    digest = hashlib.sha256(compressed).hexdigest()
    bucket = os.environ.get("GENESIS_WEIGHTS_BUCKET")
    prefix = os.environ.get("GENESIS_WEIGHTS_PREFIX", "genesis/weights/char-mlp-v0")
    saved = False
    key = f"{prefix}/genesis-char-mlp-v0-{digest[:16]}.json.gz"
    if event.get("save", True):
        if not bucket:
            raise ValueError("GENESIS_WEIGHTS_BUCKET is required for AWS checkpoint saving")
        import boto3
        s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-southeast-2"))
        s3.put_object(
            Bucket=bucket, Key=key, Body=compressed,
            ContentType="application/json", ContentEncoding="gzip",
            ServerSideEncryption="AES256",
            Metadata={"model": "genesis-char-mlp-v0", "sha256": digest},
        )
        saved = True
    return {
        "ok": True, "trained": True, "checkpoint_saved": saved,
        "s3_bucket": bucket if saved else None,
        "s3_key": key if saved else None,
        "sha256": digest,
        "checkpoint_bytes": len(compressed),
        "parameter_count": model["architecture"]["parameter_count"],
        "vocab_size": len(model["vocabulary"]),
        "initial_validation_loss": model["training"]["initial_validation_loss"],
        "final_validation_loss": model["training"]["history"][-1]["validation_cross_entropy"],
        "metrics": model["training"]["history"],
        "elapsed_seconds": round(time.monotonic() - start, 2),
    }


if __name__ == "__main__":
    print(json.dumps(lambda_handler({"save": False}, None), indent=2))
