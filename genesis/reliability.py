"""Read-only, sanitized Genesis readiness probes for Aurora supervision.

This module does not restart workers, inspect user conversations, or grant
Aurora access to Model semantics. Only Aurora's protected supervisor can
decide how to recover a failing component.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Genesis


def readiness_status(model: "Genesis") -> dict[str, str]:
    """Return a minimal routing signal without exposing private diagnostics.

    The existing self_check validates SQLite integrity and model invariants.
    A storage lock prevents a check racing with in-process SQLite writes.
    Backend availability is deliberately excluded: Genesis can remain able to
    serve non-neural functions while a generator provider is degraded.
    """
    try:
        with model.store._lock:
            ready = model.self_check().get("ok") is True
    except Exception:
        ready = False
    return {
        "component": "genesis",
        "status": "ready" if ready else "unavailable",
    }
