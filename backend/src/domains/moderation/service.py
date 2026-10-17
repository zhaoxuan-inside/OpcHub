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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModerationService:
    """Manages content moderation, illegal speech inspection and take-down actions."""

    def __init__(self):
        self._items: Dict[str, ModerationItemResponse] = {}
        self._seed_default_items()

    def _seed_default_items(self):
        defaults = [
            ModerationItemResponse(
                id="mod-101",
                target_type="FORUM_THREAD",
                target_id="th_viol_01",
                author_id="usr_leak_0821",
                author_name="匿名外包工作室",
                snippet_content="出售未经脱敏的某大厂内网 API 鉴权私钥及爬虫套件，支持大批量导出企业画像数据...",
                violation_type="ILLEGAL_TRADE",
                status="FLAGGED",
                reported_at="2026-10-17T07:12:00Z",
                reason="涉嫌商业机密泄露与非法倒卖 API 鉴权私钥"
            ),
            ModerationItemResponse(
                id="mod-102",
                target_type="FORUM_COMMENT",
                target_id="cm_viol_02",
                author_id="usr_tax_fake_33",
                author_name="财税黑中介",
                snippet_content="保证月入十万！加 V 信 138XXXX 一对一包过工商免征偷逃税，买发票冲抵进项全套服务...",
                violation_type="SCAM",
                status="TAKEN_DOWN",
                reported_at="2026-10-17T06:45:00Z",
                moderated_at="2026-10-17T07:00:00Z",
                reason="虚假违规宣传与涉税违法黑产引流",
                moderator_id="admin_001"
            ),
            ModerationItemResponse(
                id="mod-103",
                target_type="FORUM_COMMENT",
                target_id="cm_viol_03",
                author_id="usr_wash_9912",
                author_name="离岸黑产号",
                snippet_content="跨境洗钱与地下钱庄结汇免审查通道，支持高频 USDT 变现直达境内个人卡...",
                violation_type="ILLEGAL_TRADE",
                status="TAKEN_DOWN",
                reported_at="2026-10-17T05:20:00Z",
                moderated_at="2026-10-17T05:35:00Z",
                reason="外汇违法及地下钱庄非法结汇",
                moderator_id="admin_001"
            ),
            ModerationItemResponse(
                id="mod-104",
                target_type="PRODUCT_REVIEW",
                target_id="pr_viol_04",
                author_id="usr_bot_4490",
                author_name="黑灰脚本号",
                snippet_content="低价承接热帖批量刷赞、虚假点赞刷量与竞标霸榜脚本，秒杀同行...",
                violation_type="SPAM",
                status="FLAGGED",
                reported_at="2026-10-17T07:30:00Z",
                reason="作弊刷量与恶意竞争垃圾灌水"
            )
        ]
        for item in defaults:
            self._items[item.id] = item

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
            return True
        return False

    def revert_restore(self, item_id: str) -> bool:
        item = self._items.get(item_id)
        if item:
            item.status = "TAKEN_DOWN"
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

        return ModerationActionResponse(
            item_id=item.id,
            status="NORMAL",
            moderated_at=now,
            note="处罚已撤销，言论恢复正常展示"
        )


moderation_service = ModerationService()
