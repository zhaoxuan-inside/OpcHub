"""Data models for Policy Radar and Qualification Matching."""
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


class PolicyResponse(BaseModel):
    id: str
    title: str
    policy_level: str  # "国家级", "省市级", "园区级"
    category: str      # "TAX", "SUBSIDY", "RENT", "TALENT"
    subsidy_amount_max: float
    summary: str
    eligible_conditions: List[str]
    legal_basis: str


class PolicyMatchRequest(BaseModel):
    quarterly_income: float = Field(..., ge=0.0, description="季度含税销售额 (CNY)")
    maker_type: str = Field(default="INDIVIDUAL", description="INDIVIDUAL (个体户) or OPC (一人有限责任公司)")
    region: str = Field(default="杭州", description="经营所在地城市")


class PolicyMatchResponse(BaseModel):
    eligible: bool
    applicable_tax_rate: float
    estimated_tax_savings: float
    legal_basis: str
    matched_policies: List[PolicyResponse]
    explanation: str
