"""Data-only C/B/A overlapping standards registry for Genesis.

Standards express progressive evaluation targets, not execution permissions.
Current legacy GENESIS_CAPABILITY_LEVEL and Aurora C1 cloud admission remain
separate. No model may self-certify attainment or use a standard to authorize
an Engine operation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Standard:
    rank: int
    canonical: str
    aliases: tuple[str, ...]
    series: str
    designation: str
    criteria: tuple[str, ...]
    evidence_state: str = "UNVERIFIED"

    def record(self) -> dict[str, Any]:
        return asdict(self)


_STANDARDS = (
    Standard(0, "C0", ("C0",), "C", "minimum", ("Stable basic input/output", "Explicit uncertainty reporting")),
    Standard(1, "C1", ("C1",), "C", "minimum", ("Baseline policy compliance", "Repeatable basic reasoning evaluations")),
    Standard(2, "C2", ("C2",), "C", "minimum", ("Grounded information retrieval", "Source and confidence distinction")),
    Standard(3, "C3", ("C3",), "C", "minimum", ("Structured plans with bounded tools", "Action-versus-answer separation")),
    Standard(4, "C4", ("C4",), "C", "minimum", ("Consistent safety and privacy constraints", "Reproducible robustness tests")),
    Standard(5, "C5/B1", ("C5", "B1"), "C+B", "minimum_to_achievable", ("Comprehensive baseline evaluation suite", "Auditable multi-step task completion")),
    Standard(6, "B2", ("B2",), "B", "achievable", ("Cross-domain transfer on held-out tasks", "Independent error and calibration evaluation")),
    Standard(7, "B3", ("B3",), "B", "achievable", ("Reliable longer-horizon tasks", "Independent recovery and regression evaluation")),
    Standard(8, "B4", ("B4",), "B", "achievable", ("Broad capability and generalization suite", "Demonstrated tool-use robustness across environments")),
    Standard(9, "B5/A1", ("B5", "A1"), "B+A", "achievable_to_frontier", ("Independently measured comparison to contemporary frontier systems", "Documented safety, reliability and benchmark limitations")),
    Standard(10, "A2", ("A2",), "A", "hypothetical", ("Research-defined performance beyond A1", "Independent falsifiable evaluation protocol")),
    Standard(11, "A3", ("A3",), "A", "hypothetical", ("Research-defined advancement beyond A2", "Independent falsifiable evaluation protocol")),
    Standard(12, "A4", ("A4",), "A", "hypothetical", ("Research-defined advancement beyond A3", "Independent falsifiable evaluation protocol")),
    Standard(13, "A5", ("A5",), "A", "hypothetical", ("Research-defined advancement beyond A4", "Independent falsifiable evaluation protocol")),
)
_BY_ALIAS = {alias: item for item in _STANDARDS for alias in item.aliases}


class StandardsRegistry:
    """Provides an ordinal map and evidence-collection schema, not automatic awards."""

    VERSION = "cba-overlap-v1"

    @staticmethod
    def lookup(label: str) -> Standard:
        if not isinstance(label, str) or label not in _BY_ALIAS:
            raise ValueError("unknown standard label")
        return _BY_ALIAS[label]

    @classmethod
    def equivalent(cls, first: str, second: str) -> bool:
        return cls.lookup(first).rank == cls.lookup(second).rank

    @classmethod
    def compare(cls, first: str, second: str) -> int:
        """-1 when first is lower, 0 when equivalent, +1 when higher."""
        a, b = cls.lookup(first).rank, cls.lookup(second).rank
        return (a > b) - (a < b)

    @staticmethod
    def catalogue() -> list[dict[str, Any]]:
        return [s.record() for s in _STANDARDS]

    @classmethod
    def summary(cls) -> dict[str, Any]:
        return {
            "version": cls.VERSION,
            "milestone_count": len(_STANDARDS),
            "label_count": len(_BY_ALIAS),
            "boundary_equivalences": [
                {"labels": ["C5", "B1"], "canonical": "C5/B1"},
                {"labels": ["B5", "A1"], "canonical": "B5/A1"},
            ],
            "minimum_series": ["C0", "C1", "C2", "C3", "C4", "C5"],
            "achievable_series": ["B1", "B2", "B3", "B4", "B5"],
            "frontier_series": ["A1", "A2", "A3", "A4", "A5"],
            "hypothetical_labels": ["A2", "A3", "A4", "A5"],
            "current_frontier_reference": "B5/A1",
            "attainment_state": "UNVERIFIED",
            "execution_authority": "NONE",
            "legacy_capability_namespace": "GENESIS_CAPABILITY_LEVEL C0-C5 is execution-policy compatibility, not standards attainment",
        }

    @classmethod
    def evidence_requirements(cls, label: str) -> dict[str, Any]:
        standard = cls.lookup(label)
        return {
            "standard": standard.canonical,
            "criteria": list(standard.criteria),
            "required_evidence": [
                "versioned_evaluation_protocol",
                "held_out_test_results",
                "reproducible_run_artifacts",
                "independent_reviewer_record",
            ],
            "status": "NOT_QUALIFIED",
            "reason": "Defining a target is not evidence of achieving it.",
            "grants_engine_privileges": False,
        }
