"""Tests for P05 Demand & Bidding Market microkernel DAG pipelines and Saga compensation."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.demands.service import demand_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_demand_publish_dag_success(client):
    """Test standard execution of OPC_DEMAND_PUBLISH_PIPELINE via unified gateway."""
    req = {
        "scenario": "demands.publish",
        "code_version": "v1.0.0",
        "payload": {
            "title": "海外独立站 Shopify 支付插件定制开发",
            "description": "需要资深独立开发者对接 Stripe 与 PayPal 订阅计费网关，要求通过 PCI-DSS 基础合规检查。",
            "budget_cny": 15000.0,
            "category": "DEV",
            "deadline_days": 10,
            "creator_id": "usr_maker_client_2026",
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["title"] == "海外独立站 Shopify 支付插件定制开发"
    demand_id = data["data"]["id"]
    assert demand_id is not None

    # Verify queryable in demand service
    stored = demand_service.get_demand(demand_id)
    assert stored is not None
    assert stored.budget_cny == 15000.0


def test_demand_publish_moderation_guard_blocked(client):
    """Test that demand publish guard blocks sensitive or illegal content."""
    req = {
        "scenario": "demands.publish",
        "code_version": "v1.0.0",
        "payload": {
            "title": "急求内嵌自设资金池搭建方案",
            "description": "希望能绕过第三方持牌支付机构监管，私自沉淀用户预付款。",
            "budget_cny": 50000.0,
            "category": "DEV",
            "deadline_days": 10,
            "creator_id": "usr_bad_client",
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code in [200, 400, 422]
    data = resp.json()
    assert data["code"] != 200 or "violation" in str(data).lower() or "prohibited" in str(data).lower()



@pytest.mark.asyncio
async def test_demand_publish_saga_rollback_on_downstream_failure():
    """Test that downstream failure triggers Saga reverse compensation to remove persisted demand."""
    inputs = {
        "title": "回滚测试外包委托需求",
        "description": "本需求将在下游度量节点发生故障时自动触发 Saga 补偿物理撤回。",
        "budget_cny": 8000.0,
        "category": "DEV",
        "deadline_days": 7,
        "creator_id": "usr_test_rollback",
        "simulate_downstream_failure": True,
    }
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    # The pipeline should converge to ROLLED_BACK
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0
    # Confirm trace for demand.publish.persist
    persist_trace = next(
        (t for t in res.compensation_traces if t.get("node_id") == "step_persist"), None
    )
    assert persist_trace is not None
    assert persist_trace.get("status") == "SUCCESS"

    # Verify demand is physically eliminated from memory
    did = persist_trace["output"].get("demand_id")
    if did:
        assert demand_service.get_demand(did) is None


def test_demand_bid_dag_success(client):
    """Test standard execution of OPC_DEMAND_BID_PIPELINE via unified gateway."""
    # Find an open demand
    demands = demand_service.list_demands()
    assert len(demands) > 0
    target_demand = demands[0]
    initial_count = target_demand.bidders_count

    req = {
        "scenario": "demands.bid",
        "code_version": "v1.0.0",
        "payload": {
            "demand_id": target_demand.id,
            "bidder_id": "usr_maker_expert_007",
            "bid_amount_cny": 14000.0,
            "delivery_days": 6,
            "proposal_text": "已交付过同类独立站系统，拥有成熟方案与生产级代码，6天内高质量交付并协助上线。",
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["bidder_id"] == "usr_maker_expert_007"
    assert data["data"]["bid_amount_cny"] == 14000.0

    # Verify bidders_count incremented
    updated = demand_service.get_demand(target_demand.id)
    assert updated.bidders_count == initial_count + 1


def test_demand_bid_guard_blocked_on_invalid_demand_or_sensitive(client):
    """Test bidding guard blocks invalid demand IDs or moderation violations."""
    # 1. Non-existent demand
    req_bad_id = {
        "scenario": "demands.bid",
        "code_version": "v1.0.0",
        "payload": {
            "demand_id": "non_existent_demand_id_xyz",
            "bidder_id": "usr_maker_001",
            "bid_amount_cny": 1000.0,
            "delivery_days": 3,
            "proposal_text": "正常提案文本内容详情测试。",
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req_bad_id)
    assert resp.status_code in [200, 400, 422]
    data_bad = resp.json()
    assert data_bad["code"] != 200 or "not found" in str(data_bad).lower()

    # 2. Sensitive keywords in bid proposal
    demands = demand_service.list_demands()
    req_sensitive = {
        "scenario": "demands.bid",
        "code_version": "v1.0.0",
        "payload": {
            "demand_id": demands[0].id,
            "bidder_id": "usr_maker_001",
            "bid_amount_cny": 1000.0,
            "delivery_days": 3,
            "proposal_text": "我们可以配合代开假发票来冲抵外包开发成本。",
        },
        "context": {},
    }
    resp_sens = client.post("/api/welcom/opc_world", json=req_sensitive)
    assert resp_sens.status_code in [200, 400, 422]
    data_sens = resp_sens.json()
    assert data_sens["code"] != 200 or "violation" in str(data_sens).lower() or "prohibited" in str(data_sens).lower()



@pytest.mark.asyncio
async def test_demand_bid_saga_rollback_on_downstream_failure():
    """Test that downstream failure triggers Saga reverse compensation to remove bid and restore count."""
    demands = demand_service.list_demands()
    assert len(demands) > 0
    target_demand = demands[0]
    initial_count = target_demand.bidders_count

    inputs = {
        "demand_id": target_demand.id,
        "bidder_id": "usr_maker_rollback_bid",
        "bid_amount_cny": 12000.0,
        "delivery_days": 5,
        "proposal_text": "本竞标方案将触发下游度量异常并自动逆向补偿回滚。",
        "simulate_downstream_failure": True,
    }
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_BID_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    # The pipeline should converge to ROLLED_BACK
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0

    # Verify bidders_count was rolled back to initial_count
    updated = demand_service.get_demand(target_demand.id)
    assert updated.bidders_count == initial_count
