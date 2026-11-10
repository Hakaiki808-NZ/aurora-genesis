"""Independent safe-formula evaluation for proposed neural hypotheses."""
from __future__ import annotations

import json

from genesis.hypothesis_check import evaluate_hypothesis, hypothesis_coverage
from genesis.neural_adaptation import (
    parse_neural_proposal, parse_neural_hypothesis,
)


def run():
    cases = (
        ("b0 ^ b1 ^ b2", lambda b: b[0] ^ b[1] ^ b[2]),
        ("b0 ^ b1 ^ b2 ^ b3", lambda b: b[0] ^ b[1] ^ b[2] ^ b[3]),
        ("b0 & b2", lambda b: b[0] & b[2]),
        ("b0 + b1 + b2 + b3 >= 3", lambda b: int(sum(b) >= 3)),
        ("b0 + b1 + b2 + b3 == 2", lambda b: int(sum(b) == 2)),
        ("not b0 or b1", lambda b: int((not b[0]) or b[1])),
        ("(b0 and b1) or (b2 and not b3)",
         lambda b: int((b[0] and b[1]) or (b[2] and not b[3]))),
    )
    all_inputs = [
        tuple((n >> i) & 1 for i in range(4)) for n in range(16)
    ]
    for expression, oracle in cases:
        for context in all_inputs:
            assert evaluate_hypothesis(expression, context) == oracle(context), (
                expression, context
            )
        result = hypothesis_coverage(expression, all_inputs, oracle)
        assert result == {"tested": 16, "valid": 16, "accuracy": 1.0}

    attacks = (
        "__import__('os').system('whoami')",
        "b0.__class__",
        "open('/etc/passwd').read()",
        "sum([b0,b1])",
        "b0 ** 100",
        "(lambda x: x)(b0)",
        "[b0 for x in (0,1)]",
        "b0 / b1",
        "0; 1",
        "b0" * 150,
        "b0 << b1",
    )
    for text in attacks:
        assert evaluate_hypothesis(text, (0, 1, 0, 1)) is None, text
        message = json.dumps({
            "answer": 0, "confidence": 0.9, "hypothesis": text,
        })
        assert parse_neural_proposal(message, 2) == (None, None)
        assert parse_neural_hypothesis(message) is None

    valid = json.dumps({
        "answer": 1, "confidence": 0.65,
        "hypothesis": "b0 ^ b1 ^ b2",
    })
    assert parse_neural_proposal(valid, 2) == (1, 0.65)
    assert parse_neural_hypothesis(valid) == "b0 ^ b1 ^ b2"
    assert parse_neural_hypothesis('{"answer":1,"confidence":0.7}') is None
    assert parse_neural_proposal(
        '{"answer":0,"confidence":0.8,"tools":["run"]}', 2
    ) == (None, None)
    print("NEURAL_HYPOTHESIS_CHECK=PASS")


if __name__ == "__main__":
    run()
