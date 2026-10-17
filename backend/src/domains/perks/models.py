"""Data models for Developer Ecosystem Perks and Claims."""
from typing import Optional
from pydantic import BaseModel, Field


class PerkCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    provider: str = Field(..., min_length=2, max_length=255)
    value_cny: float = Field(..., ge=0.0)
    category: str = Field(default="CLOUD", description="CLOUD, AI, FINANCE, INFRA")
    summary: str = Field(..., min_length=5)
    quota_remaining: int = Field(default=100, ge=1)


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
