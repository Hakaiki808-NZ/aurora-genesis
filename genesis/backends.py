"""Pluggable neural text generation: no Aurora execution or tool authority."""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field


class GeneratorBackend:
    name = "none"

    def available(self) -> bool:
        return False

    def generate(self, prompt: str) -> str | None:
        return None


@dataclass
class OllamaBackend(GeneratorBackend):
    """Local/private Ollama adapter. The model's output is *untrusted* text."""

    model: str = "qwen2.5-coder:1.5b"
    base_url: str = "http://127.0.0.1:11434"
    timeout: float = 2.0  # Health/model-list probe timeout
    generation_timeout: float = 120.0  # CPU generation may be slow
    max_output_tokens: int = 256
    name: str = "ollama"
    _checked: bool = field(default=False, init=False, repr=False)
    _available: bool = field(default=False, init=False, repr=False)
    _last_check: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        # Remote access must be controlled by the deployment network, not a public endpoint.
        if not self.base_url.startswith(("http://", "https://")) or not self.base_url.rstrip("/"):
            raise ValueError("invalid Ollama endpoint")
        self.base_url = self.base_url.rstrip("/")
        if not self.model or len(self.model) > 160:
            raise ValueError("invalid Ollama model")
        if not (0.2 <= self.timeout <= 30.0):
            raise ValueError("invalid Ollama health timeout")
        if not (1.0 <= self.generation_timeout <= 900.0):
            raise ValueError("invalid Ollama generation timeout")
        if not (1 <= self.max_output_tokens <= 2048):
            raise ValueError("invalid Ollama max output tokens")

    def available(self) -> bool:
        # Retry failed checks periodically. The old one-time cache permanently hid models
        # which were downloaded after Genesis first started.
        now = time.monotonic()
        if self._checked and (self._available or (now - self._last_check) < 5):
            return self._available
        self._checked, self._last_check = True, now
        try:
            req = urllib.request.Request(self.base_url + "/api/tags", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read(1_000_000).decode("utf-8"))
            names = [entry.get("name") or entry.get("model") for entry in data.get("models", []) if isinstance(entry, dict)]
            names = [item for item in names if isinstance(item, str) and item]
            if self.model == "auto" and names:
                self.model = names[0]
            self._available = self.model in names
        except (OSError, ValueError, KeyError, TypeError):
            self._available = False
        return self._available

    def generate(self, prompt: str) -> str | None:
        if not isinstance(prompt, str) or not prompt.strip() or not self.available():
            return None
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt[:6000],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": self.max_output_tokens},
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.generation_timeout) as response:
                data = json.loads(response.read(1_000_000).decode("utf-8"))
            answer = data.get("response")
            return answer.strip()[:8192] if isinstance(answer, str) and answer.strip() else None
        except (OSError, ValueError, KeyError, TypeError):
            self._available = False
            self._last_check = time.monotonic()
            return None
