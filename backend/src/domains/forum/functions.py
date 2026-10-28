"""Single-responsibility pure function operators for the forum (头脑风暴) domain.

Only normalisation / calculation / assembly lives here: no I/O, no operator
calls, no orchestration and no cross-domain imports. Storage is handled by the
generic ``entity.*`` operators, guards by ``guard.*``, validation by
``validate.*``; every business rule is declared in ``config/scenarios/forum.yaml``.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.core.operators.sdk import operator

THREAD_CATEGORIES = ("DEV", "BIZ", "TAX", "AGENTS", "POLICY")
VOTE_TARGETS = ("THREAD", "ANSWER", "COMMENT")
VOTE_TYPES = ("UPVOTE", "DOWNVOTE", "CANCEL")
SORT_MODES = ("latest", "hot", "replies", "answers", "unanswered", "featured")
READ_WORDS_PER_MINUTE = 300

# Zhihu-style Newton-cooling weights (kept identical to the legacy formula).
_W_UPVOTE = 3.5
_W_DOWNVOTE = 2.0
_W_ANSWER = 6.0
_W_COMMENT = 2.0
_W_VIEW = 0.08
_W_PINNED = 20.0
_COOLING_POWER = 1.15


# ---------------------------------------------------------------------------
# Local helpers (pure)
# ---------------------------------------------------------------------------
def _pretty(value: Any) -> dict[str, Any]:
    """Return a plain dict for a mapping or a pydantic-like document."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> Optional[datetime]:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _age_hours(created_at: Any, now: Optional[datetime] = None) -> float:
    parsed = _parse_dt(created_at)
    if parsed is None:
        return 1.0
    reference = now or _now()
    return max(0.1, (reference - parsed).total_seconds() / 3600.0)


def hotness(doc: dict[str, Any], now: Optional[datetime] = None) -> float:
    """Newton-cooling thermal score of one thread document."""
    weight = (
        _int(doc.get("upvote_count")) * _W_UPVOTE
        - _int(doc.get("downvote_count")) * _W_DOWNVOTE
        + _int(doc.get("answer_count")) * _W_ANSWER
        + _int(doc.get("comment_count")) * _W_COMMENT
        + _int(doc.get("view_count")) * _W_VIEW
        + (_W_PINNED if doc.get("is_pinned") else 0.0)
    )
    score = weight / ((_age_hours(doc.get("created_at"), now) + 2.0) ** _COOLING_POWER)
    return round(max(0.0, score), 2)


def _is_dead_path(path: Any, dead_paths: Iterable[str]) -> bool:
    current = _text(path)
    if not current:
        return False
    for dead in dead_paths:
        if current == dead or current.startswith(f"{dead}/"):
            return True
    return False


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
@operator(
    "calc.forum.word_stats",
    category="CALC",
    description="Count content characters and derive the reading time in minutes",
)
def word_stats(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    content = _text(args.get("content"))
    count = len(content)
    return {
        "content": content,
        "word_count": count,
        "read_minutes": max(1, math.ceil(count / READ_WORDS_PER_MINUTE)),
    }


@operator(
    "calc.forum.hot_score",
    category="CALC",
    description="Compute the Newton-cooling hotness score of one thread document",
)
def hot_score(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {"hot_score": hotness(_pretty(args.get("thread") or args), _parse_dt(args.get("now")))}


@operator(
    "calc.forum.thread_publish",
    category="CALC",
    description="Normalise a thread publish payload and bind author identity from context",
)
def thread_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    role = _text(context.get("user_role") or "MAKER").upper()
    is_admin = role == "ADMIN"
    # Identity is server-bound: only ADMIN may attribute content to another author.
    author_id = (_text(args.get("author_id")) if is_admin else "") or _text(context.get("user_id"))
    author_name = (_text(args.get("author_name")) if is_admin else "") or _text(context.get("nickname")) or "超级个体创客"
    return {
        "category_code": (_text(args.get("category_code")) or "DEV").upper(),
        "author_id": author_id,
        "author_name": author_name,
        "author_title": _text(args.get("author_title")) or "独立创业者",
        "is_official": is_admin,
        "title": _text(args.get("title")),
        "content": _text(args.get("content")),
        "view_count": 0,
        "upvote_count": 0,
        "downvote_count": 0,
        "comment_count": 0,
        "answer_count": 0,
        "follow_count": 0,
        "bookmark_count": 0,
        "is_pinned": False,
        "status": "PUBLISHED",
        "accepted_answer_id": None,
        "hot_score": 0.0,
    }


@operator(
    "calc.forum.thread_update",
    category="CALC",
    description="Build the patch payload of a thread edit (only provided fields are rewritten)",
)
def thread_update(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "id": _text(args.get("thread_id")),
        "title": _text(args.get("title")),
        "content": _text(args.get("content")),
    }
    category = _text(args.get("category_code")).upper()
    if category:
        patch["category_code"] = category
    return {"patch": patch, "thread_id": patch["id"]}


@operator(
    "calc.forum.answer_publish",
    category="CALC",
    description="Normalise an answer publish payload with word statistics",
)
def answer_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    content = _text(args.get("content"))
    count = _int(args.get("word_count"), len(content)) or len(content)
    return {
        "thread_id": _text(args.get("thread_id") or args.get("id")),
        "author_id": (_text(args.get("author_id")) if _text(context.get("user_role")).upper() == "ADMIN" else "") or _text(context.get("user_id")),
        "author_name": (_text(args.get("author_name")) if _text(context.get("user_role")).upper() == "ADMIN" else "") or _text(context.get("nickname")) or "创客探索者",
        "author_title": _text(args.get("author_title")) or "超级个体实战家",
        "content": content,
        "upvote_count": 0,
        "downvote_count": 0,
        "comment_count": 0,
        "is_accepted": False,
        "word_count": count,
        "read_minutes": _int(args.get("read_minutes"), max(1, math.ceil(count / READ_WORDS_PER_MINUTE)))
        or max(1, math.ceil(count / READ_WORDS_PER_MINUTE)),
        "status": "PUBLISHED",
    }


@operator(
    "calc.forum.comment_publish",
    category="CALC",
    description="Normalise a comment publish payload (path fields are patched after insert)",
)
def comment_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    thread_id = _text(args.get("thread_id"))
    target_type = (_text(args.get("target_type")) or "ANSWER").upper()
    target_id = _text(args.get("target_id")) or thread_id
    return {
        "thread_id": thread_id,
        "target_type": target_type,
        "target_id": target_id,
        "author_id": (_text(args.get("author_id")) if _text(context.get("user_role")).upper() == "ADMIN" else "") or _text(context.get("user_id")),
        "author_name": (_text(args.get("author_name")) if _text(context.get("user_role")).upper() == "ADMIN" else "") or _text(context.get("nickname")) or "独立创客",
        "author_title": _text(args.get("author_title")) or None,
        "content": _text(args.get("content")),
        "parent_id": _text(args.get("parent_id")) or None,
        "root_id": None,
        "reply_to_user_id": _text(args.get("reply_to_user_id")) or None,
        "materialized_path": "",
        "depth": 0,
        "upvote_count": 0,
        "downvote_count": 0,
        "is_accepted": False,
        "status": "ACTIVE",
    }


@operator(
    "calc.forum.comment_path",
    category="CALC",
    description="Derive materialized path / root id / depth / reply target of a nested comment",
)
def comment_path(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    comment_id = _text(args.get("comment_id"))
    thread_id = _text(args.get("thread_id"))
    parent_id = _text(args.get("parent_id"))
    reply_to = _text(args.get("reply_to_user_id"))
    parent = _pretty(args.get("parent"))

    if comment_id and not thread_id:
        raise ValueError("评论路径计算缺少 thread_id")

    if parent:
        if _text(parent.get("thread_id")) != thread_id:
            raise ValueError("父评论不属于当前讨论帖，无法挂载子回复")
        root_id = _text(parent.get("root_id")) or _text(parent.get("id"))
        parent_path = _text(parent.get("materialized_path")) or f"/{parent.get('id')}"
        path = f"{parent_path}/{comment_id}"
        depth = _int(parent.get("depth")) + 1
        reply_to = reply_to or _text(parent.get("author_id"))
    elif parent_id:
        raise KeyError(f"Parent comment not found / 父评论不存在: {parent_id}")
    else:
        root_id = comment_id
        path = f"/{comment_id}"
        depth = 0

    return {
        "id": comment_id,
        "root_id": root_id,
        "materialized_path": path,
        "depth": depth,
        "reply_to_user_id": reply_to or None,
    }


@operator(
    "calc.forum.counter",
    category="CALC",
    description="Bump one numeric field of one document and clamp it at zero",
)
def counter(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    field_name = _text(params.get("field") or args.get("field"))
    if not field_name:
        raise ValueError("calc.forum.counter requires a 'field' param")
    doc_id = _text(args.get("id"))
    current = _int(args.get("current"))
    delta = _int(args.get("delta"))
    value = max(0, current + delta)
    return {"id": doc_id, "field": field_name, "value": value, "patch": {"id": doc_id, field_name: value}}


@operator(
    "calc.forum.thread_activity",
    category="CALC",
    description="Recompute a thread's activity counters and hotness from counter deltas",
)
def thread_activity(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    thread = _pretty(args.get("thread"))
    if not thread.get("id"):
        raise ValueError("calc.forum.thread_activity requires a thread document")
    answer_count = max(0, _int(thread.get("answer_count")) + _int(args.get("answer_delta")))
    comment_count = max(0, _int(thread.get("comment_count")) + _int(args.get("comment_delta")))
    view_count = max(0, _int(thread.get("view_count")) + _int(args.get("view_delta")))
    projected = {
        **thread,
        "answer_count": answer_count,
        "comment_count": comment_count,
        "view_count": view_count,
    }
    patch: dict[str, Any] = {
        "id": _text(thread.get("id")),
        "answer_count": answer_count,
        "comment_count": comment_count,
        "view_count": view_count,
        "hot_score": hotness(projected, _parse_dt(args.get("now"))),
    }
    clear_accepted = _text(args.get("clear_accepted_answer_id"))
    if clear_accepted and _text(thread.get("accepted_answer_id")) == clear_accepted:
        patch["accepted_answer_id"] = None
    return {"patch": patch, "thread_id": patch["id"], **{k: v for k, v in patch.items() if k != "id"}}


@operator(
    "calc.forum.vote_request",
    category="CALC",
    description="Normalise a vote request (target type, vote type, voter identity)",
)
def vote_request(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": _text(args.get("user_id")) or _text(context.get("user_id")),
        "target_type": _text(args.get("target_type")).upper(),
        "target_id": _text(args.get("target_id")),
        "vote_type": _text(args.get("vote_type")).upper(),
    }


@operator(
    "calc.forum.vote_transition",
    category="CALC",
    description="Apply Zhihu-style mutual exclusion between UPVOTE / DOWNVOTE / CANCEL and return counter deltas",
)
def vote_transition(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    target_type = _text(args.get("target_type")).upper()
    if target_type not in VOTE_TARGETS:
        raise ValueError(f"Unsupported vote target_type: {target_type}")
    vote_type = _text(args.get("vote_type")).upper()
    if vote_type not in VOTE_TYPES:
        raise ValueError(f"Unsupported vote_type: {vote_type}")

    current = _text(args.get("current_vote")).upper() or None
    upvotes = _int(args.get("upvote_count"))
    downvotes = _int(args.get("downvote_count"))

    if vote_type == "CANCEL" or current == vote_type:
        if current == "UPVOTE":
            upvotes -= 1
        elif current == "DOWNVOTE":
            downvotes -= 1
        new_vote: Optional[str] = None
        action = "CANCELLED"
    elif vote_type == "UPVOTE":
        if current == "DOWNVOTE":
            downvotes -= 1
        upvotes += 1
        new_vote = "UPVOTE"
        action = "SWITCHED" if current else "UPVOTED"
    else:
        if current == "UPVOTE":
            upvotes -= 1
        downvotes += 1
        new_vote = "DOWNVOTE"
        action = "SWITCHED" if current else "DOWNVOTED"

    return {
        "user_vote": new_vote,
        "new_vote": new_vote,
        "previous_vote": current,
        "action": action,
        "changed": new_vote != current,
        "target_type": target_type,
        "target_id": _text(args.get("target_id")),
        "vote_type": vote_type,
        "upvote_count": max(0, upvotes),
        "downvote_count": max(0, downvotes),
    }


@operator(
    "calc.forum.accept_transition",
    category="CALC",
    description="Toggle the accepted answer of a question and report the previously accepted one",
)
def accept_transition(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    answer_id = _text(args.get("answer_id"))
    current = _text(args.get("accepted_answer_id")) or None
    if not answer_id:
        raise ValueError("采纳观点需要 answer_id")
    if current == answer_id:
        return {
            "answer_id": answer_id,
            "action": "UNACCEPTED",
            "is_accepted": False,
            "accepted_answer_id": None,
            "previous_answer_id": None,
        }
    return {
        "answer_id": answer_id,
        "action": "ACCEPTED",
        "is_accepted": True,
        "accepted_answer_id": answer_id,
        "previous_answer_id": current,
    }


@operator(
    "calc.forum.follow_transition",
    category="CALC",
    description="Toggle one follow edge and return the resulting follow counter",
)
def follow_transition(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    existing = _pretty(args.get("existing")) or None
    thread_id = _text(args.get("thread_id"))
    if not thread_id:
        raise ValueError("关注议题需要 thread_id")
    active = existing is None
    follow_count = max(0, _int(args.get("follow_count")) + (1 if active else -1))
    return {
        "thread_id": thread_id,
        "user_id": _text(args.get("user_id")),
        "active": active,
        "is_following": active,
        "follow_count": follow_count,
    }


@operator(
    "calc.forum.query",
    category="CALC",
    description="Normalise forum list/feed query parameters into generic store filters and pager settings",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    target = _text(args.get("category_code") or args.get("id") or "ALL") or "ALL"
    filters: dict[str, Any] = {}
    status = _text(args.get("status"))
    if status:
        filters["status"] = status.upper()
    thread_id = _text(args.get("thread_id"))

    if thread_id:
        filters["id"] = thread_id
        category_code = "ALL"
    elif target.upper() == "ALL":
        category_code = "ALL"
    elif target.upper() in THREAD_CATEGORIES:
        category_code = target.upper()
        filters["category_code"] = {"in": [category_code, category_code.lower(), target]}
    else:
        # ``id`` may also carry a raw thread id (legacy list contract).
        filters["id"] = target
        category_code = "ALL"

    page = args.get("page")
    page_size = args.get("page_size")
    if page_size is None:
        page_size = args.get("page_length")
    cursor = args.get("cursor")
    limit = args.get("limit")
    sort_by = _text(args.get("sort_by") or "latest").lower()
    if sort_by == "answers":
        sort_by = "replies"
    if sort_by not in SORT_MODES:
        sort_by = "latest"
    mode = "cursor" if cursor is not None else ("page" if page is not None else "flat")
    return {
        "category_code": category_code,
        "filters": filters,
        "search": _text(args.get("search")) or None,
        "order": "-created_at",
        "sort_by": sort_by,
        "mode": mode,
        "page": None if page is None else max(1, _int(page, 1)),
        "page_size": None if page_size is None else _clamp(_int(page_size, 10), 1, 50),
        "page_length": None if page_size is None else _clamp(_int(page_size, 10), 1, 50),
        "cursor": None if cursor is None else max(0, _int(cursor)),
        "limit": None if limit is None else _clamp(_int(limit, 10), 1, 50),
    }


def _sort_key(sort_by: str):
    if sort_by == "hot":
        return lambda t: (
            bool(t.get("is_pinned")),
            hotness(t),
            _int(t.get("upvote_count")),
            _int(t.get("answer_count")),
            _text(t.get("created_at")),
        )
    if sort_by == "replies":
        return lambda t: (
            bool(t.get("is_pinned")),
            _int(t.get("answer_count")),
            _int(t.get("comment_count")),
            _text(t.get("created_at")),
        )
    if sort_by == "featured":
        return lambda t: (
            bool(t.get("is_pinned")),
            bool(t.get("is_official")),
            _int(t.get("upvote_count")),
            _text(t.get("created_at")),
        )
    return lambda t: (bool(t.get("is_pinned")), _text(t.get("created_at")))


@operator(
    "calc.forum.page",
    category="CALC",
    description="Rank threads by hotness/replies and slice one cursor or page window",
)
def page(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = [_pretty(row) for row in (args.get("items") or [])]
    sort_by = _text(args.get("sort_by") or "latest").lower()
    if sort_by == "answers":
        sort_by = "replies"
    if sort_by not in SORT_MODES:
        sort_by = "latest"

    if sort_by == "unanswered":
        items = [item for item in items if _int(item.get("answer_count")) == 0]

    now = _now()
    ranked = sorted(items, key=_sort_key(sort_by), reverse=True)
    ranked = [{**item, "hot_score": hotness(item, now)} for item in ranked]
    total = len(ranked)

    mode = _text(args.get("mode")) or ("cursor" if args.get("cursor") is not None else "page")
    envelope: dict[str, Any] = {
        "mode": mode,
        "category_code": _text(args.get("category_code") or "ALL").upper(),
        "sort_by": sort_by,
        "total": total,
    }

    if mode == "cursor":
        cursor = max(0, _int(args.get("cursor")))
        size = _clamp(_int(args.get("limit"), 10), 1, 50)
        end = cursor + size
        window = ranked[cursor:end]
        has_more = end < total
        envelope.update(
            {"cursor": cursor, "limit": size, "has_more": has_more, "next_cursor": end if has_more else None}
        )
    elif mode == "flat":
        window = ranked
        envelope.update(
            {
                "page": 1,
                "page_size": total or 1,
                "page_length": total or 1,
                "total_pages": 1 if total else 0,
                "has_more": False,
                "next_cursor": None,
            }
        )
    else:
        page_no = max(1, _int(args.get("page"), 1))
        size = _clamp(_int(args.get("page_size"), 10), 1, 50)
        offset = (page_no - 1) * size
        end = offset + size
        window = ranked[offset:end]
        has_more = end < total
        envelope.update(
            {
                "page": page_no,
                "page_size": size,
                "page_length": size,
                "total_pages": ((total + size - 1) // size) if total else 0,
                "has_more": has_more,
                "next_cursor": end if has_more else None,
            }
        )

    envelope["items"] = window
    return {
        "envelope": envelope,
        "items": window,
        "total": total,
        "has_more": envelope["has_more"],
        "next_cursor": envelope.get("next_cursor"),
    }


@operator(
    "calc.forum.comment_delete_plan",
    category="CALC",
    description="Plan the materialized-path subtree removal of one comment and the counters to rewrite",
)
def comment_delete_plan(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    comment = _pretty(args.get("comment"))
    if not comment.get("id"):
        raise ValueError("评论不存在，无法删除")
    comments = [_pretty(row) for row in (args.get("comments") or [])]
    path = _text(comment.get("materialized_path")) or f"/{comment.get('id')}"

    removed = [row for row in comments if _is_dead_path(row.get("materialized_path"), [path])]
    if not any(_text(row.get("id")) == _text(comment.get("id")) for row in removed):
        removed.append(comment)
    removed_ids = {_text(row.get("id")) for row in removed}
    remaining = [row for row in comments if _text(row.get("id")) not in removed_ids]

    answer_id = _text(comment.get("target_id")) if _text(comment.get("target_type")).upper() == "ANSWER" else ""
    answer_patch: dict[str, Any] = {}
    if answer_id:
        answer_patch = {
            "id": answer_id,
            "comment_count": len([row for row in remaining if _text(row.get("target_id")) == answer_id]),
        }
    return {
        "id": _text(comment.get("id")),
        "thread_id": _text(comment.get("thread_id")),
        "path": path,
        "removed_count": len(removed_ids),
        "removed_ids": sorted(removed_ids),
        "thread_comment_count": len(remaining),
        "answer_id": answer_id or None,
        "answer_patch": answer_patch,
    }


@operator(
    "calc.forum.answer_delete_plan",
    category="CALC",
    description="Count the comments attached to one answer before it is removed",
)
def answer_delete_plan(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    answer = _pretty(args.get("answer"))
    if not answer.get("id"):
        raise ValueError("观点回答不存在，无法删除")
    comments = [_pretty(row) for row in (args.get("comments") or [])]
    answer_id = _text(answer.get("id"))
    attached = [
        row
        for row in comments
        if _text(row.get("target_type")).upper() == "ANSWER" and _text(row.get("target_id")) == answer_id
    ]
    return {
        "answer_id": answer_id,
        "thread_id": _text(answer.get("thread_id")),
        "removed_comments": len(attached),
        "removed_ids": sorted({_text(row.get("id")) for row in attached}),
    }


# ---------------------------------------------------------------------------
# Assemblers
# ---------------------------------------------------------------------------
@operator(
    "assemble.forum.thread_detail",
    category="ASSEMBLE",
    description="Assemble one thread with its answers, nested comment tree and viewer state",
)
def thread_detail(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    thread = _pretty(args.get("thread"))
    if not thread.get("id"):
        raise KeyError("Thread not found / 讨论帖不存在或已被删除")
    tid = _text(thread.get("id"))
    viewer = _text(args.get("viewer_id"))

    answers_raw = [_pretty(row) for row in (args.get("answers") or [])]
    comments_raw = [_pretty(row) for row in (args.get("comments") or [])]
    votes = [_pretty(row) for row in (args.get("votes") or [])]
    follows = [_pretty(row) for row in (args.get("follows") or [])]
    tombstones = [_pretty(row) for row in (args.get("tombstones") or [])]

    dead_answers = {_text(t.get("id")) for t in tombstones if _text(t.get("type")).upper() == "ANSWER"}
    dead_comments = {_text(t.get("id")) for t in tombstones if _text(t.get("type")).upper() == "COMMENT"}
    dead_paths = [
        _text(t.get("path"))
        for t in tombstones
        if _text(t.get("type")).upper() == "COMMENT" and _text(t.get("path"))
    ]
    vote_map = {
        (_text(v.get("user_id")), _text(v.get("target_type")).upper(), _text(v.get("target_id"))): _text(
            v.get("vote_type")
        ).upper()
        for v in votes
    }
    following = any(_text(f.get("thread_id")) == tid for f in follows)

    answers = [
        row
        for row in answers_raw
        if _text(row.get("thread_id")) == tid and _text(row.get("id")) not in dead_answers
    ]
    answers.sort(
        key=lambda row: (bool(row.get("is_accepted")), _int(row.get("upvote_count")), _text(row.get("created_at"))),
        reverse=True,
    )
    decorated_answers = [
        {**row, "user_vote": vote_map.get((viewer, "ANSWER", _text(row.get("id")))) if viewer else None}
        for row in answers
    ]

    visible: list[dict[str, Any]] = []
    for row in comments_raw:
        if _text(row.get("thread_id")) != tid:
            continue
        if _text(row.get("status") or "ACTIVE").upper() != "ACTIVE":
            continue
        cid = _text(row.get("id"))
        if cid in dead_comments or _is_dead_path(row.get("materialized_path"), dead_paths):
            continue
        if _text(row.get("target_type")).upper() == "ANSWER" and _text(row.get("target_id")) in dead_answers:
            # The answer this comment hangs on is soft-deleted: hide the branch.
            continue
        visible.append(
            {
                **row,
                "user_vote": vote_map.get((viewer, "COMMENT", cid)) if viewer else None,
                "children": [],
            }
        )
    visible.sort(key=lambda row: (_int(row.get("depth")), _text(row.get("created_at"))))
    nodes = {_text(row.get("id")): row for row in visible}
    roots: list[dict[str, Any]] = []
    for row in visible:
        parent_id = _text(row.get("parent_id"))
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(row)
        else:
            roots.append(row)

    decorated_thread = {
        **thread,
        "answer_count": len(decorated_answers),
        "top_answers": decorated_answers[:3],
        "user_vote": vote_map.get((viewer, "THREAD", tid)) if viewer else None,
        "is_following": following if viewer else False,
        "hot_score": hotness({**thread, "answer_count": len(decorated_answers)}),
    }
    detail = {"thread": decorated_thread, "answers": decorated_answers, "comments": roots}
    return {
        "detail": detail,
        "thread": decorated_thread,
        "answers": decorated_answers,
        "comments": roots,
        "viewer_id": viewer or None,
    }


@operator(
    "assemble.forum.feed",
    category="ASSEMBLE",
    description="Batch-annotate a thread page with top answers, viewer vote/follow state and prefetch hint",
)
def feed(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    envelope = _pretty(args.get("envelope"))
    if not envelope:
        raise ValueError("assemble.forum.feed requires a page envelope")
    items = [_pretty(row) for row in (envelope.get("items") or [])]
    answers = [_pretty(row) for row in (args.get("answers") or [])]
    votes = [_pretty(row) for row in (args.get("votes") or [])]
    follows = [_pretty(row) for row in (args.get("follows") or [])]
    viewer = _text(args.get("viewer_id"))

    by_thread: dict[str, list[dict[str, Any]]] = {}
    for row in answers:
        by_thread.setdefault(_text(row.get("thread_id")), []).append(row)
    vote_map = {
        (_text(v.get("user_id")), _text(v.get("target_type")).upper(), _text(v.get("target_id"))): _text(
            v.get("vote_type")
        ).upper()
        for v in votes
    }
    follow_ids = {_text(f.get("thread_id")) for f in follows}

    decorated: list[dict[str, Any]] = []
    for item in items:
        tid = _text(item.get("id"))
        thread_answers = by_thread.get(tid, [])
        thread_answers.sort(
            key=lambda row: (
                bool(row.get("is_accepted")),
                _int(row.get("upvote_count")),
                _text(row.get("created_at")),
            ),
            reverse=True,
        )
        top = [
            {**row, "user_vote": vote_map.get((viewer, "ANSWER", _text(row.get("id")))) if viewer else None}
            for row in thread_answers[:2]
        ]
        decorated.append(
            {
                **item,
                "answer_count": len(thread_answers),
                "top_answers": top,
                "user_vote": vote_map.get((viewer, "THREAD", tid)) if viewer else None,
                "is_following": tid in follow_ids if viewer else False,
            }
        )

    envelope["items"] = decorated
    if _text(envelope.get("mode")) == "cursor" or "cursor" in envelope:
        envelope["prefetch_hint"] = {
            "recommended_prefetch_cursor": envelope.get("next_cursor"),
            "limit": envelope.get("limit"),
            "sort_by": envelope.get("sort_by"),
        }
    output_key = _text(params.get("output_key")) or "feed"
    return {
        output_key: envelope,
        "total": envelope.get("total", len(decorated)),
        "has_more": envelope.get("has_more", False),
        "next_cursor": envelope.get("next_cursor"),
    }


@operator(
    "assemble.forum.delete_result",
    category="ASSEMBLE",
    description="Shape the acknowledgement payload of one content deletion",
)
def delete_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    flag = _text(params.get("flag")) or "deleted"
    result: dict[str, Any] = {flag: True, "deleted": True}
    for key in ("id", "thread_id", "answer_id", "comment_id", "removed_count"):
        value = args.get(key)
        if value not in (None, ""):
            result[key] = value
    return result
