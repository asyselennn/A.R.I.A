import ast
import operator
import re
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_ -]?key|password|passwd|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
]


def looks_sensitive(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_calculate(expression: str) -> float | int:
    expression = expression.strip()
    if len(expression) > 200:
        raise ValueError("Expression is too long.")

    tree = ast.parse(expression, mode="eval")

    def evaluate(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if abs(node.value) > 1_000_000_000:
                raise ValueError("Number is too large.")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent is too large.")
            result = _ALLOWED_BINOPS[type(node.op)](left, right)
            if abs(result) > 1e15:
                raise ValueError("Result is too large.")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
            return _ALLOWED_UNARY[type(node.op)](evaluate(node.operand))
        raise ValueError("Only basic arithmetic is allowed.")

    return evaluate(tree.body)
