"""Declarative entity specifications for the demand marketplace domain.

This module is data only: it tells the generic entity runtime which documents
exist, how they are keyed, validated and searched. No business rule and no
orchestration lives here. The persisted family names (``demands.items`` /
``demands.bids``) are inherited from the legacy services so existing snapshots
stay readable.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.demands.models import BidResponse, DemandResponse

ENTITY_DEMAND = "demands.item"
ENTITY_BID = "demands.bid"

demand_entity = EntitySpec(
    name=ENTITY_DEMAND,
    family="demands.items",
    model=DemandResponse,
    key_fields=("id",),
    id_prefix="dmd",
    search_fields=("title", "description", "creator_name"),
    owner_field="creator_id",
    default_order="-created_at",
    defaults={
        "creator_name": None,
        "is_official": False,
        "bidders_count": 0,
        "like_count": 0,
        "favorite_count": 0,
        "love_count": 0,
        "comment_count": 0,
        "status": "OPEN",
    },
)

# A bid is one relational row per maker submission: it always points at the
# demand it answers and is owned by the bidding maker.
bid_entity = EntitySpec(
    name=ENTITY_BID,
    family="demands.bids",
    model=BidResponse,
    key_fields=("id",),
    id_prefix="bid",
    search_fields=("proposal_text",),
    owner_field="bidder_id",
    default_order="-created_at",
    defaults={"status": "SUBMITTED"},
)

entity_store.register(demand_entity)
entity_store.register(bid_entity)
