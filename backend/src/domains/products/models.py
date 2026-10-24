"""Data models for Product Showcases."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    tagline: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    category: str = Field(default="AI", description="AI, SAAS, DEV, DEV_OPS")
    pricing_model: str = Field(default="SUBSCRIPTION", description="FREE, ONE_TIME, SUBSCRIPTION")
    price_cny: float = Field(default=0.0, ge=0.0)
    demo_url: Optional[str] = None
    icon_url: Optional[str] = None
    version: Optional[str] = "1.0.0"
    official_url: Optional[str] = None
    download_url: Optional[str] = None
    author_name: Optional[str] = None
    author_id: str = ""
    is_official: bool = False
    screenshots: Optional[List[str]] = None


class ProductResponse(BaseModel):
    id: str
    author_id: str
    title: str
    tagline: str
    description: str
    category: str
    pricing_model: str
    price_cny: float
    demo_url: Optional[str] = None
    icon_url: Optional[str] = None
    version: Optional[str] = "1.0.0"
    official_url: Optional[str] = None
    download_url: Optional[str] = None
    author_name: Optional[str] = None
    is_official: bool = False
    screenshots: Optional[List[str]] = None
    upvote_count: int = 0
    favorite_count: int = 0
    love_count: int = 0
    comment_count: int = 0
    status: str = "PUBLISHED"
    created_at: str
    updated_at: str

