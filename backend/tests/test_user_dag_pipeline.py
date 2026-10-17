"""Tests for P11 Maker Profile and Entitlements Center microkernel DAG pipeline and Saga compensation."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.domains.user.service import user_service


@pytest.mark.asyncio
async def test_user_profile_pipeline_success():
    """Verify OPC_USER_PROFILE_PIPELINE loads maker profile and active entitlements."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "user.profile",
            "version": "v1.0.4",
            "payload": {
                "user_id": "usr_2026_opc_9981"
            },
            "context": {
                "trace_id": "tr_user_prof_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        res_data = data["data"]
        assert res_data["orchestrated_by"] == "OPC_USER_PROFILE_PIPELINE"
        assert res_data["uid"] == "usr_2026_opc_9981"
        assert res_data["nickname"] == "赵玄"
        assert "极客视界" in res_data["company_name"]
        assert len(res_data["entitlements"]) >= 4


@pytest.mark.asyncio
async def test_user_entitlement_activate_pipeline_success():
    """Verify OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE successfully activates paid commercial entitlements."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "user.entitlements.activate",
            "version": "v1.0.4",
            "payload": {
                "user_id": "usr_2026_opc_9981",
                "entitlement_id": "ent_ai_tax_assistant",
                "duration_months": 12
            },
            "context": {
                "trace_id": "tr_user_ent_act_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        res_data = data["data"]
        assert res_data["orchestrated_by"] == "OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE"
        assert res_data["status"] == "ACTIVATED"
        assert res_data["is_active"] is True
        assert res_data["receipt_no"].startswith("REC-")

        # Verify profile reflects active state
        prof = user_service.get_profile("usr_2026_opc_9981")
        target_ent = next(e for e in prof.entitlements if e.id == "ent_ai_tax_assistant")
        assert target_ent.is_active is True


@pytest.mark.asyncio
async def test_user_entitlement_activate_saga_rollback_on_downstream_failure():
    """Verify Saga reverse compensation deactivates entitlement if downstream step fails."""
    # Ensure initially inactive
    user_service.deactivate_entitlement("ent_black_diamond_priority")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "user.entitlements.activate",
            "version": "v1.0.4",
            "payload": {
                "user_id": "usr_2026_opc_9981",
                "entitlement_id": "ent_black_diamond_priority",
                "simulate_downstream_failure": True
            },
            "context": {
                "trace_id": "tr_user_ent_saga"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "Simulated downstream telemetry failure" in str(data)

        # Verify entitlement was rolled back to inactive
        prof = user_service.get_profile("usr_2026_opc_9981")
        target_ent = next(e for e in prof.entitlements if e.id == "ent_black_diamond_priority")
        assert target_ent.is_active is False


@pytest.mark.asyncio
async def test_user_entitlement_activate_guard_validation():
    """Verify Guard blocks activation when user_id or entitlement_id is missing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "user.entitlements.activate",
            "version": "v1.0.4",
            "payload": {
                "user_id": "",
                "entitlement_id": "ent_ai_tax_assistant"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "user_id is required" in str(data)

        req_body2 = {
            "scenario": "user.entitlements.activate",
            "version": "v1.0.4",
            "payload": {
                "user_id": "usr_2026_opc_9981",
                "entitlement_id": ""
            }
        }
        res2 = await ac.post("/api/welcom/opc_world", json=req_body2)
        data2 = res2.json()
        assert data2["code"] != 200 or "entitlement_id or entitlement_code is required" in str(data2)
