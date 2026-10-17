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

    def get_perk(self, perk_id: str) -> Optional[PerkResponse]:
        return self._perks.get(perk_id)

    def delete_perk(self, perk_id: str) -> bool:
        if perk_id in self._perks:
            del self._perks[perk_id]
            return True
        return False

    def revoke_claim(self, user_id: str, perk_id: str) -> bool:
        key = (user_id, perk_id)
        if key in self._claims:
            del self._claims[key]
            if perk_id in self._perks:
                self._perks[perk_id].quota_remaining += 1
            return True
        return False


perk_service = PerkService()

