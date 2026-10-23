"""Data models for Ecosystem Privilege Announcements and Claims.

The perks domain hosts the platform's 优惠公告 (discount announcement) board:
Token 优惠 / 服务器优惠 / SaaS 服务优惠 / 结算与支付 / AI 算力 / 基础设施等，
由生态伙伴提报、管理端发布，创客在「生态特权」页浏览并前往服务商处领取。
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class PerkCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    provider: str = Field(..., min_length=2, max_length=255)
    value_cny: float = Field(..., ge=0.0)
    category: str = Field(default="TOKEN", description="TOKEN, SERVER, SAAS, AI, FINANCE, INFRA, OTHER")
    summary: str = Field(..., min_length=5)
    quota_remaining: int = Field(default=100, ge=1)
    # --- announcement fields (优惠公告) ---
    effective_start: Optional[str] = Field(default=None, description="优惠生效开始日期 (YYYY-MM-DD)")
    effective_end: Optional[str] = Field(default=None, description="优惠生效截止日期 (YYYY-MM-DD)")
    redeem_url: Optional[str] = Field(default=None, description="领取 / 详情跳转链接")
    priority: int = Field(default=50, ge=0, le=100, description="置顶优先级，越大越靠前")
    status: str = Field(default="PUBLISHED", description="PUBLISHED / OFFLINE")
    highlights: List[str] = Field(default_factory=list, description="核心卖点短句列表")


class PerkResponse(BaseModel):
    id: str
    name: str
    provider: str
    value_cny: float
    category: str  # "TOKEN", "SERVER", "SAAS", "AI", "FINANCE", "INFRA", "OTHER"
    summary: str
    quota_remaining: int
    # --- announcement fields (优惠公告) ---
    effective_start: Optional[str] = None
    effective_end: Optional[str] = None
    redeem_url: Optional[str] = None
    priority: int = 50
    status: str = "PUBLISHED"
    highlights: List[str] = []
    created_at: Optional[str] = None
    claim_count: int = 0
    like_count: int = 0
    favorite_count: int = 0
    love_count: int = 0
    comment_count: int = 0


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
