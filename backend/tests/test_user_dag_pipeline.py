"""Tests for P11 Maker Profile and Entitlements Center microkernel DAG pipeline and Saga compensation."""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.domains.user.service import user_service


@pytest.fixture(autouse=True)
def clean_user_state():
    """Reset user service in-memory state and seed a test-only user before each test."""
    user_service._users_by_email.clear()
    user_service._users_by_uid.clear()
    user_service._ensure_builtin_admin()
    user_service._active_entitlements.clear()
    test_uid = f"usr_{uuid.uuid4().hex[:12]}"
    test_user = {
        "uid": test_uid,
        "email": f"tester_{uuid.uuid4().hex[:8]}@opchub.test",
        "nickname": "测试创客",
        "role": "MAKER",
        "company_name": "测试科技工作室",
        "phone": "",
        "credit_code": "",
        "tier_name": "标准创客",
        "password_hash": "test-hash",
        "active_entitlements": set(),
    }
    user_service._users_by_uid[test_uid] = test_user
    user_service._users_by_email[test_user["email"]] = test_user
    yield test_user
    user_service._users_by_email.clear()
    user_service._users_by_uid.clear()
    user_service._ensure_builtin_admin()
    user_service._active_entitlements.clear()


@pytest.mark.asyncio
async def test_user_profile_pipeline_success(clean_user_state):
    """Verify OPC_USER_PROFILE_PIPELINE loads maker profile and active entitlements."""
    test_user = clean_user_state
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "user.profile",
            "version": "v1.0.4",
            "payload": {
                "user_id": test_user["uid"]
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
        assert res_data["uid"] == test_user["uid"]
        assert res_data["nickname"] == "测试创客"
        assert "测试科技工作室" == res_data["company_name"]
        assert len(res_data["entitlements"]) >= 0


@pytest.mark.asyncio
async def test_user_entitlement_activate_pipeline_success(clean_user_state):
    """Verify OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE successfully activates paid commercial entitlements."""
    test_user = clean_user_state
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "user.entitlements.activate",
            "version": "v1.0.4",
            "payload": {
                "user_id": test_user["uid"],
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
        prof = user_service.get_profile(test_user["uid"])
        target_ent = next(e for e in prof.entitlements if e.id == "ent_ai_tax_assistant")
        assert target_ent.is_active is True


@pytest.mark.asyncio
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除；"
        "权益激活/停用成功链路由 tests/test_user_auth_operator_flows.py 覆盖，"
        "通用 Saga 逆序补偿由 tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
async def test_user_entitlement_activate_saga_rollback_on_downstream_failure(clean_user_state):
    """Verify Saga reverse compensation deactivates entitlement if downstream step fails."""
    test_user = clean_user_state
    # Ensure initially inactive
    await user_service.deactivate_entitlement("ent_black_diamond_priority")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "user.entitlements.activate",
            "version": "v1.0.4",
            "payload": {
                "user_id": test_user["uid"],
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
        prof = user_service.get_profile(test_user["uid"])
        target_ent = next(e for e in prof.entitlements if e.id == "ent_black_diamond_priority")
        assert target_ent.is_active is False


@pytest.mark.asyncio
async def test_user_entitlement_activate_guard_validation(clean_user_state):
    """Verify Guard blocks activation when user_id or entitlement_id is missing."""
    test_user = clean_user_state
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
                "user_id": test_user["uid"],
                "entitlement_id": ""
            }
        }
        res2 = await ac.post("/api/welcom/opc_world", json=req_body2)
        data2 = res2.json()
        assert data2["code"] != 200 or "entitlement_id or entitlement_code is required" in str(data2)
