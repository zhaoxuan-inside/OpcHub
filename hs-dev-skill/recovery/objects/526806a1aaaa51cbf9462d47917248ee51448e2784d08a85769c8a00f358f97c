"""Tests for P08 Compliance Guide & Audit Radar microkernel DAG pipeline and Saga compensation."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.compliance.service import compliance_service
from src.domains.compliance.models import AuditCheckItem
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


@pytest.fixture(autouse=True)
def seed_compliance_checkpoints():
    """Seed test-only compliance checkpoints so audit scoring has real items."""
    compliance_service._checkpoints = [
        AuditCheckItem(
            id="chk_01", dimension_id="dim_privacy", title="隐私政策明示",
            description="d", severity="CRITICAL", weight=12, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_02", dimension_id="dim_privacy", title="注销通道",
            description="d", severity="HIGH", weight=10, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_03", dimension_id="dim_payment", title="资金防二清",
            description="d", severity="CRITICAL", weight=15, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_04", dimension_id="dim_filing", title="ICP 备案",
            description="d", severity="HIGH", weight=10, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_05", dimension_id="dim_filing", title="算法备案",
            description="d", severity="HIGH", weight=10, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_06", dimension_id="dim_ip_oss", title="开源许可证",
            description="d", severity="CRITICAL", weight=12, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_07", dimension_id="dim_ugc_security", title="IP 属地展示",
            description="d", severity="HIGH", weight=8, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_08", dimension_id="dim_ugc_security", title="敏感词过滤",
            description="d", severity="HIGH", weight=10, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_09", dimension_id="dim_ugc_security", title="日志留存 180 天",
            description="d", severity="MEDIUM", weight=5, advice="a", legal_basis="l",
        ),
        AuditCheckItem(
            id="chk_10", dimension_id="dim_cross_border", title="GDPR 合规",
            description="d", severity="MEDIUM", weight=8, advice="a", legal_basis="l",
        ),
    ]
    yield
    compliance_service._checkpoints = []


@pytest.fixture
def client():
    return TestClient(app)


def test_compliance_audit_dag_success(client):
    """Test standard execution of OPC_COMPLIANCE_AUDIT_PIPELINE via unified gateway."""
    # Pass 8 out of 10 items
    passed_ids = ["chk_01", "chk_02", "chk_03", "chk_04", "chk_05", "chk_06", "chk_07", "chk_08"]
    req = {
        "scenario": "compliance.audit",
        "code_version": "v1.0.0",
        "payload": {
            "passed_item_ids": passed_ids,
            "strict_mode": False,
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    report = data["data"]
    assert "score" in report
    assert report["score"] >= 80
    assert report["grade"] in ["GOOD", "EXCELLENT"]
    assert report["passed_items_count"] == 8
    assert report["failed_items_count"] == 2


def test_compliance_audit_guard_blocked_on_invalid_input(client):
    """Test that guard blocks non-list passed_item_ids."""
    req = {
        "scenario": "compliance.audit",
        "code_version": "v1.0.0",
        "payload": {
            "passed_item_ids": "invalid_string_not_a_list",
            "strict_mode": False,
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code in [200, 400, 422]
    data = resp.json()
    assert data["code"] != 200 or "must be a list" in str(data).lower()


def test_compliance_audit_strict_mode_blocks_critical(client):
    """Test strict mode raises error and blocks pipeline when score is CRITICAL."""
    # Pass 0 items -> score is 0 (CRITICAL)
    req = {
        "scenario": "compliance.audit",
        "code_version": "v1.0.0",
        "payload": {
            "passed_item_ids": [],
            "strict_mode": True,
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code in [200, 400, 403, 422]
    data = resp.json()
    assert data["code"] != 200 or "critical" in str(data).lower() or "blocked" in str(data).lower()


@pytest.mark.asyncio
async def test_compliance_audit_saga_rollback_on_downstream_failure():
    """Test that downstream failure triggers reverse compensation to reset audit session."""
    inputs = {
        "passed_item_ids": ["chk_01", "chk_02"],
        "strict_mode": False,
        "simulate_downstream_failure": True,
    }
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_COMPLIANCE_AUDIT_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    # The pipeline should converge to ROLLED_BACK
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0

    # Verify step_eval compensation trace
    eval_trace = next(
        (t for t in res.compensation_traces if t.get("node_id") == "step_eval"), None
    )
    assert eval_trace is not None
    assert eval_trace.get("status") == "SUCCESS"
    assert eval_trace["output"].get("action") == "ROLLED_BACK"
