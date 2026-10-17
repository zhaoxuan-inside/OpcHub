"""SQLAlchemy 2.0 Declarative ORM Models for PostgreSQL 16+ (ADR-002 & ADR-003).

Strictly maps all 16 core business tables specified in:
hs_dev_docs/_03_architecture_design/_03_detailed_design/_01_database_schema.md
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from src.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Maker & Tenant Account entity (users)."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="MAKER", nullable=False)  # 'ADMIN', 'MAKER', 'GUEST'
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unified_social_credit_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    entitlements: Mapped[List["UserEntitlement"]] = relationship("UserEntitlement", back_populates="user", cascade="all, delete-orphan")
    demands: Mapped[List["Demand"]] = relationship("Demand", back_populates="creator")
    bids: Mapped[List["DemandBid"]] = relationship("DemandBid", back_populates="bidder")
    threads: Mapped[List["ForumThread"]] = relationship("ForumThread", back_populates="author")
    comments: Mapped[List["ForumComment"]] = relationship("ForumComment", back_populates="author", foreign_keys="ForumComment.author_id")
    products: Mapped[List["ProductShowcase"]] = relationship("ProductShowcase", back_populates="author")
    sop_documents: Mapped[List["SOPDocument"]] = relationship("SOPDocument", back_populates="user")
    perk_claims: Mapped[List["PerkClaim"]] = relationship("PerkClaim", back_populates="user")


class Entitlement(Base):
    """System Entitlement Catalog entity (entitlements)."""
    __tablename__ = "entitlements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. 'ENT_VIP', 'ENT_POL_VIP'
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    annual_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserEntitlement(Base):
    """User-Entitlement Association (user_entitlements)."""
    __tablename__ = "user_entitlements"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    entitlement_id: Mapped[str] = mapped_column(String(64), ForeignKey("entitlements.id", ondelete="RESTRICT"), primary_key=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="entitlements")
    entitlement: Mapped["Entitlement"] = relationship("Entitlement")


class Policy(Base):
    """Government Policy Incentive entity with pgvector semantic support (policies)."""
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_plain: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(64), default="CN_YANGTZE", nullable=False, index=True)
    max_subsidy_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    eligibility_rules: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(128), nullable=True)  # pgvector HNSW
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Perk(Base):
    """Compute and Cloud Infrastructure Perk entity (perks)."""
    __tablename__ = "perks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_name: Mapped[str] = mapped_column(String(128), nullable=False)
    perk_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'CLOUD_VOUCHER', 'API_ROUTE'
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    nominal_value_usd: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    remaining_quota: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    total_quota: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    required_entitlement: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("entitlements.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Demand(Base):
    """Outsourcing Demand Marketplace entity (demands)."""
    __tablename__ = "demands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    budget_cny: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    bidders_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False, index=True)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    creator: Mapped["User"] = relationship("User", back_populates="demands")
    bids: Mapped[List["DemandBid"]] = relationship("DemandBid", back_populates="demand", cascade="all, delete-orphan")


class DemandBid(Base):
    """Maker Demand Bidding entity (demand_bids)."""
    __tablename__ = "demand_bids"
    __table_args__ = (UniqueConstraint("demand_id", "bidder_id", name="uq_demand_bid"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    demand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("demands.id", ondelete="CASCADE"), nullable=False, index=True)
    bidder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bid_amount_cny: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    demand: Mapped["Demand"] = relationship("Demand", back_populates="bids")
    bidder: Mapped["User"] = relationship("User", back_populates="bids")


class DAGPipelineConfig(Base):
    """Microkernel Orchestration DAG Pipeline Config entity (dag_pipeline_configs)."""
    __tablename__ = "dag_pipeline_configs"
    __table_args__ = (UniqueConstraint("scenario_code", "version", name="uq_scenario_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    topology_graph: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    compiled_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ForumThread(Base):
    """Community Brainstorm & Experience Thread entity (forum_threads)."""
    __tablename__ = "forum_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_code: Mapped[str] = mapped_column(String(64), default="DEV", nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(128), nullable=True)  # pgvector HNSW
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    upvote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bookmark_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PUBLISHED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    author: Mapped["User"] = relationship("User", back_populates="threads")
    comments: Mapped[List["ForumComment"]] = relationship("ForumComment", back_populates="thread", cascade="all, delete-orphan")


class ForumComment(Base):
    """Materialized-Path Nested Comment entity (forum_comments)."""
    __tablename__ = "forum_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("forum_comments.id", ondelete="CASCADE"), nullable=True)
    root_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("forum_comments.id", ondelete="CASCADE"), nullable=True)
    reply_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    materialized_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    upvote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    thread: Mapped["ForumThread"] = relationship("ForumThread", back_populates="comments")
    author: Mapped["User"] = relationship("User", back_populates="comments", foreign_keys=[author_id])


class ForumUpvote(Base):
    """Forum Thread/Comment Upvote entity (forum_upvotes)."""
    __tablename__ = "forum_upvotes"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id", name="uq_forum_upvote_target"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'THREAD' or 'COMMENT'
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ForumBookmark(Base):
    """Forum Bookmark entity (forum_bookmarks)."""
    __tablename__ = "forum_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "thread_id", name="uq_forum_bookmark"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    folder_name: Mapped[str] = mapped_column(String(64), default="默认收藏夹", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SOPTemplate(Base):
    """Business SOP Template entity (sop_templates)."""
    __tablename__ = "sop_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 'tpl_individual_biz_reg'
    stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    required_fields: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class SOPDocument(Base):
    """Maker Generated Legal / SOP Document entity (sop_documents)."""
    __tablename__ = "sop_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[str] = mapped_column(String(64), ForeignKey("sop_templates.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    form_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    rendered_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="READY", nullable=False)
    compliance_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sop_documents")
    template: Mapped["SOPTemplate"] = relationship("SOPTemplate")


class ProductShowcase(Base):
    """Independent Maker Product Showcase entity (product_showcases)."""
    __tablename__ = "product_showcases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tagline: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="AI", nullable=False, index=True)
    pricing_model: Mapped[str] = mapped_column(String(32), default="SUBSCRIPTION", nullable=False)
    price_cny: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    demo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    upvote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PUBLISHED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    author: Mapped["User"] = relationship("User", back_populates="products")


class PerkClaim(Base):
    """Perk Redemption & Claim Record entity (perk_claims)."""
    __tablename__ = "perk_claims"
    __table_args__ = (UniqueConstraint("perk_id", "user_id", name="uq_perk_user_claim"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("perks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    voucher_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVATED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="perk_claims")
    perk: Mapped["Perk"] = relationship("Perk")


class ContentModerationLog(Base):
    """Governance & Moderation Takedown Record entity (content_moderation_logs)."""
    __tablename__ = "content_moderation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # 'FORUM_THREAD', 'COMMENT'
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    violation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    snippet_content: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'TAKEN_DOWN', 'RESTORED'
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    moderator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RAGVector(Base):
    """Native pgvector RAG Index table for policy and document semantic matching (ADR-003)."""
    __tablename__ = "rag_vectors"

    collection: Mapped[str] = mapped_column(String(128), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditLog(Base):
    """Security & Operation Audit Log (audit_logs).

    Records every privileged / state-changing operation with an encrypted detail
    payload for compliance retention (>= 180 days) per opchub_legal_compliance_spec §80.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(32), default="GUEST", nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    result: Mapped[str] = mapped_column(String(16), default="SUCCESS", nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    detail_encrypted: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)


class AuditLogArchive(Base):
    """Cold-storage archive of audit_logs past the retention window (audit_logs_archive)."""
    __tablename__ = "audit_logs_archive"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(32), default="GUEST", nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    result: Mapped[str] = mapped_column(String(16), default="SUCCESS", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    detail_encrypted: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

