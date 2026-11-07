"""Local Ollama embedding adapter for the optional Genesis memory network.

No remote embeddings, cloud service, downloads, or model starts are performed.
The operator must explicitly enable this adapter and independently make an
embedding-capable Ollama model available on loopback.
"""
from __future__ import annotations

import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from .memory_network import MemoryNetworkError


class OllamaLocalEmbeddings:
    """Synchronous, loopback-only embedding encoder for opt-in retrieval.

    Uses Ollama POST /api/embed. Do not expose model choice or the URL as
    untrusted user input. Versioning is logical, not a verified digest:
    replacing the model under the same name requires re-embedding records.
    """

    ENDPOINT = "http://127.0.0.1:11434/api/embed"
    MAX_RESPONSE_BYTES = 256 * 1024

    def __init__(self, model: str = "embeddinggemma", timeout_seconds: float = 8.0):
        if not isinstance(model, str) or not 1 <= len(model) <= 120:
            raise MemoryNetworkError("invalid Ollama embedding model identifier")
        # No path-like, control or whitespace characters in configured model IDs.
        if not all(c.isalnum() or c in "._:-/" for c in model):
            raise MemoryNetworkError("invalid Ollama embedding model identifier")
        if not 0 < timeout_seconds <= 30 or not math.isfinite(timeout_seconds):
            raise MemoryNetworkError("embedding timeout must be 0-30 seconds")
        self.model = model
        self.timeout_seconds = float(timeout_seconds)
        # Ignore proxy environment variables; a local-only encoder must stay local.
        self._opener = build_opener(ProxyHandler({}))

    def __call__(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip() or len(text) > 8192:
            raise MemoryNetworkError("embedding input must have 1-8192 characters")
        body = json.dumps({"model": self.model, "input": text, "truncate": False}).encode("utf-8")
        req = Request(self.ENDPOINT, data=body, headers={"Content-Type": "application/json"},
                      method="POST")
        try:
            with self._opener.open(req, timeout=self.timeout_seconds) as response:
                payload = response.read(self.MAX_RESPONSE_BYTES + 1)
        except (OSError, HTTPError, URLError) as exc:
            raise MemoryNetworkError(
                "local Ollama embedding unavailable; verify the explicit opt-in, "
                "running loopback server and installed embedding model"
            ) from exc
        if len(payload) > self.MAX_RESPONSE_BYTES:
            raise MemoryNetworkError("embedding response exceeds safe size limit")
        try:
            data = json.loads(payload)
            vectors = data["embeddings"]
            if not isinstance(vectors, list) or len(vectors) != 1:
                raise ValueError("one vector required")
            result = [float(x) for x in vectors[0]]
            if not 1 <= len(result) <= 4096 or any(not math.isfinite(x) for x in result):
                raise ValueError("invalid embedding vector")
        except (KeyError, ValueError, TypeError, IndexError, json.JSONDecodeError) as exc:
            raise MemoryNetworkError("local Ollama returned an invalid embedding") from exc
        return result
