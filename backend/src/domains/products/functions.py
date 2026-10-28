"""Single-responsibility pure function operators for the product domain.

Only calculations / normalisation / assembly live here. Storage is handled by
``entity.*`` operators, guards by ``guard.*``, validation by ``validate.*``.
"""
from __future__ import annotations

import math
from typing import Any

from src.core.operators.sdk import operator


@operator(
    "calc.product.normalize_publish",
    category="CALC",
    description="Normalise a product publish payload and apply declarative defaults",
)
def normalize_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get("title") or "").strip()
    tagline = str(args.get("tagline") or "").strip()
    description = str(args.get("description") or "").strip()
    price = float(args.get("price_cny") or 0.0)
    role = str(context.get("user_role") or "MAKER").upper()
    author_id = str(context.get("user_id") or args.get("author_id") or "")
    return {
        "title": title,
        "tagline": tagline,
        "description": description or tagline,
        "category": str(args.get("category") or "AI"),
        "pricing_model": str(args.get("pricing_model") or ("FREE" if price == 0 else "ONE_TIME")),
        "price_cny": price,
        "demo_url": args.get("demo_url"),
        "icon_url": args.get("icon_url"),
        "version": args.get("version") or "1.0.0",
        "official_url": args.get("official_url"),
        "download_url": args.get("download_url"),
        "author_id": author_id,
        "author_name": args.get("author_name") or context.get("nickname") or "@创客",
        "is_official": role == "ADMIN",
        "screenshots": args.get("screenshots") or [],
        "status": "PUBLISHED",
    }


@operator(
    "calc.product.query",
    category="CALC",
    description="Normalise product list query parameters into generic store filters",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    category = str(args.get("category") or "ALL").strip()
    filters: dict[str, Any] = {}
    if category and category.upper() != "ALL":
        filters["category"] = {"in": [category, category.upper(), category.lower()]}
    return {
        "filters": filters,
        "search": (args.get("search") or "").strip() or None,
        "page": int(args.get("page") or 1),
        "page_size": int(args.get("page_size") or 6),
    }


@operator(
    "calc.product.page",
    category="CALC",
    description="Derive pagination metadata from a document list",
)
def page(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = args.get("items") or []
    total = int(args.get("total") or len(items))
    page_no = max(1, int(args.get("page") or 1))
    page_size = max(1, min(100, int(args.get("page_size") or 6)))
    total_pages = math.ceil(total / page_size) if total else 1
    start = (page_no - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page_no,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": start + page_size < total,
        "from_cache": False,
    }
