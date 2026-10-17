"""Tests for FastAPI HTTP Endpoints (Ops Telemetry & System Health)."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["kernel_operators_count"] >= 5


@pytest.mark.asyncio
async def test_ops_dashboard_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/ops/dashboard")
    assert response.status_code == 200
    data = response.json()

    # Metrics without instrumentation source report 0 (no fabricated numbers)
    assert data["dau"]["value"] == "0"
    assert data["dau"]["delta_percent"] == 0.0
    assert data["uv"]["value"] == "0"
    assert data["pv"]["value"] == "0"
    assert data["mau"]["value"] == "0"

    # Terminal distribution reports 0 until real telemetry is wired in
    assert data["terminal_distribution"]["ios_percentage"] == 0.0
    assert data["terminal_distribution"]["android_percentage"] == 0.0
    assert data["terminal_distribution"]["desktop_web_percentage"] == 0.0

    # Daily trend reflects live state (today's point with 0 fabricated traffic)
    assert len(data["daily_trends"]) == 1
    assert data["daily_trends"][-1]["pv"] == 0
    assert data["daily_trends"][-1]["uv"] == 0

    # Module heatmaps reflect live domain record counts (may be empty on blank DB)
    for hm in data["module_heatmaps"]:
        assert hm["pv_count"] >= 0
        assert hm["percentage"] >= 0.0


@pytest.mark.asyncio
async def test_sandbox_validate_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Safe code
        res_safe = await ac.post("/api/v1/microkernel/sandbox/validate", json={
            "code": "def my_func(x): return x * 2"
        })
        assert res_safe.status_code == 200
        assert res_safe.json()["is_safe"] is True

        # 2. Malicious code
        res_unsafe = await ac.post("/api/v1/microkernel/sandbox/validate", json={
            "code": "import subprocess\nsubprocess.Popen(['ls'])"
        })
        assert res_unsafe.status_code == 200
        assert res_unsafe.json()["is_safe"] is False
        assert len(res_unsafe.json()["violations"]) > 0
