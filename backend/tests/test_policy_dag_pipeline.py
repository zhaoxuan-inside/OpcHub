"""Test suite for P04 Policy Center driven by Microkernel DAG Orchestration & Saga Compensation."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.policies.service import policy_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


@pytest.fixture(autouse=True)
def clean_policy_state():
    """Reset policy service state before each test and seed test-only policies."""
    policy_service.clear()
    from src.domains.policies.models import PolicyResponse
    policy_service._policies["pol_vat_exemption_2026"] = PolicyResponse(
        id="pol_vat_exemption_2026",
        title="小规模纳税人月销售额 10 万以下（季度 30 万）免征增值税",
        policy_level="国家级",
        category="TAX",
        subsidy_amount_max=9000.0,
        summary="小规模纳税人合计月销售额未超过10万元（以1个季度为纳税期限的，季度销售额未超过30万元）的，免征增值税。",
        eligible_conditions=["纳税主体为小规模纳税人（个体工商户或小微企业）"],
        legal_basis="财政部 税务总局公告 2023年第12号",
    )
    policy_service._policies["pol_ai_compute_voucher_hz"] = PolicyResponse(
        id="pol_ai_compute_voucher_hz",
        title="杭州高新区超级个体与小微人工智能算力券补贴",
        policy_level="省市级",
        category="SUBSIDY",
        subsidy_amount_max=50000.0,
        summary="为注册在本区开展大模型微调、生成式AI应用独立研发的创客主体，提供最高 30% 的实际算力消费抵扣凭据。",
        eligible_conditions=["在杭州市高新技术产业园区完成注册登记"],
        legal_basis="杭高新发〔2024〕18号",
    )
    policy_service._policies["pol_rnd_deduction_100"] = PolicyResponse(
        id="pol_rnd_deduction_100",
        title="科技型中小微企业研发费用 100% 税前加计扣除",
        policy_level="国家级",
        category="TAX",
        subsidy_amount_max=150000.0,
        summary="科技型中小企业开展研发活动中实际发生的研发费用在税前加计扣除100%。",
        eligible_conditions=["入库全国科技型中小企业信息库"],
        legal_basis="财政部 税务总局 科技部公告 2023年第11号",
    )
    yield
    policy_service.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_policy_match_via_microkernel_dag(client):
    """Verify policy matching and tax savings strictly orchestrated by OPC_POLICY_MATCH_PIPELINE DAG."""
    payload = {
        "scenario": "policies.match",
        "version": "v1.0.0",
        "client_code_version": "v1.0.4",
        "payload": {
            "quarterly_income": 280000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["code"] == 200
    assert data["scenario"] == "policies.match"

    res = data["data"]
    assert res["eligible"] is True
    assert res["is_vat_exempt"] is True
    assert res["applicable_tax_rate"] == 0.0
    assert res["estimated_tax_savings"] == 8400.0
    assert "matched_subsidies" in res
    assert len(res["matched_subsidies"]) >= 2
    assert "杭州" in str(res["matched_subsidies"])


def test_policy_match_negative_income_rejected(client):
    """Verify policy qualify guard blocks negative quarterly income."""
    payload = {
        "scenario": "policies.match",
        "version": "v1.0.0",
        "payload": {
            "quarterly_income": -50000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 400 or resp.status_code == 422 or resp.status_code == 200
    data = resp.json()
    assert data["code"] != 200 or "negative" in str(data) or "cannot be negative" in str(data)


def test_policy_publish_via_microkernel_dag(client):
    """Verify publishing a government subsidy policy via OPC_POLICY_PUBLISH_PIPELINE DAG."""
    payload = {
        "scenario": "policies.publish",
        "version": "v1.0.0",
        "payload": {
            "title": "大湾区青年创客跨境离岸结算免税专项指引",
            "policy_level": "省市级",
            "category": "TAX",
            "subsidy_amount_max": 80000.0,
            "summary": "针对在大湾区注册开展跨境独立站和SaaS软件出海的一人公司，提供增值税及所得税专项扶持。",
            "eligible_conditions": ["设立于粤港澳大湾区合规园区", "从事跨境数字贸易与软件研发"],
            "legal_basis": "粤府规〔2025〕6号 促进数字服务贸易发展若干措施",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["code"] == 200
    assert data["scenario"] == "policies.publish"

    pol = data["data"]
    assert "id" in pol
    assert pol["title"] == "大湾区青年创客跨境离岸结算免税专项指引"
    assert pol["subsidy_amount_max"] == 80000.0

    # Verify repository persistence
    all_policies = policy_service.list_policies()
    assert any(p.title == "大湾区青年创客跨境离岸结算免税专项指引" for p in all_policies)


def test_policy_publish_moderation_guard_blocks_violation(client):
    """Verify that sensitive words are blocked by policy.publish.guard."""
    payload = {
        "scenario": "policies.publish",
        "version": "v1.0.0",
        "payload": {
            "title": "全国范围代开假发票中介通道扶持计划",
            "policy_level": "国家级",
            "category": "TAX",
            "summary": "提供虚假纳税申报进项发票抵扣额度...",
            "legal_basis": "虚假规约",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 400 or resp.status_code == 422 or resp.status_code == 200
    data = resp.json()
    assert data["code"] != 200 or "violation" in str(data) or "prohibited" in str(data)


@pytest.mark.asyncio
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除，"
        "无法在写入后触发下游失败；成功链路由 tests/test_policies_operator_flows.py 覆盖，"
        "通用 Saga 逆序补偿由 tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
async def test_policy_publish_saga_rollback_on_failure():
    """Verify Saga reverse compensation deletes persisted policy when downstream fails."""
    exec_req = ScenarioExecuteRequest(
        scenario_code="OPC_POLICY_PUBLISH_PIPELINE",
        version="v1.0.0",
        inputs={
            "title": "将要在下游失败测试回滚的政府补贴政策",
            "policy_level": "省市级",
            "category": "SUBSIDY",
            "subsidy_amount_max": 20000.0,
            "summary": "用于验证微内核分布式 Saga 逆向补偿删除回滚算法的政策实体。",
            "legal_basis": "测试规约",
            "simulate_downstream_failure": True,
        },
    )

    res = await orchestration_service.execute_scenario(exec_req)
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0
    # Policy must NOT exist in service repository
    all_policies = policy_service.list_policies()
    assert not any(p.title == "将要在下游失败测试回滚的政府补贴政策" for p in all_policies)
