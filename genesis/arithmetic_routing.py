"""Bounded interpreter of elementary arithmetic questions for the existing calculator.

No eval, code generation, arbitrary word problems or untrusted program execution.
"""
from __future__ import annotations
import re
from decimal import Decimal

_NUMBER=r"(?:\d{1,9}(?:\.\d{1,3})?)"
_ARITHMETIC=re.compile(
    rf"\A\s*(?:calculate|compute|what\s+is|what's)\s+"
    rf"(?P<a>{_NUMBER})\s*"
    rf"(?P<op>divided\s+by|multiplied\s+by|times|plus|minus|\*|/|\+|\-|×|÷)"
    rf"\s*(?P<b>{_NUMBER})\s*(?:[?.]\s*)?"
    rf"(?:(?:give|answer)\s+(?:with\s+)?(?:only\s+)?(?:the\s+)?"
    rf"(?:number|result|answer)\s*[.]?\s*)?\Z",
    re.IGNORECASE,
)
_OPS={
    "divided by":"/", "multiplied by":"*", "times":"*",
    "plus":"+", "minus":"-", "×":"*", "÷":"/",
}


def parse_arithmetic(text: str) -> str | None:
    """Translate a simple, fully matched question to the calculator's safe syntax."""
    if not isinstance(text,str) or len(text)>180:
        return None
    match=_ARITHMETIC.fullmatch(text)
    if match is None:
        return None
    operation=re.sub(r"\s+"," ",match["op"].casefold())
    operation=_OPS.get(operation,operation)
    if operation=="/" and Decimal(match["b"])==0:
        return None
    return f"{match['a']} {operation} {match['b']}"
