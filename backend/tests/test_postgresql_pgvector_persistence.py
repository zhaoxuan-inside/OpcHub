"""Test suite verifying PostgreSQL 16+ ORM models, pgvector integration, and database engine (ADR-002 & ADR-003).

Validates:
1. All 16 core platform entity models strictly comply with the database schema specification.
2. PostgreSQL DDL compilation succeeds with UUID, JSONB, and Vector(128) types.
3. pgvector cosine distance operator (<=>) compilation and query building.
4. Database engine lifecycle and health check functionality.
5. PGVectorStore and SQLite fallback behavior.
"""
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from src.core.database import (
    Base,
    get_async_engine,
    get_async_sessionmaker,
    check_database_health,
)
from src.infrastructure.database.models import (
    User,
    Policy,
    Demand,
    ForumThread,
    SOPTemplate,
    RAGVector,
)
from src.core.rag.vector_store import (
    PGVectorStore,
    SQLiteVectorStore,
    VectorDocument,
    get_vector_store,
)
from src.core.rag.service import PolicyRagService, ForumRagService


def test_schema_all_core_tables_registered():
    """Verify all 16 platform tables specified in the schema contract are registered in metadata."""
    expected_tables = {
        "users",
        "entitlements",
        "user_entitlements",
        "policies",
        "perks",
        "demands",
        "demand_bids",
        "dag_pipeline_configs",
        "forum_threads",
        "forum_comments",
        "forum_upvotes",
        "forum_bookmarks",
        "sop_templates",
        "sop_documents",
        "product_showcases",
        "perk_claims",
        "content_moderation_logs",
        "rag_vectors",
    }
    actual_tables = set(Base.metadata.tables.keys())
    for t in expected_tables:
        assert t in actual_tables, f"Expected table '{t}' not found in Base.metadata.tables"


def test_postgresql_ddl_compilation_all_tables():
    """Verify clean compilation of CREATE TABLE DDL for all models using PostgreSQL dialect."""
    dialect = postgresql.dialect()
    for table_name, table in Base.metadata.tables.items():
        ddl = str(CreateTable(table).compile(dialect=dialect)).strip()
        assert ddl.startswith(f"CREATE TABLE {table_name}"), f"Failed DDL generation for {table_name}"
        assert len(ddl) > 30, f"DDL unexpectedly short for {table_name}"


def test_every_id_column_is_uuid():
    """Contract: every column named `id` or `*_id` must be a PostgreSQL UUID.

    Human-readable identifiers are stored in `code` / `key` / `handle` / `uid`
    columns, never in an identity column.
    """
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    offenders = []
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            if column.name == "id" or column.name.endswith("_id"):
                if not isinstance(column.type, PGUUID):
                    offenders.append(f"{table_name}.{column.name}:{column.type}")
    assert not offenders, f"Non-UUID identity columns: {offenders}"

    # The account handle is explicitly not an identity column.
    assert "handle" in User.__table__.columns
    assert "uid" not in User.__table__.columns


def test_pgvector_column_and_operator_compilation():
    """Verify Vector(128) column and cosine distance (<=>) operator compilation (ADR-003)."""
    # 1. Verify Vector column exists on Policy and RAGVector
    assert "embedding" in Policy.__table__.columns
    assert "embedding" in RAGVector.__table__.columns
    assert "embedding" in ForumThread.__table__.columns

    # 2. Verify cosine distance expression compiles to <=>
    dummy_vec = [0.05] * 128
    stmt = (
        select(
            RAGVector.doc_id,
            RAGVector.embedding.cosine_distance(dummy_vec).label("distance"),
        )
        .where(RAGVector.collection == "policies")
        .order_by("distance")
        .limit(10)
    )
    compiled_sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "<=>" in compiled_sql, f"Expected pgvector <=> cosine distance operator in: {compiled_sql}"
    assert "ORDER BY distance" in compiled_sql
    assert "LIMIT" in compiled_sql


def test_model_instantiation_and_defaults():
    """Verify instantiation of core models with UUIDs and default timestamps."""
    # Test User model
    user = User(
        uid="u_test_maker_001",
        email="test_maker@opchub.cn",
        nickname="SoloFounder",
        role="MAKER",
        is_active=True,
        metadata_payload={},
    )
    assert user.uid == "u_test_maker_001"
    assert user.is_active is True
    assert user.metadata_payload == {}

    # Test Policy model with pgvector embedding
    vec = [0.1] * 128
    policy = Policy(
        code="POL-TEST-001",
        title="测试政策",
        summary_plain="政策摘要测试",
        region="CN_YANGTZE",
        max_subsidy_amount=50000.00,
        embedding=vec,
        is_active=True,
    )
    assert policy.code == "POL-TEST-001"
    assert len(policy.embedding) == 128
    assert policy.is_active is True

    # Test Demand and Bid relationship definition
    demand = Demand(
        creator_id=uuid.uuid4(),
        title="需求测试",
        description="需求详细描述",
        budget_cny=15000.00,
        category="DEV",
        status="OPEN",
        deadline_at=policy.published_at if hasattr(policy, "published_at") and policy.published_at else datetime.now(timezone.utc),
    )
    assert demand.budget_cny == 15000.00
    assert demand.status == "OPEN"

    # Test SOPTemplate
    sop_tpl = SOPTemplate(
        id="tpl_test_01",
        stage=1,
        code="TPL_TEST",
        name="测试SOP模板",
        category="LEGAL",
        description="模板描述",
        template_content="# SOP Content",
        is_active=True,
    )
    assert sop_tpl.stage == 1
    assert sop_tpl.is_active is True


def test_database_engine_and_session_factory():
    """Verify AsyncEngine creation and async sessionmaker configuration."""
    engine = get_async_engine()
    assert engine is not None
    assert engine.dialect.name == "postgresql"

    sessionmaker = get_async_sessionmaker()
    assert sessionmaker is not None


@pytest.mark.asyncio
async def test_database_health_probe():
    """Verify database health probe returns structured health dictionary."""
    # Probe database health; in absence of live postgres daemon, status should be 'degraded' or 'unavailable'
    health = await check_database_health()
    assert "status" in health
    assert "dialect" in health
    assert health["dialect"] == "postgresql"
    assert "error" in health or health["status"] == "healthy"


def test_pgvector_store_factory_and_fallback():
    """Verify PGVectorStore creation, query building, and seamless fallback."""
    pg_store = get_vector_store("postgres")
    assert isinstance(pg_store, PGVectorStore)

    sqlite_store = get_vector_store("sqlite")
    assert isinstance(sqlite_store, SQLiteVectorStore)

    # Test PGVectorStore build_query
    q_vec = [0.2] * 128
    stmt = pg_store.build_query("policies", q_vec, top_k=5)
    compiled_stmt = str(stmt.compile(dialect=postgresql.dialect()))
    assert "<=>" in compiled_stmt

    # Test fallback execution when PostgreSQL is not running
    doc = VectorDocument(
        doc_id="doc_pg_test_1",
        collection="test_policies",
        title="测试标题",
        content="测试内容",
        metadata={"category": "AI"},
        vector=[0.1] * 128,
    )
    pg_store.upsert(doc)
    assert pg_store.count("test_policies") >= 1

    fetched = pg_store.get("test_policies", "doc_pg_test_1")
    assert fetched is not None
    assert fetched.title == "测试标题"

    results = pg_store.search_similarity("test_policies", [0.1] * 128, top_k=2)
    assert len(results) >= 1
    assert results[0][0].doc_id == "doc_pg_test_1"

    pg_store.clear("test_policies")
    assert pg_store.count("test_policies") == 0


def test_rag_services_with_pgvector_store():
    """Verify PolicyRagService and ForumRagService accept PGVectorStore seamlessly."""
    pg_store = PGVectorStore()
    policy_svc = PolicyRagService(vector_store=pg_store)
    assert policy_svc.vector_store is pg_store

    forum_svc = ForumRagService(vector_store=pg_store)
    assert forum_svc.vector_store is pg_store
