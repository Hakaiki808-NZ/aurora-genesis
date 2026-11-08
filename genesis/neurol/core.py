"""Original NumPy implementation of a byte-level, reset-before GRU.

Uses the established GRU architecture, not a newly invented learning algorithm.
No pretrained weights, network calls, tools, or persistent conversation state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np

BOS, EOS, VOCAB = 256, 257, 258
FORMAT = "genesis-neurol-gru-v1"
MAX_CHECKPOINT_BYTES = 48 * 1024 * 1024
# The scaled profile is 999,996 parameters larger than the 26,130-parameter prototype.
MILLION_PROFILE = (216, 437)
MAX_PARAMETERS = 1_200_000


@dataclass(frozen=True)
class Config:
    embedding: int = 16
    hidden: int = 48
    seed: int = 1907

    def __post_init__(self):
        for name, low, high in (("embedding", 2, 256), ("hidden", 2, 512), ("seed", 0, 2**32-1)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"invalid {name}")
        if self.parameter_count > MAX_PARAMETERS:
            raise ValueError("configuration exceeds the bounded research model parameter budget")

    @property
    def parameter_count(self) -> int:
        e, h = self.embedding, self.hidden
        return VOCAB*e + 3*(e*h + h*h + h) + h*VOCAB + VOCAB

    @classmethod
    def million(cls, seed: int = 1907) -> "Config":
        """Approximately one million additional *initialized*, not trained, weights."""
        return cls(embedding=MILLION_PROFILE[0], hidden=MILLION_PROFILE[1], seed=seed)


def encode(text: str) -> list[int]:
    return [BOS, *text.encode("utf-8"), EOS]


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class NeuralCore:
    def __init__(self, config: Config = Config()):
        self.config = config
        rng = np.random.default_rng(config.seed)
        e, h = config.embedding, config.hidden
        self.weights = {"E": rng.normal(0, 0.1, (VOCAB, e))}
        for gate in ("r", "z", "n"):
            self.weights["W" + gate] = rng.normal(0, 1/math.sqrt(e), (e, h))
            self.weights["U" + gate] = rng.normal(0, 1/math.sqrt(h), (h, h))
            self.weights["b" + gate] = np.zeros(h)
        self.weights["V"] = rng.normal(0, 1/math.sqrt(h), (h, VOCAB))
        self.weights["b"] = np.zeros(VOCAB)

    @property
    def parameter_count(self):
        return sum(w.size for w in self.weights.values())

    def step(self, ids, previous):
        p = self.weights
        x = p["E"][ids]
        r = sigmoid(x @ p["Wr"] + previous @ p["Ur"] + p["br"])
        z = sigmoid(x @ p["Wz"] + previous @ p["Uz"] + p["bz"])
        n = np.tanh(x @ p["Wn"] + (r * previous) @ p["Un"] + p["bn"])
        hidden = z * previous + (1-z) * n
        logits = hidden @ p["V"] + p["b"]
        return logits, hidden, (ids, x, previous, r, z, n, hidden)

    def loss_and_gradients(self, inputs, targets, *, backward=True):
        inputs, targets = np.asarray(inputs), np.asarray(targets)
        if (inputs.ndim != 2 or inputs.shape != targets.shape or not inputs.size
                or inputs.shape[0] > 32 or inputs.shape[1] > 256
                or inputs.dtype.kind not in "iu" or targets.dtype.kind not in "iu"
                or inputs.min() < 0 or inputs.max() >= VOCAB
                or targets.min() < 0 or targets.max() >= VOCAB):
            raise ValueError("invalid bounded token batch")
        batch, length = inputs.shape
        hidden = np.zeros((batch, self.config.hidden))
        cache, loss = [], 0.0
        rows = np.arange(batch)
        for t in range(length):
            logits, hidden, state = self.step(inputs[:, t], hidden)
            shifted = logits - logits.max(axis=1, keepdims=True)
            log_probs = shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))
            loss -= float(log_probs[rows, targets[:, t]].sum())
            if backward:
                delta = np.exp(log_probs)
                delta[rows, targets[:, t]] -= 1
                cache.append((state, delta / inputs.size))
        if not math.isfinite(loss):
            raise ValueError("non-finite neural loss")
        if not backward:
            return loss / inputs.size, None
        p = self.weights
        grads = {k: np.zeros_like(w) for k, w in p.items()}
        carry = np.zeros_like(hidden)
        for state, delta in reversed(cache):
            ids, x, previous, r, z, n, hidden = state
            grads["V"] += hidden.T @ delta
            grads["b"] += delta.sum(axis=0)
            dh = delta @ p["V"].T + carry
            dn = dh * (1-z) * (1-n*n)
            dz = dh * (previous-n) * z * (1-z)
            drh = dn @ p["Un"].T
            dr = drh * previous * r * (1-r)
            carry = dh*z + drh*r + dr @ p["Ur"].T + dz @ p["Uz"].T
            dx = np.zeros_like(x)
            for gate, d, recurrent in (("r", dr, previous), ("z", dz, previous), ("n", dn, r*previous)):
                grads["W"+gate] += x.T @ d
                grads["U"+gate] += recurrent.T @ d
                grads["b"+gate] += d.sum(axis=0)
                dx += d @ p["W"+gate].T
            np.add.at(grads["E"], ids, dx)
        return loss / inputs.size, grads

    def generate(self, prompt: str, *, max_new_bytes=128, temperature=0.0, seed=0):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be non-empty text")
        if type(max_new_bytes) is not int or not 1 <= max_new_bytes <= 512:
            raise ValueError("max_new_bytes must be 1..512")
        if not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or not 0 <= temperature <= 2:
            raise ValueError("temperature must be 0..2")
        # Each call starts fresh. No hidden state leaks between user sessions.
        hidden = np.zeros((1, self.config.hidden))
        for token in [BOS, *prompt[-2048:].encode("utf-8")[-2048:]]:
            logits, hidden, _ = self.step(np.array([token]), hidden)
        rng, output = np.random.default_rng(seed), []
        for _ in range(max_new_bytes):
            scores = logits[0].copy()
            scores[BOS] = -np.inf
            if temperature == 0:
                token = int(scores.argmax())
            else:
                scores = scores/temperature
                probabilities = np.exp(scores-scores.max())
                probabilities /= probabilities.sum()
                token = int(rng.choice(VOCAB, p=probabilities))
            if token == EOS:
                break
            output.append(token)
            logits, hidden, _ = self.step(np.array([token]), hidden)
        return bytes(output).decode("utf-8", errors="replace")

    def save(self, path, metadata: dict):
        payload = {"format": FORMAT, "config": asdict(self.config), "metadata": metadata,
                   "weights": {k: w.tolist() for k, w in self.weights.items()}}
        digest = hashlib.sha256(canonical(payload)).hexdigest()
        raw = canonical({"sha256": digest, "payload": payload})
        if len(raw) > MAX_CHECKPOINT_BYTES:
            raise ValueError("checkpoint too large")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temporary = handle.name
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return digest

    @classmethod
    def load(cls, path, *, expected_sha256=None):
        # JSON data only: no pickle, executable classes, or downloaded code.
        with Path(path).open("rb") as handle:
            raw = handle.read(MAX_CHECKPOINT_BYTES+1)
        if len(raw) > MAX_CHECKPOINT_BYTES:
            raise ValueError("checkpoint too large")
        try:
            wrapper = json.loads(raw)
            payload = wrapper["payload"]
            digest = hashlib.sha256(canonical(payload)).hexdigest()
            if digest != wrapper["sha256"] or (expected_sha256 is not None and digest != expected_sha256):
                raise ValueError("checkpoint digest mismatch")
            if payload["format"] != FORMAT or not isinstance(payload["metadata"], dict):
                raise ValueError("unsupported checkpoint")
            model = cls(Config(**payload["config"]))
            weights = payload["weights"]
            if weights.keys() != model.weights.keys():
                raise ValueError("invalid parameter names")
            for name, initial in model.weights.items():
                array = np.asarray(weights[name], dtype=np.float64)
                if array.shape != initial.shape or not np.isfinite(array).all() or np.abs(array).max() > 1000:
                    raise ValueError("invalid parameter values or shape")
                model.weights[name] = array
            return model, payload["metadata"], digest
        except (KeyError, TypeError, OverflowError, RecursionError) as exc:
            raise ValueError("invalid checkpoint") from exc


class Adam:
    def __init__(self, model, rate=0.003):
        if not math.isfinite(rate) or not 0 < rate <= 0.1:
            raise ValueError("invalid learning rate")
        self.model, self.rate, self.t = model, rate, 0
        self.m = {k: np.zeros_like(w) for k, w in model.weights.items()}
        self.v = {k: np.zeros_like(w) for k, w in model.weights.items()}

    def update(self, grads):
        if any(not np.isfinite(g).all() for g in grads.values()):
            raise ValueError("non-finite gradients")
        norm = math.sqrt(sum(float((g*g).sum()) for g in grads.values()))
        scale = min(1.0, 1.0/max(norm, 1e-12))
        self.t += 1
        for k, w in self.model.weights.items():
            g = grads[k]*scale
            self.m[k] = 0.9*self.m[k] + 0.1*g
            self.v[k] = 0.999*self.v[k] + 0.001*g*g
            w -= self.rate*(self.m[k]/(1-0.9**self.t))/(np.sqrt(self.v[k]/(1-0.999**self.t))+1e-8)
