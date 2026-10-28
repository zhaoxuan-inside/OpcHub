"""Declarative entity specifications for the policy domain.

This module contains no business logic and no orchestration. It only tells the
generic entity runtime which documents exist, how they are keyed, validated and
searched. The persisted family name (``policies.items``) is inherited from the
legacy service so existing snapshots stay readable.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.policies.models import PolicyResponse

ENTITY_POLICY = "policy.item"

policy_entity = EntitySpec(
    name=ENTITY_POLICY,
    family="policies.items",
    model=PolicyResponse,
    id_prefix="pol",
    search_fields=("title", "summary", "legal_basis", "region", "code"),
    owner_field="author_id",
    default_order="-created_at",
    defaults={
        "policy_level": "国家级",
        "category": "TAX",
        "subsidy_amount_max": 0.0,
        "eligible_conditions": [],
        "code": None,
        "region": "全国统一",
        "deadline": "常年有效",
        "action_text": "匹配资格",
        "author_id": "",
        "author_name": None,
        "is_official": False,
        "like_count": 0,
        "favorite_count": 0,
        "love_count": 0,
        "comment_count": 0,
    },
)

entity_store.register(policy_entity)
