"""Response shaping operators.

These operators only project / merge already-computed pipeline data. They never
read storage or perform I/O.
"""
from __future__ import annotations

from typing import Any

from src.core.operators.sdk import operator


@operator("response.build", category="RESPONSE", description="Project the final response from pipeline data")
def build(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    source_key = str(params.get("source") or "entity")
    default = args.get(source_key) if isinstance(args.get(source_key), dict) else {}
    fields = params.get("fields") or []
    if not fields:
        return {"response": default}
    response = {field: default.get(field) for field in fields if field in default}
    for target, expression in (params.get("map") or {}).items():
        response[target] = _resolve(expression, args, default)
    return {"response": response}


@operator("response.merge", category="RESPONSE", description="Merge named pipeline results into one response object")
def merge(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for target, source_key in (params.get("map") or {}).items():
        value = args.get(source_key)
        if isinstance(value, dict) and params.get("flatten_entity", True):
            result[target] = value.get("entity", value)
        else:
            result[target] = value
    result.update({k: v for k, v in args.items() if k not in (params.get("map") or {})})
    return {"response": result}


def _resolve(expression: Any, args: dict[str, Any], default: dict[str, Any]) -> Any:
    if not isinstance(expression, str):
        return expression
    if expression.startswith("$args."):
        return args.get(expression[len("$args.") :])
    if expression.startswith("$entity."):
        return default.get(expression[len("$entity.") :])
    return expression
