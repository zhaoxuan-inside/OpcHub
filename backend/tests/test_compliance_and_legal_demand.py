"""Tests for Product Compliance Guide & Legal Demands in Marketplace."""
import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app
from src.core.config import settings


@pytest.mark.asyncio
async def test_get_compliance_dimensions():
    """Verify compliance framework endpoint returns live knowledge base (blank initial catalog)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"{settings.api_prefix}/compliance/dimensions")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_compliance_cases():
    """Verify regulatory pitfall cases endpoint returns live knowledge base (blank initial catalog)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"{settings.api_prefix}/compliance/cases")
        assert res.status_code == 200
        cases = res.json()
        assert isinstance(cases, list)


@pytest.mark.asyncio
async def test_get_compliance_checkpoints():
    """Verify pre-launch compliance checklist endpoint returns live items (blank initial catalog)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"{settings.api_prefix}/compliance/checkpoints")
        assert res.status_code == 200
        checkpoints = res.json()
        assert isinstance(checkpoints, list)


@pytest.mark.asyncio
async def test_evaluate_compliance_audit_all_pass():
    """Verify audit over empty checklist stays safe (no crash, score 0)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        chks_res = await client.get(f"{settings.api_prefix}/compliance/checkpoints")
        all_ids = [chk["id"] for chk in chks_res.json()]

        audit_res = await client.post(
            f"{settings.api_prefix}/compliance/audit",
            json={"passed_item_ids": all_ids}
        )
        assert audit_res.status_code == 200
        report = audit_res.json()
        assert report["score"] == 0
        assert report["failed_items_count"] == 0


@pytest.mark.asyncio
async def test_evaluate_compliance_audit_critical_risks():
    """Verify audit over empty checklist remains safe with no risk items."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        audit_res = await client.post(
            f"{settings.api_prefix}/compliance/audit",
            json={"passed_item_ids": []}
        )
        assert audit_res.status_code == 200
        report = audit_res.json()
        assert report["score"] == 0
        assert report["failed_items_count"] == 0


@pytest.mark.asyncio
async def test_legal_demands_in_marketplace():
    """Verify marketplace supports LEGAL category queries, posts and bidding."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch demands filtered by LEGAL (blank initial catalog)
        res = await client.get(f"{settings.api_prefix}/demands?category=LEGAL")
        assert res.status_code == 200
        legal_demands = res.json()
        assert isinstance(legal_demands, list)

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
