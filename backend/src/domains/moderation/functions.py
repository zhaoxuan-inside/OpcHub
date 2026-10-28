"""Single-responsibility pure function operators for the moderation domain.

Only calculations / normalisation / assembly / state-transition policies live
here. Guards come from ``guard.*``, validation from ``validate.*``, persistence
from ``entity.*`` and observability from ``metric.*`` / ``audit.*``. Business
flows are declared in ``config/scenarios/moderation.yaml``.

Rules honoured by this module: no I/O, no orchestration, no call to another
operator, no cross-domain import.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.operators.sdk import operator
from src.domains.moderation.models import REPORTABLE_TARGET_TYPES
from src.domains.moderation.nlp_prescreen import (
    VERDICT_SAFE,
    VERDICT_VIOLATION,
    prescreen_text,
)

STATUS_FLAGGED = "FLAGGED"
STATUS_TAKEN_DOWN = "TAKEN_DOWN"
STATUS_NORMAL = "NORMAL"
STATUS_PENDING_EXTERNAL = "PENDING_EXTERNAL"

ACTION_PASS = "PASS"
ACTION_BLOCK = "BLOCK"
ACTION_DEFER = "DEFER"

DEFAULT_REPORT_REASON = "用户举报：内容疑似违规或失实"
DEFAULT_PAGE_SIZE = 20
DEFAULT_SNIPPET_LENGTH = 160
DEFAULT_ORDER = "-reported_at"

# Declarative state machine: which source statuses may move to the target status.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    STATUS_TAKEN_DOWN: (STATUS_FLAGGED, STATUS_NORMAL),
    STATUS_NORMAL: (STATUS_TAKEN_DOWN,),
}

# High-severity illegal-trade vocabulary used to classify pre-screen evidence.
_ILLEGAL_TRADE_TOKENS = {
    "代开发票", "虚开发票", "倒卖发票", "假发票", "走私", "地下钱庄", "洗钱",
    "跑分", "资金盘", "非法集资", "非法吸收公众存款", "传销", "庞氏", "诈骗",
    "电信诈骗", "网络诈骗", "杀猪盘", "博彩", "赌博", "裸聊", "色情", "代孕",
    "伪造证件", "伪造公章", "售卖枪支", "毒品", "冰毒", "买卖个人信息",
    "出售个人信息", "盗卖", "黑客工具", "木马", "钓鱼网站", "泄露内网",
    "私钥", "外挂", "刷单返利", "套现", "偷逃税", "逃税", "骗补", "骗税",
    "空壳公司", "注册空壳", "虚假申报", "骗取补贴",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


@operator(
    "calc.moderation.normalize_report",
    category="CALC",
    description="Normalise one user report and bind the reporter identity from context",
)
def normalize_report(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Project one report request into the fields consumed by the merge step."""
    target_type = _text(args.get("target_type")).upper()
    if target_type not in REPORTABLE_TARGET_TYPES:
        raise ValueError(f"Unsupported report target_type: {args.get('target_type')}")
    target_id = _text(args.get("target_id"))
    if not target_id:
        raise ValueError("target_id is required for a report")

    target_title = _text(args.get("target_title"))
    snippet = (_text(args.get("snippet_content")) or target_title)[:DEFAULT_SNIPPET_LENGTH]
    reporter_id = _text(context.get("user_id")) or _text(args.get("reporter_id"))

    return {
        "target_type": target_type,
        "target_id": target_id,
        "target_title": target_title,
        "author_id": _text(args.get("author_id")),
        "author_name": _text(args.get("author_name")),
        "snippet_content": snippet,
        "reason": _text(args.get("reason")) or DEFAULT_REPORT_REASON,
        "reporter_id": reporter_id,
        "violation_type": "USER_REPORT",
        "status": STATUS_FLAGGED,
        "reported_at": _now(),
    }


@operator(
    "assemble.moderation.report_merge",
    category="ASSEMBLE",
    description="Merge a user report into the existing flagged item for the same target",
)
def report_merge(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Combine one normalised report with the (optional) existing flagged item.

    A target keeps exactly one flagged item: repeats accumulate ``report_count``
    and the reporter set instead of creating a new document. A previously
    moderated target (TAKEN_DOWN / NORMAL) is not merged — the caller passes an
    empty ``existing`` list and a fresh item is assembled.
    """
    rows = args.get("existing") or []
    existing = rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}
    report = args.get("report") if isinstance(args.get("report"), dict) else {}
    merged = bool(existing)
    previous_count = int(existing.get("report_count") or 0) if existing else 0

    reporters = [str(r) for r in (existing.get("reporters") or []) if str(r)]
    reporter_id = _text(report.get("reporter_id"))
    if reporter_id and reporter_id not in reporters:
        reporters.append(reporter_id)

    document = {
        "id": existing.get("id") or f"mod_{uuid.uuid4().hex[:10]}",
        "target_type": existing.get("target_type") or _text(report.get("target_type")).upper(),
        "target_id": existing.get("target_id") or _text(report.get("target_id")),
        "author_id": existing.get("author_id") or _text(report.get("author_id")),
        "author_name": existing.get("author_name") or _text(report.get("author_name")),
        "snippet_content": existing.get("snippet_content") or _text(report.get("snippet_content")),
        "violation_type": existing.get("violation_type") or "USER_REPORT",
        "status": STATUS_FLAGGED,
        "report_count": previous_count + 1,
        "reported_at": _text(report.get("reported_at")) or _now(),
        "moderated_at": existing.get("moderated_at"),
        "reason": existing.get("reason") or _text(report.get("reason")) or DEFAULT_REPORT_REASON,
        "moderator_id": existing.get("moderator_id"),
        "reporter_id": reporter_id or _text(existing.get("reporter_id")),
        "reporters": reporters,
    }
    return {
        "document": document,
        "report_id": document["id"],
        "merged": merged,
        "previous_count": previous_count,
    }


@operator(
    "policy.moderation.transition",
    category="POLICY",
    description="Apply one declarative moderation state transition and build its patch",
)
def transition(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Move one moderation item to TAKEN_DOWN or NORMAL.

    This is a pure state-transition policy: it validates the allowed source
    status, then returns the patch document plus the operator-facing note. It
    never reads or writes storage.
    """
    action = _text(params.get("action") or args.get("action")).upper()
    if action not in TRANSITIONS:
        raise ValueError(f"Unsupported moderation transition: {action or '<empty>'}")

    current = _text(args.get("current") or params.get("current")).upper()
    if current and current not in TRANSITIONS[action]:
        raise ValueError(
            f"当前状态 '{current}' 不允许迁移到 '{action}'"
        )

    item_id = _text(args.get("item_id"))
    if not item_id:
        raise ValueError("item_id is required for a moderation transition")

    moderator_id = _text(context.get("user_id")) or _text(args.get("moderator_id"))
    now = _now()
    patch: dict[str, Any] = {
        "id": item_id,
        "status": action,
        "moderator_id": moderator_id,
        "moderated_at": now,
    }

    if action == STATUS_TAKEN_DOWN:
        reason = _text(args.get("reason"))
        if not reason:
            raise ValueError("下架原因不能为空")
        patch["reason"] = reason
        note = f"言论已全站下架: {reason}"
        if bool(args.get("ban_author")):
            note += " (作者已封禁)"
    else:
        note = "处罚已撤销，言论恢复正常展示"

    return {
        "patch": patch,
        "prev_status": current,
        "status": action,
        "action": action,
        "note": note,
        "moderated_at": now,
        "orchestrated_by": _text(params.get("pipeline")),
    }


@operator(
    "calc.moderation.query",
    category="CALC",
    description="Normalise moderation queue query parameters into generic store filters",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Translate a moderation queue query into filters plus optional pagination."""
    filters: dict[str, Any] = {}
    status = _text(args.get("status"))
    if status and status.upper() != "ALL":
        filters["status"] = {"in": [status.upper()]}
    target_type = _text(args.get("target_type"))
    if target_type and target_type.upper() != "ALL":
        filters["target_type"] = {"in": [target_type.upper()]}
    violation_type = _text(args.get("violation_type"))
    if violation_type and violation_type.upper() != "ALL":
        filters["violation_type"] = {"in": [violation_type.upper()]}

    raw_page = args.get("page")
    paged = raw_page not in (None, "", 0, "0", False)
    page_no = max(1, int(raw_page)) if paged else 1
    page_size = max(1, min(100, int(args.get("page_size") or DEFAULT_PAGE_SIZE)))

    return {
        "filters": filters,
        "search": _text(args.get("search")) or None,
        "order": _text(params.get("order")) or DEFAULT_ORDER,
        "page": page_no,
        "page_size": page_size,
        "offset": (page_no - 1) * page_size if paged else None,
        "limit": page_size if paged else None,
        "paged": paged,
    }


@operator(
    "assemble.moderation.list",
    category="ASSEMBLE",
    description="Project a moderation listing as either a flat queue or a paged envelope",
)
def list_response(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = [dict(item) for item in (args.get("items") or []) if isinstance(item, dict)]
    total = int(args.get("total") if args.get("total") is not None else len(items))
    if not args.get("paged"):
        return {"response": items}

    page_no = max(1, int(args.get("page") or 1))
    page_size = max(1, min(100, int(args.get("page_size") or DEFAULT_PAGE_SIZE)))
    total_pages = max(1, -(-total // page_size))
    return {
        "response": {
            "items": items,
            "total": total,
            "page": page_no,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_more": page_no * page_size < total,
        }
    }


@operator(
    "assemble.moderation.detail",
    category="ASSEMBLE",
    description="Project one moderation item document as the detail response",
)
def detail(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    doc = args.get("entity") if isinstance(args.get("entity"), dict) else {}
    return {"response": doc, "item": doc}


@operator(
    "assemble.moderation.report_result",
    category="ASSEMBLE",
    description="Project the user-report response from the created or merged item",
)
def report_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    created = args.get("created") if isinstance(args.get("created"), dict) else {}
    updated = args.get("updated") if isinstance(args.get("updated"), dict) else {}
    doc = created or updated
    return {
        "response": doc,
        "created_report": doc,
        "report_id": doc.get("id"),
        "report_previous_count": int(args.get("previous_count") or 0),
        "status": doc.get("status"),
        "merged": bool(args.get("merged")),
        "orchestrated_by": _text(params.get("pipeline")),
    }


@operator(
    "assemble.moderation.action_result",
    category="ASSEMBLE",
    description="Project a takedown/restore response from the patched item",
)
def action_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    item = args.get("item") if isinstance(args.get("item"), dict) else {}
    return {
        "response": {
            "item_id": item.get("id") or _text(args.get("item_id")),
            "status": item.get("status") or _text(args.get("status")),
            "moderated_at": item.get("moderated_at") or args.get("moderated_at"),
            "note": args.get("note") or "",
            "prev_status": args.get("prev_status"),
            "moderator_id": item.get("moderator_id"),
            "orchestrated_by": _text(params.get("pipeline")),
        }
    }


@operator(
    "calc.moderation.prescreen",
    category="CALC",
    description="Run the local NLP pre-screen and expose its three-way verdict",
)
def prescreen(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Thin pure wrapper over the existing local NLP classifier.

    ``prescreen_text`` performs no network or third-party call, so it is safe to
    expose as an operator. Ambiguous content is *not* sent to an external
    service here; the decision step declares the degradation instead.
    """
    content = str(args.get("content") or "")
    result = dict(prescreen_text(content))
    result["content"] = content
    return result


def _infer_violation_type(verdict: dict[str, Any]) -> str:
    """Classify confident violation evidence into the platform vocabulary."""
    if verdict.get("matched_patterns"):
        return "SCAM"
    hits = {str(token) for token in (verdict.get("hit_sensitive") or [])}
    if hits & _ILLEGAL_TRADE_TOKENS:
        return "ILLEGAL_TRADE"
    return "SENSITIVE_SPEECH"


@operator(
    "assemble.moderation.prescreen_decision",
    category="ASSEMBLE",
    description="Map the three-way NLP verdict into PASS/BLOCK/DEFER and its degradation",
)
def prescreen_decision(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Map a three-state verdict into an actionable moderation decision.

    The external moderation service is not reachable from a pure operator, so
    ``external_service_available`` is declarative scenario configuration. When it
    is false (the current migration baseline) ambiguous content is degraded to
    the local policy ``FLAG_FOR_HUMAN_REVIEW`` and explicitly annotated.
    """
    verdict = args.get("verdict") if isinstance(args.get("verdict"), dict) else {}
    phase = _text(verdict.get("verdict"))
    external_available = bool(params.get("external_service_available", False))

    target_type = _text(args.get("target_type")).upper()
    target_id = _text(args.get("target_id"))
    snippet = (_text(args.get("snippet_content")) or _text(args.get("target_title")))[:DEFAULT_SNIPPET_LENGTH]

    external_required = False
    degraded = False
    should_enqueue = False

    if phase == VERDICT_SAFE:
        action, status = ACTION_PASS, STATUS_NORMAL
        violation_type = ""
        note = "本地NLP预筛判定肯定没问题，直接放行，无需外呼审核服务"
    elif phase == VERDICT_VIOLATION:
        action, status = ACTION_BLOCK, STATUS_FLAGGED
        violation_type = _infer_violation_type(verdict)
        should_enqueue = True
        note = "本地NLP预筛判定肯定有问题，直接拦截并进入审核队列，无需外呼审核服务"
    elif external_available:
        action, status = ACTION_DEFER, STATUS_PENDING_EXTERNAL
        violation_type = "PENDING_EXTERNAL_REVIEW"
        external_required = True
        note = "本地NLP预筛证据不足，交由外部审核服务裁决"
    else:
        action, status = ACTION_DEFER, STATUS_FLAGGED
        violation_type = "PENDING_EXTERNAL_REVIEW"
        external_required = True
        degraded = True
        should_enqueue = True
        note = (
            "本地NLP预筛证据不足且外部审核服务不可用，"
            "已按声明式预筛降级为人工审核（FLAGGED）"
        )

    return {
        "verdict": phase,
        "action": action,
        "status": status,
        "violation_type": violation_type,
        "note": note,
        "external_service_required": external_required,
        "degraded": degraded,
        "degraded_strategy": "DECLARATIVE_PRESCREEN_FLAG_FOR_REVIEW" if degraded else "",
        "should_enqueue": should_enqueue,
        "target_type": target_type,
        "target_id": target_id,
        "author_id": _text(args.get("author_id")),
        "author_name": _text(args.get("author_name")),
        "snippet_content": snippet,
        "reported_at": _now(),
        "evidence": {
            "violation_score": verdict.get("violation_score", 0),
            "safe_score": verdict.get("safe_score", 0),
            "hit_sensitive": verdict.get("hit_sensitive") or [],
            "matched_patterns": verdict.get("matched_patterns") or [],
        },
    }


@operator(
    "assemble.moderation.prescreen_item",
    category="ASSEMBLE",
    description="Build the moderation item document enqueued by a pre-screen decision",
)
def prescreen_item(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    decision = args.get("decision") if isinstance(args.get("decision"), dict) else {}
    document = {
        "id": f"mod_{uuid.uuid4().hex[:10]}",
        "target_type": _text(decision.get("target_type")),
        "target_id": _text(decision.get("target_id")),
        "author_id": _text(decision.get("author_id")),
        "author_name": _text(decision.get("author_name")),
        "snippet_content": _text(decision.get("snippet_content")),
        "violation_type": _text(decision.get("violation_type")) or "SENSITIVE_SPEECH",
        "status": STATUS_FLAGGED,
        "report_count": 0,
        "reported_at": _text(decision.get("reported_at")) or _now(),
        "moderated_at": None,
        "reason": _text(decision.get("note")) or "NLP预筛拦截/降级",
        "moderator_id": None,
        "reporter_id": "",
        "reporters": [],
    }
    return {"document": document}


@operator(
    "assemble.moderation.prescreen_result",
    category="ASSEMBLE",
    description="Project the pre-screen response from its decision and enqueued item",
)
def prescreen_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    decision = args.get("decision") if isinstance(args.get("decision"), dict) else {}
    created = args.get("created") if isinstance(args.get("created"), dict) else None
    return {
        "response": {
            "verdict": decision.get("verdict"),
            "action": decision.get("action"),
            "status": decision.get("status"),
            "violation_type": decision.get("violation_type"),
            "note": decision.get("note"),
            "external_service_required": bool(decision.get("external_service_required")),
            "degraded": bool(decision.get("degraded")),
            "degraded_strategy": decision.get("degraded_strategy") or "",
            "evidence": decision.get("evidence") or {},
            "item": created,
            "enqueued": bool(created),
        }
    }
