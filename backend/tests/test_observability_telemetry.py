"""Tests for Observability, TraceID Propagation, and Tri-State Probes."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_liveness_probe_livez():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/livez")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ALIVE"
        assert "pid" in data
        assert len(data["trace_id"]) > 0
        assert "X-Trace-ID" in res.headers
        assert "X-Response-Time-Ms" in res.headers


@pytest.mark.asyncio
async def test_readiness_probe_readyz():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/readyz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "READY"
        checks = data["checks"]
        assert "kernel_operators" in checks
        assert checks["sop_engine"] == "OK"
        assert checks["forum"] == "OK"


@pytest.mark.asyncio
async def test_diagnostics_probe_healthz():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["service"] == "OpcHub Microkernel Platform"
        assert data["uptime_seconds"] >= 0.0
        assert data["active_operators"] >= 5


@pytest.mark.asyncio
async def test_custom_trace_id_propagation_header():
    transport = ASGITransport(app=app)
    custom_trace = "trc_custom_client_8899aabb"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/livez", headers={"X-Trace-ID": custom_trace})
        assert res.status_code == 200
        assert res.headers["X-Trace-ID"] == custom_trace
        assert res.json()["trace_id"] == custom_trace


@pytest.mark.asyncio
async def test_gateway_scenario_trace_id_penetration():
    """X-Trace-ID penetrates the unified gateway into the MicroFlow run."""
    transport = ASGITransport(app=app)
    custom_trace = "trc_pipeline_exec_776655"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/welcom/opc_world",
            json={"scenario": "auth.captcha", "version": "v1.0.0", "payload": {}},
            headers={"X-Trace-ID": custom_trace},
        )
        assert res.status_code == 200, res.text
        assert res.headers["X-Trace-ID"] == custom_trace
        data = res.json()
        assert data["trace_id"] == custom_trace

        res2 = await ac.post(
            "/api/welcom/opc_world",
            json={"scenario": "auth.captcha", "version": "v1.0.0", "payload": {}},
        )
        assert res2.status_code == 200
        assert res2.headers.get("X-Trace-ID", "").startswith("trc_")

