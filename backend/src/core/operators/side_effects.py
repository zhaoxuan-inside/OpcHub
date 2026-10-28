"""Generic side-effect operators: notifications, audit, metrics, rendering.

These operators are infrastructure-facing and contain no business semantics.
Recipients, metrics names and audit actions are supplied by scenario params.
"""
from __future__ import annotations

import string
import threading
from collections import Counter
from typing import Any

from src.core.entity import entity_store
from src.core.operators.sdk import operator


@operator("notify.emit", category="NOTIFY", description="Persist one notification for a recipient")
def emit(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = str(params.get("entity") or "notification.item")
    recipient = args.get("recipient_id") or args.get("user_id") or params.get("recipient_id")
    if not recipient:
        return {"skipped": True, "reason": "no recipient"}
    try:
        entity_store.spec(entity)
    except KeyError:
        return {"skipped": True, "reason": f"entity '{entity}' not registered"}
    doc = {
        "user_id": str(recipient),
        "kind": str(params.get("kind") or args.get("kind") or "SYSTEM"),
        "title": str(params.get("title") or args.get("title") or ""),
        "body": str(params.get("body") or args.get("body") or ""),
        "link": params.get("link") or args.get("link"),
        "status": "UNREAD",
        "meta": args.get("meta") or {},
    }
    created = entity_store.create(entity, doc)
    return {"notification": created, "id": created.get("id"), "emitted": True}


@operator("audit.write", category="AUDIT", description="Append one security audit record")
async def audit_write(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.audit import audit_service

    await audit_service.record(
        action=str(params.get("action") or args.get("action") or "scenario.action"),
        actor_id=str(context.get("user_id") or ""),
        actor_role=str(context.get("user_role") or "GUEST"),
        permission=str(params.get("permission") or ""),
        resource_type=str(params.get("resource_type") or ""),
        resource_id=str(args.get("resource_id") or params.get("resource_id") or ""),
        result=str(params.get("result") or "SUCCESS"),
        ip_address=str(context.get("client_ip") or ""),
        trace_id=str(context.get("trace_id") or ""),
        detail=dict(args.get("detail") or params.get("detail") or {}),
    )
    return {"audited": True}


_METRICS: Counter[str] = Counter()
_METRIC_LOCK = threading.Lock()


@operator("metric.incr", category="METRICS", description="Increment one in-process metric counter")
def metric_incr(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    name = str(params.get("metric") or args.get("metric") or "unnamed")
    amount = int(params.get("amount", args.get("amount", 1)) or 1)
    with _METRIC_LOCK:
        _METRICS[name] += amount
        value = _METRICS[name]
    return {"metric": name, "value": value, "recorded": True}


@operator("metric.snapshot", category="METRICS", description="Read all in-process metric counters")
def metric_snapshot(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    with _METRIC_LOCK:
        return {"metrics": dict(_METRICS)}


@operator("render.template", category="RENDER", description="Render a document from a {placeholder} template")
def render_template(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    raw = str(params.get("template") or "")
    values = {**context, **args}

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return ""

    rendered = string.Formatter().vformat(raw, (), _Safe(values))
    return {str(params.get("output_key") or "content"): rendered}
