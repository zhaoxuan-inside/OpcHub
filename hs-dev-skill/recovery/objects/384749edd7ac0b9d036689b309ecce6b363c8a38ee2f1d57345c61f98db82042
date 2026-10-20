"""Comprehensive tests for Full-Page Backend Persistence and SOP Document Engine.

All business access goes through the unified gateway entrypoint (single-entry architecture).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from conftest import DEFAULT_ADMIN_TOKEN


async def _gw(ac, scenario, payload):
    ac.headers["Authorization"] = f"Bearer {DEFAULT_ADMIN_TOKEN}"
    return await ac.post("/api/welcom/opc_world", json={
        "scenario": scenario, "version": "v1.0.0", "payload": payload,
    })


async def _data(ac, scenario, payload):
    res = await _gw(ac, scenario, payload)
    body = res.json()
    assert body["code"] == 200, f"{scenario} -> {body}"
    return body["data"]


@pytest.fixture(autouse=True)
def seed_persistence_dependencies():
    """Seed test-only catalog data required by persistence lifecycle tests."""
    from src.domains.sop.service import sop_service
    from src.domains.sop.models import SOPTemplate, SOPField
    from src.domains.perks.service import perk_service
    from src.domains.perks.models import PerkResponse
    from src.domains.policies.service import policy_service
    from src.domains.policies.models import PolicyResponse
    from src.domains.demands.service import demand_service
    from src.domains.demands.models import DemandResponse
    from src.domains.user.service import user_service

    sop_service._templates.clear()
    sop_service._documents.clear()
    sop_service._templates["tpl_individual_biz_reg"] = SOPTemplate(
        id="tpl_individual_biz_reg",
        stage=1,
        code="INDIVIDUAL_BIZ_REG",
        name="个体工商户设立登记标准申请书",
        category="TAX",
        description="测试用个体户设立登记模板",
        template_content="""个体工商户设立登记申请书
---------------------------------------------
登记机关：{registration_office}
主体全称：{company_name}
经营者：{founder_name}
主营范围：{biz_scope}
---------------------------------------------
核验流水号: {verify_serial}""",
        required_fields=[
            SOPField(key="registration_office", label="登记市场监管部门", default=""),
            SOPField(key="company_name", label="拟定经营主体字号", default=""),
            SOPField(key="founder_name", label="法定代表创客姓名", default=""),
            SOPField(key="biz_scope", label="主营经营范围描述", default=""),
        ],
        is_active=True,
    )

    perk_service._perks.clear()
    perk_service._claims.clear()
    perk_service._perks["perk_aws_activate"] = PerkResponse(
        id="perk_aws_activate",
        name="AWS Activate 创客计划",
        provider="Amazon Web Services",
        value_cny=35000.0,
        category="CLOUD",
        summary="测试用云端抵扣券",
        quota_remaining=42,
    )

    policy_service._policies.clear()
    policy_service._policies["pol_vat_exemption_2026"] = PolicyResponse(
        id="pol_vat_exemption_2026",
        title="小规模纳税人季度30万免征增值税",
        policy_level="国家级",
        category="TAX",
        subsidy_amount_max=9000.0,
        summary="小规模纳税人季度销售额未超过30万元免征增值税。",
        eligible_conditions=["小规模纳税人"],
        legal_basis="财政部 税务总局公告 2023年第12号",
    )

    demand_service._demands.clear()
    demand_service._bids.clear()
    from src.domains.demands.service import utc_now_iso
    demand_service._demands["dmd_test_seed"] = DemandResponse(
        id="dmd_test_seed",
        creator_id="usr_client_test",
        title="测试需求：出海独立站结汇接入",
        description="测试用外包需求",
        budget_cny=18000.0,
        category="DEV",
        bidders_count=0,
        status="OPEN",
        deadline_at=utc_now_iso(),
        created_at=utc_now_iso(),
    )
    demand_service._bids["dmd_test_seed"] = []

    # Reset user state and register a test-only user for profile tests
    user_service._users_by_email.clear()
    user_service._users_by_uid.clear()
    user_service._ensure_builtin_admin()
    user_service._active_entitlements.clear()
    from src.core.security import hash_password
    test_uid = "usr_test_persistence_01"
    test_user = {
        "uid": test_uid,
        "email": "persistence_tester@opchub.test",
        "nickname": "持久化测试创客",
        "role": "MAKER",
        "company_name": "持久化测试工作室",
        "phone": "",
        "credit_code": "",
        "tier_name": "标准创客",
        "password_hash": hash_password("test123456"),
        "active_entitlements": set(),
    }
    user_service._users_by_uid[test_uid] = test_user
    user_service._users_by_email[test_user["email"]] = test_user
    yield
    sop_service._templates.clear()
    sop_service._documents.clear()
    perk_service._perks.clear()
    perk_service._claims.clear()
    policy_service._policies.clear()
    demand_service._demands.clear()
    demand_service._bids.clear()
    user_service._users_by_email.clear()
    user_service._users_by_uid.clear()
    user_service._ensure_builtin_admin()
    user_service._active_entitlements.clear()


@pytest.mark.asyncio
async def test_home_overview_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        data = await _data(ac, "home.overview", {})
        assert "active_makers_count" in data
        assert data["active_makers_count"] >= 0
        assert "active_dags_count" in data
        assert len(data["quick_links"]) >= 6


@pytest.mark.asyncio
async def test_sop_templates_and_document_persistence():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Fetch predefined 4-stage steps & test template
        data = await _data(ac, "sop.templates", {})
        assert len(data["stages"]) == 4
        assert data["stages"][0]["code"] == "STAGE_TAX_ENTITY"
        assert len(data["templates"]) >= 1

        # Verify template required fields
        t_reg = next(t for t in data["templates"] if t["id"] == "tpl_individual_biz_reg")
        assert len(t_reg["required_fields"]) >= 4

        # 2. Render and save document instance to backend
        form_payload = {
            "template_id": "tpl_individual_biz_reg",
            "user_id": "usr_test_persistence_01",
            "form_data": {
                "company_name": "持久化测试（杭州）信息技术工作室",
                "founder_name": "张测试",
                "biz_scope": "软件开发；信息技术咨询服务",
                "registration_office": "杭州市市场监督管理局高新区分局",
            },
        }
        doc = await _data(ac, "sop.document.render", form_payload)
        doc_id = doc["id"]
        assert doc["compliance_passed"] is True
        assert "持久化测试（杭州）信息技术工作室" in doc["rendered_content"]

        # 3. Retrieve saved document by ID
        fetched = await _data(ac, "sop.document.get", {"doc_id": doc_id})
        assert fetched["id"] == doc_id

        # 4. List user documents
        docs = await _data(ac, "sop.document.list", {"user_id": "usr_test_persistence_01"})
        assert any(d["id"] == doc_id for d in docs)


@pytest.mark.asyncio
async def test_products_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List products (blank initial catalog)
        products = await _data(ac, "products.list", {})
        assert isinstance(products, list)

        # 2. Create new product
        new_prod = {
            "title": "单兵 AI 智能报税助手",
            "tagline": "基于微内核 DAG 的个体户极速零申报工具",
            "description": "专为无会计团队的一人公司打造，支持发票自动核验与税务零申报全流程闭环。",
            "category": "AI",
            "pricing_model": "SUBSCRIPTION",
            "price_cny": 59.00,
            "demo_url": "https://aitax.opchub.dev",
            "author_id": "usr_test_persistence_01",
        }
        created = await _data(ac, "products.publish", new_prod)
        pid = created["id"]

        # 3. Upvote product
        upvoted = await _data(ac, "products.upvote", {"product_id": pid})
        assert upvoted["upvote_count"] == 1


@pytest.mark.asyncio
async def test_policies_match_engine():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List policies (test-seeded catalog)
        policies = await _data(ac, "policies.list", {})
        assert len(policies) >= 1

        # 2. Match within 300k limit -> VAT Free
        data_free = await _data(ac, "policies.match", {
            "quarterly_income": 280000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
        })
        assert data_free["eligible"] is True
        assert data_free["applicable_tax_rate"] == 0.0
        assert data_free["estimated_tax_savings"] == 8400.0

        # 3. Match exceeding 300k limit -> VAT Applicable
        data_taxed = await _data(ac, "policies.match", {
            "quarterly_income": 400000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
        })
        assert data_taxed["eligible"] is False
        assert data_taxed["applicable_tax_rate"] == 0.03
        assert data_taxed["estimated_tax_savings"] == 0.0


@pytest.mark.asyncio
async def test_demands_and_bidding():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List demands (test-seeded)
        demands = await _data(ac, "demands.list", {})
        assert len(demands) >= 1
        demand_id = demands[0]["id"]
        init_bidders = demands[0]["bidders_count"]

        # 2. Submit bid
        bid = await _data(ac, "demands.bid", {
            "demand_id": demand_id,
            "bidder_id": "usr_test_persistence_01",
            "bid_amount_cny": 16000.0,
            "delivery_days": 5,
            "proposal_text": "已交付过3个同类型出海独立站，拥有成熟的Stripe全流程合规接入模版，5天内交付上线。",
        })
        assert bid["bid_amount_cny"] == 16000.0

        # Check bidder count incremented
        refreshed = await _data(ac, "demands.list", {})
        updated_demand = next(d for d in refreshed if d["id"] == demand_id)
        assert updated_demand["bidders_count"] == init_bidders + 1


@pytest.mark.asyncio
async def test_perks_and_claims():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List perks (test-seeded)
        perks = await _data(ac, "perks.list", {})
        assert len(perks) >= 1

        # 2. Claim perk
        claim = await _data(ac, "perks.claim", {
            "user_id": "usr_maker_test_88",
            "perk_id": "perk_aws_activate",
        })
        assert "OPC-" in claim["voucher_code"]
        assert claim["status"] == "ACTIVATED"

        # 3. Duplicate claim returns existing voucher
        claim_dup = await _data(ac, "perks.claim", {
            "user_id": "usr_maker_test_88",
            "perk_id": "perk_aws_activate",
        })
        assert claim_dup["voucher_code"] == claim["voucher_code"]


@pytest.mark.asyncio
async def test_user_profile_and_entitlements():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Get profile (test-seeded user)
        data = await _data(ac, "user.profile", {"user_id": "usr_test_persistence_01"})
        assert data["nickname"] == "持久化测试创客"
        assert len(data["entitlements"]) >= 0

        # 2. Activate paid entitlement
        act_data = await _data(ac, "user.entitlements.activate", {
            "user_id": "usr_test_persistence_01",
            "entitlement_id": "ent_ai_tax_assistant",
        })
        assert act_data["is_active"] is True
        assert "REC-" in act_data["receipt_no"]


@pytest.mark.asyncio
async def test_orchestration_persistence():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Save DAG configuration
        dag_payload = {
            "scenario_code": "finance.cross_border_settle",
            "version": "v1.0.0-prod",
            "topology_graph": {
                "nodes": [{"id": "n1", "action_handler": "gateway_ingress"}],
                "edges": [],
            },
            "status": "ACTIVE",
            "created_by": "usr_admin_001",
        }
        res_dag = await _data(ac, "orchestration.dag.save", dag_payload)
        assert len(res_dag["compiled_hash"]) > 0

        # List configs
        list_dag = await _data(ac, "orchestration.dag.list", {"scenario_code": "finance.cross_border_settle"})
        assert len(list_dag) == 1

        # 2. Save and load frontend layout
        layout_payload = {
            "layout_name": "maker_mobile_dashboard",
            "version": "v1.0.1",
            "grid_schema": {"columns": 12},
            "widgets": [{"id": "w1", "type": "card"}],
        }
        await _data(ac, "frontend.layouts.save", layout_payload)

        layout = await _data(ac, "frontend.layouts.get", {"layout_name": "maker_mobile_dashboard"})
        assert layout["layout_name"] == "maker_mobile_dashboard"
