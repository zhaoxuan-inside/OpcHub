"""Compatibility shim for the unified content interaction domain.

All business flows now live in ``config/scenarios/interactions.yaml`` and run on
the operator kernel: toggling LIKE / FAVORITE / LOVE / DISLIKE, 1-5 star rating,
comment creation / deletion, single & batch state, personal interaction centre
and counter initialisation. Pure calculations / assemblers live in
``src.domains.interactions.functions``; documents live in the generic entity
store (``src.domains.interactions.entities``).

This module therefore only keeps the legacy **data / query** surface that other
modules still import:

* ``get_state`` / ``batch_state`` / ``list_comments`` / ``mine`` – read-only
  projections assembled with the very same pure functions the scenarios use;
* ``resolve_target_author`` / ``resolve_target_title`` – read-only lookups used
  by the loyalty ledger (no cross-domain import: the target entity name comes
  from the declarative ``calc.interaction.target`` mapping);
* ``hydrate_*`` / ``clear`` – startup hydration and test isolation.

There is deliberately **no** ``toggle`` / ``rate`` / ``create_comment`` /
``delete_comment`` here anymore: those mutations are pipeline-only
(``OPC_INTERACTION_TOGGLE_PIPELINE``, ``OPC_INTERACTION_RATE_PIPELINE``,
``OPC_CONTENT_COMMENT_PUBLISH_PIPELINE``, ``OPC_INTERACTION_COMMENT_DELETE_PIPELINE``).
``src.core.gateway.adapters`` still references them until
``config/gateway_routes.yaml`` is regenerated from ``config/routes/interactions.yaml``.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.core.entity import entity_store
from src.domains.interactions import entities as _entities  # noqa: F401 - registers the EntitySpecs
from src.domains.interactions.models import (
    ContentComment,
    ContentCommentListResponse,
    InteractionState,
    MyInteractionResponse,
)
from src.infrastructure.database.persistence import domain_persistence

STATS_DOMAIN = _entities.stat_entity.family
RECORDS_DOMAIN = _entities.record_entity.family
COMMENTS_DOMAIN = _entities.comment_entity.family
RATINGS_DOMAIN = _entities.rating_entity.family

ENTITY_STAT = _entities.ENTITY_INTERACTION_STAT
ENTITY_RECORD = _entities.ENTITY_INTERACTION_RECORD
ENTITY_COMMENT = _entities.ENTITY_CONTENT_COMMENT
ENTITY_RATING = _entities.ENTITY_INTERACTION_RATING

KIND_FIELD = {
    "LIKE": "like_count",
    "FAVORITE": "favorite_count",
    "LOVE": "love_count",
    "DISLIKE": "dislike_count",
}


def _functions():
    """Lazily import the pure operators (avoids a core<->domain import cycle)."""
    # Initialise the operator kernel before the operator package so a standalone
    # ``import src.domains.interactions.service`` cannot trip the
    # core.operators <-> core.microkernel import cycle.
    import src.core.microkernel  # noqa: F401

    from src.domains.interactions import functions

    return functions


class ContentInteractionService:
    """Read-only compatibility surface over the generic interaction entities."""

    # ------------------------------------------------------------------
    # Legacy collection views (test isolation / diagnostics)
    # ------------------------------------------------------------------
    def _rows(self, entity: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        rows, _total = entity_store.list(entity, {"filters": dict(filters or {}), "limit": 0})
        return rows

    def clear(self) -> None:
        """Reset every interaction entity family for isolated test execution."""
        for entity in (ENTITY_STAT, ENTITY_RECORD, ENTITY_COMMENT, ENTITY_RATING):
            adapter = entity_store.adapter(entity)
            spec = entity_store.spec(entity)
            for row in list(adapter.all()):
                adapter.delete(spec.key_of(row))

    # ------------------------------------------------------------------
    # Persistence hydration
    # ------------------------------------------------------------------
    def hydrate_stats(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_STAT).hydrate(rows)

    def hydrate_records(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_RECORD).hydrate(rows)

    def hydrate_comments(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_COMMENT).hydrate(rows)

    def hydrate_ratings(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_RATING).hydrate(rows)

    # ------------------------------------------------------------------
    # Target resolution (declarative mapping, no cross-domain import)
    # ------------------------------------------------------------------
    def _plan(self, target_type: str, target_id: str, counts: Any = None) -> Dict[str, Any]:
        return _functions().target(
            {},
            {"target_type": target_type, "target_id": target_id, "counts": counts},
            {},
        )

    def _target_doc(self, target_type: str, target_id: str) -> Optional[Dict[str, Any]]:
        plan = self._plan(target_type, target_id)
        entity = plan.get("entity")
        if not entity:
            return None
        return entity_store.get(str(entity), {"key": str(target_id)})

    def _stat(self, target_type: str, target_id: str) -> Optional[Dict[str, Any]]:
        return entity_store.get(
            ENTITY_STAT,
            {"target_type": str(target_type).upper(), "target_id": str(target_id)},
        )

    def resolve_target_author(self, target_type: str, target_id: str) -> str:
        """Public helper for the loyalty ledger: who owns this content?"""
        doc = self._target_doc(str(target_type or "").upper(), str(target_id))
        if not doc:
            return ""
        for field_name in ("author_id", "creator_id", "owner_id", "user_id"):
            value = doc.get(field_name)
            if value:
                return str(value)
        return ""

    def resolve_target_title(self, target_type: str, target_id: str) -> str:
        """Public helper for ledger notes: human-readable content title."""
        doc = self._target_doc(str(target_type or "").upper(), str(target_id))
        if not doc:
            return ""
        for field_name in ("title", "name", "document_title"):
            value = doc.get(field_name)
            if value:
                return str(value)
        return ""

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get_state(
        self,
        user_id: Optional[str],
        target_type: str,
        target_id: str,
    ) -> InteractionState:
        tt = str(target_type or "").strip().upper()
        tid = str(target_id)
        viewer = str(user_id or "")
        counts = self._counts_for(tt, tid)
        records = self._rows(
            ENTITY_RECORD,
            {"user_id": viewer, "target_type": tt, "target_id": tid},
        )
        comments = self._rows(
            ENTITY_COMMENT,
            {"target_type": tt, "target_id": tid, "author_id": viewer},
        )
        rating = entity_store.get(
            ENTITY_RATING,
            {"user_id": viewer, "target_type": tt, "target_id": tid},
        )
        payload = _functions().state(
            {},
            {
                "target_type": tt,
                "target_id": tid,
                "counts": counts,
                "records": records,
                "comments": comments,
                "rating": rating,
                "viewer_id": viewer,
            },
            {},
        )
        return InteractionState(**payload)

    def _counts_for(self, target_type: str, target_id: str) -> Dict[str, int]:
        stat = self._stat(target_type, target_id)
        plan = _functions().target(
            {},
            {
                "target_type": target_type,
                "target_id": target_id,
                "counts": stat,
                "target": self._target_doc(target_type, target_id),
            },
            {},
        )
        return dict(plan["counts"])

    def batch_state(
        self,
        user_id: Optional[str],
        targets: Iterable[Any],
    ) -> Dict[str, Any]:
        viewer = str(user_id or "")
        normalized: List[Dict[str, str]] = []
        for raw in targets:
            if isinstance(raw, dict):
                tt = raw.get("target_type")
                tid = raw.get("target_id")
            else:
                tt = getattr(raw, "target_type", None)
                tid = getattr(raw, "target_id", None)
            if not tt or tid is None:
                continue
            normalized.append({"target_type": str(tt), "target_id": str(tid)})
        payload = _functions().batch(
            {},
            {
                "targets": normalized,
                "stats": self._rows(ENTITY_STAT),
                "records": self._rows(ENTITY_RECORD, {"user_id": viewer}),
                "comments": self._rows(ENTITY_COMMENT, {"author_id": viewer}),
                "viewer_id": viewer,
            },
            {},
        )
        return {"items": payload.get("items") or []}

    def list_comments(self, target_type: str, target_id: str) -> ContentCommentListResponse:
        tt = str(target_type or "").strip().upper()
        tid = str(target_id)
        items: List[ContentComment] = []
        for row in self._rows(ENTITY_COMMENT, {"target_type": tt, "target_id": tid}):
            try:
                items.append(ContentComment(**row))
            except Exception:
                continue
        payload = _functions().comments({}, {"items": [item.model_dump() for item in items]}, {})
        return ContentCommentListResponse(
            items=[ContentComment(**row) for row in payload["items"]],
            total=int(payload["total"]),
        )

    def mine(self, user_id: str) -> MyInteractionResponse:
        viewer = str(user_id or "")
        payload = _functions().mine(
            {},
            {
                "records": self._rows(ENTITY_RECORD, {"user_id": viewer}),
                "comments": self._rows(ENTITY_COMMENT, {"author_id": viewer}),
                "viewer_id": viewer,
            },
            {},
        )
        return MyInteractionResponse(**payload)


content_interaction_service = ContentInteractionService()

# Hydration bindings. The generic entity store also hydrates these families on
# startup; keeping the legacy ``domain_persistence`` hooks makes old snapshot
# loaders and tests that call ``register``/``hydrate`` directly keep working.
domain_persistence.register(STATS_DOMAIN, content_interaction_service.hydrate_stats)
domain_persistence.register(RECORDS_DOMAIN, content_interaction_service.hydrate_records)
domain_persistence.register(COMMENTS_DOMAIN, content_interaction_service.hydrate_comments)
domain_persistence.register(RATINGS_DOMAIN, content_interaction_service.hydrate_ratings)
