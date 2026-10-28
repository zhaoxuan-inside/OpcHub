"""Product Showcase service managing maker products and upvotes."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.domains.products.models import ProductCreate, ProductResponse
from src.infrastructure.database.persistence import domain_persistence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProductService:
    """Manages independent maker products."""

    def __init__(self):
        self._products: Dict[str, ProductResponse] = {}
        # Key: cache_key -> (timestamp, data_dict)
        self._cache: Dict[str, tuple[float, Any]] = {}

    def _require_db(self) -> None:
        """Product content is database-backed; refuse memory-only mutations."""
        domain_persistence.require("products")

    def invalidate_cache(self) -> int:
        """Evict all cached products list pages."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_cache(self, key: str, ttl_seconds: float = 120.0) -> Optional[Any]:
        """Fetch cached entry if within TTL."""
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, data = entry
        import time
        if time.time() - ts > ttl_seconds:
            self._cache.pop(key, None)
            return None
        return data

    def set_cache(self, key: str, data: Any) -> None:
        """Store cache entry with current timestamp."""
        import time
        self._cache[key] = (time.time(), data)

    def create_product(self, payload: ProductCreate) -> ProductResponse:
        self._require_db()
        pid = str(uuid.uuid4())
        now = utc_now_iso()
        product = ProductResponse(
            id=pid,
            author_id=payload.author_id or "usr_maker_anonymous",
            author_name=payload.author_name or "@创客",
            is_official=payload.is_official,
            title=payload.title,
            tagline=payload.tagline,
            description=payload.description,
            icon_url=payload.icon_url,
            category=payload.category,
            version=payload.version or "1.0.0",
            pricing_model=payload.pricing_model,
            price_cny=payload.price_cny,
            official_url=payload.official_url,
            download_url=payload.download_url,
            demo_url=payload.demo_url,
            screenshots=payload.screenshots or [],
            upvote_count=0,
            status="PUBLISHED",
            created_at=now,
            updated_at=now,
        )
        self._products[pid] = product
        domain_persistence.write("products.items", pid, product)
        self.invalidate_cache()
        return product

    def validate_publish_payload(self, inputs: dict) -> dict:
        title = inputs.get("title", "").strip()
        tagline = inputs.get("tagline", "").strip()
        desc = inputs.get("description", "").strip()
        price = float(inputs.get("price_cny", 0.0))
        if len(title) < 2:
            raise ValueError("Product title must be at least 2 characters long")
        if len(tagline) < 5 and len(desc) < 5:
            raise ValueError("Product tagline or description must be at least 5 characters long")
        if price < 0:
            raise ValueError("Product price cannot be negative")
        return {
            "guard_passed": True,
            "title": title,
            "tagline": tagline,
            "description": desc or tagline,
            "category": inputs.get("category", "DEV"),
            "pricing_model": inputs.get("pricing_model", "FREE" if price == 0 else "ONE_TIME"),
            "price_cny": price,
            "icon_url": inputs.get("icon_url"),
            "version": inputs.get("version", "1.0.0"),
            "official_url": inputs.get("official_url"),
            "download_url": inputs.get("download_url"),
            "demo_url": inputs.get("demo_url"),
            "author_id": inputs.get("author_id", ""),
            "author_name": inputs.get("author_name"),
            "screenshots": inputs.get("screenshots", []),
        }

    def list_products(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: int = 6,
        **kwargs,
    ) -> Any:
        import math

        # 1. Unpaged full list query (backward-compatible with unit tests and batch lookups)
        if page is None:
            products = list(self._products.values())
            if category and category.lower() != "all":
                products = [p for p in products if p.category == category or category.lower() in p.category.lower()]
            if search and search.strip():
                q = search.strip().lower()
                products = [
                    p for p in products
                    if (p.title and q in p.title.lower())
                    or (p.tagline and q in p.tagline.lower())
                    or (p.description and q in p.description.lower())
                    or (p.author_name and q in p.author_name.lower())
                ]
            products.sort(key=lambda p: p.upvote_count, reverse=True)
            return products

        # 2. Paged query with server-side TTL caching (120 seconds)
        clean_page = max(1, int(page))
        clean_size = max(1, min(100, int(page_size)))
        cache_key = f"{category or 'ALL'}:{search or ''}:{clean_page}:{clean_size}"
        cached = self.get_cache(cache_key)
        if cached is not None:
            cached_res = dict(cached)
            cached_res["from_cache"] = True
            return cached_res

        all_prods = list(self._products.values())
        if category and category.lower() != "all":
            all_prods = [p for p in all_prods if p.category == category or category.lower() in p.category.lower()]
        if search and search.strip():
            q = search.strip().lower()
            all_prods = [
                p for p in all_prods
                if (p.title and q in p.title.lower())
                or (p.tagline and q in p.tagline.lower())
                or (p.description and q in p.description.lower())
                or (p.author_name and q in p.author_name.lower())
            ]
        all_prods.sort(key=lambda p: p.upvote_count, reverse=True)

        total = len(all_prods)
        start = (clean_page - 1) * clean_size
        end = start + clean_size
        slice_items = all_prods[start:end]
        has_more = end < total
        total_pages = math.ceil(total / clean_size) if clean_size > 0 else 1

        res = {
            "items": [p.model_dump() if hasattr(p, "model_dump") else p for p in slice_items],
            "total": total,
            "page": clean_page,
            "page_size": clean_size,
            "total_pages": total_pages,
            "has_more": has_more,
            "from_cache": False,
        }
        self.set_cache(cache_key, res)
        return res

    def get_product(self, product_id: str) -> Optional[ProductResponse]:
        return self._products.get(product_id)

    def delete_product(self, product_id: str) -> bool:
        """Physically delete product for Saga reverse compensation."""
        self._require_db()
        if product_id in self._products:
            del self._products[product_id]
            domain_persistence.delete("products.items", product_id)
            self.invalidate_cache()
            return True
        return False

    def hydrate_items(self, rows: List[Dict]) -> int:
        for r in rows:
            self._products[r["id"]] = ProductResponse(**r)
        self.invalidate_cache()
        return len(rows)

    def clear(self) -> None:
        """Reset products state for isolated test execution."""
        self._products.clear()
        self.invalidate_cache()


product_service = ProductService()

domain_persistence.register("products.items", product_service.hydrate_items)

