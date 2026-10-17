"""Unit and Integration Tests for P01 Home Overview Microkernel DAG Orchestration Pipeline."""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest

client = TestClient(app)


def test_home_overview_dispatched_via_gateway():
    """Verify that POST /api/welcom/opc_world for scenario 'home.overview' returns DAG orchestrated data."""
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
    assert data["scenario"] == "home.overview"
    assert data["trace_id"] == "trc_test_home_001"

    res_data = data["data"]
    assert res_data["orchestrated_by"] == "OPC_HOME_OVERVIEW_PIPELINE"
    assert "active_makers_count" in res_data
    assert "quick_links" in res_data
    assert len(res_data["quick_links"]) >= 7

    # Check quick links contents
    routes = [ql["route"] for ql in res_data["quick_links"]]
    assert "forum" in routes
    assert "product" in routes
    assert "policy" in routes
    assert "demand" in routes
    assert "sop" in routes


@pytest.mark.asyncio
async def test_home_overview_direct_microkernel_dag_execution():
    """Verify that OPC_HOME_OVERVIEW_PIPELINE executes with 3 nodes via MicrokernelEngine."""
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_HOME_OVERVIEW_PIPELINE",
            version="v1.0.0",
            inputs={"region": "全国"},
        )
    )
    assert res.status == "SUCCESS"
    assert len(res.node_traces) == 3
    node_handlers = [trace.get("action_handler") if isinstance(trace, dict) else trace.action_handler for trace in res.node_traces]
    assert node_handlers == [
        "home.metrics.collector",
        "home.sitemap.builder",
        "home.overview.aggregator",
    ]
    assert res.final_output.get("orchestrated_by") == "OPC_HOME_OVERVIEW_PIPELINE"
    assert len(res.final_output.get("quick_links", [])) >= 7
