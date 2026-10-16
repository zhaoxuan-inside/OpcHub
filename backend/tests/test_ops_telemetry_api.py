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

    # Verify DAU, UV, PV metrics exist and match specs
    assert data["dau"]["value"] == "14,820"
    assert data["dau"]["delta_percent"] == 12.4
    assert data["uv"]["value"] == "89,540"
    assert data["pv"]["value"] == "628,300"
    assert data["mau"]["value"] == "182,450"

    # Verify 3-terminal distribution matches prototype
    assert data["terminal_distribution"]["ios_percentage"] == 46.2
    assert data["terminal_distribution"]["android_percentage"] == 35.8
    assert data["terminal_distribution"]["desktop_web_percentage"] == 18.0

    # Verify 7-day daily trend points
    assert len(data["daily_trends"]) == 7
    assert data["daily_trends"][-1]["date"] == "10-16"
    assert data["daily_trends"][-1]["pv"] == 628300

    # Verify Module Heatmap
    assert len(data["module_heatmaps"]) >= 5
    assert data["module_heatmaps"][0]["module_name"] == "政策雷达"
    assert data["module_heatmaps"][0]["percentage"] == 32.0


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
