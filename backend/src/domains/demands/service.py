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

    def validate_publish_payload(self, inputs: dict) -> dict:
        title = inputs.get("title", "").strip()
        desc = inputs.get("description", "").strip()
        budget = float(inputs.get("budget_cny", 0.0))
        category = inputs.get("category", "DEV").upper()
        deadline_days = int(inputs.get("deadline_days", 14))
        creator_id = inputs.get("creator_id", "")

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

