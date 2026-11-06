"""Opt-in, offline-only Hugging Face text generator for Genesis.

Pretrained model output is untrusted text. No tool calls, remote execution, model
training or Aurora authority is implemented here. Weights MUST be cached locally
before enabling this backend: from_pretrained uses local_files_only=True.
"""
from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from .backends import GeneratorBackend

ALLOWED_MODELS = frozenset({"Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"})


@dataclass
class HuggingFaceBackend(GeneratorBackend):
    model_id: str = "Qwen/Qwen3-0.6B"
    revision: str | None = None  # Reviewed immutable Hugging Face commit SHA.
    enabled: bool = False
    max_output_tokens: int = 128
    max_calls: int = 8  # Per process only; NOT a billing or memory limit.
    name: str = "huggingface"
    generator: Any = field(default=None, repr=False)
    call_count: int = field(default=0, init=False)
    last_error_code: str | None = field(default=None, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.model_id not in ALLOWED_MODELS:
            raise ValueError("model must be on the reviewed Hugging Face allowlist")
        if not 1 <= self.max_output_tokens <= 256:
            raise ValueError("max_output_tokens must be between 1 and 256")
        if not 1 <= self.max_calls <= 25:
            raise ValueError("max_calls must be between 1 and 25")

    def available(self) -> bool:
        """Configured and dependencies importable; NOT proof weights are cached."""
        if not self.enabled or self.call_count >= self.max_calls:
            return False
        return self.generator is not None or importlib.util.find_spec("transformers") is not None

    def _generator(self) -> Any:
        if self.generator is None:
            if not self.revision or not re.fullmatch(r"[0-9a-f]{40}", self.revision):
                raise ValueError("a reviewed 40-character model revision SHA is required")
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            # Deliberately offline: no implicit network fetch, custom remote code,
            # external inference API, or downloads during a Genesis user request.
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_id, revision=self.revision, local_files_only=True, trust_remote_code=False
            )
            model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                revision=self.revision,
                local_files_only=True,
                trust_remote_code=False,
                device_map="auto",
            )
            self.generator = pipeline("text-generation", model=model, tokenizer=tokenizer)
        return self.generator

    def generate(self, prompt: str) -> str | None:
        if not isinstance(prompt, str) or not prompt.strip():
            return None
        with self._lock:
            if not self.available():
                self.last_error_code = "DISABLED_OR_EXHAUSTED"
                return None
            self.call_count += 1
            try:
                response = self._generator()(
                    [
                        {
                            "role": "system",
                            "content": (
                                "You are a text-only proposal component within Genesis. "
                                "You cannot run tools, approve actions, grant permissions, "
                                "modify memories, or control Aurora. State uncertainty."
                            ),
                        },
                        {"role": "user", "content": prompt[:4000]},
                    ],
                    max_new_tokens=self.max_output_tokens,
                    do_sample=False,
                    return_full_text=False,
                )
                if not isinstance(response, list) or not response:
                    self.last_error_code = "INVALID_MODEL_OUTPUT"
                    return None
                content = response[0].get("generated_text") if isinstance(response[0], dict) else None
                if isinstance(content, list):
                    content = next(
                        (
                            message.get("content")
                            for message in reversed(content)
                            if isinstance(message, dict) and message.get("role") == "assistant"
                        ),
                        None,
                    )
                if not isinstance(content, str) or not content.strip():
                    self.last_error_code = "EMPTY_MODEL_OUTPUT"
                    return None
                self.last_error_code = None
                return content.strip()[:4096]
            except Exception as exc:
                # No raw exception or prompt logging: failures may include private data.
                self.last_error_code = type(exc).__name__[:80]
                return None
