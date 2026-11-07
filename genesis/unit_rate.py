"""Conservative, exact unit-price solver for bounded, unambiguous user questions.

This is deterministic arithmetic on user-supplied numbers, not LLM reasoning.
Ambiguous inputs are declined and left to the ordinary Genesis reasoning path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
_COUNT = r"(?:\d{1,6}|" + "|".join(_NUMBERS) + r")"
_ITEM = r"[a-z]{2,30}"
_STATEMENT = re.compile(
    rf"\A\s*(?P<count>{_COUNT})\s+(?P<item>{_ITEM})\s+costs?\s+"
    rf"(?P<currency>[$£€])\s*(?P<total>\d{{1,8}}(?:\.\d{{1,2}})?)\s*[.]\s*",
    re.IGNORECASE,
)
_QUERY = re.compile(
    rf"\A(?:what\s+(?:do|does|will|would)\s+|how\s+much\s+"
    rf"(?:do|does|will|would)\s+)(?P<count>{_COUNT})\s+(?P<item>{_ITEM})\s+cost"
    rf"(?:\s+(?:at|for)\s+(?:the\s+)?same\s+(?:rate|price(?:\s+per\s+{_ITEM})?))?\s*[?]?\s*\Z",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UnitRateResult:
    currency: str
    source_count: int
    target_count: int
    source_total: Decimal
    target_total: Decimal
    item: str

    def answer(self) -> str:
        amount = format(self.target_total, "f")
        if "." in amount:
            amount = amount.rstrip("0").rstrip(".")
        return f"{self.currency}{amount} (verified unit-price calculation: {self.currency}{self.source_total} ÷ {self.source_count} × {self.target_count})."


def _count(text: str) -> int | None:
    value = _NUMBERS.get(text.casefold()) if not text.isdecimal() else int(text)
    return value if value is not None and 1 <= value <= 1_000_000 else None


def _item(text: str) -> str:
    """Only elementary plural patterns; avoid trying to understand all grammar."""
    item = text.casefold()
    if item.endswith("ies") and len(item) > 4:
        return item[:-3] + "y"
    if item.endswith("s") and not item.endswith(("ss", "us")) and len(item) > 3:
        return item[:-1]
    return item


def solve_unit_rate(text: str) -> UnitRateResult | None:
    """Calculate one plain price statement and one same-item question only.

    Coupons, discounts, taxes, shipping, conversions and other qualifiers are
    never silently interpreted as a simple linear unit-price problem.
    """
    if not isinstance(text, str) or len(text) > 350:
        return None
    statement = _STATEMENT.match(text)
    if statement is None:
        return None
    question = _QUERY.fullmatch(text[statement.end():])
    if question is None:
        return None
    source_count, target_count = _count(statement["count"]), _count(question["count"])
    if source_count is None or target_count is None:
        return None
    source_item, target_item = _item(statement["item"]), _item(question["item"])
    if source_item != target_item:
        return None
    try:
        total = Decimal(statement["total"])
        value = total * Decimal(target_count) / Decimal(source_count)
    except (InvalidOperation, OverflowError, ZeroDivisionError):
        return None
    if total <= 0 or value > Decimal("99999999.99"):
        return None
    if value != value.quantize(Decimal("0.01")):
        # Rounding policy is not supplied by the question.
        return None
    return UnitRateResult(
        currency=statement["currency"], source_count=source_count,
        target_count=target_count, source_total=total,
        target_total=value, item=source_item
    )
