"""Declarative entity specifications for the loyalty domain.

Data only: this module tells the generic entity runtime which documents exist,
how they are keyed, validated and searched. Persistence family names are
inherited from the legacy ``loyalty_service`` so existing ``domain_snapshots``
rows stay readable. Points rules / membership plans are configuration assets
(``src.domains.loyalty.functions``) rather than entities.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.loyalty.models import MembershipInfo, PointsLedgerEntry, RedemptionOrder, RewardItem

ENTITY_ACCOUNT = "loyalty.account"
ENTITY_LEDGER = "loyalty.ledger"
ENTITY_MEMBERSHIP = "loyalty.membership"
ENTITY_ORDER = "loyalty.order"
ENTITY_ITEM = "loyalty.item"

account_entity = EntitySpec(
    name=ENTITY_ACCOUNT,
    family="loyalty.accounts",
    key_fields=("uid",),
    id_prefix="acc",
    owner_field="uid",
    default_order="-updated_at",
    defaults={
        "balance": 0,
        "frozen": 0,
        "debt": 0,
        "total_earned": 0,
        "total_spent": 0,
        "growth": 0,
        "reputation": 80,
    },
)

ledger_entity = EntitySpec(
    name=ENTITY_LEDGER,
    family="loyalty.ledger",
    model=PointsLedgerEntry,
    key_fields=("id",),
    id_prefix="pl",
    owner_field="uid",
    default_order="-created_at",
    defaults={
        "status": "SETTLED",
        "ref_type": "",
        "ref_id": "",
        "actor_id": "",
        "idempotency_key": "",
        "note": "",
        "expires_at": "",
    },
)

membership_entity = EntitySpec(
    name=ENTITY_MEMBERSHIP,
    family="loyalty.memberships",
    model=MembershipInfo,
    key_fields=("uid",),
    id_prefix="mem",
    owner_field="uid",
    default_order="-updated_at",
    defaults={
        "tier": "STANDARD",
        "tier_name": "标准创客",
        "source": "",
        "status": "NONE",
        "plan_code": "",
        "started_at": "",
        "expires_at": "",
        "days_left": 0,
        "auto_renew": False,
        "benefits": [],
    },
)

order_entity = EntitySpec(
    name=ENTITY_ORDER,
    family="loyalty.orders",
    model=RedemptionOrder,
    key_fields=("id",),
    id_prefix="ord",
    owner_field="uid",
    default_order="-created_at",
    defaults={
        "status": "COMPLETED",
        "address": None,
        "tracking_no": "",
        "note": "",
        "idempotency_key": "",
    },
)

item_entity = EntitySpec(
    name=ENTITY_ITEM,
    family="loyalty.items",
    model=RewardItem,
    key_fields=("code",),
    id_prefix="itm",
    search_fields=("name", "description"),
    default_order="points_price",
    defaults={
        "stock": 0,
        "per_user_limit": 1,
        "icon": "gift",
        "description": "",
        "meta": {},
        "active": True,
    },
)

entity_store.register(account_entity)
entity_store.register(ledger_entity)
entity_store.register(membership_entity)
entity_store.register(order_entity)
entity_store.register(item_entity)
