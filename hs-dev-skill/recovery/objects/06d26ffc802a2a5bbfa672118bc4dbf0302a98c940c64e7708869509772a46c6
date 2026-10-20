"""Content moderation service managing violation reports and take-down enforcement."""
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
