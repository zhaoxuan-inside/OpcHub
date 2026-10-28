"""Single-responsibility pure function operators for the demand marketplace.

Only calculations / normalisation / assembly live here. Guards, validation,
persistence, notifications, metrics and audit are provided by the generic
operator kernel (``src.core.operators``); business rules are declared in
``config/scenarios/demands.yaml``.

Rules honoured by this module: no I/O, no orchestration, no call to another
operator, no cross-domain import.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.operators.sdk import operator

CATEGORIES = ("DEV", "AI", "TAX", "LEGAL", "BIZ")
DEFAULT_CATEGORY = "DEV"
DEFAULT_DEADLINE_DAYS = 14
MAX_DEADLINE_DAYS = 365
DEFAULT_PAGE_SIZE = 6


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_iso(value: Any) -> str:
    return "" if value is None else str(value)


@operator(
    "calc.demand.deadline",
    category="CALC",
    description="Derive the bidding deadline from a requested window in days",
)
def deadline(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    raw_days = args.get("deadline_days")
    days = int(raw_days) if raw_days not in (None, "") else DEFAULT_DEADLINE_DAYS
    days = max(1, min(MAX_DEADLINE_DAYS, days))
    raw_now = args.get("now")
    base = datetime.fromisoformat(str(raw_now)) if raw_now else datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return {"deadline_days": days, "deadline_at": (base + timedelta(days=days)).isoformat()}


@operator(
    "calc.demand.normalize_publish",
    category="CALC",
    description="Normalise a demand publish payload and bind the creator identity from context",
)
def normalize_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    role = str(context.get("user_role") or "MAKER").upper()
    category = _as_text(args.get("category") or DEFAULT_CATEGORY).upper()
    # Display name is server-resolved: the gateway context wins so a client cannot
    # impersonate another maker (``creator_name`` is only a fallback).
    creator_name = _as_text(context.get("nickname") or args.get("creator_name")) or None
    return {
        "title": _as_text(args.get("title")),
        "description": _as_text(args.get("description")),
        "budget_cny": float(args.get("budget_cny") or 0.0),
        "category": category if category in CATEGORIES else DEFAULT_CATEGORY,
        "deadline_at": _as_iso(args.get("deadline_at")),
        "creator_id": _as_text(context.get("user_id")),
        "creator_name": creator_name,
        "is_official": role == "ADMIN",
        "status": "OPEN",
        "bidders_count": 0,
    }


@operator(
    "calc.demand.query",
    category="CALC",
    description="Normalise demand list query parameters into generic store filters and paging",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    category = _as_text(args.get("category"))
    status = _as_text(args.get("status"))
    filters: dict[str, Any] = {}
    if category and category.upper() != "ALL":
        filters["category"] = {"in": [category, category.upper(), category.lower()]}
    if status and status.upper() != "ALL":
        filters["status"] = {"in": [status, status.upper(), status.lower()]}

    raw_page = args.get("page")
    paged = raw_page not in (None, "", 0, "0", False)
    page_no = max(1, int(raw_page)) if paged else 1
    page_size = max(1, min(100, int(args.get("page_size") or DEFAULT_PAGE_SIZE)))

    order = _as_text(params.get("default_order")) or "-created_at"
    sort = _as_text(args.get("sort")).lower()
    if sort == "budget":
        order = "-budget_cny"
    elif sort == "hot":
        order = "-bidders_count"

    return {
        "filters": filters,
        "search": _as_text(args.get("search")) or None,
        "order": order,
        "page": page_no,
        "page_size": page_size,
        "offset": (page_no - 1) * page_size if paged else None,
        "limit": page_size if paged else None,
        "paged": paged,
    }


@operator(
    "assemble.demand.list",
    category="ASSEMBLE",
    description="Project a demand listing as either a flat feed or a paged envelope",
)
def list_response(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = [dict(item) for item in (args.get("items") or []) if isinstance(item, dict)]
    total = int(args.get("total") if args.get("total") is not None else len(items))
    if not args.get("paged"):
        return {"response": items}

    page_no = max(1, int(args.get("page") or 1))
    page_size = max(1, min(100, int(args.get("page_size") or DEFAULT_PAGE_SIZE)))
    return {
        "response": {
            "items": items,
            "total": total,
            "page": page_no,
            "page_size": page_size,
            "total_pages": max(1, math.ceil(total / page_size)),
            "has_more": page_no * page_size < total,
            "from_cache": False,
        }
    }


@operator(
    "calc.demand.normalize_bid",
    category="CALC",
    description="Normalise a bid payload and bind the bidder identity from context",
)
def normalize_bid(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "demand_id": _as_text(args.get("demand_id")),
        "bidder_id": _as_text(context.get("user_id")),
        "bid_amount_cny": float(args.get("bid_amount_cny") or 0.0),
        "delivery_days": int(args.get("delivery_days") or 0),
        "proposal_text": _as_text(args.get("proposal_text")),
        "status": "SUBMITTED",
    }


@operator(
    "calc.demand.bid_counter",
    category="CALC",
    description="Recompute the bidders counter of a demand document",
)
def bid_counter(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    current = int(args.get("bidders_count") or 0)
    delta = args.get("delta")
    return {
        "id": _as_text(args.get("demand_id")),
        "bidders_count": max(0, current + (1 if delta is None else int(delta))),
    }


@operator(
    "assemble.demand.detail",
    category="ASSEMBLE",
    description="Assemble one demand detail document together with its bids",
)
def demand_detail(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    demand = args.get("demand") if isinstance(args.get("demand"), dict) else {}
    bids = [dict(bid) for bid in (args.get("bids") or []) if isinstance(bid, dict)]
    return {"demand": demand, "bids": bids, "bid_count": len(bids)}


@operator(
    "assemble.demand.publish_result",
    category="ASSEMBLE",
    description="Project the publish API result from the created demand document",
)
def publish_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    doc = args.get("entity") if isinstance(args.get("entity"), dict) else {}
    return {"created_demand": doc, "response": doc}


@operator(
    "assemble.demand.bid_result",
    category="ASSEMBLE",
    description="Project the bidding API result from the created bid document",
)
def bid_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    doc = args.get("entity") if isinstance(args.get("entity"), dict) else {}
    return {"created_bid": doc, "response": doc}
