"""User message box service (消息箱).

Delivers asynchronous platform results to their owner. The first producer is the
unified content-moderation gate: every publish attempt records whether the
sensitive-word check passed or blocked the content, so makers always get a
durable receipt even when a publish is rejected before persistence.

Failure policy: notification delivery is best-effort. A broken message box must
never block publishing, so callers treat exceptions from this service as
non-fatal.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.infrastructure.database.persistence import domain_persistence

from .models import (
    KIND_PUBLISH_MODERATION,
    STATUS_READ,
    STATUS_UNREAD,
    VERDICT_BLOCKED,
    VERDICT_PASSED,
    VERDICT_PASSED_DEGRADED,
    Notification,
    NotificationActionResponse,
    NotificationListResponse,
)

logger = logging.getLogger("opchub.notifications")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotificationService:
    """In-memory index with write-behind persistence for per-user notifications."""

    def __init__(self) -> None:
        self._items: Dict[str, Notification] = {}

    # ------------------------------------------------------------------ write
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
        uid = str(user_id or "").strip()
        if not uid:
            raise ValueError("user_id is required for a notification")
        item = Notification(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            user_id=uid,
            kind=kind,
            level=str(level or "INFO").upper(),
            title=(title or "平台消息")[:160],
            content=(content or "")[:2000],
            scene=scene or "",
            target_type=(target_type or "").upper(),
            target_id=str(target_id or ""),
            verdict=(verdict or "").upper(),
            hit_words=sorted({str(w) for w in (hit_words or []) if str(w).strip()}),
            status=STATUS_UNREAD,
            created_at=utc_now_iso(),
        )
        self._items[item.id] = item
        domain_persistence.write("notifications.items", item.id, item)
        return item

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
        uid = str(user_id or "").strip()
        if not uid:
            return None

        verdict = str(verdict or "").upper()
        safe_title = (title or "未命名内容").strip()[:80]
        scene_label = (scene or "内容").strip()
        hits = sorted({str(w) for w in (hit_words or []) if str(w).strip()})

        if verdict == VERDICT_BLOCKED:
            level = "WARNING"
            heading = f"「{scene_label}」敏感词校验未通过"
            hit_text = "、".join(hits) if hits else (reason or "命中平台敏感词规则")
            body = (
                f"《{safe_title}》未通过平台敏感词校验，发布已被阻止。"
                f"命中内容：{hit_text}。请修改后重新发布。"
            )
        elif verdict == VERDICT_PASSED_DEGRADED:
            level = "INFO"
            heading = f"「{scene_label}」敏感词校验已放行"
            body = (
                f"《{safe_title}》的外部审核服务暂时不可用，平台已先行放行。"
                f"服务恢复后平台会继续复核，如发现问题将通过消息箱通知你。"
            )
        else:
            level = "SUCCESS"
            heading = f"「{scene_label}」敏感词校验通过"
            body = f"《{safe_title}》已通过平台敏感词校验，内容已进入发布流程。"

        return self.create(
            user_id=uid,
            title=heading,
            content=body,
            level=level,
            scene=scene_label,
            target_type=target_type,
            target_id=target_id,
            verdict=verdict,
            hit_words=hits,
        )

    # ------------------------------------------------------------------- read
    def list_for_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> NotificationListResponse:
        uid = str(user_id or "").strip()
        items = [n for n in self._items.values() if n.user_id == uid]
        unread = sum(1 for n in items if n.status == STATUS_UNREAD)
        if status:
            wanted = str(status).upper()
            items = [n for n in items if n.status == wanted]
        items.sort(key=lambda n: n.created_at, reverse=True)
        total = len(items)
        start = max(0, int(offset or 0))
        end = start + max(1, min(int(limit or 50), 200))
        return NotificationListResponse(
            items=items[start:end],
            total=total,
            unread=unread,
            status=(str(status).upper() if status else None),
        )

    def unread_count(self, user_id: str) -> int:
        uid = str(user_id or "").strip()
        return sum(
            1 for n in self._items.values()
            if n.user_id == uid and n.status == STATUS_UNREAD
        )

    # ----------------------------------------------------------------- mutate
    def mark_read(self, user_id: str, ids: Optional[List[str]] = None) -> NotificationActionResponse:
        uid = str(user_id or "").strip()
        wanted = {str(i) for i in (ids or []) if str(i).strip()}
        if ids is not None and not wanted:
            # Explicit empty target list: no-op (mark_all_read uses ids=None).
            return NotificationActionResponse(
                updated=0,
                unread=self.unread_count(uid),
                message="未指定要标记的消息",
            )
        updated = 0
        now = utc_now_iso()
        for item in self._items.values():
            if item.user_id != uid or item.status == STATUS_READ:
                continue
            if wanted and item.id not in wanted:
                continue
            item.status = STATUS_READ
            item.read_at = now
            domain_persistence.write("notifications.items", item.id, item)
            updated += 1
        return NotificationActionResponse(
            updated=updated,
            unread=self.unread_count(uid),
            message=f"已标记 {updated} 条消息为已读",
        )

    def mark_all_read(self, user_id: str) -> NotificationActionResponse:
        return self.mark_read(user_id, ids=None)

    def delete(self, user_id: str, notification_id: str) -> NotificationActionResponse:
        uid = str(user_id or "").strip()
        item = self._items.get(str(notification_id or ""))
        if item is None or item.user_id != uid:
            return NotificationActionResponse(unread=self.unread_count(uid), message="消息不存在")
        del self._items[item.id]
        domain_persistence.delete("notifications.items", item.id)
        return NotificationActionResponse(
            updated=1,
            unread=self.unread_count(uid),
            message="消息已删除",
        )

    # --------------------------------------------------------------- hydrate
    def hydrate_items(self, rows: List[Dict]) -> int:
        for row in rows:
            item = Notification(**row)
            self._items[item.id] = item
        return len(rows)

    def clear(self) -> None:
        """Test helper: drop every in-memory notification."""
        self._items.clear()


notification_service = NotificationService()
domain_persistence.register("notifications.items", notification_service.hydrate_items)
