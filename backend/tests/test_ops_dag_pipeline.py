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
        # v2 大盘是纯读场景（count/list + assemble），不再有旧 audit/orchestrated_by 字段。
        assert res_data["is_live"] is True
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
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除；"
        "大盘成功链路由 tests/test_ops_telemetry_api.py 覆盖，通用 Saga 逆序补偿由 "
        "tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
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
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧 ops.dashboard 时间范围硬校验算子已移除；"
        "当前场景将 time_range 原样透传给 assemble.telemetry.dashboard，"
        "大盘契约（含 time_range 回显）由 tests/test_ops_telemetry_api.py 覆盖。"
    )
)
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
