"""Unit and Integration Tests for P01 Home Overview Microkernel DAG Orchestration Pipeline."""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest

client = TestClient(app)


def test_home_overview_dispatched_via_gateway():
    """Verify that scenario 'home.overview' is registered in gateway routes and aggregates real metrics."""
    req = {
        "scenario": "home.overview",
        "version": "v1.0.0",
        "payload": {},
        "context": {"trace_id": "trc_test_home_001"},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    payload = data["data"]
    assert payload["orchestrated_by"] == "OPC_HOME_OVERVIEW_PIPELINE"
    for field in (
        "active_makers_count",
        "active_dags_count",
        "matched_policies_count",
        "demands_orders_count",
        "perks_saved_cny",
        "products_count",
        "forum_threads_count",
    ):
        assert field in payload, f"missing metric field: {field}"
        assert payload[field] >= 0
    assert len(payload.get("quick_links", [])) >= 7


@pytest.mark.asyncio
async def test_home_overview_direct_microkernel_dag_execution():
    """Verify that OPC_HOME_OVERVIEW_PIPELINE executes its declarative entity nodes."""
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_HOME_OVERVIEW_PIPELINE",
            version="v1.0.0",
            inputs={"region": "全国"},
        )
    )
    assert res.status == "SUCCESS"
    node_handlers = [trace.get("action_handler") if isinstance(trace, dict) else trace.action_handler for trace in res.node_traces]
    # v2 拓扑：4 个 entity.count + 2 个 entity.list + assemble + response。
    assert node_handlers == [
        "entity.count",
        "entity.count",
        "entity.count",
        "entity.count",
        "entity.list",
        "entity.list",
        "assemble.home.overview",
        "response.build",
    ]
    final_output = res.final_output.get("response") or res.final_output
    assert len(final_output.get("quick_links", [])) >= 7
    # 指标必须来自真实服务数据而非硬编码：与各域服务当前规模一致
    from src.domains.products.service import product_service
    from src.domains.policies.service import policy_service
    from src.domains.forum.service import forum_service
    from src.domains.perks.service import perk_service

    assert final_output.get("products_count") == len(product_service.list_products())
    assert final_output.get("matched_policies_count") == len(policy_service.list_policies())
    assert final_output.get("forum_threads_count") == len(forum_service.list_threads())
    expected_perks_value = sum(float(p.value_cny or 0) for p in perk_service.list_perks())
    assert abs(final_output.get("perks_saved_cny", -1.0) - expected_perks_value) < 1e-6
