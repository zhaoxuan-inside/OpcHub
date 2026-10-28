"""Generic validation operators.

Validation is fully declarative: field rules come from scenario node params, so
no domain import is required and the same operator powers every business flow.
"""
from __future__ import annotations

import re
from typing import Any

from src.core.microkernel.expr import evaluate
from src.core.operators.sdk import operator

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "str": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "bool": lambda v: isinstance(v, bool),
    "list": lambda v: isinstance(v, (list, tuple)),
    "array": lambda v: isinstance(v, (list, tuple)),
    "object": lambda v: isinstance(v, dict),
    "dict": lambda v: isinstance(v, dict),
    "any": lambda v: True,
}


def _check_rule(field: str, value: Any, rule: dict[str, Any]) -> None:
    expected = rule.get("type")
    if expected and not _TYPE_CHECKS.get(str(expected), lambda v: True)(value):
        raise ValueError(f"字段 '{field}' 类型应为 {expected}")
    if isinstance(value, str):
        if rule.get("min_length") is not None and len(value) < int(rule["min_length"]):
            raise ValueError(rule.get("message") or f"字段 '{field}' 长度不能少于 {rule['min_length']} 个字符")
        if rule.get("max_length") is not None and len(value) > int(rule["max_length"]):
            raise ValueError(rule.get("message") or f"字段 '{field}' 长度不能超过 {rule['max_length']} 个字符")
        if rule.get("pattern") and not re.search(str(rule["pattern"]), value):
            raise ValueError(rule.get("message") or f"字段 '{field}' 格式不合法")
        if rule.get("strip", True):
            value = value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if rule.get("min") is not None and value < float(rule["min"]):
            raise ValueError(rule.get("message") or f"字段 '{field}' 不能小于 {rule['min']}")
        if rule.get("max") is not None and value > float(rule["max"]):
            raise ValueError(rule.get("message") or f"字段 '{field}' 不能大于 {rule['max']}")
    if rule.get("enum") and value not in rule["enum"]:
        raise ValueError(rule.get("message") or f"字段 '{field}' 取值不在允许范围内")


@operator("validate.fields", category="VALIDATE", description="Validate mapped fields against declarative rules")
def fields(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = dict(params.get("fields") or {})
    for field_name, rule in rules.items():
        value = args.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            if rule.get("required", False):
                raise ValueError(rule.get("message") or f"字段 '{field_name}' 为必填项")
            continue
        _check_rule(field_name, value, rule)
    return {"valid": True}


@operator("validate.expression", category="VALIDATE", description="Assert declarative boolean expressions")
def expressions(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    scope = {"args": args, "params": params, "context": context, "inputs": context.get("inputs", {})}
    for condition in params.get("conditions") or []:
        expression = condition.get("expr") if isinstance(condition, dict) else str(condition)
        message = condition.get("message") if isinstance(condition, dict) else ""
        if not evaluate(expression, scope):
            raise ValueError(message or f"业务校验未通过: {expression}")
    return {"valid": True}


@operator("validate.enum", category="VALIDATE", description="Validate a value against an enumeration")
def enum(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    field_name = str(params.get("field") or "value")
    value = args.get(field_name)
    allowed = [str(v) for v in (params.get("allowed") or [])]
    if allowed and str(value) not in allowed:
        raise ValueError(params.get("message") or f"字段 '{field_name}' 取值不在允许范围内")
    return {"valid": True, field_name: value}
