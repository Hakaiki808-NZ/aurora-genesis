"""Opt-in bridge to the existing Genesis text-only generator contract."""
from __future__ import annotations

import re
import threading

from ..backends import GeneratorBackend


class NeurolBackend(GeneratorBackend):
    name = "neurol"

    def __init__(self, checkpoint="", *, enabled=False, expected_sha256="", max_new_bytes=128):
        if type(enabled) is not bool or type(max_new_bytes) is not int or not 1 <= max_new_bytes <= 512:
            raise ValueError("invalid Neurol configuration")
        self.checkpoint, self.enabled = checkpoint, enabled
        self.expected_sha256, self.max_new_bytes = expected_sha256, max_new_bytes
        self._core, self._lock = None, threading.Lock()
        self._status = "disabled" if not enabled else "not_loaded"

    def available(self):
        if not self.enabled:
            return False
        with self._lock:
            if self._core is not None:
                return True
            if not self.checkpoint or not re.fullmatch(r"[a-f0-9]{64}", self.expected_sha256):
                self._status = "checkpoint_and_digest_required"
                return False
            try:
                from .core import NeuralCore
                core, metadata, digest = NeuralCore.load(self.checkpoint, expected_sha256=self.expected_sha256)
                # This flag reports a measured learning check, not a safety approval.
                if metadata.get("stage") != "experimental_candidate" or metadata.get("learning_check_passed") is not True:
                    self._status = "candidate_learning_check_missing"
                    return False
                for weight in core.weights.values():
                    weight.flags.writeable = False
                self._core, self._status = core, "experimental_ready"
            except (ImportError, OSError, ValueError, TypeError, RecursionError):
                self._status = "unavailable_or_invalid_checkpoint"
                return False
        return True

    def generate(self, prompt):
        if not isinstance(prompt, str) or not prompt.strip() or not self.available():
            return None
        # Inference is read-only; model output is never parsed into executable actions.
        output = self._core.generate(prompt, max_new_bytes=self.max_new_bytes)
        return output.strip() or None

    def status(self):
        return {"name": self.name, "enabled": self.enabled, "status": self._status,
                "experimental": True, "training_during_chat": False, "execution_authority": False,
                "checkpoint_sha256": self.expected_sha256 if self._core is not None else None}
