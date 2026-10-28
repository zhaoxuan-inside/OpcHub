"""Declarative entity specifications for the content-moderation domain.

This module contains no business logic and no orchestration. It only tells the
generic entity runtime which documents exist, how they are keyed, validated and
searched. The persisted family name (``moderation.items``) is inherited from the
legacy service so existing snapshots stay readable.

A single document models one moderation *item*: either a user report merged by
target or an item enqueued by the local NLP pre-screen. Duplicate reports are
merged by the ``REPORT_PIPELINE`` scenario through the entity itself
(``report_count`` / ``reporters``), so no separate report table is required.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.moderation.models import ModerationItemResponse

ENTITY_MODERATION_ITEM = "moderation.item"

moderation_item_entity = EntitySpec(
    name=ENTITY_MODERATION_ITEM,
    family="moderation.items",
    model=ModerationItemResponse,
    id_prefix="mod",
    search_fields=("target_id", "snippet_content", "reason", "author_name"),
    owner_field="author_id",
    default_order="-reported_at",
    defaults={
        "target_type": "",
        "target_id": "",
        "author_id": "",
        "author_name": "",
        "snippet_content": "",
        "violation_type": "USER_REPORT",
        "status": "FLAGGED",
        "report_count": 0,
        "reported_at": "",
        "moderated_at": None,
        "reason": None,
        "moderator_id": None,
        "reporter_id": "",
        "reporters": [],
    },
)

entity_store.register(moderation_item_entity)
