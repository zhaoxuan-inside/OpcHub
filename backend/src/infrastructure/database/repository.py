"""Asynchronous Database Repository for PostgreSQL 16+ (ADR-002 & ADR-003).

Provides async database CRUD operations across all core business tables with graceful fallback.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_engine, get_async_sessionmaker, check_database_health
from src.core.security import hash_password
from src.infrastructure.database.models import (
    Base,
    User,
    Entitlement,
    UserEntitlement,
    Policy,
    Perk,
    PerkClaim,
    Demand,
    DemandBid,
    DAGPipelineConfig,
    ForumThread,
    ForumComment,
    ForumUpvote,
    ForumBookmark,
    SOPTemplate,
    SOPDocument,
    ProductShowcase,
    ContentModerationLog,
    RAGVector,
)

logger = logging.getLogger("opchub.repository")


class DatabaseRepository:
    """Central repository managing asynchronous persistence for OpcHub."""

    def __init__(self):
        self._initialized = False

    async def is_ready(self) -> bool:
        """Probe if live PostgreSQL instance is available and healthy."""
        try:
            health = await check_database_health()
            return health.get("status") == "healthy"
        except Exception:
            return False

    async def ensure_schema_and_seed(self) -> None:
        """Create tables if not exist and seed foundational catalog data."""
        if self._initialized:
            return
        if not await self.is_ready():
            logger.info("PostgreSQL daemon not online; skipping DB DDL initialization.")
            return

        engine = get_async_engine()
        async with engine.begin() as conn:
            # Create extension pgvector if possible
            try:
                from sqlalchemy import text
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception as e:
                logger.debug("vector extension create skipped: %s", e)
            await conn.run_sync(Base.metadata.create_all)

        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            # Seed Entitlements
            ent_count = (await session.execute(select(func.count(Entitlement.id)))).scalar() or 0
            if ent_count == 0:
                default_ents = [
                    Entitlement(id="ent_microkernel_pipeline", name="微内核高并发编排算力通道", description="基础微内核 DAG 串联与沙箱执行能力", annual_price=0.00, is_active=True),
                    Entitlement(id="ent_policy_radar_basic", name="全国与地方政策雷达白话提炼", description="免费查阅与匹配国家级增值税与小微企业免税政策", annual_price=0.00, is_active=True),
                    Entitlement(id="ent_ai_tax_assistant", name="AI 政策智能测算与申报材料极速出具", description="解锁一键生成符合政务标准的设立登记、软著申报全套文书", annual_price=199.00, is_active=True),
                    Entitlement(id="ent_black_diamond_priority", name="黑钻合伙人 VIP 优先需求派单特权", description="获得企业技术外包与出海委托优先推荐接单权限", annual_price=899.00, is_active=True),
                ]
                session.add_all(default_ents)

            # Seed Default User
            user_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
            if user_count == 0:
                demo_maker = User(
                    uid="usr_2026_opc_9981",
                    email="maker@opchub.cn",
                    nickname="赵玄",
                    role="MAKER",
                    company_name="极客视界（杭州）信息技术工作室",
                    unified_social_credit_code="92330106MAD7XXXX8Y",
                    password_hash=hash_password("maker123456"),
                    is_active=True,
                    metadata_payload={"tier": "BLACK_DIAMOND", "vat_savings_ytd": 24000.0},
                )
                session.add(demo_maker)

            # Seed Default Policies
            pol_count = (await session.execute(select(func.count(Policy.id)))).scalar() or 0
            if pol_count == 0:
                p1 = Policy(
                    code="POL-VAT-2026",
                    title="小规模纳税人月销售额 10 万以下（季度 30 万）免征增值税",
                    summary_plain="小规模纳税人合计月销售额未超过10万元（以1个季度为纳税期限的，季度销售额未超过30万元）的，免征增值税。",
                    region="CN_NATIONAL",
                    max_subsidy_amount=9000.00,
                    eligibility_rules={"min_quarterly_income": 0, "max_quarterly_income": 300000},
                    is_active=True,
                )
                p2 = Policy(
                    code="POL-RND-100",
                    title="科技型中小微企业研发费用 100% 税前加计扣除",
                    summary_plain="科技型中小企业开展研发活动中实际发生的研发费用，未形成无形资产计入当期损益的，在税前加计扣除100%。",
                    region="CN_NATIONAL",
                    max_subsidy_amount=150000.00,
                    eligibility_rules={"tech_enterprise": True},
                    is_active=True,
                )
                p3 = Policy(
                    code="POL-AI-HZ-2026",
                    title="杭州高新区超级个体与小微人工智能算力券补贴",
                    summary_plain="为注册在本区开展大模型微调、生成式AI应用独立研发的创客主体，提供最高 30% 的实际算力消费抵扣凭据。",
                    region="CN_YANGTZE",
                    max_subsidy_amount=50000.00,
                    eligibility_rules={"region": "CN_YANGTZE"},
                    is_active=True,
                )
                session.add_all([p1, p2, p3])

            await session.commit()
            self._initialized = True
            logger.info("PostgreSQL tables and seed catalog initialized successfully.")

    # -------------------------------------------------------------
    # User & Auth Repository Methods
    # -------------------------------------------------------------
    async def get_user_by_email(self, email: str) -> Optional[User]:
        if not await self.is_ready():
            return None
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(User).where(User.email == email.strip().lower())
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_user_by_uid(self, uid: str) -> Optional[User]:
        if not await self.is_ready():
            return None
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(User).where(User.uid == uid)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password_plain: str,
        nickname: Optional[str] = None,
        company_name: Optional[str] = None,
        role: str = "MAKER",
    ) -> User:
        clean_email = email.strip().lower()
        clean_nick = nickname.strip() if nickname else clean_email.split("@")[0]
        uid = f"usr_{uuid.uuid4().hex[:12]}"
        pwd_hash = hash_password(password_plain)

        new_user = User(
            uid=uid,
            email=clean_email,
            nickname=clean_nick,
            company_name=company_name or f"{clean_nick}独立工作室",
            role=role,
            password_hash=pwd_hash,
            is_active=True,
            metadata_payload={"tier": "STANDARD", "created_source": "EMAIL_REG"},
        )

        if await self.is_ready():
            session_maker = get_async_sessionmaker()
            async with session_maker() as session:
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
        return new_user

    # -------------------------------------------------------------
    # Forum Repository Methods
    # -------------------------------------------------------------
    async def list_forum_threads(self, limit: int = 50) -> List[ForumThread]:
        if not await self.is_ready():
            return []
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(ForumThread).order_by(ForumThread.is_pinned.desc(), ForumThread.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create_forum_thread(
        self,
        author_id: uuid.UUID,
        title: str,
        content: str,
        category_code: str = "DEV",
        embedding: Optional[List[float]] = None,
    ) -> ForumThread:
        thread = ForumThread(
            author_id=author_id,
            title=title,
            content=content,
            category_code=category_code,
            embedding=embedding,
            status="PUBLISHED",
        )
        if await self.is_ready():
            session_maker = get_async_sessionmaker()
            async with session_maker() as session:
                session.add(thread)
                await session.commit()
                await session.refresh(thread)
        return thread

    # -------------------------------------------------------------
    # Demands Repository Methods
    # -------------------------------------------------------------
    async def list_demands(self, status: str = "OPEN", limit: int = 50) -> List[Demand]:
        if not await self.is_ready():
            return []
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(Demand).where(Demand.status == status).order_by(Demand.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create_demand(
        self,
        creator_id: uuid.UUID,
        title: str,
        description: str,
        budget_cny: float,
        category: str,
        deadline_at: datetime,
    ) -> Demand:
        demand = Demand(
            creator_id=creator_id,
            title=title,
            description=description,
            budget_cny=budget_cny,
            category=category,
            deadline_at=deadline_at,
            status="OPEN",
        )
        if await self.is_ready():
            session_maker = get_async_sessionmaker()
            async with session_maker() as session:
                session.add(demand)
                await session.commit()
                await session.refresh(demand)
        return demand

    async def create_demand_bid(
        self,
        demand_id: uuid.UUID,
        bidder_id: uuid.UUID,
        bid_amount_cny: float,
        delivery_days: int,
        proposal_text: str,
    ) -> DemandBid:
        bid = DemandBid(
            demand_id=demand_id,
            bidder_id=bidder_id,
            bid_amount_cny=bid_amount_cny,
            delivery_days=delivery_days,
            proposal_text=proposal_text,
            status="SUBMITTED",
        )
        if await self.is_ready():
            session_maker = get_async_sessionmaker()
            async with session_maker() as session:
                session.add(bid)
                # Increment demand bidders_count
                await session.execute(
                    update(Demand).where(Demand.id == demand_id).values(bidders_count=Demand.bidders_count + 1)
                )
                await session.commit()
                await session.refresh(bid)
        return bid


db_repository = DatabaseRepository()
