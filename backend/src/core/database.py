"""PostgreSQL 16+ Core Relational & Vector Storage Engine (ADR-002 & ADR-003).

Provides asynchronous database connections via asyncpg and SQLAlchemy 2.0 AsyncSession.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

logger = logging.getLogger("opchub.database")


class Base(DeclarativeBase):
    """Base declarative class for all PostgreSQL ORM entities."""
    pass


_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine() -> AsyncEngine:
    """Obtain or lazily initialize the singleton AsyncEngine for PostgreSQL."""
    global _async_engine, _async_session_factory
    if _async_engine is None:
        url = settings.database_url
        logger.info("Initializing PostgreSQL 2.0 AsyncEngine: %s", url.split("@")[-1] if "@" in url else url)
        _async_engine = create_async_engine(
            url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_engine


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Obtain the async session factory."""
    if _async_session_factory is None:
        get_async_engine()
    assert _async_session_factory is not None
    return _async_session_factory


async def check_database_health() -> dict:
    """Probe PostgreSQL database health returning structured telemetry."""
    try:
        from sqlalchemy import text
        engine = get_async_engine()
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            healthy = res.scalar() == 1
            return {
                "status": "healthy" if healthy else "unhealthy",
                "dialect": engine.dialect.name,
                "connected": healthy,
            }
    except Exception as exc:
        logger.debug("Database health check probe failed (database may be offline in dev): %s", exc)
        return {
            "status": "unavailable",
            "dialect": "postgresql",
            "connected": False,
            "error": str(exc),
        }
