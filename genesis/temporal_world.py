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
                    errors[kind] = {
                        "predicted": track.predicted_next,
                        "observed": point,
                    }
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
        if track is None:
            return None
        values = list(track.positions)
        if len(values) < self.min_period * 2:
            return None
        # Accept an observed periodic suffix only when two complete cycles
        # match. Missing/occluded observations invalidate that candidate.
        for p in range(self.min_period, min(self.max_period, len(values)//2)+1):
            first, second = values[-2*p:-p], values[-p:]
            if (first == second and all(x is not None for x in second)
                and len(set(second)) > 1):
                positions = tuple(second[i % p] for i in range(horizon))
                track.predicted_next = positions[0]
                track.last_forecast_period = p
                verified = track.confirmations
                contradicted = track.contradictions
                confidence = min(0.99, (2*p+verified)/(2*p+verified+contradicted+1))
                return MotionForecast(
                    positions_after_actions=positions, period=p,
                    confidence=confidence, observed_samples=len(values),
                    method="two_identical_observed_cycles",
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
            }
        return {
            "episode": episode, "tracks": items,
            "events_recorded": len(self._events.get(episode, ())),
        }
