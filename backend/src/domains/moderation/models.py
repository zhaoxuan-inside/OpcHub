"""Data models and schemas for Content Moderation domain."""
from typing import Optional, List
from pydantic import BaseModel, Field


class ModerationItemResponse(BaseModel):
    id: str
    target_type: str = Field(..., description="FORUM_THREAD, FORUM_COMMENT, PRODUCT_REVIEW")
    target_id: str
    author_id: str
    author_name: str
    snippet_content: str
    violation_type: str = Field(..., description="ILLEGAL_TRADE, SENSITIVE_SPEECH, SCAM, SPAM")
    status: str = Field(default="FLAGGED", description="FLAGGED, TAKEN_DOWN, NORMAL")
    reported_at: str
    moderated_at: Optional[str] = None
    reason: Optional[str] = None
    moderator_id: Optional[str] = None


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
