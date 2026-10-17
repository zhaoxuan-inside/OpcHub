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


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    nickname: Optional[str] = None
    company_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class AuthSessionResponse(BaseModel):
    token: str
    uid: str
    email: str
    nickname: str
    role: str = "MAKER"
    company_name: Optional[str] = None
    tier_name: str = "标准创客"
    message: str = "登录成功"

