"""Opt-in, text-only Bedrock inference. No tool execution or engine authority.

This adapter does not train a neural network. Model output is untrusted text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from .backends import GeneratorBackend


@dataclass
class BedrockBackend(GeneratorBackend):
    """A bounded Converse adapter for a pre-trained external foundation model."""

    model: str = "openai.gpt-oss-120b-1:0"
    region: str = "ap-southeast-2"
    enabled: bool = False
    max_output_tokens: int = 256
    max_calls: int = 8  # Per process, NOT an account-level spending cap.
    name: str = "bedrock"
    client: Any = field(default=None, repr=False)
    call_count: int = field(default=0, init=False)
    last_error_code: str | None = field(default=None, init=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_output_tokens <= 512:
            raise ValueError("max_output_tokens must be between 1 and 512")
        if not 1 <= self.max_calls <= 25:
            raise ValueError("max_calls must be between 1 and 25")
        if not self.model or len(self.model) > 200:
            raise ValueError("invalid model identifier")
        if not self.region or len(self.region) > 60:
            raise ValueError("invalid AWS region")

    def available(self) -> bool:
        """Configured/SDK available only; NOT proof of AWS service quota or access."""
        if not self.enabled or self.call_count >= self.max_calls:
            return False
        if self.client is not None:
            return True
        try:
            import boto3  # optional; never imported for symbolic-only use
            return bool(boto3)
        except ImportError:
            return False

    def _client(self) -> Any:
        if self.client is None:
            import boto3
            from botocore.config import Config
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                config=Config(
                    connect_timeout=3,
                    read_timeout=12,
                    retries={"mode": "standard", "max_attempts": 1},
                ),
            )
        return self.client

    def generate(self, prompt: str) -> str | None:
        if not isinstance(prompt, str) or not prompt.strip():
            return None
        # No raw prompt logging; trim to cap token usage and privacy exposure.
        prompt = prompt[:6000]
        with self._lock:
            if not self.available():
                self.last_error_code = "DISABLED_OR_EXHAUSTED"
                return None
            self.call_count += 1  # Count attempted calls, including errors.
        try:
            result = self._client().converse(
                modelId=self.model,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": self.max_output_tokens, "temperature": 0.2},
            )
            if result.get("stopReason") not in ("end_turn", "stop_sequence"):
                self.last_error_code = "NON_FINAL_MODEL_OUTPUT"
                return None
            blocks = result.get("output", {}).get("message", {}).get("content", [])
            answer = "\n".join(x["text"] for x in blocks if isinstance(x, dict) and isinstance(x.get("text"), str)).strip()
            if not answer:
                self.last_error_code = "EMPTY_MODEL_OUTPUT"
                return None
            self.last_error_code = None
            return answer[:4096]
        except Exception as exc:
            # Never surface or log exception messages; they may contain user data.
            code = getattr(exc, "response", {}).get("Error", {}).get("Code") if isinstance(getattr(exc, "response", None), dict) else None
            self.last_error_code = (code if isinstance(code, str) and code.isidentifier() else type(exc).__name__)[:80]
            return None
