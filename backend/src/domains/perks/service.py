"""Perks service managing discounts, cloud vouchers and claim codes."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from src.domains.perks.models import (
    PerkCreate,
    PerkResponse,
    PerkClaimRequest,
    PerkClaimResponse,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PerkService:
    """Manages cloud credits and infra deals."""

    def __init__(self):
        self._perks: Dict[str, PerkResponse] = {}
        # Key: (user_id, perk_id)
        self._claims: Dict[Tuple[str, str], PerkClaimResponse] = {}
        self._seed_default_perks()

    def _seed_default_perks(self):
        items = [
            (
                "perk_aws_activate",
                "AWS Activate 创客计划",
                "Amazon Web Services",
                35000.0,
                "CLOUD",
                "价值 $5,000 云端算力与全球负载均衡抵扣券，覆盖 EC2、S3 及 Bedrock。",
                42,
            ),
            (
                "perk_aliyun_bailian",
                "阿里云百炼大模型专属算力包",
                "阿里云",
                12000.0,
                "AI",
                "赠送 1,000 万通义千问 Qwen-Max 与 Qwen-Plus 旗舰模型推理 Tokens 额度。",
                150,
            ),
            (
                "perk_cloudflare_workers",
                "Cloudflare Workers Pro 特权",
                "Cloudflare",
                1800.0,
                "INFRA",
                "全球边缘无服务器函数 1 年期 Pro 订阅，免除边缘并发冷启动与流量费用。",
                88,
            ),
            (
                "perk_stripe_atlas",
                "Stripe Atlas 离岸开办绿色通道",
                "Stripe",
                1800.0,
                "FINANCE",
                "立减 $250 美元注册费用，极速设立特拉华州 C-Corp 或 LLC 并开立企业银行账户。",
                25,
            ),
        ]
        for pid, name, provider, val, cat, summary, quota in items:
            self._perks[pid] = PerkResponse(
                id=pid,
                name=name,
                provider=provider,
                value_cny=val,
                category=cat,
                summary=summary,
                quota_remaining=quota,
            )

    def list_perks(self) -> List[PerkResponse]:
        return list(self._perks.values())

    def create_perk(self, req: PerkCreate) -> PerkResponse:
        """Create and publish a new developer perk or subsidy."""
        pid = f"perk_{uuid.uuid4().hex[:8]}"
        perk = PerkResponse(
            id=pid,
            name=req.name,
            provider=req.provider,
            value_cny=req.value_cny,
            category=req.category,
            summary=req.summary,
            quota_remaining=req.quota_remaining,
        )
        self._perks[pid] = perk
        return perk

    def claim_perk(self, req: PerkClaimRequest) -> PerkClaimResponse:
        if req.perk_id not in self._perks:
            raise KeyError(f"Perk {req.perk_id} not found")
        perk = self._perks[req.perk_id]

        key = (req.user_id, req.perk_id)
        if key in self._claims:
            return self._claims[key]

        if perk.quota_remaining <= 0:
            raise ValueError(f"Perk {perk.name} is fully redeemed")

        perk.quota_remaining -= 1
        voucher = "OPC-" + uuid.uuid4().hex[:6].upper() + "-2026"
        cid = str(uuid.uuid4())
        claim = PerkClaimResponse(
            claim_id=cid,
            perk_id=perk.id,
            perk_name=perk.name,
            user_id=req.user_id,
            voucher_code=voucher,
            status="ACTIVATED",
            instructions=f"核销说明：请在 {perk.provider} 控制台优惠券兑换入口输入此凭据。",
            created_at=utc_now_iso(),
        )
        self._claims[key] = claim
        return claim


perk_service = PerkService()
