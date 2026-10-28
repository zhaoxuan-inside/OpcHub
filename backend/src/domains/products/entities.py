"""Declarative entity specifications for the product showcase domain.

This module contains no business logic and no orchestration. It only tells the
generic entity runtime which documents exist, how they are keyed, validated and
searched.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.products.models import ProductResponse

ENTITY_PRODUCT = "product.item"

product_entity = EntitySpec(
    name=ENTITY_PRODUCT,
    family="products.items",
    model=ProductResponse,
    id_prefix="prd",
    search_fields=("title", "tagline", "description", "author_name"),
    owner_field="author_id",
    default_order="-upvote_count",
    defaults={
        "author_id": "",
        "author_name": "@创客",
        "is_official": False,
        "category": "AI",
        "pricing_model": "SUBSCRIPTION",
        "price_cny": 0.0,
        "version": "1.0.0",
        "screenshots": [],
        "upvote_count": 0,
        "favorite_count": 0,
        "love_count": 0,
        "comment_count": 0,
        "status": "PUBLISHED",
    },
)

entity_store.register(product_entity)
