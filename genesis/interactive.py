"""Typed, bounded interactive exploration for Genesis.

This lightweight reference policy is not an AGI solver. It answers a specific
systems question: can Genesis take genuine observations and return a legal
action WITHOUT routing environmental data through its chat/learning parser?

Aurora retains exclusive authority over actual external execution. This module
returns a recommendation only; the test harness dispatches game actions.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class _GameSession:
    tried: dict[str, int] = field(default_factory=dict)
    changed: dict[str, int] = field(default_factory=dict)
    attempts: int = 0
    pending: dict[str, Any] | None = None
    recent: list[str] = field(default_factory=list)
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    pointer_step: int = 0


class InteractiveExplorer:
    """General, explicitly non-neural baseline using action/outcome history.

    Explore every available action once; thereafter prioritize actions that
    actually changed the observed state, with a recency penalty to limit
    useless repetition. This is a deterministic exploration baseline, NOT
    semantic world modelling or successful goal inference.
    """
    _allowed = re.compile(r"^ACTION[1-6]$")
    _pointer_positions = (
        (32, 32), (16, 16), (48, 16), (16, 48), (48, 48),
        (32, 16), (16, 32), (48, 32), (32, 48), (8, 8),
        (56, 8), (8, 56), (56, 56), (32, 32),
    )

    def __init__(self, max_history: int = 256) -> None:
        if max_history < 1:
            raise ValueError("max_history must be positive")
        self.max_history = max_history
        self._games: dict[str, _GameSession] = {}

    def _session(self, game_id: str) -> _GameSession:
        if not isinstance(game_id, str) or not game_id.strip():
            raise ValueError("game_id must be a non-empty string")
        return self._games.setdefault(game_id, _GameSession())

    @staticmethod
    def _fingerprint(frame: str) -> str:
        if not isinstance(frame, str) or not frame:
            raise ValueError("a non-empty serialized observation is required")
        return hashlib.sha256(frame.encode("utf-8")).hexdigest()

    def observe_outcome(self, game_id: str, frame: str, state: str = "UNKNOWN") -> dict[str, Any]:
        """Apply environmental feedback to an outstanding action once."""
        session = self._session(game_id)
        signature = self._fingerprint(frame)
        previous = session.pending
        if previous is None:
            return {"recorded": False, "reason": "no pending action"}
        changed = signature != previous["from_frame"]
        action = previous["action_type"]
        if changed:
            session.changed[action] = session.changed.get(action, 0) + 1
        result = {
            "step": previous["step"],
            "action_type": action,
            "changed_observation": changed,
            "resulting_state": str(state),
        }
        session.outcomes.append(result)
        if len(session.outcomes) > self.max_history:
            del session.outcomes[:-self.max_history]
        session.pending = None
        return {"recorded": True, **result}

    def decide_action(
        self, game_id: str, frame: str, allowed_actions: Iterable[str]
    ) -> dict[str, Any]:
        """Return one VALID typed action, or an explicit abstention.

        No side effects and no user-language parsing. Observations are untrusted
        environmental data; they never become instructions or learned claims.
        """
        session = self._session(game_id)
        signature = self._fingerprint(frame)
        valid = sorted({
            act for act in allowed_actions
            if isinstance(act, str) and self._allowed.fullmatch(act)
        })
        if not valid:
            return {"action": None, "reason": "no_valid_allowed_actions", "policy": "explore-v1"}
        if session.pending is not None:
            return {"action": None, "reason": "awaiting_environment_feedback", "policy": "explore-v1"}

        untried = [act for act in valid if session.tried.get(act, 0) == 0]
        if untried:
            chosen = untried[0]
            reason = "systematic_first_visit"
        else:
            def merit(act: str) -> tuple[float, int, str]:
                used = session.tried.get(act, 0)
                observed_changes = session.changed.get(act, 0)
                changes = observed_changes / max(used, 1)
                repeat_penalty = 0.15 * session.recent[-3:].count(act)
                return (changes - repeat_pen, -used, act)
            chosen = max(valid, key=merit)
            reason = "observed_change_rate_and_repeat_penalty"

        action: dict[str, Any] = {"action_type": chosen}
        if chosen == "ACTION6":
            x, y = self._pointer_positions[session.pointer_step % len(self._pointer_positions)]
            session.pointer_step += 1
            action.update(x=x, y=y)

        session.tried[chosen] = session.tried.get(chosen, 0) + 1
        session.attempts += 1
        session.recent.append(chosen)
        session.recent = session.recent[-8:]
        session.pending = {
            "step": session.attempts,
            "action_type": chosen,
            "from_frame": signature,
        }
        return {
            "action": action,
            "reason": reason,
            "policy": "explore-v1",
            "step": session.attempts,
            "last_observed_changes": dict(session.changed),
            "note": "bounded action-choice baseline, not a learned world model",
        }

    def history(self, game_id: str) -> dict[str, Any]:
        s = self._session(game_id)
        return {
            "steps_issued": s.attempts,
            "action_counts": dict(s.tried),
            "observation_changes_by_action": dict(s.changed),
            "outcomes": list(s.outcomes),
            "awaiting_feedback": s.pending is not None,
        }
