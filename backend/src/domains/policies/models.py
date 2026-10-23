"""Data models for Policy Center and Qualification Matching."""
from typing import List, Optional
from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    policy_level: str = Field(default="国家级", description="国家级, 省市级, 园区级")
    category: str = Field(default="TAX", description="TAX, SUBSIDY, RENT, TALENT")
    subsidy_amount_max: float = Field(default=0.0, ge=0.0)
    summary: str = Field(..., min_length=5)
    eligible_conditions: List[str] = Field(default_factory=list)
    legal_basis: str = Field(..., min_length=2)
    code: Optional[str] = Field(default=None, description="政策编号 (如 POL-2026-081)")
    region: Optional[str] = Field(default="全国统一", description="适用地域")
    deadline: Optional[str] = Field(default="常年有效", description="申报截止日期")
    action_text: Optional[str] = Field(default="匹配资格", description="卡片操作文案")


class PolicyResponse(BaseModel):
    id: str
    title: str
    policy_level: str  # "国家级", "省市级", "园区级"
    category: str      # "TAX", "SUBSIDY", "RENT", "TALENT"
    subsidy_amount_max: float
    summary: str
    eligible_conditions: List[str]
    legal_basis: str
    code: Optional[str] = "POL-2026-001"
    region: Optional[str] = "全国统一"
    deadline: Optional[str] = "常年有效"
    action_text: Optional[str] = "匹配资格"
    like_count: int = 0
    favorite_count: int = 0
    love_count: int = 0
    comment_count: int = 0


class PolicyMatchRequest(BaseModel):
    quarterly_income: float = Field(..., ge=0.0, description="季度含税销售额 (CNY)")
    maker_type: str = Field(default="INDIVIDUAL", description="INDIVIDUAL (个体户) or OPC (一人有限责任公司)")
    region: str = Field(default="杭州", description="经营所在地城市")
    search_query: Optional[str] = Field(default=None, description="自然语言业务描述或意向关键词")
    industry_keywords: Optional[List[str]] = Field(default=None, description="业务行业标签列表")


class PolicyMatchResponse(BaseModel):
    eligible: bool
    applicable_tax_rate: float
    estimated_tax_savings: float
    legal_basis: str
    matched_policies: List[PolicyResponse]
    explanation: str
    relevance_scores: Optional[dict[str, float]] = None
