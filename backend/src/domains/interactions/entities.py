"""Declarative entity specifications for the unified interaction domain.

Data only: this module tells the generic entity runtime which documents exist,
how they are keyed, validated and searched. Every business flow lives in
``config/scenarios/interactions.yaml``; the calculations live in
``src.domains.interactions.functions``. No rule and no orchestration here.

Composite keys make the storage invariants explicit:

* one counter row per ``(target_type, target_id)`` – aggregate interaction state;
* one ledger row per ``(user_id, target_type, target_id, kind)`` – a user may
  toggle LIKE / FAVORITE / LOVE / DISLIKE independently, and "cancel" is a plain
  row delete;
* one rating row per ``(user_id, target_type, target_id)`` – re-rating overwrites
  instead of double counting.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.interactions.models import ContentComment

ENTITY_INTERACTION_STAT = "interaction.stat"
ENTITY_INTERACTION_RECORD = "interaction.record"
ENTITY_CONTENT_COMMENT = "content.comment"
ENTITY_INTERACTION_RATING = "interaction.rating"

# Aggregate counters. No pydantic model on purpose: counters are maintained by
# pure-function patches (``calc.interaction.*`` + ``entity.patch``/``upsert``),
# and the document shape is the counter contract itself.
stat_entity = EntitySpec(
    name=ENTITY_INTERACTION_STAT,
    family="interactions.stats",
    key_fields=("target_type", "target_id"),
    id_prefix="ist",
    default_order="-updated_at",
    defaults={
        "like_count": 0,
        "favorite_count": 0,
        "love_count": 0,
        "comment_count": 0,
        "dislike_count": 0,
        "rating_sum": 0,
        "rating_count": 0,
    },
)

# Per-user toggle ledger. The composite key is what makes "one person, one
# toggle per kind" a storage invariant instead of an application rule.
record_entity = EntitySpec(
    name=ENTITY_INTERACTION_RECORD,
    family="interactions.records",
    key_fields=("user_id", "target_type", "target_id", "kind"),
    id_prefix="irec",
    owner_field="user_id",
    default_order="-created_at",
    defaults={"target_title": ""},
)

# Public comments on any interaction target.
comment_entity = EntitySpec(
    name=ENTITY_CONTENT_COMMENT,
    family="interactions.comments",
    model=ContentComment,
    key_fields=("id",),
    id_prefix="cmt",
    search_fields=("content",),
    owner_field="author_id",
    default_order="created_at",
    defaults={
        "author_name": "创客",
        "parent_id": None,
        "target_title": "",
    },
)

# 1-5 star ratings. Re-rating updates the same row.
rating_entity = EntitySpec(
    name=ENTITY_INTERACTION_RATING,
    family="interactions.ratings",
    key_fields=("user_id", "target_type", "target_id"),
    id_prefix="irat",
    owner_field="user_id",
    default_order="-updated_at",
    defaults={"score": 0},
)

entity_store.register(stat_entity)
entity_store.register(record_entity)
entity_store.register(comment_entity)
entity_store.register(rating_entity)
