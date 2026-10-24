"""Data models for Corporate Demands and Maker Bids."""
from typing import Optional
from pydantic import BaseModel, Field


class DemandCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    budget_cny: float = Field(..., ge=0.0)
    category: str = Field(default="DEV", description="DEV, BIZ, TAX, AI, LEGAL")
    deadline_days: int = Field(default=14, ge=1)
    creator_id: str
    creator_name: Optional[str] = None
    is_official: bool = False


class DemandResponse(BaseModel):
    id: str
    creator_id: str
    creator_name: Optional[str] = None
    is_official: bool = False
    title: str
    description: str
    budget_cny: float
    category: str
    bidders_count: int = 0
    like_count: int = 0
    favorite_count: int = 0
    love_count: int = 0
    comment_count: int = 0
    status: str = "OPEN"  # "OPEN", "BIDDING", "CLOSED"
    deadline_at: str
    created_at: str


class BidCreate(BaseModel):
    bidder_id: str
    bid_amount_cny: float = Field(..., ge=0.0)
    delivery_days: int = Field(..., ge=1)
    proposal_text: str = Field(..., min_length=5)


class BidResponse(BaseModel):
    id: str
    demand_id: str
    bidder_id: str
    bid_amount_cny: float
    delivery_days: int
    proposal_text: str
    status: str = "SUBMITTED"
    created_at: str
