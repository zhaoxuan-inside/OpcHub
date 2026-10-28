"""Compatibility shim for the user message box (消息箱).

Business flows (list / unread count / mark read / mark all read / delete /
internal delivery) now live in ``config/scenarios/notifications.yaml`` and are
executed by the operator kernel. Pure calculations and projections live in
``src.domains.notifications.functions``; documents live in the generic entity
store (``src.domains.notifications.entities``).

This module therefore keeps only the legacy **data / query** surface that other
modules still import — most importantly ``notification_service.create`` used by
the content-moderation gate to record publish receipts.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.core.entity import entity_store
from src.domains.notifications import entities as _entities  # noqa: F401 - registers EntitySpecs
from src.domains.notifications.models import (
    KIND_PUBLISH_MODERATION,
    Notification,
    NotificationActionResponse,
    NotificationListResponse,
)
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.notifications")

ENTITY_NOTIFICATION = _entities.ENTITY_NOTIFICATION
ENTITY_INBOX = _entities.ENTITY_INBOX


def _functions():
    """Import the pure operators lazily (avoids an operator-kernel import cycle)."""
    from src.domains.notifications import functions

    return functions


class NotificationService:
    """Legacy accessors over the generic notification entity store."""

    # ------------------------------------------------------------------- reads
    def _rows(self, user_id: str) -> List[Dict[str, Any]]:
        rows, _total = entity_store.list(
            ENTITY_NOTIFICATION,
            {"filters": {"user_id": user_id}, "limit": 0},
        )
        return rows

    def _read_map(self, user_id: str) -> Dict[str, str]:
        doc = entity_store.get(ENTITY_INBOX, {"key": user_id}) or {}
        value = doc.get("read_map")
        return dict(value) if isinstance(value, dict) else {}

    def _save_read_map(self, user_id: str, read_map: Dict[str, str]) -> None:
        record = {"user_id": user_id, "read_map": dict(read_map)}
        if entity_store.get(ENTITY_INBOX, {"key": user_id}) is None:
            entity_store.create(ENTITY_INBOX, record)
        else:
            entity_store.update(ENTITY_INBOX, record)

    def list_for_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> NotificationListResponse:
        uid = str(user_id or "").strip()
        assembled = _functions().list_response(
            {},
            {
                "items": self._rows(uid),
                "read_map": self._read_map(uid),
                "status": status,
                "limit": limit,
                "offset": offset,
            },
            {},
        )
        return NotificationListResponse(
            items=[Notification(**item) for item in assembled["items"]],
            total=assembled["total"],
            unread=assembled["unread"],
            status=assembled["status"],
        )

    def unread_count(self, user_id: str) -> int:
        uid = str(user_id or "").strip()
        counted = _functions().unread_count(
            {},
            {"items": self._rows(uid), "read_map": self._read_map(uid)},
            {},
        )
        return int(counted["unread"])

    # ------------------------------------------------------------------ writes
    def create(
        self,
        *,
        user_id: str,
        title: str,
        content: str,
        kind: str = KIND_PUBLISH_MODERATION,
        level: str = "INFO",
        scene: str = "",
        target_type: str = "",
        target_id: str = "",
        verdict: str = "",
        hit_words: Optional[List[str]] = None,
    ) -> Notification:
        doc = _functions().normalize(
            {},
            {
                "user_id": user_id,
                "title": title,
                "content": content,
                "kind": kind,
                "level": level,
                "scene": scene,
                "target_type": target_type,
                "target_id": target_id,
                "verdict": verdict,
                "hit_words": hit_words or [],
            },
            {},
        )
        return Notification(**entity_store.create(ENTITY_NOTIFICATION, doc))

    def record_moderation_result(
        self,
        *,
        user_id: str,
        scene: str,
        title: str,
        verdict: str,
        hit_words: Optional[List[str]] = None,
        reason: str = "",
        target_type: str = "",
        target_id: str = "",
    ) -> Optional[Notification]:
        """Record one sensitive-word check receipt for the content publisher."""
        doc = _functions().moderation_receipt(
            {},
            {
                "user_id": user_id,
                "scene": scene,
                "title": title,
                "verdict": verdict,
                "hit_words": hit_words or [],
                "reason": reason,
                "target_type": target_type,
                "target_id": target_id,
            },
            {},
        )
        if not doc or doc.get("skip"):
            return None
        return Notification(**entity_store.create(ENTITY_NOTIFICATION, doc))

    def mark_read(self, user_id: str, ids: Optional[List[str]] = None) -> NotificationActionResponse:
        uid = str(user_id or "").strip()
        read_map = self._read_map(uid)
        plan = _functions().read_plan(
            {"scope": "all" if ids is None else "ids"},
            {"items": self._rows(uid), "read_map": read_map, "ids": ids},
            {"user_id": uid},
        )
        if plan["record"]["read_map"] != read_map:
            self._save_read_map(uid, plan["record"]["read_map"])
        return NotificationActionResponse(
            updated=int(plan["updated"]),
            unread=int(plan["unread"]),
            message=str(plan["message"]),
        )

    def mark_all_read(self, user_id: str) -> NotificationActionResponse:
        return self.mark_read(user_id, ids=None)

    def delete(self, user_id: str, notification_id: str) -> NotificationActionResponse:
        uid = str(user_id or "").strip()
        item = entity_store.get(ENTITY_NOTIFICATION, {"key": str(notification_id or "")})
        if item is None or str(item.get("user_id")) != uid:
            return NotificationActionResponse(unread=self.unread_count(uid), message="消息不存在")
        entity_store.delete(ENTITY_NOTIFICATION, {"key": str(item.get("id"))})
        return NotificationActionResponse(
            updated=1,
            unread=self.unread_count(uid),
            message="消息已删除",
        )

    # --------------------------------------------------------------- hydrate
    def hydrate_items(self, rows: List[Dict]) -> int:
        return entity_store.adapter(ENTITY_NOTIFICATION).hydrate(rows)

    def clear(self) -> None:
        """Test helper: drop every in-memory notification and read state."""
        for entity in (ENTITY_NOTIFICATION, ENTITY_INBOX):
            adapter = entity_store.adapter(entity)
            for row in list(adapter.all()):
                key = str(row.get("id") or row.get("user_id") or "")
                if key:
                    adapter.delete(key)


notification_service = NotificationService()
domain_persistence.register("notifications.items", notification_service.hydrate_items)
