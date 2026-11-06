"""Observation-only temporal world model for Genesis agents.

Tracks positions and state changes without access to any environment's source
code or hidden state. It is separate from the text-learning API. The model
only predicts motion when a recurring cycle is supported by evidence.
This is an experimental perception/memory module, not an AGI claim.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Mapping

Point = tuple[int, int]


@dataclass(frozen=True)
class MotionForecast:
    positions_after_actions: tuple[Point, ...]
    period: int
    confidence: float
    observed_samples: int
    method: str


@dataclass
class _Track:
    positions: deque[Point | None] = field(default_factory=lambda: deque(maxlen=80))
    confirmations: int = 0
    contradictions: int = 0
    total_updates: int = 0
    predicted_next: Point | None = None
    last_forecast_period: int | None = None
    surprise_cooldown: int = 0


class TemporalWorldModel:
    """Track synchronized moving entities and validate one-step forecasts.

    Entity identity is scoped to an episode and caller-provided kind.
    None means occlusion or no unambiguous detection, not object removal.
    """

    def __init__(self, min_period: int = 2, max_period: int = 32):
        if min_period < 1 or max_period < min_period:
            raise ValueError("invalid period bounds")
        self.min_period = min_period
        self.max_period = max_period
        self._tracks: dict[tuple[str, str], _Track] = {}
        self._events: dict[str, deque[dict[str, Any]]] = {}

    def reset_episode(self, episode: str) -> None:
        for key in list(self._tracks):
            if key[0] == episode:
                del self._tracks[key]
        self._events.pop(episode, None)

    @staticmethod
    def _point(point: Any) -> Point | None:
        if point is None:
            return None
        if (
            isinstance(point, (tuple, list))
            and len(point) == 2
            and all(type(x) is int for x in point)
        ):
            return (point[0], point[1])
        raise ValueError("position must be [integer x, integer y] or None")

    def observe(
        self,
        episode: str,
        observations: Mapping[str, Point | None],
        action_number: int,
    ) -> dict[str, Any]:
        """Append one observed position for each track, or None if missing."""
        if not episode or action_number < 0:
            raise ValueError("episode and nonnegative action_number required")
        tracks = {kind for ep, kind in self._tracks if ep == episode}
        tracks.update(observations)
        errors = {}
        for kind in sorted(tracks):
            point = self._point(observations.get(kind))
            track = self._tracks.setdefault((episode, kind), _Track())
            if track.predicted_next is not None and point is not None:
                if track.predicted_next == point:
                    track.confirmations += 1
                else:
                    track.contradictions += 1
                    track.surprise_cooldown = 2
                    errors[kind] = {
                        "predicted": track.predicted_next,
                        "observed": point,
                    }
            if point is not None and kind not in errors and track.surprise_cooldown > 0:
                track.surprise_cooldown -= 1
            track.predicted_next = None
            track.positions.append(point)
            track.total_updates += 1
        event = {"step": action_number, "observed": dict(observations),
                 "prediction_errors": errors}
        history = self._events.setdefault(episode, deque(maxlen=128))
        history.append(event)
        return {
            "episode": episode,
            "step": action_number,
            "prediction_errors": errors,
            "tracks": sorted(tracks),
        }

    def forecast(self, episode: str, kind: str, horizon: int) -> MotionForecast | None:
        if horizon < 1 or horizon > 128:
            raise ValueError("forecast horizon must be 1..128")
        track = self._tracks.get((episode, kind))
        if track is None or track.surprise_cooldown > 0:
            return None
        values = list(track.positions)
        if len(values) < self.min_period * 2:
            return None
        # Occlusion is not lack of periodicity. Reconstruct each phase from
        # repeated *observed* positions, ignoring invisible frames. A period
        # is accepted only when every phase has an observed position, at
        # least two cycles of samples support it, and contradictions are few.
        # The freshest 48 steps limit stale-cycle contamination after resets.
        from collections import Counter
        window = values[-48:]
        n = len(window)
        for p in range(self.min_period, min(self.max_period,n//2)+1):
            bins = {i:Counter() for i in range(p)}
            for i, point in enumerate(window):
                if point is not None:
                    bins[i%p][point] += 1
            if any(not bin_values for bin_values in bins.values()):
                continue
            visible = sum(sum(bin_values.values()) for bin_values in bins.values())
            if visible < 2*p:
                continue
            phases = {i:bins[i].most_common(1)[0][0] for i in range(p)}
            if len(set(phases.values())) < 2:
                continue
            consistent = sum(bins[i][phases[i]] for i in range(p))
            if consistent < visible * 0.85:
                continue
            # The end of the window is the latest observation, so phase n
            # is the position AFTER the next action.
            positions = tuple(phases[(n+i)%p] for i in range(horizon))
            track.predicted_next = positions[0]
            track.last_forecast_period = p
            confidence = min(0.99, consistent/(visible+1))
            return MotionForecast(
                positions_after_actions=positions, period=p,
                confidence=confidence, observed_samples=visible,
                method="occlusion_tolerant_periodic_phase",
            )
        return None

    def summary(self, episode: str) -> dict[str, Any]:
        items = {}
        for (ep, kind), track in self._tracks.items():
            if ep != episode:
                continue
            items[kind] = {
                "observations": track.total_updates,
                "visible_observations": sum(p is not None for p in track.positions),
                "prediction_confirmations": track.confirmations,
                "prediction_contradictions": track.contradictions,
                "last_observed": track.positions[-1] if track.positions else None,
                "last_period": track.last_forecast_period,
                "surprise_cooldown": track.surprise_cooldown,
            }
        return {
            "episode": episode, "tracks": items,
            "events_recorded": len(self._events.get(episode, ())),
        }
