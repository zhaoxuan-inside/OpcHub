"""Single-responsibility pure function operators for the message box domain.

Only calculations / normalisation / assembly live here. Guards, validation,
persistence, notifications, metrics and audit are supplied by the generic
operator kernel (``src.core.operators``); every business flow is declared in
``config/scenarios/notifications.yaml``.

Rules honoured by this module: no I/O, no orchestration, no call to another
operator, no cross-domain import.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.operators.sdk import operator
from src.domains.notifications.models import (
    KIND_PUBLISH_MODERATION,
    STATUS_READ,
    STATUS_UNREAD,
    VERDICT_BLOCKED,
    VERDICT_PASSED_DEGRADED,
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_TITLE_LENGTH = 160
MAX_CONTENT_LENGTH = 2000


def _text(value: Any) -> str:
    return str(value or "").strip()


def _read_map(value: Any) -> dict[str, str]:
    return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def _is_read(doc: dict[str, Any], read_map: dict[str, str]) -> bool:
    if _text(doc.get("status")).upper() == STATUS_READ:
        return True
    return _text(doc.get("id")) in read_map


def _decorate(doc: dict[str, Any], read_map: dict[str, str]) -> dict[str, Any]:
    """Project one stored receipt with its *current* read state."""
    item = dict(doc)
    notification_id = _text(item.get("id"))
    is_read = _is_read(item, read_map)
    item["status"] = STATUS_READ if is_read else STATUS_UNREAD
    item["read_at"] = (read_map.get(notification_id) or item.get("read_at")) if is_read else None
    # ``notify.emit`` writes ``body`` while moderation receipts write ``content``.
    item["content"] = _text(item.get("content")) or _text(item.get("body"))
    item["body"] = _text(item.get("body")) or item["content"]
    item["hit_words"] = sorted({_text(word) for word in (item.get("hit_words") or []) if _text(word)})
    return item


@operator(
    "calc.notification.query",
    category="CALC",
    description="Normalise message-box list parameters (status filter + window)",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    status = _text(args.get("status") or params.get("status")).upper()
    if status not in (STATUS_READ, STATUS_UNREAD):
        status = ""
    limit = max(1, min(MAX_LIMIT, int(args.get("limit") or DEFAULT_LIMIT)))
    offset = max(0, int(args.get("offset") or 0))
    return {"status": status or None, "limit": limit, "offset": offset}


@operator(
    "assemble.notification.list",
    category="ASSEMBLE",
    description="Join stored receipts with the caller's read state and page the inbox",
)
def list_response(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = [_decorate(item, _read_map(args.get("read_map"))) for item in (args.get("items") or []) if isinstance(item, dict)]
    unread = sum(1 for item in items if item["status"] == STATUS_UNREAD)

    status = _text(args.get("status") or params.get("status")).upper()
    visible = [item for item in items if item["status"] == status] if status in (STATUS_READ, STATUS_UNREAD) else items
    total = len(visible)

    limit = max(1, min(MAX_LIMIT, int(args.get("limit") or params.get("limit") or DEFAULT_LIMIT)))
    offset = max(0, int(args.get("offset") or 0))
    page = visible[offset : offset + limit]

    response = {
        "items": page,
        "total": total,
        "unread": unread,
        "status": status or None,
    }
    return {**response, "response": response}


@operator(
    "calc.notification.unread",
    category="CALC",
    description="Count unread receipts for one recipient from receipts + read state",
)
def unread_count(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    read_map = _read_map(args.get("read_map"))
    items = [item for item in (args.get("items") or []) if isinstance(item, dict)]
    unread = sum(1 for item in items if not _is_read(item, read_map))
    return {"unread": unread}


@operator(
    "calc.notification.read_plan",
    category="CALC",
    description="Plan the read-state merge for selected ids or for the whole inbox",
)
def read_plan(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    user_id = _text(context.get("user_id") or args.get("user_id"))
    if not user_id:
        raise ValueError("该操作需要登录，请先登录创客账号")

    items = [item for item in (args.get("items") or []) if isinstance(item, dict)]
    read_map = _read_map(args.get("read_map"))
    scope = _text(params.get("scope") or args.get("scope") or "ids").lower()

    wanted: set[str] | None = None
    if scope != "all":
        raw_ids = args.get("ids")
        if raw_ids is None:
            raw_ids = args.get("id")
        if isinstance(raw_ids, str):
            raw_ids = [raw_ids]
        wanted = {_text(value) for value in (raw_ids or []) if _text(value)}
        if not wanted:
            return {
                "record": {"user_id": user_id, "read_map": read_map},
                "updated": 0,
                "unread": sum(1 for item in items if not _is_read(item, read_map)),
                "message": "未指定要标记的消息",
            }

    now = datetime.now(timezone.utc).isoformat()
    merged = dict(read_map)
    updated = 0
    for item in items:
        notification_id = _text(item.get("id"))
        if not notification_id or notification_id in merged:
            continue
        if wanted is not None and notification_id not in wanted:
            continue
        if _text(item.get("status")).upper() == STATUS_READ:
            continue
        merged[notification_id] = now
        updated += 1

    unread = sum(1 for item in items if not _is_read(item, merged))
    return {
        "record": {"user_id": user_id, "read_map": merged},
        "updated": updated,
        "unread": unread,
        "message": f"已标记 {updated} 条消息为已读",
    }


@operator(
    "assemble.notification.action",
    category="ASSEMBLE",
    description="Project the message-box action envelope (updated / unread / message)",
)
def action_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    response = {
        "updated": int(args.get("updated") or 0),
        "unread": int(args.get("unread") or 0),
        "message": _text(args.get("message") or params.get("message")),
    }
    return {**response, "response": response}


def _build_doc(user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Pure payload shaping shared by the create and moderation assemblers."""
    content = _text(args.get("content")) or _text(args.get("body"))
    body = _text(args.get("body")) or content
    meta = args.get("meta") if isinstance(args.get("meta"), dict) else {}
    return {
        "user_id": user_id,
        "kind": _text(args.get("kind")) or KIND_PUBLISH_MODERATION,
        "level": (_text(args.get("level")) or "INFO").upper(),
        "title": _text(args.get("title"))[:MAX_TITLE_LENGTH] or "平台消息",
        "content": content[:MAX_CONTENT_LENGTH],
        "body": body[:MAX_CONTENT_LENGTH],
        "scene": _text(args.get("scene")),
        "target_type": _text(args.get("target_type")).upper(),
        "target_id": _text(args.get("target_id")),
        "verdict": _text(args.get("verdict")).upper(),
        "hit_words": sorted({_text(word) for word in (args.get("hit_words") or []) if _text(word)}),
        "status": STATUS_UNREAD,
        "read_at": None,
        "link": args.get("link"),
        "meta": dict(meta),
    }


@operator(
    "calc.notification.normalize",
    category="CALC",
    description="Normalise a notification payload and bind the recipient",
)
def normalize(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    user_id = _text(args.get("user_id") or args.get("recipient_id") or context.get("user_id"))
    if not user_id:
        raise ValueError("user_id is required for a notification")
    return _build_doc(user_id, args)


@operator(
    "assemble.notification.moderation_receipt",
    category="ASSEMBLE",
    description="Assemble the moderation receipt copy for one publish attempt",
)
def moderation_receipt(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    user_id = _text(args.get("user_id") or context.get("user_id"))
    if not user_id:
        return {"skip": True}

    verdict = _text(args.get("verdict")).upper()
    scene_label = _text(args.get("scene")) or "内容"
    safe_title = _text(args.get("title"))[:80] or "未命名内容"
    hits = sorted({_text(word) for word in (args.get("hit_words") or []) if _text(word)})

    if verdict == VERDICT_BLOCKED:
        level = "WARNING"
        heading = f"「{scene_label}」敏感词校验未通过"
        hit_text = "、".join(hits) if hits else (_text(args.get("reason")) or "命中平台敏感词规则")
        body = (
            f"《{safe_title}》未通过平台敏感词校验，发布已被阻止。"
            f"命中内容：{hit_text}。请修改后重新发布。"
        )
    elif verdict == VERDICT_PASSED_DEGRADED:
        level = "INFO"
        heading = f"「{scene_label}」敏感词校验已放行"
        body = (
            f"《{safe_title}》的外部审核服务暂时不可用，平台已先行放行。"
            f"服务恢复后平台会继续复核，如发现问题将通过消息箱通知你。"
        )
    else:
        level = "SUCCESS"
        heading = f"「{scene_label}」敏感词校验通过"
        body = f"《{safe_title}》已通过平台敏感词校验，内容已进入发布流程。"

    return _build_doc(
        user_id,
        {
            "title": heading,
            "content": body,
            "level": level,
            "scene": scene_label,
            "target_type": args.get("target_type"),
            "target_id": args.get("target_id"),
            "verdict": verdict,
            "hit_words": hits,
        },
    )
