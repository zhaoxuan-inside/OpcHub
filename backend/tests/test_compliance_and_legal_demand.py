"""Tests for Product Compliance Guide & Legal Demands in Marketplace."""
import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app
from src.core.config import settings


@pytest.mark.asyncio
async def test_get_compliance_dimensions():
    """Verify 6-dimensional product compliance framework is returned."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"{settings.api_prefix}/compliance/dimensions")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 6
        dim_ids = [d["id"] for d in data]
        assert "dim_privacy" in dim_ids
        assert "dim_payment" in dim_ids
        assert "dim_filing" in dim_ids
        assert "dim_ip_oss" in dim_ids
        assert "dim_cross_border" in dim_ids
        assert "dim_ugc_security" in dim_ids


@pytest.mark.asyncio
async def test_get_compliance_cases():
    """Verify real-world regulatory pitfall cases are accessible."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"{settings.api_prefix}/compliance/cases")
        assert res.status_code == 200
        cases = res.json()
        assert len(cases) >= 3
        assert any("二清" in c["title"] for c in cases)
        assert any("GDPR" in c["title"] for c in cases)
        assert any("AGPL" in c["title"] for c in cases)


@pytest.mark.asyncio
async def test_get_compliance_checkpoints():
    """Verify 10-point standard pre-launch compliance checklist."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"{settings.api_prefix}/compliance/checkpoints")
        assert res.status_code == 200
        checkpoints = res.json()
        assert len(checkpoints) == 10
        total_weight = sum(chk["weight"] for chk in checkpoints)
        assert total_weight == 100


@pytest.mark.asyncio
async def test_evaluate_compliance_audit_all_pass():
    """Verify full checklist produces 100 score and EXCELLENT grade."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        chks_res = await client.get(f"{settings.api_prefix}/compliance/checkpoints")
        all_ids = [chk["id"] for chk in chks_res.json()]

        audit_res = await client.post(
            f"{settings.api_prefix}/compliance/audit",
            json={"passed_item_ids": all_ids}
        )
        assert audit_res.status_code == 200
        report = audit_res.json()
        assert report["score"] == 100
        assert report["grade"] == "EXCELLENT"
        assert report["failed_items_count"] == 0
        assert len(report["risk_items"]) == 0
        assert report["legal_help_recommendation"] is None


@pytest.mark.asyncio
async def test_evaluate_compliance_audit_critical_risks():
    """Verify failure of critical checkpoints produces warnings and legal demand suggestions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        audit_res = await client.post(
            f"{settings.api_prefix}/compliance/audit",
            json={"passed_item_ids": []}
        )
        assert audit_res.status_code == 200
        report = audit_res.json()
        assert report["score"] == 0
        assert report["grade"] == "CRITICAL"
        assert report["failed_items_count"] == 10
        assert len(report["risk_items"]) == 10
        assert "建议前往需求集市发布专项法律求助" in report["legal_help_recommendation"]


@pytest.mark.asyncio
async def test_legal_demands_in_marketplace():
    """Verify marketplace supports LEGAL category queries, posts and bidding."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch demands filtered by LEGAL
        res = await client.get(f"{settings.api_prefix}/demands?category=LEGAL")
        assert res.status_code == 200
        legal_demands = res.json()
        assert len(legal_demands) >= 2
        assert all(d["category"] == "LEGAL" for d in legal_demands)

        # 2. Publish a new LEGAL help demand
        new_demand = {
            "title": "海外 SaaS 平台出海数据跨境合规及 DPA 协议定制委托",
            "description": "寻找具备涉外网络数据安全合规经验的法务团队起草数据出境评估报告与标准合同。",
            "budget_cny": 15000.0,
            "category": "LEGAL",
            "deadline_days": 7,
            "creator_id": "usr_maker_test_88"
        }
        create_res = await client.post(f"{settings.api_prefix}/demands", json=new_demand)
        assert create_res.status_code == 201
        created_data = create_res.json()
        assert created_data["category"] == "LEGAL"
        demand_id = created_data["id"]

        # 3. Bid on the legal help demand
        bid_payload = {
            "bidder_id": "usr_legal_expert_01",
            "bid_amount_cny": 14000.0,
            "delivery_days": 5,
            "proposal_text": "专业涉外网络安全律所，已主导完成数十个出海独立项目的 GDPR/DPA 审查交付。"
        }
        bid_res = await client.post(f"{settings.api_prefix}/demands/{demand_id}/bids", json=bid_payload)
        assert bid_res.status_code == 201
        assert bid_res.json()["bidder_id"] == "usr_legal_expert_01"
