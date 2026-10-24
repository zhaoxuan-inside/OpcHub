"""Demands service managing corporate outsourcing requirements and maker bids."""
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domains.demands.models import (
    DemandCreate,
    DemandResponse,
    BidCreate,
    BidResponse,
)
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.demands")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_demand_seeds() -> Dict[str, Dict[str, Any]]:
    """Load baseline corporate demand seeds from an external data file.

    Maintains strict code, config, and data separation: zero demand records hardcoded in source.
    """
    search_paths = [
        Path("backend/data/seeds/demands.json"),
        Path("data/seeds/demands.json"),
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "demands.json",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load demand seeds from %s: %s", p, e)
    return {}


DEFAULT_DEMAND_SEEDS: Dict[str, Dict[str, Any]] = _load_demand_seeds()


class DemandService:
    """Manages demands and bids."""

    def __init__(self):
        self._demands: Dict[str, DemandResponse] = {}
        self._bids: Dict[str, List[BidResponse]] = {}
        # Key: cache_key -> (timestamp, data_dict)
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._init_seeds()

    def _init_seeds(self) -> None:
        """Initialize the in-memory marketplace catalog from external data seeds."""
        for did, data in DEFAULT_DEMAND_SEEDS.items():
            if did not in self._demands:
                demand = DemandResponse(**data)
                self._demands[did] = demand
                self._bids.setdefault(did, [])
                domain_persistence.write("demands.items", did, demand)

    def invalidate_cache(self) -> int:
        """Evict all cached demands list pages."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_cache(self, key: str, ttl_seconds: float = 120.0) -> Optional[Any]:
        """Fetch cached entry if within TTL."""
        if key not in self._cache:
            return None
        ts, data = self._cache[key]
        if time.time() - ts > ttl_seconds:
            self._cache.pop(key, None)
            return None
        return data

    def set_cache(self, key: str, data: Any) -> None:
        """Store cache entry with current timestamp."""
        self._cache[key] = (time.time(), data)

    def create_demand(self, payload: DemandCreate) -> DemandResponse:
        did = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        deadline = (now + timedelta(days=payload.deadline_days)).isoformat()
        demand = DemandResponse(
            id=did,
            creator_id=payload.creator_id,
            creator_name=payload.creator_name,
            is_official=payload.is_official,
            title=payload.title,
            description=payload.description,
            budget_cny=payload.budget_cny,
            category=payload.category,
            bidders_count=0,
            status="OPEN",
            deadline_at=deadline,
            created_at=now.isoformat(),
        )
        self._demands[did] = demand
        self._bids[did] = []
        domain_persistence.write("demands.items", did, demand)
        self.invalidate_cache()
        return demand

    def list_demands(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: int = 6,
        **kwargs: Any,
    ) -> Any:
        """List demands, either as a flat list (unpaged) or a paged envelope."""
        import math

        # 1. Unpaged full list query (backward-compatible with unit tests and batch lookups)
        if page is None:
            demands = list(self._demands.values())
            if category and category.lower() != "all":
                demands = [d for d in demands if d.category == category]
            if search and search.strip():
                q = search.strip().lower()
                demands = [
                    d for d in demands
                    if (d.title and q in d.title.lower())
                    or (d.description and q in d.description.lower())
                    or (d.creator_name and q in d.creator_name.lower())
                ]
            demands.sort(key=lambda d: d.created_at, reverse=True)
            return demands

        # 2. Paged query with server-side TTL caching (120 seconds)
        clean_page = max(1, int(page))
        clean_size = max(1, min(100, int(page_size)))
        cache_key = f"{category or 'ALL'}:{search or ''}:{clean_page}:{clean_size}"
        cached = self.get_cache(cache_key)
        if cached is not None:
            cached_res = dict(cached)
            cached_res["from_cache"] = True
            return cached_res

        all_demands = list(self._demands.values())
        if category and category.lower() != "all":
            all_demands = [d for d in all_demands if d.category == category]
        if search and search.strip():
            q = search.strip().lower()
            all_demands = [
                d for d in all_demands
                if (d.title and q in d.title.lower())
                or (d.description and q in d.description.lower())
                or (d.creator_name and q in d.creator_name.lower())
            ]
        all_demands.sort(key=lambda d: d.created_at, reverse=True)

        total = len(all_demands)
        start = (clean_page - 1) * clean_size
        end = start + clean_size
        slice_items = all_demands[start:end]
        has_more = end < total
        total_pages = math.ceil(total / clean_size) if clean_size > 0 else 1

        res = {
            "items": [d.model_dump() if hasattr(d, "model_dump") else d for d in slice_items],
            "total": total,
            "page": clean_page,
            "page_size": clean_size,
            "total_pages": total_pages,
            "has_more": has_more,
            "from_cache": False,
        }
        self.set_cache(cache_key, res)
        return res

    def submit_bid(self, demand_id: str, payload: BidCreate) -> BidResponse:
        if demand_id not in self._demands:
            raise KeyError(f"Demand {demand_id} not found")
        demand = self._demands[demand_id]

        bid_id = str(uuid.uuid4())
        now = utc_now_iso()
        bid = BidResponse(
            id=bid_id,
            demand_id=demand_id,
            bidder_id=payload.bidder_id,
            bid_amount_cny=payload.bid_amount_cny,
            delivery_days=payload.delivery_days,
            proposal_text=payload.proposal_text,
            status="SUBMITTED",
            created_at=now,
        )
        if demand_id not in self._bids:
            self._bids[demand_id] = []
        self._bids[demand_id].append(bid)
        demand.bidders_count += 1
        domain_persistence.write("demands.bids", bid_id, bid)
        domain_persistence.write("demands.items", demand_id, demand)
        self.invalidate_cache()
        return bid

    def get_demand(self, demand_id: str) -> Optional[DemandResponse]:
        return self._demands.get(demand_id)

    def validate_publish_payload(self, inputs: dict) -> dict:
        title = inputs.get("title", "").strip()
        desc = inputs.get("description", "").strip()
        budget = float(inputs.get("budget_cny", 0.0))
        category = inputs.get("category", "DEV").upper()
        deadline_days = int(inputs.get("deadline_days", 14))
        creator_id = inputs.get("creator_id", "")
        creator_name = inputs.get("creator_name", "")

        if len(title) < 2:
            raise ValueError("Demand title must be at least 2 characters long")
        if len(desc) < 5:
            raise ValueError("Demand description must be at least 5 characters long")
        if budget < 0:
            raise ValueError("Demand budget cannot be negative")
        if category not in {"DEV", "AI", "TAX", "LEGAL", "BIZ"}:
            category = "DEV"
        if deadline_days < 1:
            deadline_days = 14
        return {
            "guard_passed": True,
            "title": title,
            "description": desc,
            "budget_cny": budget,
            "category": category,
            "deadline_days": deadline_days,
            "creator_id": creator_id,
            "creator_name": creator_name,
        }

    def validate_bid_payload(self, inputs: dict) -> dict:
        demand_id = inputs.get("demand_id", "").strip()
        bidder_id = inputs.get("bidder_id", "").strip()
        amount = float(inputs.get("bid_amount_cny", 0.0))
        delivery_days = int(inputs.get("delivery_days", 7))
        proposal = inputs.get("proposal_text", "").strip()

        if not demand_id:
            raise ValueError("demand_id is required for bidding")
        demand = self.get_demand(demand_id)
        if not demand:
            raise KeyError(f"Demand with ID {demand_id} not found")
        if demand.status != "OPEN":
            raise ValueError(f"Demand {demand_id} is not open for bidding (status: {demand.status})")
        if amount < 0:
            raise ValueError("bid_amount_cny cannot be negative")
        if delivery_days < 1:
            raise ValueError("delivery_days must be at least 1")
        if len(proposal) < 5:
            raise ValueError("proposal_text must be at least 5 characters long")
        return {
            "guard_passed": True,
            "demand_id": demand_id,
            "bidder_id": bidder_id,
            "bid_amount_cny": amount,
            "delivery_days": delivery_days,
            "proposal_text": proposal,
        }

    def delete_demand(self, demand_id: str) -> bool:
        if demand_id in self._demands:
            del self._demands[demand_id]
            domain_persistence.delete("demands.items", demand_id)
            for bid in self._bids.pop(demand_id, []):
                domain_persistence.delete("demands.bids", bid.id)
            return True
        return False

    def delete_bid(self, demand_id: str, bid_id: str) -> bool:
        if demand_id in self._demands and demand_id in self._bids:
            original_len = len(self._bids[demand_id])
            self._bids[demand_id] = [b for b in self._bids[demand_id] if b.id != bid_id]
            if len(self._bids[demand_id]) < original_len:
                if self._demands[demand_id].bidders_count > 0:
                    self._demands[demand_id].bidders_count -= 1
                domain_persistence.delete("demands.bids", bid_id)
                domain_persistence.write("demands.items", demand_id, self._demands[demand_id])
                return True
        return False

    def hydrate_demands(self, rows: List[Dict]) -> int:
        for r in rows:
            self._demands[r["id"]] = DemandResponse(**r)
            self._bids.setdefault(r["id"], [])
        return len(rows)

    def hydrate_bids(self, rows: List[Dict]) -> int:
        for r in rows:
            self._bids.setdefault(r["demand_id"], []).append(BidResponse(**r))
        return len(rows)


demand_service = DemandService()

domain_persistence.register("demands.items", demand_service.hydrate_demands)
domain_persistence.register("demands.bids", demand_service.hydrate_bids)

