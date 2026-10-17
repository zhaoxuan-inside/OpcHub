"""Tests for P07 Perks & Infrastructure microkernel DAG pipelines and Saga compensation."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.perks.service import perk_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_perk_claim_dag_success(client):
    """Test standard execution of OPC_PERK_CLAIM_PIPELINE via unified gateway."""
    perk = perk_service.get_perk("perk_aliyun_bailian")
    assert perk is not None
    init_quota = perk.quota_remaining

    req = {
        "scenario": "perks.claim",
        "code_version": "v1.0.0",
        "payload": {
            "perk_id": "perk_aliyun_bailian",
            "user_id": "usr_maker_cloud_claim",
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    claim = data["data"]
    assert "voucher_code" in claim
    assert "OPC-" in claim["voucher_code"]
    assert claim["status"] == "ACTIVATED"

    # Verify quota decremented
    updated_perk = perk_service.get_perk("perk_aliyun_bailian")
    assert updated_perk.quota_remaining == init_quota - 1


def test_perk_claim_guard_blocked_on_invalid_perk(client):
    """Test that perk claim guard blocks non-existent perks."""
    req = {
        "scenario": "perks.claim",
        "code_version": "v1.0.0",
        "payload": {
            "perk_id": "perk_non_existent_404",
            "user_id": "usr_maker_test",
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code in [200, 400, 422]
    data = resp.json()
    assert data["code"] != 200 or "not found" in str(data).lower()


@pytest.mark.asyncio
async def test_perk_claim_saga_rollback_on_downstream_failure():
    """Test that downstream failure triggers reverse compensation to revoke claim and restore quota."""
    perk = perk_service.get_perk("perk_cloudflare_workers")
    assert perk is not None
    initial_quota = perk.quota_remaining

    inputs = {
        "perk_id": "perk_cloudflare_workers",
        "user_id": "usr_maker_rollback_perk",
        "simulate_downstream_failure": True,
    }
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PERK_CLAIM_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    # The pipeline should converge to ROLLED_BACK
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0

    # Verify quota was restored
    updated_perk = perk_service.get_perk("perk_cloudflare_workers")
    assert updated_perk.quota_remaining == initial_quota


def test_perk_publish_dag_success(client):
    """Test standard execution of OPC_PERK_PUBLISH_PIPELINE via unified gateway."""
    req = {
        "scenario": "perks.publish",
        "code_version": "v1.0.0",
        "payload": {
            "name": "Supabase 出海开发者专属优惠包",
            "provider": "Supabase",
            "value_cny": 2400.0,
            "category": "INFRA",
            "summary": "享受 6 个月 Pro Plan 费用减免，包含 8GB 数据库与 100GB 存储空间。",
            "quota_remaining": 50,
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    perk_data = data["data"]
    assert "id" in perk_data
    assert perk_data["name"] == "Supabase 出海开发者专属优惠包"

    # Verify queryable in perk service
    pid = perk_data["id"]
    stored = perk_service.get_perk(pid)
    assert stored is not None
    assert stored.value_cny == 2400.0


def test_perk_publish_guard_blocked_on_sensitive(client):
    """Test that sensitive keywords are blocked by perk.publish.guard."""
    req = {
        "scenario": "perks.publish",
        "code_version": "v1.0.0",
        "payload": {
            "name": "洗钱与虚构外包支付特权通道",
            "provider": "黑灰产服务商",
            "value_cny": 99999.0,
            "category": "FINANCE",
            "summary": "协助各类违规操作规避监管。",
            "quota_remaining": 10,
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code in [200, 400, 422]
    data = resp.json()
    assert data["code"] != 200 or "violation" in str(data).lower() or "prohibited" in str(data).lower()


@pytest.mark.asyncio
async def test_perk_publish_saga_rollback_on_downstream_failure():
    """Test that downstream failure triggers reverse compensation to remove published perk."""
    inputs = {
        "name": "测试回滚特权福利项",
        "provider": "回滚测试供应商",
        "value_cny": 5000.0,
        "category": "CLOUD",
        "summary": "当下游度量失败时该特权项将被物理回滚撤除。",
        "quota_remaining": 20,
        "simulate_downstream_failure": True,
    }
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PERK_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    # The pipeline should converge to ROLLED_BACK
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0

    # Verify perk was deleted
    persist_trace = next(
        (t for t in res.compensation_traces if t.get("node_id") == "step_persist"), None
    )
    assert persist_trace is not None
    assert persist_trace.get("status") == "SUCCESS"
    pid = persist_trace["output"].get("perk_id")
    if pid:
        assert perk_service.get_perk(pid) is None
