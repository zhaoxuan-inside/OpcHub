"""Product showcase data/query shim.

Business flow lives in ``config/scenarios/products.yaml``:
auth -> validate -> moderation -> normalise -> entity.create -> metric -> response.
This module keeps legacy imports and read helpers working.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from collections.abc import Iterator, MutableMapping

from src.core.entity import entity_store
from src.domains.products import entities as _entities  # noqa: F401 - registers the EntitySpec
from src.domains.products.functions import normalize_publish, query
from src.domains.products.models import ProductCreate, ProductResponse

ENTITY_PRODUCT = "product.item"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _ProductCatalog(MutableMapping):
    """Dict-like compatibility view that yields ProductResponse objects."""

    def __getitem__(self, key: str) -> ProductResponse:
        row = entity_store.get(ENTITY_PRODUCT, {"key": str(key)})
        if row is None:
            raise KeyError(key)
        return ProductResponse(**row)

    def __setitem__(self, key: str, value: Any) -> None:
        doc = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
        doc.setdefault("id", str(key))
        if entity_store.get(ENTITY_PRODUCT, {"key": str(doc["id"])}) is not None:
            entity_store.update(ENTITY_PRODUCT, doc, partial=False)
        else:
            entity_store.create(ENTITY_PRODUCT, doc)

    def __delitem__(self, key: str) -> None:
        if not entity_store.delete(ENTITY_PRODUCT, {"key": str(key)}):
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        rows, _total = entity_store.list(ENTITY_PRODUCT, {"limit": 0})
        return iter([str(row.get("id")) for row in rows])

    def __len__(self) -> int:
        return entity_store.count(ENTITY_PRODUCT)


class ProductService:
    """Thin compatibility layer over the generic entity store."""

    def __init__(self) -> None:
        self._products = _ProductCatalog()
        self._cache: Dict[str, tuple[float, Any]] = {}

    def invalidate_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_cache(self, key: str, ttl_seconds: float = 120.0) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, data = entry
        if time.time() - ts > ttl_seconds:
            self._cache.pop(key, None)
            return None
        return data

    def set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = (time.time(), data)

    def create_product(self, payload: ProductCreate) -> ProductResponse:
        context = {
            "user_id": payload.author_id or "",
            "user_role": "ADMIN" if payload.is_official else "MAKER",
            "nickname": payload.author_name,
        }
        doc = normalize_publish({}, payload.model_dump(), context)
        created = entity_store.create(ENTITY_PRODUCT, doc)
        self.invalidate_cache()
        return ProductResponse(**created)

    def validate_publish_payload(self, inputs: dict) -> dict:
        return normalize_publish({}, inputs, {})

    def list_products(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: int = 6,
        **kwargs,
    ) -> Any:
        normalized = query({}, {"category": category, "search": search, "page": page or 1, "page_size": page_size}, {})
        items, total = entity_store.list(
            ENTITY_PRODUCT,
            {"filters": normalized["filters"], "search": normalized["search"], "order": "-upvote_count", "limit": 0},
        )
        if page is None:
            return [ProductResponse(**row) for row in items]
        return page_result(items, total, normalized["page"], normalized["page_size"])

    def get_product(self, product_id: str) -> Optional[ProductResponse]:
        row = entity_store.get(ENTITY_PRODUCT, {"key": product_id})
        return ProductResponse(**row) if row else None

    def delete_product(self, product_id: str) -> bool:
        deleted = entity_store.delete(ENTITY_PRODUCT, {"key": product_id})
        if deleted:
            self.invalidate_cache()
        return deleted

    def hydrate_items(self, rows: List[Dict]) -> int:
        for row in rows:
            doc = ProductResponse(**row).model_dump(mode="json")
            try:
                entity_store.create(ENTITY_PRODUCT, doc)
            except ValueError:
                entity_store.update(ENTITY_PRODUCT, doc, partial=False)
        self.invalidate_cache()
        return len(rows)

    def clear(self) -> None:
        for key in list(self._products):
            entity_store.delete(ENTITY_PRODUCT, {"key": key})
        self.invalidate_cache()


def page_result(items: list[dict], total: int, page_no: int, page_size: int) -> dict:
    from src.domains.products.functions import page as page_fn

    return page_fn({}, {"items": items, "total": total, "page": page_no, "page_size": page_size}, {})


product_service = ProductService()
