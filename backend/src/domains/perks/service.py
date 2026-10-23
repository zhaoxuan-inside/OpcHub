"""Perks service managing the 优惠公告 (discount announcement) board and claim codes.

生态特权页面的数据源：由生态伙伴提报、管理端审核发布的优惠公告（Token 优惠、服务器优惠、
SaaS 服务优惠、结算支付、AI 算力、基础设施等），创客在前端浏览公告并前往服务商处领取。
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.domains.perks.models import (
    PerkCreate,
    PerkResponse,
    PerkClaimRequest,
    PerkClaimResponse,
)
from src.core.config import settings
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.perks")

# 生态优惠公告分类与状态枚举统一从 backend/config/application.yaml 加载（代码/配置/数据三分离）
PERK_CATEGORIES = set(settings.perk_categories)
PERK_STATUSES = set(settings.perk_statuses)


def _load_perk_seeds() -> Dict[str, Dict[str, Any]]:
    """Load baseline ecosystem discount announcement seeds from external data file.

    Maintains strict code, config, and data separation: zero announcements hardcoded in source.
    """
    search_paths = [
        Path("backend/data/seeds/perks.json"),
        Path("data/seeds/perks.json"),
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "perks.json",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load perk seeds from %s: %s", p, e)
    return {}


DEFAULT_PERK_SEEDS: Dict[str, Dict[str, Any]] = _load_perk_seeds()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PerkService:
    """Manages ecosystem privilege announcements (discount board) and claims."""

    def __init__(self):
        self._perks: Dict[str, PerkResponse] = {}
        # Key: (user_id, perk_id)
        self._claims: Dict[Tuple[str, str], PerkClaimResponse] = {}
        self._init_seeds()

    def _init_seeds(self) -> None:
        """Initialize in-memory announcement catalog from external data seeds."""
        for pid, data in DEFAULT_PERK_SEEDS.items():
            if pid not in self._perks:
                perk = PerkResponse(**data)
                self._perks[pid] = perk
                domain_persistence.write("perks.items", pid, perk)

    def list_perks(self, payload: Optional[Dict[str, Any]] = None) -> List[PerkResponse]:
        """List published discount announcements, optionally filtered by category.

        Sorted by display priority (desc) then effective start date (desc) so featured
        and freshest offers surface first on the 生态特权 announcement board.
        """
        category = ""
        if isinstance(payload, dict):
            category = str(payload.get("category", "") or "").strip()

        perks = list(self._perks.values())
        if category and category.upper() != "ALL":
            perks = [p for p in perks if p.category == category.upper()]
        # Public board only exposes PUBLISHED announcements
        perks = [p for p in perks if p.status == "PUBLISHED"]
        perks.sort(
            key=lambda p: (
                p.priority,
                p.effective_start or "",
            ),
            reverse=True,
        )
        return perks

    def list_all(self) -> List[PerkResponse]:
        """Return every announcement regardless of status (admin / management views)."""
        return sorted(
            self._perks.values(),
            key=lambda p: (p.priority, p.effective_start or ""),
            reverse=True,
        )

    def create_perk(self, req: PerkCreate) -> PerkResponse:
        """Create and publish a new ecosystem discount announcement."""
        pid = f"perk_{uuid.uuid4().hex[:8]}"
        perk = PerkResponse(
            id=pid,
            name=req.name,
            provider=req.provider,
            value_cny=req.value_cny,
            category=req.category,
            summary=req.summary,
            quota_remaining=req.quota_remaining,
            effective_start=req.effective_start,
            effective_end=req.effective_end,
            redeem_url=req.redeem_url,
            priority=req.priority,
            status=req.status,
            highlights=req.highlights,
            created_at=utc_now_iso(),
        )
        self._perks[pid] = perk
        domain_persistence.write("perks.items", pid, perk)
        return perk

    def validate_publish_payload(self, inputs: dict) -> dict:
        name = str(inputs.get("name", "")).strip()
        provider = str(inputs.get("provider", "")).strip()
        val = float(inputs.get("value_cny", 0.0))
        summary = str(inputs.get("summary", "")).strip()
        category = str(inputs.get("category", settings.perk_default_category)).strip().upper()
        quota_remaining = int(inputs.get("quota_remaining", settings.perk_default_quota))
        priority = int(inputs.get("priority", settings.perk_default_priority))
        status = str(inputs.get("status", settings.perk_default_status)).strip().upper()

        if len(name) < 2:
            raise ValueError("Announcement name must be at least 2 characters long")
        if len(provider) < 2:
            raise ValueError("Announcement provider must be at least 2 characters long")
        if val < 0:
            raise ValueError("Announcement value_cny cannot be negative")
        if len(summary) < 5:
            raise ValueError("Announcement summary must be at least 5 characters long")
        if quota_remaining < 1:
            raise ValueError("Announcement quota_remaining must be at least 1")
        if priority < 0 or priority > 100:
            raise ValueError("Announcement priority must be within 0..100")
        if status not in PERK_STATUSES:
            raise ValueError("Announcement status must be one of: " + ", ".join(sorted(PERK_STATUSES)))

        redeem_url = str(inputs.get("redeem_url") or "").strip() or None
        effective_start = str(inputs.get("effective_start") or "").strip() or None
        effective_end = str(inputs.get("effective_end") or "").strip() or None
        highlights = inputs.get("highlights") or []
        if isinstance(highlights, list):
            highlights = [str(h).strip() for h in highlights if str(h).strip()][:8]

        return {
            "guard_passed": True,
            "name": name,
            "provider": provider,
            "value_cny": val,
            "category": category,
            "summary": summary,
            "quota_remaining": quota_remaining,
            "effective_start": effective_start,
            "effective_end": effective_end,
            "redeem_url": redeem_url,
            "priority": priority,
            "status": status,
            "highlights": highlights,
        }

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
        domain_persistence.write("perks.items", perk.id, perk)
        domain_persistence.write_raw("perks.claims", f"{req.user_id}|{req.perk_id}", claim.model_dump(mode="json"))
        return claim

    def get_perk(self, perk_id: str) -> Optional[PerkResponse]:
        return self._perks.get(perk_id)

    def delete_perk(self, perk_id: str) -> bool:
        if perk_id in self._perks:
            del self._perks[perk_id]
            domain_persistence.delete("perks.items", perk_id)
            return True
        return False

    def revoke_claim(self, user_id: str, perk_id: str) -> bool:
        key = (user_id, perk_id)
        if key in self._claims:
            del self._claims[key]
            domain_persistence.delete("perks.claims", f"{user_id}|{perk_id}")
            if perk_id in self._perks:
                self._perks[perk_id].quota_remaining += 1
                domain_persistence.write("perks.items", perk_id, self._perks[perk_id])
            return True
        return False

    def hydrate_perks(self, rows: List[Dict]) -> int:
        if rows:
            for r in rows:
                self._perks[r["id"]] = PerkResponse(**r)
            return len(rows)
        # If DB is empty, persist baseline announcement seeds to PostgreSQL snapshots
        for pid, perk in self._perks.items():
            domain_persistence.write("perks.items", pid, perk)
        return len(self._perks)

    def hydrate_claims(self, rows: List[Dict]) -> int:
        for r in rows:
            self._claims[(r["user_id"], r["perk_id"])] = PerkClaimResponse(**r)
        return len(rows)


perk_service = PerkService()

domain_persistence.register("perks.items", perk_service.hydrate_perks)
domain_persistence.register("perks.claims", perk_service.hydrate_claims)
