"""Generic CRUD operators over the declarative entity store.

The operator code never mentions a business domain. The entity type is supplied
by the scenario node params (``entity: forum.thread``); the store resolves the
declarative spec registered by the owning domain.
"""
from __future__ import annotations

from typing import Any

from src.core.entity import entity_store
from src.core.operators.sdk import operator


def _entity(params: dict[str, Any], args: dict[str, Any] | None = None) -> str:
    """Resolve the entity name from static params or a mapped argument.

    Static params are preferred; a scenario may also map a computed entity name
    (``entity: $nodes.plan.entity``) so one operator can serve polymorphic
    targets without importing any domain.
    """
    name = str(params.get("entity") or (args or {}).get("entity") or "").strip()
    if not name:
        raise ValueError("Entity operator requires a 'entity' param")
    return name


def _payload(args: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    key = str(params.get("payload_key") or "data")
    value = args.get(key)
    if isinstance(value, dict):
        payload = dict(value)
        for extra in params.get("payload_fields") or []:
            if extra in args:
                payload[extra] = args[extra]
        return payload
    excluded = {"params", "args", "_node", "entity"}
    return {k: v for k, v in args.items() if k not in excluded and v is not None}


def _compensate_create(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Saga compensator: delete the entity document created by this node."""
    entity = str(params.get("entity") or "")
    if not entity:
        return {"compensated": False, "reason": "no entity"}
    doc = args.get("entity") or {}
    key = args.get("id") or args.get("key")
    payload = dict(doc) if isinstance(doc, dict) else {}
    if key is not None:
        payload["key"] = key
    if not payload:
        return {"compensated": False, "reason": "no created document"}
    deleted = entity_store.delete(entity, payload)
    return {"compensated": bool(deleted), "id": key, "entity": entity}


@operator(
    "entity.create",
    category="PERSISTENCE",
    description="Create one entity document",
    compensator=_compensate_create,
)
def create(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    doc = entity_store.create(entity, _payload(args, params))
    return {"entity": doc, "id": doc.get("id"), "created": True}


@operator("entity.update", category="PERSISTENCE", description="Replace one entity document")
def update(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    doc = entity_store.update(entity, _payload(args, params), partial=False)
    return {"entity": doc, "id": doc.get("id"), "updated": True}


@operator("entity.patch", category="PERSISTENCE", description="Patch selected fields of one entity document")
def patch(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    doc = entity_store.update(entity, _payload(args, params), partial=True)
    return {"entity": doc, "id": doc.get("id"), "updated": True}


@operator("entity.delete", category="PERSISTENCE", description="Delete one entity document")
def delete(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    key = args.get("key")
    if key is None and len(entity_store.spec(entity).key_fields) == 1:
        key = args.get(entity_store.spec(entity).key_fields[0])
    payload = dict(args)
    if key is not None:
        payload["key"] = key
    deleted = entity_store.delete(entity, payload)
    return {"deleted": deleted, "key": key}


@operator("entity.upsert", category="PERSISTENCE", description="Create or replace one entity document")
def upsert(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    payload = _payload(args, params)
    spec = entity_store.spec(entity)
    key = spec.key_of(payload)
    empty = "::".join([""] * len(spec.key_fields))
    if key and key != empty and entity_store.get(entity, payload):
        doc = entity_store.update(entity, payload, partial=False)
        return {"entity": doc, "id": doc.get("id"), "updated": True, "created": False}
    doc = entity_store.create(entity, payload)
    return {"entity": doc, "id": doc.get("id"), "created": True, "updated": False}


@operator("entity.get", category="QUERY", description="Read one entity document")
def get(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    doc = entity_store.get(entity, dict(args))
    if doc is None and params.get("required", True):
        raise KeyError(params.get("message") or f"{entity} 不存在")
    return {"entity": doc, "found": doc is not None, "id": (doc or {}).get("id")}


@operator("entity.list", category="QUERY", description="List entity documents with generic filter/sort")
def list_entities(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    query = dict(params.get("query") or {})
    for key in ("filters", "order", "limit", "offset", "search"):
        if key in args and args[key] is not None:
            query[key] = args[key]
    merged_filters = dict(query.get("filters") or {})
    for field_name, value in (params.get("filters") or {}).items():
        merged_filters.setdefault(field_name, value)
    query["filters"] = merged_filters
    items, total = entity_store.list(entity, query)
    return {"items": items, "total": total, "count": len(items)}


@operator("entity.count", category="QUERY", description="Count entity documents matching filters")
def count(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    filters = dict(params.get("filters") or {})
    filters.update({k: v for k, v in (args.get("filters") or {}).items()})
    total = entity_store.count(entity, {"filters": filters})
    return {"total": total, "count": total}


@operator("entity.exists", category="QUERY", description="Check whether any entity matches the filters")
def exists(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    filters = dict(params.get("filters") or {})
    filters.update({k: v for k, v in (args.get("filters") or {}).items()})
    found = entity_store.exists(entity, {"filters": filters})
    return {"exists": found}


@operator("entity.create_many", category="PERSISTENCE", description="Create several entity documents")
def create_many(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = _entity(params, args)
    items = args.get("items") or []
    created = [entity_store.create(entity, dict(item)) for item in items]
    return {"items": created, "created": len(created)}
