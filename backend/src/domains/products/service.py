"""Product Showcase service managing maker products and upvotes."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.domains.products.models import ProductCreate, ProductResponse
from src.infrastructure.database.persistence import domain_persistence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProductService:
    """Manages independent maker products."""

    def __init__(self):
        self._products: Dict[str, ProductResponse] = {}

    def create_product(self, payload: ProductCreate) -> ProductResponse:
        pid = str(uuid.uuid4())
        now = utc_now_iso()
        product = ProductResponse(
            id=pid,
            author_id=payload.author_id,
            title=payload.title,
            tagline=payload.tagline,
            description=payload.description,
            category=payload.category,
            pricing_model=payload.pricing_model,
            price_cny=payload.price_cny,
            demo_url=payload.demo_url,
            upvote_count=0,
            status="PUBLISHED",
            created_at=now,
            updated_at=now,
        )
        self._products[pid] = product
        domain_persistence.write("products.items", pid, product)
        return product

    def list_products(self, category: Optional[str] = None) -> List[ProductResponse]:
        products = list(self._products.values())
        if category:
            products = [p for p in products if p.category == category]
        products.sort(key=lambda p: p.upvote_count, reverse=True)
        return products

    def upvote_product(self, product_id: str) -> ProductResponse:
        if product_id not in self._products:
            raise KeyError(f"Product {product_id} not found")
        prod = self._products[product_id]
        prod.upvote_count += 1
        domain_persistence.write("products.items", product_id, prod)
        return prod


    def delete_product(self, product_id: str) -> bool:
        """Physically delete product for Saga reverse compensation."""
        if product_id in self._products:
            del self._products[product_id]
            domain_persistence.delete("products.items", product_id)
            return True
        return False

    def hydrate_items(self, rows: List[Dict]) -> int:
        for r in rows:
            self._products[r["id"]] = ProductResponse(**r)
        return len(rows)

    def clear(self) -> None:
        """Reset products state for isolated test execution."""
        self._products.clear()


product_service = ProductService()

domain_persistence.register("products.items", product_service.hydrate_items)
