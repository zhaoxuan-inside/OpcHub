"""Data models for Maker Profile and Paid Entitlements."""
from typing import List, Optional
from pydantic import BaseModel, Field


class EntitlementItem(BaseModel):
    id: str
    name: str
    tier: str  # "STANDARD", "PRO", "BLACK_DIAMOND"
    price_cny: float
    description: str
    is_active: bool = False
    quota_desc: str


class MakerProfileResponse(BaseModel):
    uid: str
    nickname: str
    role: str
    company_name: str
    credit_code: str
    tier_name: str
    entitlements: List[EntitlementItem]


class EntitlementActivateRequest(BaseModel):
    user_id: str
    entitlement_id: str


class EntitlementActivateResponse(BaseModel):
    user_id: str
    entitlement_id: str
    is_active: bool
    status: str = "ACTIVATED"
    receipt_no: str
    message: str
