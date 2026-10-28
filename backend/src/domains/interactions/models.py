"""Models for unified content interactions and comments.

The platform exposes four interactions on every public card:

* ``LIKE``     - 点赞 (thumbs up, yellow)
* ``FAVORITE`` - 收藏 (star, blue)
* ``LOVE``     - 喜欢 (heart, red)
* comments     - 评论 (bubble, green)

``target_type`` is a stable, upper-case resource discriminator so one interaction
store can serve every public content domain without cross-domain imports.
"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

InteractionKind = Literal["LIKE", "FAVORITE", "LOVE", "DISLIKE"]

TARGET_TYPES = {
    "PRODUCT",
    "POLICY",
    "DEMAND",
    "FORUM_THREAD",
    "SOP_DOCUMENT",
    "SOP_FLOW",
    "PERK",
}

INTERACTION_KINDS = {"LIKE", "FAVORITE", "LOVE", "DISLIKE"}


class InteractionTarget(BaseModel):
    target_type: str
    target_id: str
    target_title: Optional[str] = None


class InteractionToggleRequest(InteractionTarget):
    kind: str


class InteractionViewerState(BaseModel):
    liked: bool = False
    favorited: bool = False
    loved: bool = False
    commented: bool = False
    disliked: bool = False
    rating: int = 0


class InteractionState(BaseModel):
    target_type: str
    target_id: str
    like_count: int = 0
    favorite_count: int = 0
    love_count: int = 0
    comment_count: int = 0
    dislike_count: int = 0
    rating_avg: float = 0.0
    rating_count: int = 0
    viewer: InteractionViewerState = Field(default_factory=InteractionViewerState)


class InteractionToggleResponse(InteractionState):
    kind: str
    active: bool = False
    count: int = 0


class InteractionStateBatchRequest(BaseModel):
    targets: List[InteractionTarget] = Field(default_factory=list)


class InteractionStateBatchResponse(BaseModel):
    items: List[InteractionState] = Field(default_factory=list)


class InteractionRateRequest(BaseModel):
    target_type: str
    target_id: str
    score: int = Field(..., ge=1, le=5)


class ContentCommentCreate(BaseModel):
    target_type: str
    target_id: str
    content: str = Field(..., min_length=1, max_length=4000)
    author_name: Optional[str] = None
    parent_id: Optional[str] = None


class ContentComment(BaseModel):
    id: str
    target_type: str
    target_id: str
    author_id: str
    author_name: Optional[str] = "创客"
    content: str
    parent_id: Optional[str] = None
    # Snapshot of the owning target's display title, so the personal interaction
    # centre can be assembled without cross-domain lookups.
    target_title: Optional[str] = ""
    created_at: str


class ContentCommentListResponse(BaseModel):
    items: List[ContentComment] = Field(default_factory=list)
    total: int = 0


class MyInteractionItem(BaseModel):
    target_type: str
    target_id: str
    kind: str
    title: str = ""
    subtitle: str = ""
    tab: str = ""
    created_at: str = ""


class MyInteractionResponse(BaseModel):
    items: List[MyInteractionItem] = Field(default_factory=list)
    counts: Dict[str, int] = Field(default_factory=dict)
