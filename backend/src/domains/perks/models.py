"""Data models for Developer Ecosystem Perks and Claims."""
from typing import Optional
from pydantic import BaseModel, Field


class PerkResponse(BaseModel):
    id: str
    name: str
    provider: str
    value_cny: float
    category: str  # "CLOUD", "AI", "FINANCE", "INFRA"
    summary: str
    quota_remaining: int


class PerkClaimRequest(BaseModel):
    user_id: str
    perk_id: str


class PerkClaimResponse(BaseModel):
    claim_id: str
    perk_id: str
    perk_name: str
    user_id: str
    voucher_code: str
    status: str = "ACTIVATED"
    instructions: str
    created_at: str
