"""Strict, non-executing evaluator for proposed binary explanatory rules.

An LLM may *describe* an explanation as a short expression, but only this
restricted AST interpreter may check it. No eval/exec, names beyond b0..b3,
attribute access, calls, indexing, loops, or tool invocation are allowed.
"""
from __future__ import annotations

import ast
from typing import Any


_ALLOWED_VARIABLES = ("b0", "b1", "b2", "b3")
MAX_EXPRESSION_LENGTH = 120
MAX_AST_NODES = 48
MAX_DEPTH = 12


def evaluate_hypothesis(expression: Any,
                        features: tuple[int, int, int, int] | list[int]) -> int | None:
    if not isinstance(expression, str) or not (
        1 <= len(expression) <= MAX_EXPRESSION_LENGTH
    ):
        return None
    if not isinstance(features, (tuple, list)) or len(features) != 4:
        return None
    if any(type(x) is not int or x not in (0, 1) for x in features):
        return None
    try:
        tree = ast.parse(expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
            return None
    except (SyntaxError, ValueError, RecursionError):
        return None
    values = dict(zip(_ALLOWED_VARIABLES, features))

    def compute(node, depth=0) -> int:
        if depth > MAX_DEPTH:
            raise ValueError("expression too deep")
        if isinstance(node, ast.Expression):
            return compute(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) is int:
            if 0 <= node.value <= 4:
                return node.value
            raise ValueError("constant not allowed")
        if isinstance(node, ast.Name) and node.id in values:
            return int(values[node.id])
        if isinstance(node, ast.UnaryOp):
            value = compute(node.operand, depth + 1)
            if isinstance(node.op, (ast.Invert, ast.Not)):
                if value not in (0, 1):
                    raise ValueError("not expects binary")
                return 1 - value
            raise ValueError("unary operator denied")
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            parts = [compute(v, depth + 1) for v in node.values]
            if isinstance(node.op, ast.And):
                return int(all(parts))
            return int(any(parts))
        if isinstance(node, ast.BinOp):
            left = compute(node.left, depth + 1)
            right = compute(node.right, depth + 1)
            if isinstance(node.op, ast.BitXor):
                out = left ^ right
            elif isinstance(node.op, ast.BitAnd):
                out = left & right
            elif isinstance(node.op, ast.BitOr):
                out = left | right
            elif isinstance(node.op, ast.Add):
                out = left + right
            elif isinstance(node.op, ast.Sub):
                out = left - right
            else:
                raise ValueError("operator denied")
            if not -16 <= out <= 16:
                raise ValueError("intermediate value too large")
            return out
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left = compute(node.left, depth + 1)
            right = compute(node.comparators[0], depth + 1)
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                return int(left == right)
            if isinstance(op, ast.NotEq):
                return int(left != right)
            if isinstance(op, ast.Gt):
                return int(left > right)
            if isinstance(op, ast.GtE):
                return int(left >= right)
            if isinstance(op, ast.Lt):
                return int(left < right)
            if isinstance(op, ast.LtE):
                return int(left <= right)
            raise ValueError("comparison denied")
        raise ValueError("unsupported AST node")

    try:
        answer = compute(tree)
    except (ValueError, TypeError, RecursionError, OverflowError):
        return None
    return answer if answer in (0, 1) else None


def hypothesis_coverage(expression: str, contexts: list[tuple[int, ...]],
                        oracle) -> dict[str, Any]:
    """Independent lab-only checker; never sends oracle truth to the model."""
    predicted = [evaluate_hypothesis(expression, context) for context in contexts]
    valid = [i for i, value in enumerate(predicted) if value is not None]
    return {
        "tested": len(contexts),
        "valid": len(valid),
        "accuracy": (
            sum(predicted[i] == oracle(contexts[i]) for i in valid) / len(valid)
            if valid else None
        ),
    }
