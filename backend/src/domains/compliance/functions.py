"""Single-responsibility pure function operators for the compliance domain.

Only calculations / normalisation / assembly live here. Storage is handled by
``entity.*`` operators, guards by ``guard.*``, validation by ``validate.*``.
There is no I/O, no orchestration and no cross-domain import.
"""
from __future__ import annotations

import uuid
from typing import Any

from src.core.config import settings
from src.core.operators.sdk import operator

KIND_LAW = "law"
KIND_CASE = "case"
KIND_CHECKPOINT = "checkpoint"

_SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_int(value: Any, default: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


@operator(
    "calc.compliance.normalize_publish",
    category="CALC",
    description="Normalise a law/case publish payload and bind gateway identity",
)
def normalize_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Project one law/case publish payload into a persistable unified item."""
    kind = _text(args.get("kind") or params.get("kind")).lower()
    if kind not in (KIND_LAW, KIND_CASE):
        raise ValueError(f"Unsupported compliance publish kind: {kind or '<empty>'}（仅支持 law / case）")

    title = _text(args.get("title"))
    if not title:
        raise ValueError("字段 'title' 为必填项")

    # Identity and the official badge are decided by the gateway context only;
    # payload-provided author/official fields are intentionally ignored.
    role = _text(context.get("user_role")).upper()
    author_id = _text(context.get("user_id"))
    author_name = _text(context.get("nickname")) or _text(args.get("author_name")) or "@创客"
    suffix = uuid.uuid4().hex[:8]

    if kind == KIND_LAW:
        item_id = _text(args.get("id")) or f"law_{suffix}"
        code = _text(args.get("code")) or f"LAW-{uuid.uuid4().hex[:4].upper()}"
        return {
            "id": item_id,
            "kind": KIND_LAW,
            "code": code,
            "name": _text(args.get("name")),
            "title": title,
            "summary": _text(args.get("summary")) or title,
            "content": _text(args.get("content")),
            "level": _text(args.get("level")) or "国家级",
            "issuer": _text(args.get("issuer")),
            "published_at": _text(args.get("published_at")),
            "penalties": _text(args.get("penalties")),
            "law_ref": _text(args.get("law_ref")),
            "icon_name": _text(args.get("icon_name")) or "shield",
            "hot_score": _as_int(args.get("hot_score")),
            "author_id": author_id,
            "author_name": author_name,
            "is_official": role == "ADMIN",
        }

    return {
        "id": _text(args.get("id")) or f"case_{suffix}",
        "kind": KIND_CASE,
        "title": title,
        "badge": _text(args.get("badge")) or "新增避坑案例",
        "industry": _text(args.get("industry")) or "综合行业",
        "violation": _text(args.get("violation")),
        "consequence": _text(args.get("consequence")),
        "lesson": _text(args.get("lesson")),
        "badge_color": _text(args.get("badge_color")) or "#5B6472",
        "hot_score": _as_int(args.get("hot_score")),
        "author_id": author_id,
        "author_name": author_name,
        "is_official": role == "ADMIN",
    }


@operator(
    "calc.compliance.query",
    category="CALC",
    description="Normalise a compliance catalog query for one declared kind",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Translate a catalog query into generic entity-store filters + paging."""
    kind = _text(params.get("kind") or args.get("kind")).lower()
    filters: dict[str, Any] = {"kind": kind} if kind else {}

    level = _text(args.get("level"))
    if level and level.upper() != "ALL":
        filters["level"] = level

    industry = _text(args.get("industry"))
    if industry and industry.upper() != "ALL":
        filters["industry"] = industry

    dimension_id = _text(args.get("dimension_id"))
    if dimension_id and dimension_id.upper() != "ALL":
        filters["dimension_id"] = dimension_id

    return {
        "kind": kind,
        "filters": filters,
        "search": _text(args.get("search")) or None,
        "page": int(args.get("page") or 1),
        "page_size": int(args.get("page_size") or params.get("default_page_size") or 50),
    }


@operator(
    "calc.compliance.page",
    category="CALC",
    description="Derive pagination metadata from a compliance document list",
)
def page(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Slice one catalog page and attach pagination metadata."""
    items = args.get("items") or []
    total = int(args.get("total") if args.get("total") is not None else len(items))
    page_no = max(1, int(args.get("page") or 1))
    page_size = max(1, min(200, int(args.get("page_size") or 50)))
    total_pages = max(1, -(-total // page_size))
    start = (page_no - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page_no,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": start + page_size < total,
    }


def _checkpoints(items: Any) -> list[dict[str, Any]]:
    return [item for item in (items or []) if isinstance(item, dict)]


def _passed_set(passed_item_ids: Any) -> set[str]:
    if passed_item_ids is None:
        return set()
    if isinstance(passed_item_ids, str):
        raise ValueError("passed_item_ids 必须为检查项 ID 数组")
    if not isinstance(passed_item_ids, (list, tuple, set)):
        raise ValueError("passed_item_ids 必须为检查项 ID 数组")
    return {str(item) for item in passed_item_ids}


@operator(
    "calc.compliance.score",
    category="CALC",
    description="Compute the weighted compliance self-audit score and grade",
)
def score(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Score one checklist against the passed item ids (weighted, 0-100)."""
    items = _checkpoints(args.get("items"))
    passed = _passed_set(args.get("passed_item_ids"))

    total_weight = sum(_as_int(item.get("weight")) for item in items)
    earned_weight = sum(
        _as_int(item.get("weight")) for item in items if str(item.get("id") or "") in passed
    )
    failed_items = [item for item in items if str(item.get("id") or "") not in passed]
    passed_count = len(items) - len(failed_items)

    value = int(round((earned_weight / total_weight) * 100)) if total_weight > 0 else 0
    if value >= settings.compliance_grade_excellent:
        grade = "EXCELLENT"
    elif value >= settings.compliance_grade_good:
        grade = "GOOD"
    elif value >= settings.compliance_grade_warning:
        grade = "WARNING"
    else:
        grade = "CRITICAL"

    return {
        "score": value,
        "grade": grade,
        "total_items": len(items),
        "passed_items_count": passed_count,
        "failed_items_count": len(failed_items),
        "total_weight": total_weight,
        "earned_weight": earned_weight,
        "failed_items": failed_items,
    }


@operator(
    "calc.compliance.dimension_scores",
    category="CALC",
    description="Aggregate compliance audit results per defence dimension",
)
def dimension_scores(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Compute one weighted score card per ``dimension_id`` (the six defence lines)."""
    items = _checkpoints(args.get("items"))
    passed = _passed_set(args.get("passed_item_ids"))

    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        dimension_id = _text(item.get("dimension_id")) or "UNCLASSIFIED"
        bucket = buckets.setdefault(
            dimension_id,
            {
                "dimension_id": dimension_id,
                "total_items": 0,
                "passed_items_count": 0,
                "total_weight": 0,
                "earned_weight": 0,
            },
        )
        weight = _as_int(item.get("weight"))
        passed_item = str(item.get("id") or "") in passed
        bucket["total_items"] += 1
        bucket["total_weight"] += weight
        if passed_item:
            bucket["passed_items_count"] += 1
            bucket["earned_weight"] += weight

    cards: list[dict[str, Any]] = []
    for dimension_id in sorted(buckets):
        bucket = buckets[dimension_id]
        total_weight = bucket["total_weight"]
        bucket["failed_items_count"] = bucket["total_items"] - bucket["passed_items_count"]
        bucket["score"] = (
            int(round((bucket["earned_weight"] / total_weight) * 100)) if total_weight > 0 else 0
        )
        cards.append(bucket)

    return {"dimension_scores": cards, "dimension_count": len(cards)}


@operator(
    "calc.compliance.rank",
    category="CALC",
    description="Rank compliance risk items by severity then weight",
)
def rank(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Order risk items so the most severe / heaviest findings surface first."""
    items = _checkpoints(args.get("items"))
    ranked = sorted(
        items,
        key=lambda item: (
            _SEVERITY_ORDER.get(_text(item.get("severity")).upper(), 0),
            _as_int(item.get("weight")),
            _text(item.get("title")),
        ),
        reverse=True,
    )
    return {"risk_items": ranked, "risk_count": len(ranked)}


@operator(
    "assemble.compliance.audit_report",
    category="ASSEMBLE",
    description="Assemble the compliance audit report from score, dimensions and risks",
)
def audit_report(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Merge scoring, dimension cards and ranked risks into the public report."""
    scored = args.get("scored") or {}
    dimension = args.get("dimensions") or {}
    ranked = args.get("ranked") or {}
    risk_items = ranked.get("risk_items") or scored.get("failed_items") or []

    suggestions: list[str] = []
    for item in risk_items:
        advice = _text(item.get("advice"))
        if advice and advice not in suggestions:
            suggestions.append(advice)

    legal_help = None
    if risk_items:
        template = settings.compliance_legal_help_recommendation_template
        legal_help = template.format(
            count=len(risk_items),
            first=_text(risk_items[0].get("title")),
        )

    report = {
        "score": scored.get("score", 0),
        "grade": scored.get("grade", "CRITICAL"),
        "total_items": scored.get("total_items", 0),
        "passed_items_count": scored.get("passed_items_count", 0),
        "failed_items_count": scored.get("failed_items_count", 0),
        "total_weight": scored.get("total_weight", 0),
        "earned_weight": scored.get("earned_weight", 0),
        "dimension_scores": dimension.get("dimension_scores") or [],
        "dimension_count": dimension.get("dimension_count", 0),
        "risk_items": risk_items,
        "remedy_suggestions": suggestions,
        "legal_help_recommendation": legal_help,
    }
    return {**report, "audit_report": report}


@operator(
    "assemble.compliance.published",
    category="ASSEMBLE",
    description="Project a persisted compliance item as the publish response",
)
def published(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Expose the created law/case document under the publish contract key."""
    return {"created_entry": args.get("entity") or {}}
