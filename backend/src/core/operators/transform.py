"""Generic, side-effect free transformation operators."""
from __future__ import annotations

import re
import string
from typing import Any

from src.core.microkernel.expr import evaluate
from src.core.operators.sdk import operator


def _get_path(data: Any, path: str) -> Any:
    current = data
    for part in str(path).split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


@operator("transform.pick", category="TRANSFORM", description="Project selected fields from a mapping")
def pick(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    source = args.get("source") if "source" in args else args
    keys = params.get("keys") or list(source.keys())
    return {key: source.get(key) for key in keys}


@operator("transform.merge", category="TRANSFORM", description="Merge a list of mappings in order")
def merge(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in params.get("items") or args.get("items") or []:
        if isinstance(item, dict):
            merged.update(item)
    return merged


@operator("transform.template", category="TRANSFORM", description="Render a {placeholder} template")
def template(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    raw = str(params.get("template") or "")
    values = {**context, **args}

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return ""

    rendered = string.Formatter().vformat(raw, (), _Safe(values))
    key = str(params.get("output_key") or "text")
    return {key: rendered}


@operator("transform.normalize", category="TRANSFORM", description="Trim and normalize strings and string lists")
def normalize(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in args.items():
        if isinstance(value, str):
            result[key] = re.sub(r"[ \t]+", " ", value.strip())
        elif isinstance(value, list):
            result[key] = [v.strip() if isinstance(v, str) else v for v in value]
        else:
            result[key] = value
    return result


@operator("transform.derive", category="TRANSFORM", description="Compute one value from a safe expression")
def derive(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    scope = {"args": args, "context": context, "inputs": context.get("inputs", {})}
    value = evaluate(str(params.get("expr") or ""), scope)
    return {str(params.get("output_key") or "value"): value}


@operator("transform.coerce", category="TRANSFORM", description="Coerce selected fields to declared primitive types")
def coerce(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    result = dict(args)
    for field_name, target in (params.get("types") or {}).items():
        value = result.get(field_name)
        if value is None:
            continue
        if target in ("int", "integer"):
            result[field_name] = int(value)
        elif target in ("float", "number"):
            result[field_name] = float(value)
        elif target in ("str", "string"):
            result[field_name] = str(value)
        elif target in ("bool", "boolean"):
            result[field_name] = bool(value)
    return result


@operator("transform.wrap", category="TRANSFORM", description="Wrap the mapped arguments under one output key")
def wrap(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {str(params.get("output_key") or "data"): args}


@operator("transform.flatten", category="TRANSFORM", description="Flatten a nested list one level")
def flatten(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = args.get("items") or []
    flat = [item for group in items for item in (group if isinstance(group, list) else [group])]
    return {str(params.get("output_key") or "items"): flat}
