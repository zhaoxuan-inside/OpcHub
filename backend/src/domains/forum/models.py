"""Data models and schemas for the Forum (头脑风暴) domain in Zhihu-style architecture."""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ForumThreadCreate(BaseModel):
    category_code: str = Field(default="DEV", description="DEV, BIZ, TAX, AGENTS, POLICY")
    author_id: str = Field(..., description="UUID of author maker")
    author_name: Optional[str] = Field(None, description="Display name of author maker")
    author_title: Optional[str] = Field(None, description="Maker bio or badge title")
    is_official: bool = Field(False, description="官方认证标签")
    title: str = Field(..., min_length=2, max_length=255, description="Thread or question title")
    content: str = Field(..., min_length=1, description="Thread description in markdown")


class ForumAnswerCreate(BaseModel):
    thread_id: str = Field(..., description="UUID of parent thread or question")
    author_id: str = Field(..., description="UUID of answering maker")
    author_name: Optional[str] = Field(None, description="Display name of answering maker")
    author_title: Optional[str] = Field(None, description="Maker role or bio")
    content: str = Field(..., min_length=5, description="In-depth perspective markdown content")


class ForumAnswerResponse(BaseModel):
    id: str
    thread_id: str
    author_id: str
    author_name: Optional[str] = None
    author_title: Optional[str] = None
    author_avatar: Optional[str] = None
    content: str
    upvote_count: int = 0
    downvote_count: int = 0
    comment_count: int = 0
    is_accepted: bool = False
    word_count: int = 0
    read_minutes: int = 1
    status: str = "PUBLISHED"
    user_vote: Optional[str] = None
    created_at: str
    updated_at: str


class ForumThreadResponse(BaseModel):
    id: str
    category_code: str
    author_id: str
    author_name: Optional[str] = None
    author_title: Optional[str] = None
    is_official: bool = False
    title: str
    content: str
    view_count: int = 0
    upvote_count: int = 0
    downvote_count: int = 0
    comment_count: int = 0
    answer_count: int = 0
    follow_count: int = 0
    bookmark_count: int = 0
    love_count: int = 0
    is_pinned: bool = False
    status: str = "PUBLISHED"
    accepted_answer_id: Optional[str] = None
    hot_score: float = 0.0
    top_answers: List[ForumAnswerResponse] = Field(default_factory=list)
    user_vote: Optional[str] = None
    is_bookmarked: bool = False
    is_following: bool = False
    created_at: str
    updated_at: str


class ForumCommentCreate(BaseModel):
    author_id: str = Field(..., description="UUID of replying maker")
    content: str = Field(..., min_length=1, description="Reply markdown content")
    target_type: Literal["THREAD", "ANSWER"] = Field("ANSWER", description="Target type being commented on")
    target_id: Optional[str] = Field(None, description="UUID of target thread or answer")
    parent_id: Optional[str] = Field(None, description="Parent comment UUID, None for top-level reply")
    reply_to_user_id: Optional[str] = Field(None, description="Optional target user UUID being replied to")


class ForumCommentResponse(BaseModel):
    id: str
    thread_id: str
    target_type: str = "ANSWER"
    target_id: str = ""
    author_id: str
    author_name: Optional[str] = None
    author_title: Optional[str] = None
    content: str
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    reply_to_user_id: Optional[str] = None
    materialized_path: str
    depth: int = 0
    upvote_count: int = 0
    downvote_count: int = 0
    is_accepted: bool = False
    status: str = "ACTIVE"
    created_at: str
    updated_at: str


class CommentTreeNode(BaseModel):
    id: str
    thread_id: str
    target_type: str = "ANSWER"
    target_id: str = ""
    author_id: str
    author_name: Optional[str] = None
    author_title: Optional[str] = None
    content: str
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    reply_to_user_id: Optional[str] = None
    materialized_path: str
    depth: int = 0
    upvote_count: int = 0
    downvote_count: int = 0
    is_accepted: bool = False
    status: str = "ACTIVE"
    created_at: str
    updated_at: str
    children: List["CommentTreeNode"] = Field(default_factory=list)


CommentTreeNode.model_rebuild()


class ThreadDetailResponse(BaseModel):
    thread: ForumThreadResponse
    answers: List[ForumAnswerResponse] = Field(default_factory=list)
    comments: List[CommentTreeNode] = Field(default_factory=list)


class VoteRequest(BaseModel):
    user_id: str
    target_type: Literal["THREAD", "ANSWER", "COMMENT"]
    target_id: str
    vote_type: Literal["UPVOTE", "DOWNVOTE", "CANCEL"]


class VoteResponse(BaseModel):
    user_vote: Optional[Literal["UPVOTE", "DOWNVOTE"]] = None
    upvote_count: int
    downvote_count: int
    target_type: Literal["THREAD", "ANSWER", "COMMENT"]
    target_id: str


# Backwards compatibility models
class UpvoteRequest(BaseModel):
    user_id: str
    target_type: Literal["THREAD", "COMMENT", "ANSWER"]
    target_id: str


class UpvoteResponse(BaseModel):
    is_upvoted: bool
    upvote_count: int
    target_type: Literal["THREAD", "COMMENT", "ANSWER"]
    target_id: str


class AnswerAcceptRequest(BaseModel):
    thread_id: str
    answer_id: str
    operator_user_id: str


class AnswerAcceptResponse(BaseModel):
    thread_id: str
    answer_id: str
    is_accepted: bool
    status: str


class BookmarkRequest(BaseModel):
    user_id: str
    thread_id: str
    folder_name: str = "默认收藏夹"


class BookmarkResponse(BaseModel):
    is_bookmarked: bool
    bookmark_count: int
    thread_id: str
    folder_name: str
