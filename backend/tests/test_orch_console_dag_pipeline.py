"""Tests for P12 Backend Orchestration Console DAG pipelines and Saga compensation."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.domains.orchestration.service import orchestration_service


@pytest.mark.asyncio
async def test_orchestration_operators_list_pipeline():
    """Verify OPC_ORCHESTRATION_OPERATORS_LIST_PIPELINE returns full set of domain operators."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "orchestration.operators.list",
            "version": "v1.0.4",
            "payload": {},
            "context": {
                "trace_id": "tr_orch_list_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        operators = data["data"]
        assert len(operators) >= 15
        op_names = [op["name"] for op in operators]
        assert "auth_guard" in op_names
        assert "policy.calculate_tax" in op_names
        assert "compliance.evaluate_audit" in op_names
        assert "moderation.takedown.persist" in op_names


@pytest.mark.asyncio
async def test_orchestration_control_pipeline_save_dag_success():
    """Verify OPC_ORCHESTRATION_CONTROL_PIPELINE compiles and deploys new DAG topology."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        test_topo = {
            "topology": "DAG",
            "entry_node": "n1",
            "nodes": [
                {"id": "n1", "action_handler": "auth_guard", "type": "GUARD"},
                {"id": "n2", "action_handler": "policy.calculate_tax", "type": "BIZ"}
            ],
            "edges": [
                {"from": "n1", "to": "n2"}
            ]
        }
        req_body = {
            "scenario": "orchestration.dag.save",
            "version": "v1.0.4",
            "payload": {
                "scenario_code": "TEST_ORCH_SCENARIO_2026",
                "version": "v1.0.0",
                "topology_graph": test_topo,
                "created_by": "admin_sys_01"
            },
            "context": {
                "trace_id": "tr_orch_save_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        res_data = data["data"]
        assert res_data["orchestrated_by"] == "OPC_ORCHESTRATION_CONTROL_PIPELINE"
        assert res_data["scenario_code"] == "TEST_ORCH_SCENARIO_2026"
        assert res_data["version"] == "v1.0.0"
        assert res_data["compiled_hash"] is not None

        # Verify domain state has the new DAG
        rec = orchestration_service.get_dag_config("TEST_ORCH_SCENARIO_2026", "v1.0.0")
        assert rec is not None
        assert rec.scenario_code == "TEST_ORCH_SCENARIO_2026"


@pytest.mark.asyncio
async def test_orchestration_control_saga_rollback_on_downstream_failure():
    """Verify Saga reverse compensation deletes DAG config if downstream step fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        test_topo = {
            "topology": "DAG",
            "entry_node": "n1",
            "nodes": [{"id": "n1", "action_handler": "auth_guard", "type": "GUARD"}],
            "edges": []
        }
        req_body = {
            "scenario": "orchestration.dag.save",
            "version": "v1.0.4",
            "payload": {
                "scenario_code": "ROLLBACK_TEST_SCENARIO",
                "version": "v9.9.9",
                "topology_graph": test_topo,
                "simulate_downstream_failure": True
            },
            "context": {
                "trace_id": "tr_orch_saga_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "Simulated downstream telemetry failure" in str(data)

        # Verify DAG was rolled back and deleted
        with pytest.raises(KeyError):
            orchestration_service.get_dag_config("ROLLBACK_TEST_SCENARIO", "v9.9.9")


@pytest.mark.asyncio
async def test_orchestration_control_guard_validation():
    """Verify Guard blocks requests with missing scenario_code or version."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "orchestration.dag.save",
            "version": "v1.0.4",
            "payload": {
                "scenario_code": "",
                "version": "v1.0.0"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "scenario_code is required" in str(data)
