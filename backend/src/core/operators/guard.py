"""Generic guard operators: identity, permission, ownership, state, uniqueness.

All guards are business-agnostic. They read only the pipeline context, the
declarative node params and the generic entity store.
"""
from __future__ import annotations

import time
from typing import Any

from src.core.entity import entity_store
from src.core.operators.sdk import operator


def _identity(context: dict[str, Any]) -> tuple[str, str]:
    uid = str(context.get("user_id") or "").strip()
    role = str(context.get("user_role") or "GUEST").upper()
    return uid, role


@operator("guard.authn", category="GUARD", description="Require an authenticated maker identity")
def authn(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid, role = _identity(context)
    if not uid and context.get("token"):
        from src.core.security import verify_session_token

        payload = verify_session_token(str(context["token"]))
        if payload:
            uid = str(payload.get("uid") or "")
            role = str(payload.get("role") or "MAKER").upper()
            context["user_id"] = uid
            context["user_role"] = role
    if not uid and params.get("required", True):
        raise PermissionError(params.get("message") or "该操作需要登录，请先登录创客账号")
    return {"authenticated": bool(uid), "user_id": uid, "user_role": role}


@operator("guard.permission", category="GUARD", description="Require a declarative RBAC permission")
def permission(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    _uid, role = _identity(context)
    required = str(params.get("permission") or args.get("permission") or "").strip()
    if not required:
        return {"allowed": True}
    from src.core.rbac import has_permission

    if not has_permission(role, required):
        raise PermissionError(params.get("message") or f"权限不足：缺少所需权限 '{required}'")
    return {"allowed": True, "permission": required}


@operator("guard.role", category="GUARD", description="Require one of a declarative role set")
def role_guard(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    _uid, role = _identity(context)
    roles = {str(r).upper() for r in (params.get("roles") or args.get("roles") or [])}
    if roles and role not in roles:
        raise PermissionError(params.get("message") or "角色权限不足")
    return {"allowed": True, "user_role": role}


@operator("guard.owner", category="GUARD", description="Require caller ownership or ADMIN role")
def owner(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid, role = _identity(context)
    owner_id = args.get("owner_id", params.get("owner_id"))
    if role == "ADMIN" or params.get("allow_admin", True):
        if role == "ADMIN":
            return {"allowed": True, "is_owner": True, "is_admin": True}
    if not uid:
        raise PermissionError("该操作需要登录，请先登录创客账号")
    if str(owner_id or "") != uid:
        raise PermissionError(params.get("message") or "权限拒绝：您无权修改或操作非本人拥有的资产")
    return {"allowed": True, "is_owner": True, "is_admin": False}


@operator("guard.state", category="GUARD", description="Require entity state to be in an allowed set")
def state_guard(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    current = args.get("current", params.get("current"))
    allowed = params.get("allowed") or args.get("allowed") or []
    if allowed and str(current) not in {str(v) for v in allowed}:
        raise ValueError(params.get("message") or f"当前状态 '{current}' 不允许执行该操作")
    return {"allowed": True, "current": current}


@operator("guard.unique", category="GUARD", description="Require no existing entity matches the filters")
def unique(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entity = str(params.get("entity") or "")
    filters = dict(params.get("filters") or {})
    filters.update({k: v for k, v in args.items() if v is not None})
    if not entity:
        raise ValueError("guard.unique requires 'entity'")
    if entity_store.exists(entity, {"filters": filters}):
        raise ValueError(params.get("message") or "记录已存在，请勿重复提交")
    return {"unique": True}


def _record_blocked_receipt(
    params: dict[str, Any],
    args: dict[str, Any],
    context: dict[str, Any],
    content: str,
    hits: list[str],
) -> None:
    """Persist a BLOCKED moderation receipt in the maker's inbox (best effort)."""
    uid = str(context.get("user_id") or "")
    if not uid:
        return
    try:
        from src.core.entity import entity_store

        entity_store.spec("notification.item")
        entity_store.create(
            "notification.item",
            {
                "user_id": uid,
                "kind": "PUBLISH_MODERATION",
                "level": "ERROR",
                "title": str(args.get("title") or params.get("scene") or "内容发布审核"),
                "content": f"内容合规校验未通过：命中敏感词 {'、'.join(hits)}",
                "scene": str(params.get("scene") or ""),
                "target_type": str(args.get("target_type") or params.get("target_type") or ""),
                "target_id": str(args.get("target_id") or ""),
                "verdict": "BLOCKED",
                "hit_words": list(hits),
                "status": "UNREAD",
            },
        )
    except Exception:  # pragma: no cover - receipts are best effort
        return


_IDEMPOTENCY: dict[str, float] = {}


@operator("guard.idempotency", category="GUARD", description="Reject duplicate submissions within a TTL window")
def idempotency(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    key = str(params.get("key") or args.get("key") or "").strip()
    if not key:
        return {"deduplicated": False}
    ttl = float(params.get("ttl_seconds", 300))
    now = time.time()
    expired = [k for k, ts in _IDEMPOTENCY.items() if now - ts > ttl]
    for k in expired:
        _IDEMPOTENCY.pop(k, None)
    if key in _IDEMPOTENCY:
        raise ValueError(params.get("message") or "请求重复，请勿重复提交")
    _IDEMPOTENCY[key] = now
    return {"deduplicated": True, "key": key}


@operator("guard.moderation", category="GUARD", description="Run the unified content safety gate over declared fields")
async def moderation(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Two-tier content gate (local NLP first, external scan when uncertain).

    The operator is business-agnostic: the scenario declares which fields carry
    user-generated text. Blocked content raises a ValueError so the gateway
    returns a 400 without persisting anything.
    """
    fields = params.get("fields") or ["content"]
    content = " ".join(str(args.get(field) or "") for field in fields).strip()
    if not content:
        return {"passed": True, "moderation": {"verdict": "CONFIRMED_SAFE", "empty": True}}
    blocklist = [str(word) for word in (params.get("blocklist") or []) if str(word)]
    hits = [word for word in blocklist if word in content]
    if hits:
        _record_blocked_receipt(params, args, context, content, hits)
        raise ValueError(f"内容合规校验未通过（敏感词）：{'、'.join(hits)}")
    from src.infrastructure.external_gateway.content_moderation_gateway import prescreen_and_record

    result = await prescreen_and_record(
        content,
        field_name=str(params.get("field_name") or "content"),
        user_id=str(context.get("user_id") or ""),
        scene=str(params.get("scene") or args.get("scene") or ""),
        title=str(args.get("title") or params.get("title") or ""),
        target_type=str(args.get("target_type") or params.get("target_type") or ""),
        target_id=str(args.get("target_id") or params.get("target_id") or ""),
    )
    if not result.get("passed", True):
        hits = (result.get("nlp") or {}).get("hit_sensitive") or []
        suffix = f"：{'、'.join(str(h) for h in hits)}" if hits else ""
        raise ValueError(f"内容合规校验未通过（敏感词）{suffix}")
    return {"passed": True, "moderation": result}
