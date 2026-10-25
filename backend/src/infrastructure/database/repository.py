"""Asynchronous Database Repository for PostgreSQL 16+ (ADR-002 & ADR-003).

Provides async database CRUD operations across all core business tables with graceful fallback.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete as sa_delete, select, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.database import get_async_engine, get_async_sessionmaker, check_database_health
from src.core.security import hash_password
from src.infrastructure.database.models import (
    AuditLog,
    AuditLogArchive,
    Base,
    Demand,
    DomainSnapshot,
    ForumThread,
    User,
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
        """Create tables if not exist. No demo seed data is injected (blank initial catalog)."""
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

        self._initialized = True
        logger.info("PostgreSQL tables initialized (blank catalog, no demo seed).")

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

    async def get_user_by_account(self, account: str) -> Optional[User]:
        """Fetch a user by email, uid, or nickname."""
        if not await self.is_ready():
            return None
        session_maker = get_async_sessionmaker()
        clean = (account or "").strip()
        clean_lower = clean.lower()
        async with session_maker() as session:
            stmt = select(User).where(
                or_(
                    User.email == clean_lower,
                    User.uid == clean,
                    User.nickname == clean,
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def create_user(
        self,
        email: str,
        password_plain: str,
        nickname: Optional[str] = None,
        company_name: Optional[str] = None,
        role: str = "MAKER",
        credit_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        clean_email = email.strip().lower()
        clean_nick = nickname.strip() if nickname else clean_email.split("@")[0]
        uid = str(uuid.uuid4())
        pwd_hash = hash_password(password_plain)

        user_meta = {"tier": "STANDARD", "created_source": "COMMERCIAL_REG"}
        if metadata:
            user_meta.update(metadata)

        new_user = User(
            uid=uid,
            email=clean_email,
            nickname=clean_nick,
            company_name=company_name or "",
            unified_social_credit_code=credit_code,
            role=role,
            password_hash=pwd_hash,
            is_active=True,
            metadata_payload=user_meta,
        )

        if await self.is_ready():
            session_maker = get_async_sessionmaker()
            async with session_maker() as session:
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
        return new_user

    async def ensure_builtin_admin(
        self,
        uid: str,
        email: str,
        nickname: str,
        password_hash: str,
    ) -> Optional[User]:
        """Idempotently persist the built-in ADMIN account (RBAC §1.1)."""
        if not await self.is_ready():
            return None
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(User).where(User.uid == uid)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                return existing
            admin = User(
                uid=uid,
                email=email.strip().lower(),
                nickname=nickname,
                role="ADMIN",
                company_name="OpcHub 平台运营",
                password_hash=password_hash,
                is_active=True,
                metadata_payload={"must_change_password": True, "builtin": True, "tier_name": "平台管理员"},
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            return admin

    async def get_user_by_uid(self, uid: str) -> Optional[User]:
        """Fetch a user by its stable business uid."""
        if not await self.is_ready():
            return None
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(User).where(User.uid == uid)
            return (await session.execute(stmt)).scalar_one_or_none()

    async def list_users(self, limit: int = 10000) -> List[User]:
        """List persisted users (used to hydrate the in-memory user index on startup)."""
        if not await self.is_ready():
            return []
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(User).order_by(User.created_at.asc()).limit(limit)
            return list((await session.execute(stmt)).scalars().all())

    async def count_makers(self) -> int:
        """Count persisted non-ADMIN users; campaign ordinals must skip the built-in admin."""
        if not await self.is_ready():
            return 0
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(User.uid).where(User.role != "ADMIN")
            return len(list((await session.execute(stmt)).scalars().all()))

    async def update_user_fields(
        self,
        uid: str,
        nickname: Optional[str] = None,
        company_name: Optional[str] = None,
        password_hash: Optional[str] = None,
        metadata_patch: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Commit profile / credential / metadata field changes for a user.

        Returns ``True`` when a matching row was updated (``False`` when the database
        is unavailable or the user does not exist).
        """
        if not await self.is_ready():
            return False
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(User).where(User.uid == uid)
            user = (await session.execute(stmt)).scalar_one_or_none()
            if user is None:
                return False
            if nickname is not None:
                user.nickname = nickname
            if company_name is not None:
                user.company_name = company_name
            if password_hash is not None:
                user.password_hash = password_hash
            if metadata_patch:
                meta = dict(user.metadata_payload or {})
                meta.update(metadata_patch)
                user.metadata_payload = meta
            await session.commit()
            return True

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


    # -------------------------------------------------------------
    # Security Audit Log Repository Methods (audit_logs / audit_logs_archive)
    # -------------------------------------------------------------
    @staticmethod
    def _audit_row_to_dict(row: Any) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "actor_id": row.actor_id,
            "actor_role": row.actor_role,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "permission": row.permission,
            "result": row.result,
            "ip_address": row.ip_address,
            "trace_id": row.trace_id,
            "detail_encrypted": row.detail_encrypted,
            "created_at": row.created_at.isoformat() if row.created_at else "",
        }

    async def insert_audit_log(self, record: Dict[str, Any]) -> None:
        if not await self.is_ready():
            return
        created = record.get("created_at")
        try:
            created_at = datetime.fromisoformat(created) if created else datetime.now(timezone.utc)
        except ValueError:
            created_at = datetime.now(timezone.utc)
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            session.add(AuditLog(
                id=uuid.UUID(record["id"]),
                actor_id=record.get("actor_id", ""),
                actor_role=record.get("actor_role", "GUEST"),
                action=record.get("action", ""),
                resource_type=record.get("resource_type", ""),
                resource_id=record.get("resource_id", ""),
                permission=record.get("permission", ""),
                result=record.get("result", "SUCCESS"),
                ip_address=record.get("ip_address", ""),
                trace_id=record.get("trace_id", ""),
                detail_encrypted=record.get("detail_encrypted", ""),
                created_at=created_at,
            ))
            await session.commit()

    async def list_audit_logs(
        self,
        limit: int = 100,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not await self.is_ready():
            return []
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(AuditLog)
            if actor_id:
                stmt = stmt.where(AuditLog.actor_id == actor_id)
            if action:
                stmt = stmt.where(AuditLog.action == action)
            stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._audit_row_to_dict(r) for r in rows]

    async def archive_audit_logs(self, cutoff: datetime, batch_size: int = 500) -> int:
        if not await self.is_ready():
            return 0
        session_maker = get_async_sessionmaker()
        moved = 0
        async with session_maker() as session:
            stmt = select(AuditLog).where(AuditLog.created_at < cutoff).limit(batch_size)
            rows = (await session.execute(stmt)).scalars().all()
            for r in rows:
                session.add(AuditLogArchive(
                    id=r.id,
                    actor_id=r.actor_id,
                    actor_role=r.actor_role,
                    action=r.action,
                    resource_type=r.resource_type,
                    resource_id=r.resource_id,
                    permission=r.permission,
                    result=r.result,
                    ip_address=r.ip_address,
                    trace_id=r.trace_id,
                    detail_encrypted=r.detail_encrypted,
                    created_at=r.created_at,
                    archived_at=datetime.now(timezone.utc),
                ))
                await session.delete(r)
                moved += 1
            await session.commit()
        return moved

    async def list_archived_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not await self.is_ready():
            return []
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(AuditLogArchive).order_by(AuditLogArchive.created_at.desc()).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._audit_row_to_dict(r) for r in rows]

    # -------------------------------------------------------------
    # Generic Domain Snapshot Store (domain_snapshots)
    # Enables in-memory primary index hydration + write-behind persistence
    # -------------------------------------------------------------
    async def load_domain_snapshots(self, domain: str) -> List[Dict[str, Any]]:
        """Load every persisted document for a domain (used for startup hydration)."""
        if not await self.is_ready():
            return []
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = select(DomainSnapshot).where(DomainSnapshot.domain == domain)
            rows = (await session.execute(stmt)).scalars().all()
            return [dict(r.payload) for r in rows]

    async def upsert_domain_snapshot(self, domain: str, entity_id: str, payload: Dict[str, Any]) -> None:
        """Atomically insert or update a single domain aggregate document."""
        if not await self.is_ready():
            return
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = pg_insert(DomainSnapshot).values(
                domain=domain,
                entity_id=entity_id,
                payload=payload,
                updated_at=datetime.now(timezone.utc),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[DomainSnapshot.domain, DomainSnapshot.entity_id],
                set_={
                    "payload": stmt.excluded.payload,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            await session.execute(stmt)
            await session.commit()

    async def delete_domain_snapshot(self, domain: str, entity_id: str) -> None:
        """Remove a single domain aggregate document."""
        if not await self.is_ready():
            return
        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            stmt = sa_delete(DomainSnapshot).where(
                DomainSnapshot.domain == domain, DomainSnapshot.entity_id == entity_id
            )
            await session.execute(stmt)
            await session.commit()


db_repository = DatabaseRepository()
