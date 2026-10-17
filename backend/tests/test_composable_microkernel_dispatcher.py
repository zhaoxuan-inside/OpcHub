"""Unit tests for Microkernel Dual-Mode Dispatcher and Composable Low-Code Pipelines."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.microkernel.dispatcher import dispatcher, DispatchMode
from src.core.microkernel.registry import registry
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest, OperatorModeUpdateRequest

client = TestClient(app)


def test_list_registered_operators_across_domains():
    """Verify operators across all domains and external gateways are properly registered."""
    descriptors = dispatcher.list_descriptors()
    names = {d.name for d in descriptors}

    # Core operators
    assert "gateway_ingress" in names
    assert "auth_guard" in names
    assert "invoice_tax_calc" in names

    # Domain operators
    assert "policy.calculate_tax" in names
    assert "policy.match_subsidies" in names
    assert "sop.render_document" in names
    assert "compliance.evaluate_audit" in names
    assert "moderation.inspect_content" in names

    # External gateway operators
    assert "external.ai.generate_charter" in names
    assert "external.crawler.fetch_policy" in names
    assert "external.payment.split_order" in names
    assert "external.sms.send_auth_code" in names


@pytest.mark.asyncio
async def test_in_process_direct_dispatch():
    """Test in-process direct memory execution with zero network latency."""
    handler = registry.get("policy.calculate_tax")
    assert handler is not None

    res = await dispatcher.dispatch(
        name="policy.calculate_tax",
        handler=handler,
        inputs={"quarterly_income": 200000.0},
        context={"trace_id": "test_trace_direct"},
    )
    assert res["tax_calculated"] is True
    assert res["is_vat_exempt"] is True
    assert res["estimated_tax_amount"] == 0.0


@pytest.mark.asyncio
async def test_operator_mode_toggle():
    """Test toggling operator between IN_PROCESS and HTTP_REMOTE."""
    op_name = "policy.calculate_tax"
    orig_mode, _ = dispatcher.get_operator_mode(op_name)

    # Switch to HTTP_REMOTE
    dispatcher.set_operator_mode(op_name, DispatchMode.HTTP_REMOTE, remote_endpoint="http://policy-svc:8080/tax")
    mode, endpoint = dispatcher.get_operator_mode(op_name)
    assert mode == DispatchMode.HTTP_REMOTE
    assert endpoint == "http://policy-svc:8080/tax"

    # Restore to IN_PROCESS
    dispatcher.set_operator_mode(op_name, DispatchMode.IN_PROCESS)
    mode, _ = dispatcher.get_operator_mode(op_name)
    assert mode == DispatchMode.IN_PROCESS


@pytest.mark.asyncio
async def test_execute_composable_startup_compliance_flow():
    """Test executing full composable startup flow (auth -> tax -> AI charter -> SOP doc -> compliance)."""
    req = ScenarioExecuteRequest(
        scenario_code="OPC_COMPLIANCE_STARTUP_FLOW",
        inputs={
            "quarterly_income": 250000.0,
            "company_name": "杭州极客超级个体科技有限公司",
            "owner_name": "李创客",
            "checked_ids": ["chk-privacy", "chk-escrow-thirdparty", "chk-opensource-license"],
        },
        override_dispatch_mode=DispatchMode.IN_PROCESS,
    )
    resp = await orchestration_service.execute_scenario(req, trace_id="trace_startup_flow_001")

    assert resp.status == "SUCCESS"
    assert resp.scenario_code == "OPC_COMPLIANCE_STARTUP_FLOW"
    assert resp.trace_id == "trace_startup_flow_001"
    assert len(resp.node_traces) == 5

    # Check node outputs
    assert resp.final_output.get("auth_passed") is True
    assert resp.final_output.get("is_vat_exempt") is True
    assert resp.final_output.get("ai_charter_generated") is True
    assert "sop_document_id" in resp.final_output
    assert "document_title" in resp.final_output
    assert "compliance_score" in resp.final_output


@pytest.mark.asyncio
async def test_execute_composable_policy_match_flow():
    """Test executing policy tax and AI subsidy matching scenario."""
    req = ScenarioExecuteRequest(
        scenario_code="OPC_POLICY_TAX_AI_MATCH",
        inputs={
            "quarterly_income": 180000.0,
            "city": "杭州",
            "entity_type": "个体工商户",
        },
    )
    resp = await orchestration_service.execute_scenario(req, trace_id="trace_policy_match_002")

    assert resp.status == "SUCCESS"
    assert len(resp.node_traces) == 5
    assert resp.final_output.get("vat_exemption_eligible") is True
    assert resp.final_output.get("subsidies_matched") is True
    assert resp.final_output.get("audit_recorded") is True


def test_api_list_operators():
    """Test HTTP API GET /api/v1/orchestration/operators."""
    response = client.get("/api/v1/orchestration/operators")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 12
    op_names = [item["name"] for item in data]
    assert "policy.calculate_tax" in op_names
    assert "external.ai.generate_charter" in op_names


def test_api_update_operator_mode():
    """Test HTTP API POST /api/v1/orchestration/operators/mode."""
    payload = {
        "name": "external.ai.generate_charter",
        "mode": "HTTP_REMOTE",
        "remote_endpoint": "http://ai-svc:8080/generate",
    }
    response = client.post("/api/v1/orchestration/operators/mode", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "external.ai.generate_charter"
    assert data["mode"] == "HTTP_REMOTE"

    # Reset back to IN_PROCESS
    payload["mode"] = "IN_PROCESS"
    payload["remote_endpoint"] = None
    client.post("/api/v1/orchestration/operators/mode", json=payload)


def test_api_execute_scenario():
    """Test HTTP API POST /api/v1/orchestration/scenarios/execute."""
    payload = {
        "scenario_code": "OPC_POLICY_TAX_AI_MATCH",
        "inputs": {
            "quarterly_income": 150000.0,
            "city": "杭州",
            "entity_type": "个体工商户",
        },
    }
    response = client.post("/api/v1/orchestration/scenarios/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["scenario_code"] == "OPC_POLICY_TAX_AI_MATCH"
    assert "execution_time_ms" in data
    assert "node_traces" in data
    assert len(data["node_traces"]) == 5
    assert data["final_output"]["vat_exemption_eligible"] is True
