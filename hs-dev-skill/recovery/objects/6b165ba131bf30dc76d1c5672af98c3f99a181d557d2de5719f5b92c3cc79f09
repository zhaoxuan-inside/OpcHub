"""Demands service managing corporate outsourcing requirements and maker bids."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from src.domains.demands.models import (
    DemandCreate,
    DemandResponse,
    BidCreate,
    BidResponse,
)
from src.infrastructure.database.persistence import domain_persistence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DemandService:
    """Manages demands and bids."""

    def __init__(self):
        self._demands: Dict[str, DemandResponse] = {}
        self._bids: Dict[str, List[BidResponse]] = {}

    def create_demand(self, payload: DemandCreate) -> DemandResponse:
        did = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        deadline = (now + timedelta(days=payload.deadline_days)).isoformat()
        demand = DemandResponse(
            id=did,
            creator_id=payload.creator_id,
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
        return demand

    def list_demands(self, category: Optional[str] = None) -> List[DemandResponse]:
        demands = list(self._demands.values())
        if category:
            demands = [d for d in demands if d.category == category]
        demands.sort(key=lambda d: d.created_at, reverse=True)
        return demands

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
        return bid

    def get_demand(self, demand_id: str) -> Optional[DemandResponse]:
        return self._demands.get(demand_id)

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

