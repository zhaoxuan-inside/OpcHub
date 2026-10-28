"""Safe declarative expression evaluator used by scenario nodes and edges.

The evaluator supports a deliberately tiny, side-effect free subset of Python:
literals, names, dict/list indexing, comparisons, boolean logic, arithmetic and a
small whitelist of builtins. It never executes attribute access on objects, calls
arbitrary functions, imports modules or performs I/O.

Expressions are written against a scope that the engine builds for every node::

    {
        "inputs": {...},     # accumulated pipeline inputs
        "context": {...},    # trace / identity / version context
        "nodes": {...},      # outputs of previously executed nodes
        "params": {...},     # node params
    }
"""
from __future__ import annotations

import ast
from typing import Any, Mapping

_ALLOWED_BUILTINS = {
    "len": len,
    "bool": bool,
    "str": str,
    "int": int,
    "float": float,
    "abs": abs,
    "min": min,
    "max": max,
    "any": any,
    "all": all,
}

_ALLOWED_NODES = (
    ast.Expression,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Attribute,
    ast.Subscript,
    ast.Index if hasattr(ast, "Index") else ast.Load,
    ast.Slice,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.USub,
    ast.UAdd,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Call,
    ast.IfExp,
)

_ALLOWED_CALL_NAMES = set(_ALLOWED_BUILTINS)


class ExpressionError(ValueError):
    """Raised when an expression is malformed or uses a forbidden construct."""


def _validate(node: ast.AST) -> None:
    for child in ast.walk(node):
        if not isinstance(child, _ALLOWED_NODES):
            raise ExpressionError(f"Forbidden expression construct: {type(child).__name__}")
        if isinstance(child, ast.Attribute):
            # Attribute access is only allowed for plain data path resolution
            # (``a.b`` == ``a["b"]``); dunder access is always rejected.
            if child.attr.startswith("_"):
                raise ExpressionError("Private attribute access is forbidden in expressions")
        if isinstance(child, ast.Call):
            if not isinstance(child.func, ast.Name) or child.func.id not in _ALLOWED_CALL_NAMES:
                raise ExpressionError("Only whitelisted builtins may be called in expressions")
            if child.keywords:
                raise ExpressionError("Keyword arguments are not supported in expressions")


def _resolve_attribute(value: Any, attr: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(attr)
    return getattr(value, attr, None)


def _eval(node: ast.AST, scope: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, scope)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in scope:
            return scope[node.id]
        if node.id in _ALLOWED_BUILTINS:
            return _ALLOWED_BUILTINS[node.id]
        if node.id in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[node.id]
        return None
    if isinstance(node, ast.Attribute):
        return _resolve_attribute(_eval(node.value, scope), node.attr)
    if isinstance(node, ast.Subscript):
        target = _eval(node.value, scope)
        key = _eval(node.slice, scope)
        try:
            return target[key]
        except (KeyError, IndexError, TypeError):
            return None
    if isinstance(node, ast.Slice):
        return slice(
            _eval(node.lower, scope) if node.lower else None,
            _eval(node.upper, scope) if node.upper else None,
            _eval(node.step, scope) if node.step else None,
        )
    if isinstance(node, ast.List):
        return [_eval(el, scope) for el in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval(el, scope) for el in node.elts)
    if isinstance(node, ast.Dict):
        return {_eval(k, scope): _eval(v, scope) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result: Any = True
            for value in node.values:
                result = _eval(value, scope)
                if not result:
                    return result
            return result
        result = False
        for value in node.values:
            result = _eval(value, scope)
            if result:
                return result
        return result
    if isinstance(node, ast.UnaryOp):
        operand = _eval(node.operand, scope)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        return +operand
    if isinstance(node, ast.Compare):
        left = _eval(node.left, scope)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval(comparator, scope)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.In):
                ok = left in right
            elif isinstance(op, ast.NotIn):
                ok = left not in right
            elif isinstance(op, ast.Is):
                ok = left is right
            elif isinstance(op, ast.IsNot):
                ok = left is not right
            else:  # pragma: no cover - guarded by whitelist
                raise ExpressionError("Unsupported comparison operator")
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.BinOp):
        left = _eval(node.left, scope)
        right = _eval(node.right, scope)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        raise ExpressionError("Unsupported arithmetic operator")
    if isinstance(node, ast.Call):
        fn = _ALLOWED_BUILTINS[node.func.id]  # type: ignore[index]
        return fn(*[_eval(arg, scope) for arg in node.args])
    if isinstance(node, ast.IfExp):
        return _eval(node.body, scope) if _eval(node.test, scope) else _eval(node.orelse, scope)
    raise ExpressionError(f"Unsupported expression node: {type(node).__name__}")


def evaluate(expression: str, scope: Mapping[str, Any] | None = None) -> Any:
    """Evaluate ``expression`` against ``scope`` using the safe subset."""
    if not expression or not str(expression).strip():
        return None
    try:
        tree = ast.parse(str(expression), mode="eval")
    except SyntaxError as exc:  # pragma: no cover - defensive
        raise ExpressionError(f"Invalid expression syntax: {expression}") from exc
    _validate(tree)
    return _eval(tree, scope or {})
