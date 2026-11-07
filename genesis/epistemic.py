"""Conservative abstention for unsourced exact time-stamped observational claims.

This is an epistemic gate only, not an external data source or content filter.
"""
from __future__ import annotations
import re

_OBSERVATION=re.compile(
    r"\b(?:humidity|temperature|rainfall|precipitation|wind\s+speed|"
    r"air\s+pressure|air\s+quality|water\s+level)\b",re.I
)
_EXACT=re.compile(r"\b(?:exact|precise|specific\s+reading)\b",re.I)
_TIME=re.compile(
    r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{4}|yesterday|last\s+(?:week|month|year)|today|now)\b",
    re.I,
)


def unsourced_exact_observation(text: str) -> str | None:
    """Never manufacture an exact time-stamped sensor value when sources are excluded."""
    if (not isinstance(text,str) or len(text)>600
            or not _OBSERVATION.search(text)
            or not _EXACT.search(text)
            or not _TIME.search(text)):
        return None
    return (
        "I cannot verify that exact measurement without observation records "
        "or a trusted source. I won't invent a value."
    )
