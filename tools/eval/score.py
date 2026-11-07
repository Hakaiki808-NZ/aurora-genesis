"""Strict mechanical scoring for a frozen public smoke set, NOT human judgment."""
from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation


def grade(case: dict, answer: str | None) -> dict:
    """pass/fail/review: never silently turn ambiguous responses into successes."""
    if not isinstance(answer, str) or not answer.strip():
        return {"status":"fail","reason":"empty generation"}
    text=answer.strip()
    kind=case["kind"]
    expected=str(case.get("expected",""))
    if kind=="exact_number":
        match=re.fullmatch(
            r"(?:(?:The )?[Aa]nswer(?: is)?\s*:?\s*)?(-?\d+(?:\.\d+)?)[.!]?",text
        )
        if match:
            try:
                correct=Decimal(match.group(1))==Decimal(expected)
                return {"status":"pass" if correct else "fail","reason":"strict numeric answer"}
            except InvalidOperation:
                pass
        return {"status":"review","reason":"noncanonical numeric answer"}
    if kind=="currency":
        match=re.fullmatch(r"([$£€])\s*(\d{1,10}(?:\.\d{1,2})?)",expected)
        if match is None:
            raise ValueError("invalid expected currency")
        currency,value=match.groups()
        amounts=re.findall(r"([$£€])\s*(\d{1,10}(?:\.\d{1,2})?)",text)
        if not amounts:
            return {"status":"review","reason":"no currency amount in answer"}
        if text.startswith(expected+" (verified unit-price calculation:"):
            return {"status":"pass","reason":"verified deterministic unit-price proof"}
        unique={(cur,Decimal(number)) for cur,number in amounts}
        if len(unique)>1:
            return {"status":"review","reason":"multiple distinct prices; needs reasoning review"}
        actual=next(iter(unique))
        return {"status":"pass" if actual==(currency,Decimal(value)) else "fail",
                "reason":"single reported currency price"}
    if kind=="yes_no":
        match=re.match(r"(?i)^\s*(yes|no)\b",text)
        if not match:
            return {"status":"review","reason":"no direct yes/no answer"}
        return {"status":"pass" if match.group(1).casefold()==expected.casefold()
                else "fail","reason":"initial yes/no conclusion"}
    if kind=="contains":
        if all(term.casefold() in text.casefold() for term in case["terms"]):
            return {"status":"pass","reason":"all required terms present"}
        return {"status":"fail","reason":"required fact missing"}
    if kind=="abstain":
        abstained=re.search(
            r"(?i)\b(?:can't know|cannot know|don't know|do not know|unknown|"
            r"no access|cannot determine|can't determine|without (?:records|data)|"
            r"not enough information|no way to know|cannot verify)\b",text
        )
        invented=re.search(r"\b\d{1,3}\s*%(?!\w)|\b\d{1,3}\s*degrees\b",text,flags=re.I)
        if abstained and not invented:
            return {"status":"pass","reason":"explicit epistemic abstention"}
        return {"status":"review","reason":"no clear uncertainty statement"}
    if kind=="exact_text":
        return {"status":"pass" if text==expected else "fail",
                "reason":"strict exact-text instruction"}
    if kind=="human_review":
        return {"status":"review","reason":"semantic quality requires independent judgment"}
    raise ValueError("unknown evaluation kind")
