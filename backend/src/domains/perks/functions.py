"""Single-responsibility pure function operators for the perks domain.

Only calculations / normalisation / assembly live here. Storage is handled by
``entity.*`` operators, guards by ``guard.*``, validation by ``validate.*``.
No I/O, no orchestration, no cross-domain imports.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.config import settings
from src.core.operators.sdk import operator


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@operator(
    "calc.perk.publish_payload",
    category="CALC",
    description="Normalise an announcement publish payload and bind author identity",
)
def publish_payload(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    role = str(context.get("user_role") or "MAKER").upper()
    is_admin = role == "ADMIN"
    author_id = str((args.get("author_id") if is_admin else None) or context.get("user_id") or "")
    highlights = args.get("highlights") or []
    if not isinstance(highlights, list):
        highlights = []
    return {
        "name": str(args.get("name") or "").strip(),
        "provider": str(args.get("provider") or "").strip(),
        "value_cny": float(args.get("value_cny") or 0.0),
        "category": str(args.get("category") or settings.perk_default_category).strip().upper(),
        "summary": str(args.get("summary") or "").strip(),
        "quota_remaining": int(args.get("quota_remaining") or settings.perk_default_quota),
        "effective_start": str(args.get("effective_start") or "").strip() or None,
        "effective_end": str(args.get("effective_end") or "").strip() or None,
        "redeem_url": str(args.get("redeem_url") or "").strip() or None,
        "priority": int(args.get("priority") if args.get("priority") is not None else settings.perk_default_priority),
        "status": str(args.get("status") or settings.perk_default_status).strip().upper(),
        "highlights": [str(item).strip() for item in highlights if str(item).strip()][:8],
        "author_id": author_id,
        "author_name": (args.get("author_name") if is_admin else None) or context.get("nickname") or None,
        "is_official": is_admin,
    }


@operator(
    "calc.perk.query",
    category="CALC",
    description="Normalise public announcement board query parameters into store filters",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    category = str(args.get("category") or "").strip().upper()
    filters: dict[str, Any] = {"status": "PUBLISHED"}
    if category and category != "ALL":
        filters["category"] = {"in": [category]}
    else:
        category = ""
    return {"filters": filters, "category": category}


@operator(
    "assemble.perk.board",
    category="ASSEMBLE",
    description="Filter expired announcements and order the public board by priority and freshness",
)
def board(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = args.get("items") or []
    category = str(args.get("category") or "").strip().upper()
    today = _today()
    visible: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").upper() != "PUBLISHED":
            continue
        if category and category != "ALL" and str(item.get("category") or "").upper() != category:
            continue
        effective_end = str(item.get("effective_end") or "")
        if effective_end and effective_end < today:
            continue
        visible.append(dict(item))
    visible.sort(
        key=lambda item: (
            int(item.get("priority") or 0),
            str(item.get("effective_start") or ""),
        ),
        reverse=True,
    )
    return {"items": visible, "total": len(visible)}


@operator(
    "calc.perk.claim_eligibility",
    category="CALC",
    description="Decide whether an announcement can still be claimed right now",
)
def claim_eligibility(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    perk = args.get("perk") or {}
    if str(perk.get("status") or "").upper() != "PUBLISHED":
        raise ValueError("该优惠公告已下线，无法领取")
    effective_end = str(perk.get("effective_end") or "")
    if effective_end and effective_end < _today():
        raise ValueError("该优惠已过有效期，无法领取")
    if int(perk.get("quota_remaining") or 0) <= 0:
        raise ValueError(f"优惠「{perk.get('name') or perk.get('id') or ''}」已被领完")
    return {"claimable": True}


@operator(
    "calc.perk.claim_counters",
    category="CALC",
    description="Derive the post-claim quota and claim counters for an announcement",
)
def claim_counters(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    perk = args.get("perk") or {}
    return {
        "quota_remaining": max(0, int(perk.get("quota_remaining") or 0) - 1),
        "claim_count": int(perk.get("claim_count") or 0) + 1,
    }


@operator(
    "calc.perk.release_counters",
    category="CALC",
    description="Derive the post-revocation quota and claim counters for an announcement",
)
def release_counters(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    perk = args.get("perk") or {}
    return {
        "quota_remaining": int(perk.get("quota_remaining") or 0) + 1,
        "claim_count": max(0, int(perk.get("claim_count") or 0) - 1),
    }


@operator(
    "calc.perk.voucher",
    category="CALC",
    description="Generate one redemption voucher code",
)
def voucher(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    prefix = str(params.get("prefix") or "OPC")
    suffix = str(params.get("suffix") or datetime.now(timezone.utc).year)
    return {"voucher_code": f"{prefix}-{uuid.uuid4().hex[:6].upper()}-{suffix}"}


@operator(
    "calc.perk.claim_identity",
    category="CALC",
    description="Resolve the claiming maker from context, falling back to the legacy payload field",
)
def claim_identity(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    user_id = str(context.get("user_id") or args.get("user_id") or "").strip()
    if not user_id:
        raise PermissionError("领取优惠需要登录，请先登录创客账号")
    return {"user_id": user_id}


@operator(
    "assemble.perk.claim",
    category="ASSEMBLE",
    description="Assemble one claim document from an announcement and a voucher code",
)
def assemble_claim(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    perk = args.get("perk") or {}
    provider = str(perk.get("provider") or "")
    return {
        "claim_id": f"clm_{uuid.uuid4().hex[:16]}",
        "perk_id": str(perk.get("id") or args.get("perk_id") or ""),
        "perk_name": str(perk.get("name") or ""),
        "user_id": str(args.get("user_id") or ""),
        "voucher_code": str(args.get("voucher_code") or ""),
        "status": "ACTIVATED",
        "instructions": f"核销说明：请在 {provider} 控制台优惠券兑换入口输入此凭据。",
        "created_at": _now_iso(),
    }


@operator(
    "assemble.perk.publish_result",
    category="ASSEMBLE",
    description="Project the publish API result from the created announcement document",
)
def publish_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    doc = args.get("entity") if isinstance(args.get("entity"), dict) else {}
    return {"created_perk": doc, "response": doc}


@operator(
    "assemble.perk.claim_result",
    category="ASSEMBLE",
    description="Project the claim API result from the created claim document",
)
def claim_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    doc = args.get("entity") if isinstance(args.get("entity"), dict) else {}
    return {"created_claim": doc, "response": doc}
