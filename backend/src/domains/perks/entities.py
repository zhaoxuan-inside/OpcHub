"""Declarative entity specifications for the perks (生态特权) domain.

This module is data only: it tells the generic entity runtime which documents
exist, how they are keyed, validated and searched. No business rules live here.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.perks.models import PerkClaimResponse, PerkResponse

ENTITY_PERK = "perk.item"
ENTITY_PERK_CLAIM = "perk.claim"

perk_entity = EntitySpec(
    name=ENTITY_PERK,
    family="perks.items",
    model=PerkResponse,
    id_prefix="perk",
    search_fields=("name", "provider", "summary"),
    owner_field="author_id",
    default_order="-priority",
    defaults={
        "category": "TOKEN",
        "value_cny": 0.0,
        "quota_remaining": 100,
        "priority": 60,
        "status": "PUBLISHED",
        "highlights": [],
        "author_id": "",
        "author_name": None,
        "is_official": False,
        "claim_count": 0,
        "like_count": 0,
        "favorite_count": 0,
        "love_count": 0,
        "comment_count": 0,
    },
)

# A claim is a relational row: one maker may claim one announcement at most once.
# The composite key is what makes ``guard.unique`` + ``entity.create`` idempotent
# by construction.
perk_claim_entity = EntitySpec(
    name=ENTITY_PERK_CLAIM,
    family="perks.claims",
    model=PerkClaimResponse,
    key_fields=("user_id", "perk_id"),
    id_prefix="clm",
    default_order="-created_at",
    defaults={"status": "ACTIVATED"},
)

entity_store.register(perk_entity)
entity_store.register(perk_claim_entity)
