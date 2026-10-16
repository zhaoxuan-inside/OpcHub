"""Product Showcase service managing maker products and upvotes."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.domains.products.models import ProductCreate, ProductResponse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProductService:
    """Manages independent maker products."""

    def __init__(self):
        self._products: Dict[str, ProductResponse] = {}
        self._seed_default_products()

    def _seed_default_products(self):
        items = [
            (
                "AI 提示词工程效率助手",
                "一键优化 Claude 3.5 与 GPT-4o 复杂系统提示词结构",
                "专为一人公司创客打造的提示词编译与沙箱测试工具，内置少样本链式提示词模版库。",
                "AI",
                "SUBSCRIPTION",
                39.00,
                "https://prompt.opchub.dev",
                48,
            ),
            (
                "出海跨境合规税务核算器",
                "自动解析 Stripe / PayPal 账单并一键生成申报表",
                "直连中国银行与外管局外汇结算申报标准，秒级计算综合增值税与跨境免税额度。",
                "SAAS",
                "ONE_TIME",
                299.00,
                "https://tax.opchub.dev",
                36,
            ),
            (
                "单兵自动化爬虫编排器",
                "零代码微内核 DAG 并发抓取与结构化入库引擎",
                "基于 Python AST 安全沙箱与代理池动态轮转，支持海量公开政策数据毫秒级同步。",
                "DEV",
                "FREE",
                0.00,
                "https://spider.opchub.dev",
                52,
            ),
        ]
        now = utc_now_iso()
        for title, tagline, desc, cat, pricing, price, url, upvotes in items:
            pid = str(uuid.uuid4())
            self._products[pid] = ProductResponse(
                id=pid,
                author_id="usr_2026_opc_9981",
                title=title,
                tagline=tagline,
                description=desc,
                category=cat,
                pricing_model=pricing,
                price_cny=price,
                demo_url=url,
                upvote_count=upvotes,
                status="PUBLISHED",
                created_at=now,
                updated_at=now,
            )

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
        return prod


product_service = ProductService()
