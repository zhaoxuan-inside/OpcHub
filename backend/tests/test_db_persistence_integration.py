"""Opt-in PostgreSQL persistence integration tests.

The default suite runs without infrastructure (see ``tests/conftest.py``), so these
tests are skipped unless a live PostgreSQL instance is provided:

    OPCHUB_IT_DATABASE_URL=postgresql+asyncpg://opc:opchub_secret@localhost:5432/opchub \
        python3 -m pytest tests/test_db_persistence_integration.py -v

They prove the write-behind + hydrate-on-startup contract end-to-end: mutations made
through the domain services are flushed to PostgreSQL, the process-level in-memory
indexes are wiped, and rebuilding them reproduces the exact same working state.
"""
import os

import pytest

IT_URL = os.getenv("OPCHUB_IT_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not IT_URL, reason="Set OPCHUB_IT_DATABASE_URL to run PostgreSQL integration tests."
)


async def _disabled() -> bool:  # pragma: no cover - teardown helper
    return False


@pytest.fixture()
def live_db():
    """Point the platform at the live test database and enable persistence.

    Function-scoped: pytest-asyncio runs each test on a fresh event loop, so the
    async engine/session factory must be rebuilt per test (otherwise it is bound to a
    closed loop).
    """
    from src.core import database as db_core
    from src.core.config import settings
    from src.infrastructure.database.repository import db_repository

    settings.database_url = IT_URL
    db_core._async_engine = None
    db_core._async_session_factory = None
    # Restore the real readiness probe (conftest force-disables DB for the default suite)
    if "is_ready" in db_repository.__dict__:
        del db_repository.is_ready

    yield db_repository

    # Release the per-test engine and re-hide the database from later test modules
    db_repository.is_ready = _disabled
    db_core._async_engine = None
    db_core._async_session_factory = None
    from src.infrastructure.database.persistence import domain_persistence
    domain_persistence.enabled = False
    domain_persistence._tail = None


@pytest.fixture(autouse=True)
async def _clean_state(live_db):
    """Truncate persisted domain/user state before and after each test."""
    from sqlalchemy import text
    from src.core.database import get_async_engine

    async def _wipe():
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM domain_snapshots"))
            await conn.execute(text(
                "DELETE FROM users WHERE email LIKE 'it_%@opchub.test' OR uid = 'usr_admin_builtin'"
            ))

    await live_db.ensure_schema_and_seed()
    await _wipe()
    yield
    await _wipe()


@pytest.mark.asyncio
async def test_forum_state_survives_restart(live_db):
    """Threads, comments, upvotes and bookmarks round-trip through PostgreSQL."""
    from src.domains.forum.models import ForumThreadCreate, ForumCommentCreate
    from src.domains.forum.service import forum_service
    from src.infrastructure.database.persistence import domain_persistence

    await domain_persistence.initialize()
    assert domain_persistence.enabled is True

    thread = forum_service.create_thread(ForumThreadCreate(
        category_code="DEV", author_id="it_user", title="持久化线程", content="内容正文足够长",
    ))
    comment = forum_service.create_comment(thread.id, ForumCommentCreate(
        author_id="it_user", content="一级评论内容",
    ))
    forum_service.toggle_upvote("it_user", "THREAD", thread.id)
    forum_service.toggle_bookmark("it_user", thread.id, "默认收藏夹")
    await domain_persistence.flush()

    # Simulate a process restart: wipe memory, rebuild from PostgreSQL
    forum_service.clear()
    assert forum_service.list_threads() == []
    await domain_persistence.initialize()

    restored = forum_service.get_thread(thread.id, record_view=False)
    assert restored.title == "持久化线程"
    assert restored.comment_count == 1
    assert restored.upvote_count == 1
    assert restored.bookmark_count == 1
    assert forum_service._comments[comment.id].content == "一级评论内容"
    assert ("it_user", "THREAD", thread.id) in forum_service._upvotes
    assert forum_service._bookmarks[("it_user", thread.id)] == "默认收藏夹"

    # Deletion is durable too
    forum_service.delete_thread(thread.id)
    await domain_persistence.flush()
    forum_service.clear()
    await domain_persistence.initialize()
    assert forum_service.list_threads() == []


@pytest.mark.asyncio
async def test_catalog_domains_survive_restart(live_db):
    """Products, policies, demands/bids, perks/claims and SOP docs round-trip."""
    from src.domains.products.models import ProductCreate
    from src.domains.products.service import product_service
    from src.domains.policies.models import PolicyCreate
    from src.domains.policies.service import policy_service
    from src.domains.demands.models import DemandCreate, BidCreate
    from src.domains.demands.service import demand_service
    from src.domains.perks.models import PerkCreate, PerkClaimRequest
    from src.domains.perks.service import perk_service
    from src.domains.sop.models import SOPTemplateCreate, SOPDocumentCreate, SOPField
    from src.domains.sop.service import sop_service
    from src.infrastructure.database.persistence import domain_persistence

    await domain_persistence.initialize()

    product = product_service.create_product(ProductCreate(
        author_id="it_user", title="持久化产品", tagline="产品标语", description="产品详细描述内容",
        category="TOOL", pricing_model="FREE", price_cny=0.0, demo_url="",
    ))
    policy = policy_service.create_policy(PolicyCreate(
        title="持久化政策", policy_level="NATIONAL", category="TAX",
        subsidy_amount_max=1000.0, summary="政策摘要内容", eligible_conditions=[], legal_basis="法规依据",
    ))
    demand = demand_service.create_demand(DemandCreate(
        creator_id="it_user", title="持久化需求", description="需求详细描述内容",
        budget_cny=100.0, category="DEV", deadline_days=30,
    ))
    demand_service.submit_bid(demand.id, BidCreate(
        bidder_id="it_bidder", bid_amount_cny=90.0, delivery_days=10, proposal_text="投标方案内容",
    ))
    perk = perk_service.create_perk(PerkCreate(
        name="持久化权益", provider="火山引擎", value_cny=200.0, category="CLOUD",
        summary="权益摘要内容", quota_remaining=5,
    ))
    perk_service.claim_perk(PerkClaimRequest(user_id="it_user", perk_id=perk.id))
    template = sop_service.create_template(SOPTemplateCreate(
        stage=1, code="IT_TPL", name="持久化模板", category="REG",
        description="模板详细描述", template_content="公司：{company_name}",
        required_fields=[SOPField(key="company_name", label="公司", default="默认")],
    ))
    document = sop_service.render_and_save_document(SOPDocumentCreate(
        template_id=template.id, user_id="it_user",
        form_data={"company_name": "持久化科技"},
    ))

    await domain_persistence.flush()

    # Wipe every catalog index, then rebuild from PostgreSQL
    product_service.clear()
    policy_service.clear()
    demand_service._demands.clear()
    demand_service._bids.clear()
    perk_service._perks.clear()
    perk_service._claims.clear()
    sop_service._templates.clear()
    sop_service._documents.clear()

    await domain_persistence.initialize()

    assert product_service._products[product.id].title == "持久化产品"
    assert policy_service._policies[policy.id].title == "持久化政策"
    assert demand_service._demands[demand.id].bidders_count == 1
    assert len(demand_service._bids[demand.id]) == 1
    assert perk_service._perks[perk.id].quota_remaining == 4
    assert ("it_user", perk.id) in perk_service._claims
    restored_doc = sop_service._documents[document.id]
    assert restored_doc.form_data["company_name"] == "持久化科技"
    assert "持久化科技" in restored_doc.rendered_content


@pytest.mark.asyncio
async def test_orchestration_configs_survive_restart(live_db):
    """Saved DAG configs and frontend layouts round-trip through PostgreSQL."""
    from src.domains.orchestration.models import (
        DAGConfigSaveRequest, FrontendLayoutSaveRequest,
    )
    from src.domains.orchestration.service import orchestration_service
    from src.infrastructure.database.persistence import domain_persistence

    await domain_persistence.initialize()

    graph = {
        "topology": "DAG", "entry_node": "n1",
        "nodes": [{"id": "n1", "action_handler": "gateway_ingress", "type": "GATEWAY"}],
        "edges": [],
    }
    orchestration_service.save_dag_config(DAGConfigSaveRequest(
        scenario_code="IT_SCENARIO", version="v9.9.9", topology_graph=graph, status="ACTIVE",
    ))
    orchestration_service.save_frontend_layout(FrontendLayoutSaveRequest(
        layout_name="it_layout", version="v1", grid_schema={"a": 1}, widgets=[],
    ))
    await domain_persistence.flush()

    orchestration_service._dag_configs = {
        k: v for k, v in orchestration_service._dag_configs.items()
        if k[0] != "IT_SCENARIO"
    }
    orchestration_service._layouts.pop("it_layout", None)
    await domain_persistence.initialize()

    assert orchestration_service.get_dag_config("IT_SCENARIO", "v9.9.9").status == "ACTIVE"
    assert orchestration_service.get_frontend_layout("it_layout").version == "v1"


@pytest.mark.asyncio
async def test_user_credentials_and_profile_are_durable(live_db):
    """Registration, profile update and password rotation persist to the users table."""
    from src.domains.user.models import (
        UserRegisterRequest, UserProfileUpdateRequest, ChangePasswordRequest,
    )
    from src.domains.user.service import user_service
    from src.infrastructure.database.persistence import domain_persistence

    await domain_persistence.initialize()

    email = "it_durable@opchub.test"
    session = await user_service.register_by_email(UserRegisterRequest(
        email=email, password="InitPass#2026", nickname="持久化创客",
    ))
    uid = session.uid

    await user_service.update_profile(UserProfileUpdateRequest(
        user_id=uid, nickname="改名后", company_name="持久化科技", phone="13800000000",
    ), token=session.token)

    rotated = await user_service.change_password(ChangePasswordRequest(
        user_id=uid, old_password="InitPass#2026", new_password="Rotated#2026",
    ))
    assert rotated.must_change_password is False

    # Simulate restart: drop the in-memory user index, rebuild from PostgreSQL
    user_service._users_by_uid.clear()
    user_service._users_by_email.clear()
    restored_count = await user_service.hydrate_from_db()
    assert restored_count >= 1

    record = user_service._users_by_uid[uid]
    assert record["nickname"] == "改名后"
    assert record["company_name"] == "持久化科技"
    assert record["phone"] == "13800000000"

    # The rotated password is the one that now authenticates against the DB row
    from src.domains.user.models import UserLoginRequest
    relogin = await user_service.login_by_email(UserLoginRequest(email=email, password="Rotated#2026"))
    assert relogin.uid == uid


@pytest.mark.asyncio
async def test_builtin_admin_rotation_is_durable(live_db):
    """The built-in admin's forced rotation flag is persisted and survives restart."""
    from src.domains.user.service import user_service
    from src.domains.user.models import ChangePasswordRequest, UserLoginRequest
    from src.core.config import settings
    from src.infrastructure.database.persistence import domain_persistence

    await domain_persistence.initialize()
    # Ensure the built-in admin exists in memory with its initial credential, then rotate
    user_service._users_by_uid.pop("usr_admin_builtin", None)
    user_service._users_by_email.pop(settings.admin_email.strip().lower(), None)
    user_service._ensure_builtin_admin()
    admin = user_service._users_by_uid["usr_admin_builtin"]
    await live_db.ensure_builtin_admin(
        uid=admin["uid"], email=admin["email"],
        nickname=admin["nickname"], password_hash=admin["password_hash"],
    )
    await user_service.change_password(ChangePasswordRequest(
        user_id="usr_admin_builtin", old_password=settings.admin_initial_password,
        new_password="AdminRotated#2026",
    ))

    # Restart: hydrate the index from PostgreSQL
    user_service._users_by_uid.clear()
    user_service._users_by_email.clear()
    await user_service.hydrate_from_db()

    record = user_service._users_by_uid["usr_admin_builtin"]
    assert record["must_change_password"] is False
    assert record["tier_name"] == "平台管理员"

    relogin = await user_service.login_by_email(UserLoginRequest(
        email=record["email"], password="AdminRotated#2026",
    ))
    assert relogin.must_change_password is False
