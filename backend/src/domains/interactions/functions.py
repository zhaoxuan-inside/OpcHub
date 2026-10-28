"""Single-responsibility pure function operators for unified interactions.

Only calculations / normalisation / assembly live here. Storage is handled by
``entity.*`` operators, guards by ``guard.*``, validation by ``validate.*``.
There is no I/O, no orchestration and no cross-domain import in this module.

The scenario asset ``config/scenarios/interactions.yaml`` composes these
functions into the business flows (toggle / rate / comments / state / mine) and
performs the cross-domain counter write-back by feeding
``calc.interaction.target``'s ``{entity, key, patch}`` into ``entity.patch``.
"""
from __future__ import annotations

from typing import Any, Iterable

from src.core.operators.sdk import operator
from src.domains.interactions.models import INTERACTION_KINDS, TARGET_TYPES

COUNTER_FIELDS = (
    "like_count",
    "favorite_count",
    "love_count",
    "comment_count",
    "dislike_count",
    "rating_sum",
    "rating_count",
)

#: interaction kind -> counter field on ``interaction.stat``
KIND_FIELD = {
    "LIKE": "like_count",
    "FAVORITE": "favorite_count",
    "LOVE": "love_count",
    "DISLIKE": "dislike_count",
}

#: owning-domain entity name per target type (``None`` = not entity-migrated yet)
TARGET_ENTITIES = {
    "PRODUCT": "product.item",
    "POLICY": "policy.item",
    "DEMAND": "demand.item",
    "FORUM_THREAD": "forum.thread",
    "SOP_DOCUMENT": "sop.node",
    "SOP_FLOW": "sop.flow_template",
    "PERK": "perk.item",
}

#: stat counter -> legacy field on the owning entity, used to seed first reads
TARGET_SEED_FIELDS = {
    "PRODUCT": {
        "like_count": "upvote_count",
        "favorite_count": "favorite_count",
        "love_count": "love_count",
        "comment_count": "comment_count",
    },
    "POLICY": {
        "like_count": "like_count",
        "favorite_count": "favorite_count",
        "love_count": "love_count",
        "comment_count": "comment_count",
    },
    "DEMAND": {
        "like_count": "like_count",
        "favorite_count": "favorite_count",
        "love_count": "love_count",
        "comment_count": "comment_count",
    },
    "FORUM_THREAD": {
        "favorite_count": "bookmark_count",
        "love_count": "love_count",
        "comment_count": "comment_count",
    },
    # Legacy SOP "like" was the 喜欢 (LOVE) counter; praise_count is 点赞.
    "SOP_DOCUMENT": {
        "like_count": "praise_count",
        "favorite_count": "favorite_count",
        "love_count": "like_count",
        "comment_count": "comment_count",
    },
    "SOP_FLOW": {
        "like_count": "praise_count",
        "favorite_count": "favorite_count",
        "love_count": "like_count",
        "comment_count": "comment_count",
    },
    "PERK": {
        "like_count": "like_count",
        "favorite_count": "favorite_count",
        "love_count": "love_count",
        "comment_count": "comment_count",
    },
}

#: stat counter -> owning entity field written back after a mutation.
#: Forum upvote/comment counters belong to the forum vote ledger, so only the
#: unified 收藏/喜欢 counters are mirrored onto threads.
TARGET_PATCH_FIELDS = {
    "PRODUCT": dict(TARGET_SEED_FIELDS["PRODUCT"]),
    "POLICY": dict(TARGET_SEED_FIELDS["POLICY"]),
    "DEMAND": dict(TARGET_SEED_FIELDS["DEMAND"]),
    "FORUM_THREAD": {
        "favorite_count": "bookmark_count",
        "love_count": "love_count",
    },
    "SOP_DOCUMENT": dict(TARGET_SEED_FIELDS["SOP_DOCUMENT"]),
    "SOP_FLOW": dict(TARGET_SEED_FIELDS["SOP_FLOW"]),
    "PERK": dict(TARGET_SEED_FIELDS["PERK"]),
}

KIND_LABEL = {"LIKE": "点赞", "FAVORITE": "收藏", "LOVE": "喜欢", "DISLIKE": "踩"}
TAB_MAP = {
    "PRODUCT": "product",
    "POLICY": "policy",
    "DEMAND": "demand",
    "FORUM_THREAD": "forum",
    "SOP_DOCUMENT": "sop",
    "SOP_FLOW": "sop",
    "PERK": "perk",
}


# ---------------------------------------------------------------------------
# Internal helpers (pure)
# ---------------------------------------------------------------------------
def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _target_type(value: Any) -> str:
    tt = _text(value).upper()
    if tt not in TARGET_TYPES:
        raise ValueError(f"Unsupported interaction target_type: {value}")
    return tt


def _target_id(value: Any) -> str:
    tid = _text(value)
    if not tid:
        raise ValueError("互动目标 target_id 不能为空")
    return tid


def _rows(value: Any) -> list[dict[str, Any]]:
    items = value if isinstance(value, (list, tuple)) else []
    return [dict(item) for item in items if isinstance(item, dict)]


def _counts(source: Any) -> dict[str, int]:
    raw = source if isinstance(source, dict) else {}
    return {field_name: max(0, _int(raw.get(field_name))) for field_name in COUNTER_FIELDS}


def _seed_counts(target_type: str, target: Any) -> dict[str, int]:
    counts = _counts(None)
    doc = target if isinstance(target, dict) else {}
    for stat_field, entity_field in (TARGET_SEED_FIELDS.get(target_type) or {}).items():
        counts[stat_field] = max(0, _int(doc.get(entity_field)))
    return counts


def _resolve_counts(source: Any, target_type: str, target: Any) -> dict[str, int]:
    """Stat document wins; otherwise seed from the owning entity's legacy fields."""
    if isinstance(source, dict) and source:
        return _counts(source)
    return _seed_counts(target_type, target)


def _target_title(target: Any, explicit: Any = None) -> str:
    title = _text(explicit)
    if title:
        return title
    doc = target if isinstance(target, dict) else {}
    for field_name in ("title", "name", "document_title", "content"):
        value = _text(doc.get(field_name))
        if value:
            return value
    return ""


def _rating_avg(counts: dict[str, int]) -> float:
    total = _int(counts.get("rating_sum"))
    count = _int(counts.get("rating_count"))
    if count <= 0:
        return 0.0
    return round(total / count, 1)


def _state_payload(
    target_type: str,
    target_id: str,
    counts: dict[str, int],
    records: Iterable[dict[str, Any]],
    comments: Iterable[dict[str, Any]],
    viewer_id: str,
    rating_score: int = 0,
) -> dict[str, Any]:
    """Assemble one InteractionState-shaped dict (no I/O)."""
    uid = _text(viewer_id)
    kinds = {
        _text(row.get("kind")).upper()
        for row in records
        if uid
        and _text(row.get("user_id")) == uid
        and _text(row.get("target_type")).upper() == target_type
        and _text(row.get("target_id")) == target_id
    }
    commented = any(
        uid
        and _text(comment.get("author_id")) == uid
        and _text(comment.get("target_type")).upper() == target_type
        and _text(comment.get("target_id")) == target_id
        for comment in comments
    )
    return {
        "target_type": target_type,
        "target_id": target_id,
        "like_count": counts["like_count"],
        "favorite_count": counts["favorite_count"],
        "love_count": counts["love_count"],
        "comment_count": counts["comment_count"],
        "dislike_count": counts["dislike_count"],
        "rating_avg": _rating_avg(counts),
        "rating_count": counts["rating_count"],
        "viewer": {
            "liked": "LIKE" in kinds,
            "favorited": "FAVORITE" in kinds,
            "loved": "LOVE" in kinds,
            "commented": commented,
            "disliked": "DISLIKE" in kinds,
            "rating": max(0, _int(rating_score)),
        },
    }


# ---------------------------------------------------------------------------
# CALC
# ---------------------------------------------------------------------------
@operator(
    "calc.interaction.toggle",
    category="CALC",
    description="Decide one LIKE/FAVORITE/LOVE/DISLIKE toggle and its counter delta",
)
def toggle(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    target_type = _target_type(args.get("target_type"))
    target_id = _target_id(args.get("target_id"))
    kind = _text(args.get("kind")).upper()
    if kind not in INTERACTION_KINDS:
        raise ValueError(f"Unsupported interaction kind: {args.get('kind')}")
    user_id = _text(args.get("user_id")) or _text(context.get("user_id"))
    if not user_id:
        raise PermissionError("请先登录创客账号后再进行互动")

    counts = _counts(args.get("counts"))
    existing = args.get("existing")
    active = not existing
    field_name = KIND_FIELD[kind]
    delta = 1 if active else -1
    counts[field_name] = max(0, counts[field_name] + delta)

    record = {
        "user_id": user_id,
        "target_type": target_type,
        "target_id": target_id,
        "kind": kind,
        "target_title": _target_title(args.get("target"), args.get("target_title"))[:255],
    }
    return {
        "target_type": target_type,
        "target_id": target_id,
        "kind": kind,
        "user_id": user_id,
        "active": active,
        "field": field_name,
        "delta": delta,
        "count": counts[field_name],
        "counts": counts,
        "record": record if active else None,
        "stat": {"target_type": target_type, "target_id": target_id, **counts},
    }


@operator(
    "calc.interaction.rating",
    category="CALC",
    description="Apply one 1-5 star rating to the aggregate counters (overwrite, never double count)",
)
def rating(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    target_type = _target_type(args.get("target_type"))
    target_id = _target_id(args.get("target_id"))
    user_id = _text(args.get("user_id")) or _text(context.get("user_id"))
    if not user_id:
        raise PermissionError("请先登录创客账号后再进行打分")

    try:
        score = int(args.get("score"))
    except (TypeError, ValueError) as exc:
        raise ValueError("打分范围必须为 1-5 分") from exc
    if score < 1 or score > 5:
        raise ValueError("打分范围必须为 1-5 分")

    counts = _counts(args.get("counts"))
    previous = _int(args.get("previous"))
    if previous:
        counts["rating_sum"] = max(0, counts["rating_sum"] - previous)
    else:
        counts["rating_count"] += 1
    counts["rating_sum"] += score

    return {
        "target_type": target_type,
        "target_id": target_id,
        "user_id": user_id,
        "score": score,
        "previous": previous,
        "counts": counts,
        "rating_avg": _rating_avg(counts),
        "rating_count": counts["rating_count"],
        "rating": {
            "user_id": user_id,
            "target_type": target_type,
            "target_id": target_id,
            "score": score,
        },
        "stat": {"target_type": target_type, "target_id": target_id, **counts},
    }


@operator(
    "calc.interaction.target",
    category="CALC",
    description="Map a target type to its owning entity, key and counter write-back patch",
)
def target(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    target_type = _target_type(args.get("target_type"))
    target_id = _target_id(args.get("target_id"))
    entity = TARGET_ENTITIES.get(target_type)
    target_doc = args.get("target") if isinstance(args.get("target"), dict) else None
    counts = _resolve_counts(args.get("counts"), target_type, target_doc)

    found = bool(target_doc)
    patch: dict[str, Any] | None = None
    field_map = TARGET_PATCH_FIELDS.get(target_type)
    if entity and found and field_map:
        patch = {"id": target_id}
        for stat_field, entity_field in field_map.items():
            patch[entity_field] = counts[stat_field]

    return {
        "target_type": target_type,
        "target_id": target_id,
        "entity": entity,
        "key": {"id": target_id},
        "key_fields": ["id"],
        "exists": bool(entity),
        "found": found,
        "field_map": field_map or {},
        "seed": _seed_counts(target_type, target_doc),
        "counts": counts,
        "patch": patch,
    }


@operator(
    "calc.interaction.state",
    category="CALC",
    description="Assemble interaction counters plus the viewer's own state for one target",
)
def state(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    target_type = _target_type(args.get("target_type"))
    target_id = _target_id(args.get("target_id"))
    counts = _resolve_counts(args.get("counts"), target_type, args.get("target"))
    viewer_id = _text(args.get("viewer_id")) or _text(context.get("user_id"))
    rating_doc = args.get("rating")
    rating_score = _int(rating_doc.get("score")) if isinstance(rating_doc, dict) else _int(rating_doc)
    return _state_payload(
        target_type,
        target_id,
        counts,
        _rows(args.get("records")),
        _rows(args.get("comments")),
        viewer_id,
        rating_score,
    )


@operator(
    "calc.interaction.comment",
    category="CALC",
    description="Normalise one public comment payload for persistence",
)
def comment(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    target_type = _target_type(args.get("target_type"))
    target_id = _target_id(args.get("target_id"))
    user_id = _text(args.get("author_id")) or _text(context.get("user_id"))
    if not user_id:
        raise PermissionError("请先登录创客账号后再发表评论")
    text = _text(args.get("content"))
    if not text:
        raise ValueError("评论内容不能为空")
    return {
        "target_type": target_type,
        "target_id": target_id,
        "author_id": user_id,
        "target_title": _target_title(args.get("target"), args.get("target_title"))[:255],
        "data": {
            "target_type": target_type,
            "target_id": target_id,
            "author_id": user_id,
            "author_name": (_text(args.get("author_name")) or _text(context.get("nickname")) or "创客")[:64],
            "content": text[:4000],
            "parent_id": args.get("parent_id") or None,
            "target_title": _target_title(args.get("target"), args.get("target_title"))[:255],
        },
    }


# ---------------------------------------------------------------------------
# ASSEMBLE
# ---------------------------------------------------------------------------
@operator(
    "assemble.interaction.batch",
    category="ASSEMBLE",
    description="Assemble viewer state for a batch of interaction targets",
)
def batch(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    viewer_id = _text(args.get("viewer_id")) or _text(context.get("user_id"))
    stats = _rows(args.get("stats"))
    records = _rows(args.get("records"))
    comments = _rows(args.get("comments"))
    items: list[dict[str, Any]] = []
    for raw in _rows(args.get("targets")):
        try:
            target_type = _target_type(raw.get("target_type"))
            target_id = _target_id(raw.get("target_id"))
        except ValueError:
            continue
        stat_row = next(
            (
                row
                for row in stats
                if _text(row.get("target_type")).upper() == target_type
                and _text(row.get("target_id")) == target_id
            ),
            None,
        )
        items.append(
            _state_payload(
                target_type,
                target_id,
                _counts(stat_row),
                records,
                comments,
                viewer_id,
            )
        )
    return {"items": items}


@operator(
    "assemble.interaction.comments",
    category="ASSEMBLE",
    description="Normalise a comment list into the public response envelope",
)
def comments(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = _rows(args.get("items"))
    items.sort(key=lambda row: _text(row.get("created_at")))
    return {"items": items, "total": len(items)}


@operator(
    "assemble.interaction.mine",
    category="ASSEMBLE",
    description="Assemble the caller's personal interaction centre from ledger and comment rows",
)
def mine(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    user_id = _text(args.get("viewer_id")) or _text(context.get("user_id"))
    items: list[dict[str, Any]] = []
    counts = {"like": 0, "favorite": 0, "love": 0, "dislike": 0, "comment": 0}

    if not user_id:
        return {"items": items, "counts": counts}

    for row in _rows(args.get("records")):
        if _text(row.get("user_id")) != user_id:
            continue
        kind = _text(row.get("kind")).upper()
        target_type = _text(row.get("target_type")).upper()
        if kind == "LIKE":
            counts["like"] += 1
        elif kind == "FAVORITE":
            counts["favorite"] += 1
        elif kind == "LOVE":
            counts["love"] += 1
        elif kind == "DISLIKE":
            counts["dislike"] += 1
        items.append(
            {
                "target_type": target_type,
                "target_id": _text(row.get("target_id")),
                "kind": kind,
                "title": _text(row.get("target_title")),
                "subtitle": KIND_LABEL.get(kind, kind),
                "tab": TAB_MAP.get(target_type, ""),
                "created_at": _text(row.get("created_at")),
            }
        )

    for row in _rows(args.get("comments")):
        if _text(row.get("author_id")) != user_id:
            continue
        target_type = _text(row.get("target_type")).upper()
        counts["comment"] += 1
        items.append(
            {
                "target_type": target_type,
                "target_id": _text(row.get("target_id")),
                "kind": "COMMENT",
                "title": _text(row.get("target_title")),
                "subtitle": _text(row.get("content"))[:80],
                "tab": TAB_MAP.get(target_type, ""),
                "created_at": _text(row.get("created_at")),
            }
        )

    items.sort(key=lambda row: _text(row.get("created_at")), reverse=True)
    return {"items": items, "counts": counts}
