"""User and entitlement management service."""
import uuid
from typing import Dict, List, Set, Optional

from src.domains.user.models import (
    EntitlementItem,
    MakerProfileResponse,
    EntitlementActivateRequest,
    EntitlementActivateResponse,
)


class UserService:
    """Manages maker profile and entitlements."""

    def __init__(self):
        self._active_entitlements: Set[str] = {"ent_microkernel_pipeline", "ent_policy_radar_basic"}
        self._entitlements: Dict[str, EntitlementItem] = {}
        self._seed_default_entitlements()

    def _seed_default_entitlements(self):
        items = [
            (
                "ent_microkernel_pipeline",
                "微内核高并发编排算力通道",
                "STANDARD",
                0.0,
                "基础微内核 DAG 串联与沙箱执行能力，日调用上限 10,000 次。",
                "10,000 次/日",
            ),
            (
                "ent_policy_radar_basic",
                "全国与地方政策雷达白话提炼",
                "STANDARD",
                0.0,
                "免费查阅与匹配国家级增值税与小微企业免税政策。",
                "实时全量",
            ),
            (
                "ent_ai_tax_assistant",
                "AI 政策智能测算与申报材料极速出具",
                "PRO",
                199.0,
                "解锁一键生成符合政务标准的设立登记、软著申报全套文书。",
                "无限次导出",
            ),
            (
                "ent_black_diamond_priority",
                "黑钻合伙人 VIP 优先需求派单特权",
                "BLACK_DIAMOND",
                899.0,
                "获得企业技术外包与出海委托优先推荐接单权限，技术担保履约背书。",
                "顶格优先派单",
            ),
        ]
        for eid, name, tier, price, desc, quota in items:
            self._entitlements[eid] = EntitlementItem(
                id=eid,
                name=name,
                tier=tier,
                price_cny=price,
                description=desc,
                is_active=(eid in self._active_entitlements),
                quota_desc=quota,
            )

    def get_profile(self, uid: str = "usr_2026_opc_9981") -> MakerProfileResponse:
        ent_list = []
        for e in self._entitlements.values():
            e_copy = e.model_copy()
            e_copy.is_active = e.id in self._active_entitlements
            ent_list.append(e_copy)

        return MakerProfileResponse(
            uid=uid,
            nickname="赵玄",
            role="MAKER",
            company_name="极客视界（杭州）信息技术工作室",
            credit_code="92330106MAD7XXXX8Y",
            tier_name="黑钻创客 VIP",
            entitlements=ent_list,
        )

    def activate_entitlement(self, req: EntitlementActivateRequest) -> EntitlementActivateResponse:
        if req.entitlement_id not in self._entitlements:
            raise KeyError(f"Entitlement {req.entitlement_id} not found")

        self._active_entitlements.add(req.entitlement_id)
        receipt = "REC-" + uuid.uuid4().hex[:10].upper()
        return EntitlementActivateResponse(
            user_id=req.user_id,
            entitlement_id=req.entitlement_id,
            is_active=True,
            status="ACTIVATED",
            receipt_no=receipt,
            message="专属创客收费权益已激活并绑定，权限即刻生效！",
        )


user_service = UserService()
