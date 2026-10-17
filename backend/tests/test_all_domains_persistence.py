"""Comprehensive tests for Full-Page Backend Persistence and SOP Document Engine."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_home_overview_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/home/overview")
        assert res.status_code == 200
        data = res.json()
        assert data["active_makers_count"] >= 10000
        assert data["active_dags_count"] >= 100
        assert len(data["quick_links"]) >= 6


@pytest.mark.asyncio
async def test_sop_templates_and_document_persistence():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Fetch predefined 4-stage steps & templates
        res = await ac.get("/api/v1/sop/templates")
        assert res.status_code == 200
        data = res.json()
        assert len(data["stages"]) == 4
        assert data["stages"][0]["code"] == "STAGE_TAX_ENTITY"
        assert len(data["templates"]) >= 4

        # Verify template required fields
        t_reg = next(t for t in data["templates"] if t["id"] == "tpl_individual_biz_reg")
        assert len(t_reg["required_fields"]) >= 4

        # 2. Render and save document instance to backend
        form_payload = {
            "template_id": "tpl_individual_biz_reg",
            "user_id": "usr_2026_opc_9981",
            "form_data": {
                "company_name": "极客视界（杭州）信息技术工作室",
                "founder_name": "赵玄 (33010619920101XXXX)",
                "biz_scope": "软件开发；信息技术咨询服务；人工智能应用软件开发",
                "address_type": "集群租赁商务秘书地址 (免实际租赁)",
                "capital_cny": "100,000",
                "registration_office": "杭州市市场监督管理局高新区分局",
            },
        }
        create_res = await ac.post("/api/v1/sop/documents", json=form_payload)
        assert create_res.status_code == 201
        doc = create_res.json()
        doc_id = doc["id"]
        assert doc["compliance_passed"] is True
        assert doc["status"] == "READY"
        assert "极客视界（杭州）信息技术工作室" in doc["rendered_content"]
        assert "赵玄" in doc["rendered_content"]

        # 3. Retrieve saved document by ID
        get_res = await ac.get(f"/api/v1/sop/documents/{doc_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == doc_id

        # 4. List user documents
        list_res = await ac.get("/api/v1/sop/documents?user_id=usr_2026_opc_9981")
        assert list_res.status_code == 200
        docs = list_res.json()
        assert any(d["id"] == doc_id for d in docs)


@pytest.mark.asyncio
async def test_products_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List seeded products
        res = await ac.get("/api/v1/products")
        assert res.status_code == 200
        products = res.json()
        assert len(products) >= 3

        # 2. Create new product
        new_prod = {
            "title": "单兵 AI 智能报税助手",
            "tagline": "基于微内核 DAG 的个体户极速零申报工具",
            "description": "专为无会计团队的一人公司打造，支持发票自动核验与税务零申报全流程闭环。",
            "category": "AI",
            "pricing_model": "SUBSCRIPTION",
            "price_cny": 59.00,
            "demo_url": "https://aitax.opchub.dev",
            "author_id": "usr_2026_opc_9981",
        }
        create_res = await ac.post("/api/v1/products", json=new_prod)
        assert create_res.status_code == 201
        pid = create_res.json()["id"]

        # 3. Upvote product
        up_res = await ac.post(f"/api/v1/products/{pid}/upvote")
        assert up_res.status_code == 200
        assert up_res.json()["upvote_count"] == 1


@pytest.mark.asyncio
async def test_policies_match_engine():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List policies
        res = await ac.get("/api/v1/policies")
        assert res.status_code == 200
        assert len(res.json()) >= 3

        # 2. Match within 300k limit -> VAT Free
        match_free = await ac.post("/api/v1/policies/match", json={
            "quarterly_income": 280000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
        })
        assert match_free.status_code == 200
        data_free = match_free.json()
        assert data_free["eligible"] is True
        assert data_free["applicable_tax_rate"] == 0.0
        assert data_free["estimated_tax_savings"] == 8400.0
        assert len(data_free["matched_policies"]) >= 2

        # 3. Match exceeding 300k limit -> VAT Applicable
        match_taxed = await ac.post("/api/v1/policies/match", json={
            "quarterly_income": 400000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
        })
        assert match_taxed.status_code == 200
        data_taxed = match_taxed.json()
        assert data_taxed["eligible"] is False
        assert data_taxed["applicable_tax_rate"] == 0.03
        assert data_taxed["estimated_tax_savings"] == 0.0


@pytest.mark.asyncio
async def test_demands_and_bidding():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List demands
        res = await ac.get("/api/v1/demands")
        assert res.status_code == 200
        demands = res.json()
        assert len(demands) >= 3
        demand_id = demands[0]["id"]
        init_bidders = demands[0]["bidders_count"]

        # 2. Submit bid
        bid_res = await ac.post(f"/api/v1/demands/{demand_id}/bids", json={
            "bidder_id": "usr_2026_opc_9981",
            "bid_amount_cny": 16000.0,
            "delivery_days": 5,
            "proposal_text": "已交付过3个同类型出海独立站，拥有成熟的Stripe全流程合规接入模版，5天内交付上线。",
        })
        assert bid_res.status_code == 201
        bid = bid_res.json()
        assert bid["bid_amount_cny"] == 16000.0

        # Check bidder count incremented
        check_res = await ac.get("/api/v1/demands")
        updated_demand = next(d for d in check_res.json() if d["id"] == demand_id)
        assert updated_demand["bidders_count"] == init_bidders + 1


@pytest.mark.asyncio
async def test_perks_and_claims():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List perks
        res = await ac.get("/api/v1/perks")
        assert res.status_code == 200
        perks = res.json()
        assert len(perks) >= 4

        # 2. Claim perk
        claim_res = await ac.post("/api/v1/perks/claim", json={
            "user_id": "usr_maker_test_88",
            "perk_id": "perk_aws_activate",
        })
        assert claim_res.status_code == 200
        claim = claim_res.json()
        assert "OPC-" in claim["voucher_code"]
        assert claim["status"] == "ACTIVATED"

        # 3. Duplicate claim returns existing voucher
        claim_dup = await ac.post("/api/v1/perks/claim", json={
            "user_id": "usr_maker_test_88",
            "perk_id": "perk_aws_activate",
        })
        assert claim_dup.status_code == 200
        assert claim_dup.json()["voucher_code"] == claim["voucher_code"]


@pytest.mark.asyncio
async def test_user_profile_and_entitlements():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Get profile
        res = await ac.get("/api/v1/user/profile")
        assert res.status_code == 200
        data = res.json()
        assert data["nickname"] == "赵玄"
        assert len(data["entitlements"]) >= 4

        # 2. Activate paid entitlement
        act_res = await ac.post("/api/v1/user/entitlements/activate", json={
            "user_id": "usr_2026_opc_9981",
            "entitlement_id": "ent_ai_tax_assistant",
        })
        assert act_res.status_code == 200
        act_data = act_res.json()
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
        res_dag = await ac.post("/api/v1/microkernel/dag/configs", json=dag_payload)
        assert res_dag.status_code == 201
        assert len(res_dag.json()["compiled_hash"]) > 0

        # List configs
        list_dag = await ac.get("/api/v1/microkernel/dag/configs?scenario_code=finance.cross_border_settle")
        assert list_dag.status_code == 200
        assert len(list_dag.json()) == 1

        # 2. Save and load frontend layout
        layout_payload = {
            "layout_name": "maker_mobile_dashboard",
            "version": "v1.0.1",
            "grid_schema": {"columns": 12},
            "widgets": [{"id": "w1", "type": "card"}],
        }
        res_layout = await ac.post("/api/v1/frontend/layouts", json=layout_payload)
        assert res_layout.status_code == 201

        get_layout = await ac.get("/api/v1/frontend/layouts?layout_name=maker_mobile_dashboard")
        assert get_layout.status_code == 200
        assert get_layout.json()["layout_name"] == "maker_mobile_dashboard"
