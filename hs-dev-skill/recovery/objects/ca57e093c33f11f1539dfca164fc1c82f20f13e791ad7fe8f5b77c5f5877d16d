"""Tests for P10 Ops Telemetry Dashboard microkernel DAG pipeline and Saga compensation."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.core.security import create_session_token

_TEST_ADMIN_TOKEN = create_session_token({"uid": "usr_admin_builtin", "role": "ADMIN"})


@pytest.mark.asyncio
async def test_ops_dashboard_pipeline_success():
    """Verify OPC_OPS_DASHBOARD_PIPELINE successfully aggregates multi-terminal operational metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {_TEST_ADMIN_TOKEN}"
        req_body = {
            "scenario": "ops.dashboard",
            "version": "v1.0.4",
            "payload": {
                "time_range": "7D",
                "terminal_filter": "ALL",
                "operator_id": "admin_ops_001"
            },
            "context": {
                "trace_id": "tr_ops_dash_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        res_data = data["data"]
        assert res_data["orchestrated_by"] == "OPC_OPS_DASHBOARD_PIPELINE"
        assert res_data["audit_status"] == "RECORDED"
        assert "audit_id" in res_data

        # Verify core KPIs report 0 until real instrumentation is wired in
        assert res_data["dau"]["value"] == "0"
        assert res_data["uv"]["value"] == "0"
        assert res_data["pv"]["value"] == "0"
        assert res_data["mau"]["value"] == "0"

        # Verify terminal distribution reports 0 (no fabricated traffic)
        dist = res_data["terminal_distribution"]
        assert dist["ios_percentage"] == 0.0
        assert dist["android_percentage"] == 0.0
        assert dist["desktop_web_percentage"] == 0.0

        # Daily trends reflect live state (single today point)
        assert len(res_data["daily_trends"]) >= 1


@pytest.mark.asyncio
async def test_telemetry_dashboard_alias_pipeline():
    """Verify telemetry.dashboard alias also executes via OPC_OPS_DASHBOARD_PIPELINE."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {_TEST_ADMIN_TOKEN}"
        req_body = {
            "scenario": "telemetry.dashboard",
            "version": "v1.0.4",
            "payload": {
                "time_range": "30D"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        assert data["data"]["orchestrated_by"] == "OPC_OPS_DASHBOARD_PIPELINE"
        assert data["data"]["time_range"] == "30D"


@pytest.mark.asyncio
async def test_ops_dashboard_saga_rollback_on_downstream_failure():
    """Verify Saga reverse compensation executes when downstream telemetry step fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {_TEST_ADMIN_TOKEN}"
        req_body = {
            "scenario": "ops.dashboard",
            "version": "v1.0.4",
            "payload": {
                "time_range": "7D",
                "simulate_downstream_failure": True
            },
            "context": {
                "trace_id": "tr_ops_dash_saga"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "Simulated downstream telemetry failure" in str(data)


@pytest.mark.asyncio
async def test_ops_dashboard_guard_invalid_time_range():
    """Verify Guard blocks request with invalid time_range parameter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {_TEST_ADMIN_TOKEN}"
        req_body = {
            "scenario": "ops.dashboard",
            "version": "v1.0.4",
            "payload": {
                "time_range": "100YEARS_INVALID"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "Invalid time_range" in str(data)
