"""Data models for the user message box (消息箱) domain.

The message box is the durable delivery channel for asynchronous platform
results. Today it carries content-moderation receipts (敏感词校验结果) for
published UGC; the model is intentionally generic so review/claim notices can
reuse it later.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Notification kinds (extensible).
KIND_PUBLISH_MODERATION = "PUBLISH_MODERATION"

# Delivery status.
STATUS_UNREAD = "UNREAD"
STATUS_READ = "READ"

# Moderation verdicts carried by a notification.
VERDICT_PASSED = "PASSED"
VERDICT_PASSED_DEGRADED = "PASSED_DEGRADED"
VERDICT_BLOCKED = "BLOCKED"


class Notification(BaseModel):
    id: str
    user_id: str
    kind: str = KIND_PUBLISH_MODERATION
    level: str = Field(default="INFO", description="SUCCESS / WARNING / ERROR / INFO")
    title: str
    content: str = ""
    scene: str = ""
    target_type: str = ""
    target_id: str = ""
    verdict: str = ""
    hit_words: List[str] = Field(default_factory=list)
    status: str = STATUS_UNREAD
    created_at: str
    read_at: Optional[str] = None
    # Fields written by the generic ``notify.emit`` operator. Kept optional so a
    # moderation receipt (content only) and a system notification (body + link)
    # can share the very same entity document.
    body: str = ""
    link: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class NotificationListResponse(BaseModel):
    items: List[Notification] = Field(default_factory=list)
    total: int = 0
    unread: int = 0
    status: Optional[str] = None


class NotificationActionResponse(BaseModel):
    updated: int = 0
    unread: int = 0
    message: str = ""
