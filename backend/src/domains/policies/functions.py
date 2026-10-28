"""Single-responsibility pure function operators for the policy domain.

Only calculations / normalisation / assembly live here. Storage is handled by
``entity.*`` operators, guards by ``guard.*``, validation by ``validate.*``.
There is no I/O, no orchestration and no cross-domain import.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.config import settings
from src.core.operators.sdk import operator

DEFAULT_REGION = "全国统一"
DEFAULT_DEADLINE = "常年有效"
DEFAULT_ACTION_TEXT = "匹配资格"
_TOKEN_SPLIT = re.compile(r"[\s,，、;；/]+")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    return [str(item).strip() for item in value if str(item).strip()]


@operator(
    "calc.policy.normalize_publish",
    category="CALC",
    description="Normalise a policy publish payload and apply declarative defaults",
)
def normalize_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Project one policy publish payload into a persistable document."""
    title = str(args.get("title") or "").strip()
    summary = str(args.get("summary") or "").strip()
    legal_basis = str(args.get("legal_basis") or "").strip()
    code = str(args.get("code") or "").strip()
    if not code:
        year = datetime.now(timezone.utc).year
        code = f"POL-{year}-{uuid.uuid4().hex[:4].upper()}"

    role = str(context.get("user_role") or "MAKER").upper()
    is_official = args.get("is_official")
    if is_official is None:
        is_official = role == "ADMIN"

    author_id = str(context.get("user_id") or args.get("author_id") or "")
    author_name = args.get("author_name") or context.get("nickname") or "@创客"

    return {
        "title": title,
        "policy_level": str(args.get("policy_level") or "国家级").strip(),
        "category": str(args.get("category") or "TAX").strip(),
        "subsidy_amount_max": _as_float(args.get("subsidy_amount_max")),
        "summary": summary,
        "eligible_conditions": _as_str_list(args.get("eligible_conditions")),
        "legal_basis": legal_basis,
        "code": code,
        "region": str(args.get("region") or DEFAULT_REGION).strip(),
        "deadline": str(args.get("deadline") or DEFAULT_DEADLINE).strip(),
        "action_text": str(args.get("action_text") or DEFAULT_ACTION_TEXT).strip(),
        "author_id": author_id,
        "author_name": author_name,
        "is_official": bool(is_official),
    }


@operator(
    "calc.policy.query",
    category="CALC",
    description="Normalise policy list query parameters into generic store filters",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Translate a policy catalog query into generic filters plus pagination."""
    filters: dict[str, Any] = {}

    category = str(args.get("category") or "ALL").strip()
    if category and category.upper() != "ALL":
        filters["category"] = {"in": [category, category.upper(), category.lower()]}

    policy_level = str(args.get("policy_level") or "ALL").strip()
    if policy_level and policy_level.upper() != "ALL":
        filters["policy_level"] = {"in": [policy_level]}

    return {
        "filters": filters,
        "search": str(args.get("search") or "").strip() or None,
        "page": int(args.get("page") or 1),
        "page_size": int(args.get("page_size") or 20),
    }


@operator(
    "calc.policy.page",
    category="CALC",
    description="Derive pagination metadata from a policy document list",
)
def page(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Slice one policy page and attach pagination metadata."""
    items = args.get("items") or []
    total = int(args.get("total") if args.get("total") is not None else len(items))
    page_no = max(1, int(args.get("page") or 1))
    page_size = max(1, min(100, int(args.get("page_size") or 20)))
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


@operator(
    "calc.policy.tax_assessment",
    category="CALC",
    description="Assess VAT exemption eligibility, applicable rate and estimated savings",
)
def tax_assessment(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Compute the VAT position of one maker's quarterly revenue."""
    income = _as_float(args.get("quarterly_income"))
    threshold = _as_float(args.get("threshold"), settings.vat_exemption_quarterly_threshold)
    standard_rate = _as_float(args.get("standard_rate"), settings.vat_standard_rate)
    threshold_desc = f"{int(threshold / 10000)} 万元"
    exempt = income <= threshold

    if exempt:
        applicable_rate = 0.0
        tax_savings = round(income * standard_rate, 2)
        explanation = (
            f"恭喜！您本季度申报销售额 ¥{income:,.2f} 未超过 {threshold_desc}免征红线，"
            f"享受国家小规模纳税人增值税全额免征，预计直接减免税额 ¥{tax_savings:,.2f}。"
        )
    else:
        applicable_rate = standard_rate
        tax_savings = 0.0
        explanation = (
            f"提示：您本季度申报销售额 ¥{income:,.2f} 已超出 {threshold_desc}免税门槛，"
            f"全额按 {int(standard_rate * 100)}% 简易计税缴纳增值税，"
            f"应纳增值税额约 ¥{round(income * standard_rate, 2):,.2f}。"
        )

    return {
        "eligible": exempt,
        "is_vat_exempt": exempt,
        "quarterly_income": income,
        "threshold_amount": threshold,
        "applicable_tax_rate": applicable_rate,
        "estimated_tax_savings": tax_savings,
        "explanation": explanation,
    }


def _search_tokens(search_query: Any, industry_keywords: Any) -> set[str]:
    tokens: set[str] = set()
    for part in _TOKEN_SPLIT.split(str(search_query or "")):
        if len(part) >= 2:
            tokens.add(part.lower())
    for keyword in industry_keywords or []:
        text = str(keyword).strip().lower()
        if text:
            tokens.add(text)
    return tokens


def _region_hits(region: str, policy: dict[str, Any]) -> bool:
    if not region:
        return False
    corpus = f"{policy.get('title') or ''} {policy.get('summary') or ''}"
    if region in corpus:
        return True
    policy_region = str(policy.get("region") or "")
    if not policy_region:
        return False
    return policy_region in region or region in policy_region


@operator(
    "calc.policy.rank_matches",
    category="CALC",
    description="Select and rank policies by eligibility and text relevance",
)
def rank_matches(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Score every policy against one eligibility profile and return the matches."""
    policies = [p for p in (args.get("policies") or []) if isinstance(p, dict)]
    region = str(args.get("region") or "").strip()
    is_vat_free = bool(args.get("is_vat_free"))
    tokens = _search_tokens(args.get("search_query"), args.get("industry_keywords"))

    matched: list[dict[str, Any]] = []
    relevance_scores: dict[str, float] = {}

    for policy in policies:
        policy_id = str(policy.get("id") or "")
        corpus = (
            f"{policy.get('title') or ''} {policy.get('summary') or ''} "
            f"{' '.join(_as_str_list(policy.get('eligible_conditions')))} "
            f"{policy.get('legal_basis') or ''}"
        ).lower()

        score = 0.5
        is_match = False

        if is_vat_free and str(policy.get("category") or "").upper() == "TAX":
            score += 0.3
            is_match = True
        if _region_hits(region, policy):
            score += 0.2
            is_match = True
        if tokens:
            hit_tokens = [token for token in tokens if token in corpus]
            if hit_tokens:
                score += 0.4 * (len(hit_tokens) / len(tokens))
                is_match = True

        if is_match:
            matched.append(policy)
        if policy_id:
            relevance_scores[policy_id] = min(1.0, round(score, 2))

    matched.sort(
        key=lambda p: (relevance_scores.get(str(p.get("id") or ""), 0.0), _as_float(p.get("subsidy_amount_max"))),
        reverse=True,
    )
    return {"matched_policies": matched, "relevance_scores": relevance_scores}


@operator(
    "assemble.policy.match_response",
    category="ASSEMBLE",
    description="Assemble the policy match response from tax assessment and ranked matches",
)
def match_response(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Merge one tax assessment and one ranking into the public match payload."""
    assessment = args.get("assessment") or {}
    ranking = args.get("ranking") or {}
    matched = ranking.get("matched_policies") or []
    return {
        "eligible": bool(assessment.get("eligible")),
        "is_vat_exempt": bool(assessment.get("is_vat_exempt")),
        "applicable_tax_rate": assessment.get("applicable_tax_rate", 0.0),
        "estimated_tax_savings": assessment.get("estimated_tax_savings", 0.0),
        "explanation": assessment.get("explanation") or "",
        "legal_basis": settings.vat_legal_basis,
        "matched_policies": matched,
        # Legacy alias kept for clients that still read ``matched_subsidies``.
        "matched_subsidies": matched,
        "matched_count": len(matched),
        "relevance_scores": ranking.get("relevance_scores") or {},
    }


@operator(
    "assemble.policy.published",
    category="ASSEMBLE",
    description="Project a persisted policy document as the publish response",
)
def published(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Expose the created document under the publish contract key."""
    return {"created_policy": args.get("entity") or {}}
