"""Local-only, explicitly enabled Hugging Face text generation for Genesis.

No remote inference, implicit downloads, tools, Aurora privileges or training.
Imported content is untrusted model data. The backend is intentionally CPU-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from threading import Lock
from typing import Any

from .backends import GeneratorBackend
from .hf_models import ModelImportError, verify_local_model


@dataclass
class HuggingFaceBackend(GeneratorBackend):
    model_dir: str = ""
    enabled: bool = False
    max_output_tokens: int = 128
    max_calls: int = 8
    name: str = "huggingface"
    call_count: int = field(default=0, init=False)
    last_error_code: str | None = field(default=None, init=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _model: Any = field(default=None, init=False, repr=False)
    _tokenizer: Any = field(default=None, init=False, repr=False)
    _verified: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_output_tokens <= 256:
            raise ValueError("max_output_tokens must be between 1 and 256")
        if not 1 <= self.max_calls <= 25:
            raise ValueError("max_calls must be between 1 and 25")

    def available(self) -> bool:
        if not self.enabled or not self.model_dir or self.call_count >= self.max_calls:
            return False
        try:
            verify_local_model(self.model_dir)
            return find_spec("torch") is not None and find_spec("transformers") is not None
        except (ModelImportError, ImportError, OSError, ValueError):
            return False

    def generate(self, prompt: str) -> str | None:
        if not isinstance(prompt, str) or not prompt.strip():
            return None
        # Serialize generation to avoid races and unintended CPU memory growth.
        with self._lock:
            if not self.available():
                self.last_error_code = "DISABLED_OR_UNAVAILABLE"
                return None
            self.call_count += 1
            try:
                if not self._verified:
                    verify_local_model(self.model_dir, verify_hashes=True)
                    self._verified = True
                if self._model is None:
                    import torch
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    path = str(Path(self.model_dir).resolve())
                    self._tokenizer = AutoTokenizer.from_pretrained(
                        path, local_files_only=True, trust_remote_code=False
                    )
                    self._model = AutoModelForCausalLM.from_pretrained(
                        path, local_files_only=True, trust_remote_code=False,
                        use_safetensors=True, torch_dtype=torch.float32
                    )
                    self._model.eval()
                import torch
                messages = [{"role": "user", "content": prompt[:6000]}]
                tokens = self._tokenizer.apply_chat_template(
                    messages, tokenize=True, add_generation_prompt=True,
                    return_tensors="pt"
                )
                with torch.inference_mode():
                    outputs = self._model.generate(
                        input_ids=tokens, max_new_tokens=self.max_output_tokens,
                        do_sample=False,
                        pad_token_id=self._tokenizer.eos_token_id
                    )
                answer = self._tokenizer.decode(
                    outputs[0][tokens.shape[-1]:], skip_special_tokens=True
                ).strip()
                self.last_error_code = None if answer else "EMPTY_MODEL_OUTPUT"
                return answer[:4096] if answer else None
            except Exception as exc:
                # Do not expose source prompts, arbitrary exception messages or paths.
                self.last_error_code = type(exc).__name__[:80]
                return None
