"""Compatibility shim for the forum (头脑风暴) domain.

All business flows now live in the scenario asset ``config/scenarios/forum.yaml``
and execute on the operator kernel: publishing / editing / deleting threads,
answers and nested comments, mutual voting, following, detail, list and feed.
Pure calculations and assemblers live in ``src.domains.forum.functions`` and the
documents in the generic entity store (``src.domains.forum.entities``).

This module therefore only keeps the legacy **data / query** surface that other
modules still import:

* ``_threads`` / ``_answers`` / ``_comments`` / ``_votes`` / ``_follows`` and the
  ``_deleted_*`` sets – read-only mapping/set views over the entity store;
* ``get_thread`` / ``get_answer`` / ``list_threads`` / ``get_comments_tree`` /
  ``get_thread_detail`` / ``list_threads_paginated`` – queries assembled with the
  very same pure functions the scenarios use;
* ``hydrate_*`` / ``clear`` – startup hydration and test isolation.

Three methods remain as *legacy gateway bridges* because ``core/gateway/adapters.py``
still calls them directly (``forum.threads.get`` / ``forum.threads.follow`` /
``forum.threads.delete``). They contain no business rules: they only compose the
domain pure functions with generic store reads/writes, and will be deleted once
``config/gateway_routes.yaml`` is regenerated from ``config/routes/forum.yaml``.
"""
from __future__ import annotations

from collections.abc import Iterator, MutableMapping, MutableSet
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.core.entity import entity_store
from src.domains.forum import entities as _entities  # noqa: F401 - registers the EntitySpecs
from src.domains.forum.models import (
    CommentTreeNode,
    ForumAnswerResponse,
    ForumCommentResponse,
    ForumThreadResponse,
    ThreadDetailResponse,
)
from src.infrastructure.database.persistence import domain_persistence

ENTITY_THREAD = _entities.ENTITY_THREAD
ENTITY_ANSWER = _entities.ENTITY_ANSWER
ENTITY_COMMENT = _entities.ENTITY_COMMENT
ENTITY_VOTE = _entities.ENTITY_VOTE
ENTITY_FOLLOW = _entities.ENTITY_FOLLOW
ENTITY_TOMBSTONE = _entities.ENTITY_TOMBSTONE


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _functions():
    """Lazily import the pure operators (avoids a core<->domain import cycle)."""
    from src.domains.forum import functions

    return functions


class _Catalog(MutableMapping[str, Any]):
    """Legacy ``_threads`` / ``_answers`` / ``_comments`` view over the entity store.

    The mapping is a *projection*: it never owns a second copy of the data, so
    legacy readers (rbac owner check, RAG indexer, interactions, tests) observe
    exactly what the operator kernel persisted.
    """

    def __init__(self, entity: str, model: type):
        self._entity = entity
        self._model = model

    def _row(self, key: Any) -> Optional[Dict[str, Any]]:
        return entity_store.get(self._entity, {"key": str(key)})

    def __getitem__(self, key: str) -> Any:
        row = self._row(key)
        if row is None:
            raise KeyError(key)
        return self._model(**row)

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(value, "model_dump"):
            doc = value.model_dump(mode="json")
        else:
            doc = dict(value)
        doc["id"] = doc.get("id") or str(key)
        if self._row(doc["id"]) is None:
            entity_store.create(self._entity, doc)
        else:
            entity_store.update(self._entity, doc, partial=True)

    def __delitem__(self, key: str) -> None:
        if not entity_store.delete(self._entity, {"key": str(key)}):
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        for row in entity_store.adapter(self._entity).all():
            if row.get("id"):
                yield str(row["id"])

    def __len__(self) -> int:
        return len(entity_store.adapter(self._entity).all())


class _VoteLedger(MutableMapping[Tuple[str, str, str], str]):
    """Legacy ``_votes`` ledger view: ``(user_id, target_type, target_id) -> UPVOTE/DOWNVOTE``.

    Votes belonging to soft-deleted targets (tombstoned answers/comments) are
    hidden, mirroring the legacy "purge votes on delete" behaviour.
    """

    def __getitem__(self, key: Tuple[str, str, str]) -> str:
        user_id, target_type, target_id = (str(part) for part in key)
        row = entity_store.get(
            ENTITY_VOTE,
            {"user_id": user_id, "target_type": target_type.upper(), "target_id": target_id},
        )
        if row is None:
            raise KeyError(key)
        if entity_store.get(ENTITY_TOMBSTONE, {"key": target_id}) is not None:
            raise KeyError(key)
        if target_type.upper() == "COMMENT":
            comment = entity_store.get(ENTITY_COMMENT, {"key": target_id})
            if comment is None:
                raise KeyError(key)
            path = str(comment.get("materialized_path") or "")
            for tombstone in entity_store.adapter(ENTITY_TOMBSTONE).all():
                dead = str(tombstone.get("path") or "")
                if dead and (path == dead or path.startswith(f"{dead}/")):
                    raise KeyError(key)
        return str(row.get("vote_type") or "").upper()

    def __setitem__(self, key: Tuple[str, str, str], value: str) -> None:
        user_id, target_type, target_id = (str(part) for part in key)
        payload = {
            "user_id": user_id,
            "target_type": target_type.upper(),
            "target_id": target_id,
            "vote_type": str(value).upper(),
        }
        if entity_store.get(ENTITY_VOTE, payload) is None:
            entity_store.create(ENTITY_VOTE, payload)
        else:
            entity_store.update(ENTITY_VOTE, payload)

    def __delitem__(self, key: Tuple[str, str, str]) -> None:
        user_id, target_type, target_id = (str(part) for part in key)
        deleted = entity_store.delete(
            ENTITY_VOTE,
            {"user_id": user_id, "target_type": target_type.upper(), "target_id": target_id},
        )
        if not deleted:
            raise KeyError(key)

    def __iter__(self) -> Iterator[Tuple[str, str, str]]:
        for row in entity_store.adapter(ENTITY_VOTE).all():
            yield (
                str(row.get("user_id") or ""),
                str(row.get("target_type") or "").upper(),
                str(row.get("target_id") or ""),
            )

    def __len__(self) -> int:
        return len(entity_store.adapter(ENTITY_VOTE).all())


class _FollowSet(MutableSet[Tuple[str, str]]):
    """Legacy ``_follows`` set view over the follow entity family."""

    def __contains__(self, item: object) -> bool:
        try:
            user_id, thread_id = (str(part) for part in item)  # type: ignore[misc]
        except (TypeError, ValueError):
            return False
        return entity_store.get(ENTITY_FOLLOW, {"user_id": user_id, "thread_id": thread_id}) is not None

    def __iter__(self) -> Iterator[Tuple[str, str]]:
        for row in entity_store.adapter(ENTITY_FOLLOW).all():
            yield (str(row.get("user_id") or ""), str(row.get("thread_id") or ""))

    def __len__(self) -> int:
        return len(entity_store.adapter(ENTITY_FOLLOW).all())

    def add(self, item: Tuple[str, str]) -> None:
        user_id, thread_id = (str(part) for part in item)
        payload = {"user_id": user_id, "thread_id": thread_id}
        if entity_store.get(ENTITY_FOLLOW, payload) is None:
            entity_store.create(ENTITY_FOLLOW, payload)

    def discard(self, item: Tuple[str, str]) -> None:
        try:
            user_id, thread_id = (str(part) for part in item)
        except (TypeError, ValueError):
            return
        entity_store.delete(ENTITY_FOLLOW, {"user_id": user_id, "thread_id": thread_id})


class _TombstoneSet(MutableSet[str]):
    """Legacy ``_deleted_thread_ids`` / ``_deleted_answer_ids`` view over tombstones."""

    def __init__(self, kind: str):
        self._kind = kind.upper()

    def __contains__(self, item: object) -> bool:
        key = str(item)
        row = entity_store.get(ENTITY_TOMBSTONE, {"key": key})
        return bool(row) and str(row.get("type") or "").upper() == self._kind

    def __iter__(self) -> Iterator[str]:
        for row in entity_store.adapter(ENTITY_TOMBSTONE).all():
            if str(row.get("type") or "").upper() == self._kind and row.get("id"):
                yield str(row["id"])

    def __len__(self) -> int:
        return len(list(iter(self)))

    def add(self, item: str) -> None:
        key = str(item)
        payload = {"id": key, "type": self._kind}
        if entity_store.get(ENTITY_TOMBSTONE, {"key": key}) is None:
            entity_store.create(ENTITY_TOMBSTONE, payload)

    def discard(self, item: str) -> None:
        entity_store.delete(ENTITY_TOMBSTONE, {"key": str(item)})


class ForumService:
    """Legacy read surface over the generic forum entity store."""

    def __init__(self) -> None:
        # Feed caching was removed with the operator-kernel migration: ranking and
        # cursor slicing are pure functions (calc.forum.page) and need no cache.
        self._feed_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Legacy collection views
    # ------------------------------------------------------------------
    @property
    def _threads(self) -> MutableMapping[str, ForumThreadResponse]:
        return _Catalog(ENTITY_THREAD, ForumThreadResponse)

    @property
    def _answers(self) -> MutableMapping[str, ForumAnswerResponse]:
        return _Catalog(ENTITY_ANSWER, ForumAnswerResponse)

    @property
    def _comments(self) -> MutableMapping[str, ForumCommentResponse]:
        return _Catalog(ENTITY_COMMENT, ForumCommentResponse)

    @property
    def _votes(self) -> MutableMapping[Tuple[str, str, str], str]:
        return _VoteLedger()

    @property
    def _follows(self) -> MutableSet[Tuple[str, str]]:
        return _FollowSet()

    @property
    def _deleted_thread_ids(self) -> MutableSet[str]:
        return _TombstoneSet("THREAD")

    @property
    def _deleted_answer_ids(self) -> MutableSet[str]:
        return _TombstoneSet("ANSWER")

    # ------------------------------------------------------------------
    # Feed cache compatibility (removed)
    # ------------------------------------------------------------------
    def invalidate_feed_cache(self, category_code: Optional[str] = None) -> int:
        """No-op: the feed cache was removed (see calc.forum.page)."""
        self._feed_cache.clear()
        return 0

    def get_feed_cache(self, cache_key: str, ttl_seconds: float = 180.0) -> Optional[Dict[str, Any]]:
        """No-op: the feed cache was removed (see calc.forum.page)."""
        return None

    def set_feed_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """No-op: the feed cache was removed (see calc.forum.page)."""
        return None

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_thread(self, thread_id: str, record_view: bool = True) -> ForumThreadResponse:
        tid = str(thread_id)
        row = entity_store.get(ENTITY_THREAD, {"key": tid})
        if row is None:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        if record_view:
            # Legacy read-model projection: the canonical path is
            # OPC_FORUM_DETAIL_PIPELINE (activity calc + entity.patch).
            activity = _functions().thread_activity({}, {"thread": row, "view_delta": 1}, {})
            row = entity_store.update(ENTITY_THREAD, activity["patch"], partial=True)
        return ForumThreadResponse(**row)

    def get_answer(self, answer_id: str) -> ForumAnswerResponse:
        row = entity_store.get(ENTITY_ANSWER, {"key": str(answer_id)})
        if row is None:
            raise KeyError(f"Forum answer with ID {answer_id} not found")
        return ForumAnswerResponse(**row)

    def list_threads(
        self,
        category_code: Optional[str] = None,
        id: Optional[str] = None,
    ) -> List[ForumThreadResponse]:
        """List live threads, pinned first then newest first."""
        target = str(category_code or id or "ALL").upper()
        filters: Dict[str, Any] = {}
        if target != "ALL" and target not in _functions().THREAD_CATEGORIES:
            filters["id"] = target
        elif target in _functions().THREAD_CATEGORIES:
            filters["category_code"] = {"in": [target, target.lower()]}
        rows, _total = entity_store.list(
            ENTITY_THREAD, {"filters": filters, "order": "-created_at", "limit": 0}
        )
        live = [row for row in rows if str(row.get("id")) not in self._deleted_thread_ids]
        live.sort(key=lambda row: (bool(row.get("is_pinned")), str(row.get("created_at") or "")), reverse=True)
        return [ForumThreadResponse(**row) for row in live]

    def list_threads_paginated(
        self,
        id: Optional[str] = None,
        category_code: Optional[str] = None,
        page: int = 1,
        page_size: Optional[int] = None,
        page_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Paged thread listing (same envelope as OPC_FORUM_LIST_PIPELINE)."""
        normalized = _functions().query(
            {},
            {
                "category_code": category_code,
                "id": id,
                "page": page if page is not None else 1,
                "page_size": page_size,
                "page_length": page_length,
            },
            {},
        )
        rows, _total = entity_store.list(
            ENTITY_THREAD,
            {
                "filters": normalized["filters"],
                "search": normalized["search"],
                "order": normalized["order"],
                "limit": 0,
            },
        )
        page_result = _functions().page(
            {},
            {
                "items": rows,
                "mode": "page",
                "category_code": normalized["category_code"],
                "sort_by": normalized["sort_by"],
                "page": normalized["page"],
                "page_size": normalized["page_size"] or 10,
            },
            {},
        )
        enriched = _functions().feed(
            {"output_key": "feed"},
            {
                "envelope": page_result["envelope"],
                "answers": entity_store.list(ENTITY_ANSWER, {"limit": 0})[0],
                "votes": [],
                "follows": [],
            },
            {},
        )
        return enriched["feed"]

    def get_comments_tree(
        self,
        thread_id: str,
        target_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[CommentTreeNode]:
        """Assemble the materialized-path comment tree of one thread."""
        tid = str(thread_id)
        rows, _total = entity_store.list(ENTITY_COMMENT, {"filters": {"thread_id": tid}, "limit": 0})
        if target_id:
            rows = [row for row in rows if str(row.get("target_id")) == str(target_id)]
        detail = _functions().thread_detail(
            {},
            {
                "thread": {"id": str(thread_id)},
                "comments": rows,
                "votes": entity_store.list(ENTITY_VOTE, {"filters": {"user_id": str(user_id or "")}, "limit": 0})[0],
                "tombstones": entity_store.list(ENTITY_TOMBSTONE, {"limit": 0})[0],
                "viewer_id": user_id,
            },
            {},
        )
        return [CommentTreeNode(**node) for node in detail["comments"]]

    def get_thread_detail(
        self,
        thread_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[ThreadDetailResponse]:
        """Read one thread detail with answers, comment tree and viewer state."""
        tid = str(thread_id)
        row = entity_store.get(ENTITY_THREAD, {"key": tid})
        if row is None:
            return None
        # View counting stays on the legacy gateway path; the canonical write is
        # OPC_FORUM_DETAIL_PIPELINE's activity + entity.patch.
        activity = _functions().thread_activity({}, {"thread": row, "view_delta": 1}, {})
        row = entity_store.update(ENTITY_THREAD, activity["patch"], partial=True)
        viewer = str(user_id or "")
        detail = _functions().thread_detail(
            {},
            {
                "thread": row,
                "answers": entity_store.list(ENTITY_ANSWER, {"filters": {"thread_id": tid}, "limit": 0})[0],
                "comments": entity_store.list(ENTITY_COMMENT, {"filters": {"thread_id": tid}, "limit": 0})[0],
                "votes": entity_store.list(ENTITY_VOTE, {"filters": {"user_id": viewer}, "limit": 0})[0],
                "follows": entity_store.list(ENTITY_FOLLOW, {"filters": {"user_id": viewer}, "limit": 0})[0],
                "tombstones": entity_store.list(ENTITY_TOMBSTONE, {"limit": 0})[0],
                "viewer_id": viewer,
            },
            {},
        )
        return ThreadDetailResponse(**detail["detail"])

    # ------------------------------------------------------------------
    # Legacy gateway bridges (deleted once gateway_routes.yaml is regenerated)
    # ------------------------------------------------------------------
    def toggle_follow(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Follow/unfollow bridge used by the legacy ``forum.threads.follow`` handler."""
        tid = str(thread_id)
        thread = entity_store.get(ENTITY_THREAD, {"key": tid})
        if thread is None:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        uid = str(user_id)
        existing = entity_store.get(ENTITY_FOLLOW, {"user_id": uid, "thread_id": tid})
        transition = _functions().follow_transition(
            {}, {"existing": existing, "thread_id": tid, "user_id": uid, "follow_count": thread.get("follow_count")}, {}
        )
        if transition["active"]:
            entity_store.create(ENTITY_FOLLOW, {"user_id": uid, "thread_id": tid})
        else:
            entity_store.delete(ENTITY_FOLLOW, {"user_id": uid, "thread_id": tid})
        entity_store.update(ENTITY_THREAD, {"id": tid, "follow_count": transition["follow_count"]}, partial=True)
        return {
            "is_following": transition["is_following"],
            "follow_count": transition["follow_count"],
            "thread_id": tid,
        }

    def delete_thread(self, thread_id: str) -> bool:
        """Delete bridge used by the legacy ``forum.threads.delete`` handler."""
        tid = str(thread_id)
        if entity_store.get(ENTITY_THREAD, {"key": tid}) is None:
            return False
        if entity_store.get(ENTITY_TOMBSTONE, {"key": tid}) is None:
            entity_store.create(ENTITY_TOMBSTONE, {"id": tid, "type": "THREAD"})
        entity_store.delete(ENTITY_THREAD, {"key": tid})
        return True

    # ------------------------------------------------------------------
    # Hydration / test isolation
    # ------------------------------------------------------------------
    def hydrate_tombstones(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_TOMBSTONE).hydrate(rows)

    def hydrate_threads(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_THREAD).hydrate(rows)

    def hydrate_answers(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_ANSWER).hydrate(rows)

    def hydrate_comments(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_COMMENT).hydrate(rows)

    def hydrate_votes(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_VOTE).hydrate(rows)

    def clear(self) -> None:
        """Reset all forum entity families for isolated test execution."""
        for entity in (
            ENTITY_THREAD,
            ENTITY_ANSWER,
            ENTITY_COMMENT,
            ENTITY_VOTE,
            ENTITY_FOLLOW,
            ENTITY_TOMBSTONE,
        ):
            adapter = entity_store.adapter(entity)
            for row in list(adapter.all()):
                key = str(row.get("id") or "")
                if entity in (ENTITY_VOTE, ENTITY_FOLLOW):
                    spec = entity_store.spec(entity)
                    adapter.delete(spec.key_of(row))
                elif key:
                    adapter.delete(key)
        self._feed_cache.clear()


forum_service = ForumService()

# Hydration bindings (legacy ``domain_persistence`` contract, kept for old snapshots).
domain_persistence.register("forum.tombstones", forum_service.hydrate_tombstones)
domain_persistence.register("forum.threads", forum_service.hydrate_threads)
domain_persistence.register("forum.answers", forum_service.hydrate_answers)
domain_persistence.register("forum.comments", forum_service.hydrate_comments)
domain_persistence.register("forum.votes", forum_service.hydrate_votes)
