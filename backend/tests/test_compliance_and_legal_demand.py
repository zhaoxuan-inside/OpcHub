"""Tests for Product Compliance Guide & Legal Demands in Marketplace.

All business access goes through the unified gateway entrypoint (single-entry architecture).
"""
import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app
from conftest import DEFAULT_ADMIN_TOKEN


async def _gw(client, scenario, payload, token=None):
    client.headers["Authorization"] = f"Bearer {token or DEFAULT_ADMIN_TOKEN}"
    return await client.post("/api/welcom/opc_world", json={
        "scenario": scenario, "version": "v1.0.0", "payload": payload,
    })


@pytest.mark.asyncio
async def test_get_compliance_dimensions():
    """Verify compliance framework endpoint returns live knowledge base (blank initial catalog)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await _gw(client, "compliance.dimensions", {})
        assert res.json()["code"] == 200
        data = res.json()["data"]
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_compliance_cases():
    """Verify regulatory pitfall cases endpoint returns live knowledge base (blank initial catalog)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await _gw(client, "compliance.cases", {})
        assert res.json()["code"] == 200
        cases = res.json()["data"]
        assert isinstance(cases, list)


@pytest.mark.asyncio
async def test_get_compliance_checkpoints():
    """Verify pre-launch compliance checklist endpoint returns live items (blank initial catalog)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await _gw(client, "compliance.checkpoints", {})
        assert res.json()["code"] == 200
        checkpoints = res.json()["data"]
        assert isinstance(checkpoints, list)


@pytest.mark.asyncio
async def test_evaluate_compliance_audit_all_pass():
    """Verify audit over the full seeded checklist yields a perfect score."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        chks_res = await _gw(client, "compliance.checkpoints", {})
        all_ids = [chk["id"] for chk in chks_res.json()["data"]]
        assert all_ids, "Seeded compliance checkpoints must exist"

        audit_res = await _gw(client, "compliance.audit", {"passed_item_ids": all_ids, "strict_mode": False})
        assert audit_res.json()["code"] == 200
        report = audit_res.json()["data"]
        assert report["score"] == 100
        assert report["failed_items_count"] == 0


@pytest.mark.asyncio
async def test_evaluate_compliance_audit_critical_risks():
    """Verify audit over an empty pass list flags every seeded checkpoint as a risk."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        audit_res = await _gw(client, "compliance.audit", {"passed_item_ids": [], "strict_mode": False})
        assert audit_res.json()["code"] == 200
        report = audit_res.json()["data"]
        assert report["score"] == 0
        assert report["failed_items_count"] > 0
        assert len(report["risk_items"]) == report["failed_items_count"]


@pytest.mark.asyncio
async def test_legal_demands_in_marketplace():
    """Verify marketplace supports LEGAL category queries, posts and bidding."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch demands filtered by LEGAL (blank initial catalog)
        res = await _gw(client, "demands.list", {"category": "LEGAL"})
        assert res.json()["code"] == 200
        legal_demands = res.json()["data"]
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
        create_res = await _gw(client, "demands.publish", new_demand)
        assert create_res.json()["code"] == 200
        created_data = create_res.json()["data"]
        assert created_data["category"] == "LEGAL"
        demand_id = created_data["id"]

        # 3. Bid on the legal help demand
        bid_payload = {
            "demand_id": demand_id,
            "bidder_id": "usr_legal_expert_01",
            "bid_amount_cny": 14000.0,
            "delivery_days": 5,
            "proposal_text": "专业涉外网络安全律所，已主导完成数十个出海独立项目的 GDPR/DPA 审查交付。"
        }
        from src.core.security import create_session_token
        expert_token = create_session_token({
            "uid": "usr_legal_expert_01", "role": "MAKER", "nickname": "涉外合规专家",
        })
        bid_res = await _gw(client, "demands.bid", bid_payload, token=expert_token)
        assert bid_res.json()["code"] == 200
        assert bid_res.json()["data"]["bidder_id"] == "usr_legal_expert_01"
