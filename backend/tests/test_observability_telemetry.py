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
async def test_dag_pipeline_trace_id_penetration():
    transport = ASGITransport(app=app)
    custom_trace = "trc_pipeline_exec_776655"
    dag_payload = {
        "config": {
            "version": "v1.0.4-draft",
            "scenario_code": "tax.calculate_vat_exemption",
            "execution_graph": {
                "topology": "DAG",
                "entry_node": "dnode-1",
                "nodes": [
                    {
                        "id": "dnode-1", "action_handler": "transform.derive", "type": "BIZ",
                        "params": {"expr": "args.income * 0", "output_key": "rate"},
                        "inputs_map": {"income": "$inputs.quarterly_income"},
                    },
                    {
                        "id": "dnode-2", "action_handler": "transform.derive", "type": "BIZ",
                        "params": {"expr": "args.rate + 1", "output_key": "step"},
                        "inputs_map": {"rate": "$nodes.dnode-1.rate"},
                    },
                    {
                        "id": "dnode-3", "action_handler": "transform.derive", "type": "BIZ",
                        "params": {"expr": "args.step * 2", "output_key": "doubled"},
                        "inputs_map": {"step": "$nodes.dnode-2.step"},
                    },
                    {
                        "id": "dnode-4", "action_handler": "transform.derive", "type": "BIZ",
                        "params": {"expr": "args.doubled + 0", "output_key": "final"},
                        "inputs_map": {"doubled": "$nodes.dnode-3.doubled"},
                    },
                ],
                "edges": [
                    {"from": "dnode-1", "to": "dnode-2"},
                    {"from": "dnode-2", "to": "dnode-3"},
                    {"from": "dnode-3", "to": "dnode-4"},
                ],
            },
        },
        "inputs": {"quarterly_income": 280000.0, "auth_token": "valid_token"},
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/microkernel/dag/execute",
            json=dag_payload,
            headers={"X-Trace-ID": custom_trace},
        )
        assert res.status_code == 200
        assert res.headers["X-Trace-ID"] == custom_trace
        data = res.json()
        assert data["trace_id"] == custom_trace
        assert len(data["node_traces"]) == 4
        for trace in data["node_traces"]:
            assert trace["trace_id"] == custom_trace
