"""Content moderation service managing violation reports and take-down enforcement."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import HTTPException
from .models import (
    ModerationItemResponse,
    TakedownRequest,
    RestoreRequest,
    ModerationActionResponse,
)
from src.infrastructure.database.persistence import domain_persistence
from .models import ContentReportRequest, REPORTABLE_TARGET_TYPES


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModerationService:
    """Manages content moderation, illegal speech inspection and take-down actions."""

    def __init__(self):
        self._items: Dict[str, ModerationItemResponse] = {}

    def list_items(self, status: Optional[str] = None) -> List[ModerationItemResponse]:
        items = list(self._items.values())
        if status:
            items = [it for it in items if it.status.upper() == status.upper()]
        return items

    def get_item(self, item_id: str) -> Optional[ModerationItemResponse]:
        return self._items.get(item_id)

    def report(self, req: ContentReportRequest) -> ModerationItemResponse:
        """Record a user report (举报) against a piece of published content.

        Community reports are the user-interaction signal that keeps published
        information honest: the platform does not verify authenticity itself —
        reported content lands in the FLAGGED queue for operator disposition
        (takedown / restore). Reports on the same target are merged into one
        item whose report_count accumulates.
        """
        from .models import ModerationItemResponse as _Item

        tt = str(req.target_type or "").strip().upper()
        tid = str(req.target_id or "").strip()
        if tt not in REPORTABLE_TARGET_TYPES:
            raise ValueError(f"Unsupported report target_type: {req.target_type}")
        if not tid:
            raise ValueError("target_id is required for a report")

        now = utc_now_iso()
        existing = next(
            (it for it in self._items.values()
             if it.target_type == tt and it.target_id == tid and it.status == "FLAGGED"),
            None,
        )
        if existing:
            existing.report_count += 1
            existing.reported_at = now
            if req.reason and not existing.reason:
                existing.reason = req.reason
            domain_persistence.write("moderation.items", existing.id, existing)
            return existing

        item_id = f"mod_{uuid.uuid4().hex[:10]}"
        snippet = (req.snippet_content or req.target_title or "").strip()[:160]
        item = _Item(
            id=item_id,
            target_type=tt,
            target_id=tid,
            author_id=req.author_id or "",
            author_name=req.author_name or "",
            snippet_content=snippet,
            violation_type="USER_REPORT",
            status="FLAGGED",
            report_count=1,
            reported_at=now,
            reason=req.reason or "用户举报：内容疑似违规或失实",
        )
        self._items[item_id] = item
        domain_persistence.write("moderation.items", item_id, item)
        return item

    def revert_takedown(self, item_id: str, prev_status: str = "FLAGGED") -> bool:
        item = self._items.get(item_id)
        if item:
            item.status = prev_status
            item.moderated_at = None
            domain_persistence.write("moderation.items", item_id, item)
            return True
        return False

    def revert_restore(self, item_id: str) -> bool:
        item = self._items.get(item_id)
        if item:
            item.status = "TAKEN_DOWN"
            domain_persistence.write("moderation.items", item_id, item)
            return True
        return False

    def revert_report(self, item_id: str, previous_count: int = 0) -> bool:
        """Roll back a recorded report (Saga compensation).

        A newly-created report is removed; an incremental report on an existing
        item is restored to its previous ``report_count``.
        """
        item = self._items.get(item_id)
        if not item:
            return False
        if previous_count <= 0:
            del self._items[item_id]
            domain_persistence.delete("moderation.items", item_id)
            return True
        item.report_count = previous_count
        domain_persistence.write("moderation.items", item.id, item)
        return True

    def takedown(self, req: TakedownRequest) -> ModerationActionResponse:
        item = self._items.get(req.item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Moderation item {req.item_id} not found")
        
        now = utc_now_iso()
        item.status = "TAKEN_DOWN"
        item.reason = req.reason
        item.moderator_id = req.moderator_id
        item.moderated_at = now
        domain_persistence.write("moderation.items", item.id, item)

        return ModerationActionResponse(
            item_id=item.id,
            status="TAKEN_DOWN",
            moderated_at=now,
            note=f"言论已全站下架: {req.reason}" + (" (作者已封禁)" if req.ban_author else "")
        )

    def restore(self, req: RestoreRequest) -> ModerationActionResponse:
        item = self._items.get(req.item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Moderation item {req.item_id} not found")
        
        now = utc_now_iso()
        item.status = "NORMAL"
        item.moderator_id = req.moderator_id
        item.moderated_at = now
        domain_persistence.write("moderation.items", item.id, item)

        return ModerationActionResponse(
            item_id=item.id,
            status="NORMAL",
            moderated_at=now,
            note="处罚已撤销，言论恢复正常展示"
        )

    def hydrate_items(self, rows: List[Dict]) -> int:
        for r in rows:
            self._items[r["id"]] = ModerationItemResponse(**r)
        return len(rows)


moderation_service = ModerationService()

domain_persistence.register("moderation.items", moderation_service.hydrate_items)
