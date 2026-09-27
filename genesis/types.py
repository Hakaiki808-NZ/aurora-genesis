from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Evidence:
    source: str
    confidence: float = 1.0
    kind: str = "explicit"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Candidate:
    name: str
    response: str
    score: float
    rationale: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    action: dict[str, Any] | None = None

    def record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    chosen: Candidate
    candidates: list[Candidate]
    confidence: float


@dataclass
class ToolResult:
    ok: bool
    tool: str
    output: Any = None
    error: str | None = None


@dataclass
class GoalStep:
    step_no: int
    description: str
    action: str
    args: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Any = None
