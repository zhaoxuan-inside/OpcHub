"""Data models for Product Compliance Guide (法条 / 案例 知识库).

数据 / 配置 / 代码三分离：业务数据存于 backend/data/seeds/compliance.json 并
持久化至 PostgreSQL；本文件仅定义领域模型与请求/响应契约。
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ComplianceLaw(BaseModel):
    """法条条目：法律、行政法规、部门规章等的白话提炼与条文要点。"""
    id: str
    code: str = ""  # 展示编号 (如 LAW-01)
    name: str = ""  # 短名称 (如 个人信息保护)
    title: str  # 法条标题
    summary: str  # 白话要点
    content: str = ""  # 核心条文内容
    level: str = "国家级"  # 效力级别 (法律/行政法规/部门规章/地方性法规)
    issuer: str = ""  # 发布机关
    published_at: str = ""  # 发布日期
    penalties: str = ""  # 违规罚则
    law_ref: str = ""  # 法条依据引用
    icon_name: str = ""
    hot_score: int = 0  # 热度分 (打榜/热门排序)


class ComplianceCase(BaseModel):
    """避坑案例：真实监管处罚与踩坑教训。"""
    id: str
    title: str
    badge: str = ""  # 徽章文案 (如 二清违规冻结 · 涉案 68 万元)
    industry: str
    violation: str
    consequence: str
    lesson: str
    badge_color: str = "#5B6472"
    hot_score: int = 0  # 热度分 (打榜/热门排序)


class CompliancePublishRequest(BaseModel):
    """发布法条或案例的统一入参。kind: "law" | "case" """
    kind: str  # "law" | "case"
    id: Optional[str] = None
    code: str = ""
    name: str = ""
    title: str
    summary: str = ""
    content: str = ""
    level: str = "国家级"
    issuer: str = ""
    published_at: str = ""
    penalties: str = ""
    law_ref: str = ""
    icon_name: str = ""
    industry: str = ""
    violation: str = ""
    consequence: str = ""
    lesson: str = ""
    badge: str = ""
    badge_color: str = "#5B6472"


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
