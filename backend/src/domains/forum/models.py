"""Data models and schemas for the Forum domain."""
from datetime import datetime, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ForumThreadCreate(BaseModel):
    category_code: str = Field(default="DEV", description="DEV, BIZ, TAX, AGENTS")
    author_id: str = Field(..., description="UUID of author maker")
    title: str = Field(..., min_length=2, max_length=255, description="Thread title")
    content: str = Field(..., min_length=1, description="Thread markdown content")


class ForumThreadResponse(BaseModel):
    id: str
    category_code: str
    author_id: str
    title: str
    content: str
    view_count: int = 0
    upvote_count: int = 0
    comment_count: int = 0
    bookmark_count: int = 0
    is_pinned: bool = False
    status: str = "PUBLISHED"
    created_at: str
    updated_at: str


class ForumCommentCreate(BaseModel):
    author_id: str = Field(..., description="UUID of replying maker")
    content: str = Field(..., min_length=1, description="Reply markdown content")
    parent_id: Optional[str] = Field(None, description="Parent comment UUID, None for top-level answer")
    reply_to_user_id: Optional[str] = Field(None, description="Optional target user UUID being replied to")


class ForumCommentResponse(BaseModel):
    id: str
    thread_id: str
    author_id: str
    content: str
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    reply_to_user_id: Optional[str] = None
    materialized_path: str
    depth: int = 0
    upvote_count: int = 0
    is_accepted: bool = False
    status: str = "ACTIVE"
    created_at: str
    updated_at: str


class CommentTreeNode(BaseModel):
    id: str
    thread_id: str
    author_id: str
    content: str
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    reply_to_user_id: Optional[str] = None
    materialized_path: str
    depth: int = 0
    upvote_count: int = 0
    is_accepted: bool = False
    status: str = "ACTIVE"
    created_at: str
    updated_at: str
    children: List["CommentTreeNode"] = Field(default_factory=list)


CommentTreeNode.model_rebuild()


class ThreadDetailResponse(BaseModel):
    thread: ForumThreadResponse
    comments: List[CommentTreeNode] = Field(default_factory=list)


class UpvoteRequest(BaseModel):
    user_id: str
    target_type: Literal["THREAD", "COMMENT"]
    target_id: str


class UpvoteResponse(BaseModel):
    is_upvoted: bool
    upvote_count: int
    target_type: Literal["THREAD", "COMMENT"]
    target_id: str


class BookmarkRequest(BaseModel):
    user_id: str
    thread_id: str
    folder_name: str = "默认收藏夹"


class BookmarkResponse(BaseModel):
    is_bookmarked: bool
    bookmark_count: int
    thread_id: str
    folder_name: str
