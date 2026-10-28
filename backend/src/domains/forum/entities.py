"""Declarative entity specifications for the forum (头脑风暴) domain.

Data only: this module tells the generic entity runtime which documents exist,
how they are keyed, validated and searched. Persistence family names are
inherited from the legacy ``forum_service`` so existing ``domain_snapshots``
rows stay readable. No business rule and no orchestration lives here.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.forum.models import (
    ForumAnswerResponse,
    ForumCommentResponse,
    ForumFollowRecord,
    ForumThreadResponse,
    ForumTombstoneRecord,
    ForumVoteRecord,
)

ENTITY_THREAD = "forum.thread"
ENTITY_ANSWER = "forum.answer"
ENTITY_COMMENT = "forum.comment"
ENTITY_VOTE = "forum.vote"
ENTITY_FOLLOW = "forum.follow"
ENTITY_TOMBSTONE = "forum.tombstone"

thread_entity = EntitySpec(
    name=ENTITY_THREAD,
    family="forum.threads",
    model=ForumThreadResponse,
    key_fields=("id",),
    id_prefix="thr",
    search_fields=("title", "content", "author_name"),
    owner_field="author_id",
    default_order="-created_at",
    defaults={
        "category_code": "DEV",
        "author_name": "超级个体创客",
        "author_title": "独立创业者",
        "is_official": False,
        "view_count": 0,
        "upvote_count": 0,
        "downvote_count": 0,
        "comment_count": 0,
        "answer_count": 0,
        "follow_count": 0,
        "bookmark_count": 0,
        "love_count": 0,
        "is_pinned": False,
        "status": "PUBLISHED",
        "accepted_answer_id": None,
        "hot_score": 0.0,
        "top_answers": [],
        "user_vote": None,
        "is_following": False,
    },
)

answer_entity = EntitySpec(
    name=ENTITY_ANSWER,
    family="forum.answers",
    model=ForumAnswerResponse,
    key_fields=("id",),
    id_prefix="ans",
    search_fields=("content", "author_name"),
    owner_field="author_id",
    default_order="-created_at",
    defaults={
        "author_name": "创客探索者",
        "author_title": "超级个体实战家",
        "upvote_count": 0,
        "downvote_count": 0,
        "comment_count": 0,
        "is_accepted": False,
        "word_count": 0,
        "read_minutes": 1,
        "status": "PUBLISHED",
        "user_vote": None,
    },
)

comment_entity = EntitySpec(
    name=ENTITY_COMMENT,
    family="forum.comments",
    model=ForumCommentResponse,
    key_fields=("id",),
    id_prefix="cmt",
    search_fields=("content", "author_name"),
    owner_field="author_id",
    default_order="created_at",
    defaults={
        "target_type": "ANSWER",
        "target_id": "",
        "author_name": "独立创客",
        "parent_id": None,
        "root_id": None,
        "reply_to_user_id": None,
        "materialized_path": "",
        "depth": 0,
        "upvote_count": 0,
        "downvote_count": 0,
        "is_accepted": False,
        "status": "ACTIVE",
    },
)

# One vote ledger row per (user, target). The composite key makes "one person,
# one vote per target" a storage invariant instead of an application rule.
vote_entity = EntitySpec(
    name=ENTITY_VOTE,
    family="forum.votes",
    model=ForumVoteRecord,
    key_fields=("user_id", "target_type", "target_id"),
    id_prefix="vote",
    owner_field="user_id",
    default_order="-created_at",
    defaults={},
)

follow_entity = EntitySpec(
    name=ENTITY_FOLLOW,
    family="forum.follows",
    model=ForumFollowRecord,
    key_fields=("user_id", "thread_id"),
    id_prefix="fol",
    owner_field="user_id",
    default_order="-created_at",
    defaults={},
)

tombstone_entity = EntitySpec(
    name=ENTITY_TOMBSTONE,
    family="forum.tombstones",
    model=ForumTombstoneRecord,
    key_fields=("id",),
    id_prefix="tmb",
    default_order="-created_at",
    defaults={"path": None, "thread_id": None},
)

entity_store.register(thread_entity)
entity_store.register(answer_entity)
entity_store.register(comment_entity)
entity_store.register(vote_entity)
entity_store.register(follow_entity)
entity_store.register(tombstone_entity)
