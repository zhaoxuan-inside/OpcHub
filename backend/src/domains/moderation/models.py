"""Data models and schemas for Content Moderation domain."""
from typing import Optional
from pydantic import BaseModel, Field


# User-reportable content targets (aligns with the unified interaction targets).
REPORTABLE_TARGET_TYPES = {
    "PRODUCT", "POLICY", "DEMAND", "FORUM_THREAD", "SOP_DOCUMENT", "SOP_FLOW", "PERK",
}


class ModerationItemResponse(BaseModel):
    id: str
    target_type: str = Field(
        ...,
        description="FORUM_THREAD, FORUM_COMMENT, PRODUCT_REVIEW, PRODUCT, POLICY, DEMAND, SOP_DOCUMENT, SOP_FLOW, PERK",
    )
    target_id: str
    author_id: str
    author_name: str
    snippet_content: str
    violation_type: str = Field(..., description="ILLEGAL_TRADE, SENSITIVE_SPEECH, SCAM, SPAM, USER_REPORT")
    status: str = Field(default="FLAGGED", description="FLAGGED, TAKEN_DOWN, NORMAL")
    report_count: int = Field(default=0, description="用户举报累计次数")
    reported_at: str
    moderated_at: Optional[str] = None
    reason: Optional[str] = None
    moderator_id: Optional[str] = None


class ContentReportRequest(BaseModel):
    """User-submitted report on questionable content (举报失实/违规内容)."""
    target_type: str
    target_id: str
    target_title: str = ""
    snippet_content: str = ""
    author_id: str = ""
    author_name: str = ""
    reason: str = ""
    reporter_id: str = ""


class TakedownRequest(BaseModel):
    item_id: str
    reason: str
    moderator_id: str = "admin_001"
    ban_author: bool = False


class RestoreRequest(BaseModel):
    item_id: str
    moderator_id: str = "admin_001"


class ModerationActionResponse(BaseModel):
    item_id: str
    status: str
    moderated_at: str
    note: str
