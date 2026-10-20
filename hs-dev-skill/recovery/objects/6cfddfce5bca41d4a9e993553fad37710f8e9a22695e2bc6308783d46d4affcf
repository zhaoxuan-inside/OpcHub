"""Data models for Product Development Compliance & Risk Audit."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ComplianceDimension(BaseModel):
    id: str
    title: str
    summary: str
    core_rules: List[str]
    penalties: str
    law_ref: str
    icon_name: str


class ComplianceCase(BaseModel):
    id: str
    title: str
    industry: str
    violation: str
    consequence: str
    lesson: str
    badge_color: str


class AuditCheckItem(BaseModel):
    id: str
    dimension_id: str
    title: str
    description: str
    severity: str  # "HIGH", "CRITICAL", "MEDIUM"
    weight: int
    advice: str
    legal_basis: str


class AuditEvaluateRequest(BaseModel):
    passed_item_ids: List[str] = Field(default_factory=list)


class AuditReportResponse(BaseModel):
    score: int
    grade: str  # "EXCELLENT", "GOOD", "WARNING", "CRITICAL"
    total_items: int
    passed_items_count: int
    failed_items_count: int
    risk_items: List[AuditCheckItem]
    remedy_suggestions: List[str]
    legal_help_recommendation: Optional[str] = None
