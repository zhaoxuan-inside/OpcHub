"""Tests for P06 SOP Documents microkernel DAG pipeline and Saga compensation."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.sop.service import sop_service
from src.domains.sop.models import SOPTemplate, SOPField
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


@pytest.fixture(autouse=True)
def seed_sop_templates():
    """Seed test-only SOP templates for document rendering tests."""
    sop_service._templates.clear()
    sop_service._documents.clear()
    sop_service._templates["tpl_individual_biz_reg"] = SOPTemplate(
        id="tpl_individual_biz_reg",
        stage=1,
        code="INDIVIDUAL_BIZ_REG",
        name="个体工商户设立登记标准申请书",
        category="TAX",
        description="测试用个体户设立登记模板",
        template_content="""个体工商户设立登记申请书
---------------------------------------------
登记机关：{registration_office}
主体全称：{company_name}
经营者：{founder_name}
主营范围：{biz_scope}

申报承诺：本人保证所提交材料真实、合法、有效。
---------------------------------------------
[电子印签] 状态: READY FOR SUBMISSION
核验流水号: {verify_serial}""",
        required_fields=[
            SOPField(key="registration_office", label="登记市场监管部门", default=""),
            SOPField(key="company_name", label="拟定经营主体字号", default=""),
            SOPField(key="founder_name", label="法定代表创客姓名", default=""),
            SOPField(key="biz_scope", label="主营经营范围描述", default=""),
        ],
        is_active=True,
    )
    yield
    sop_service._templates.clear()
    sop_service._documents.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_sop_document_render_dag_success(client):
    """Test standard execution of OPC_SOP_DOCUMENT_RENDER_PIPELINE via unified gateway."""
    req = {
        "scenario": "sop.document.render",
        "code_version": "v1.0.0",
        "payload": {
            "template_id": "tpl_individual_biz_reg",
            "user_id": "usr_maker_2026",
            "form_data": {
                "registration_office": "杭州市滨江区市场监督管理局",
                "company_name": "杭州极速微光智能科技有限公司",
                "founder_name": "张创客",
                "biz_scope": "软件开发、人工智能算法研究及技术咨询服务",
            },
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    doc_data = data["data"]
    assert "id" in doc_data
    assert "杭州极速微光智能科技有限公司" in doc_data["document_title"]
    assert "VER-" in doc_data["rendered_content"]
    assert doc_data["compliance_passed"] is True

    # Verify queryable in sop service
    doc_id = doc_data["id"]
    stored = sop_service.get_document(doc_id)
    assert stored is not None
    assert stored.form_data["founder_name"] == "张创客"


def test_sop_document_validate_guard_blocked_on_invalid_template(client):
    """Test guard blocks non-existent SOP template ID."""
    req = {
        "scenario": "sop.document.render",
        "code_version": "v1.0.0",
        "payload": {
            "template_id": "tpl_non_existent_404",
            "user_id": "usr_maker_2026",
            "form_data": {"company_name": "测试主体"},
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code in [200, 400, 422]
    data = resp.json()
    assert data["code"] != 200 or "not found" in str(data).lower()


def test_sop_document_moderation_guard_blocked_on_sensitive(client):
    """Test moderation guard blocks prohibited keywords in SOP form data."""
    req = {
        "scenario": "sop.document.render",
        "code_version": "v1.0.0",
        "payload": {
            "template_id": "tpl_individual_biz_reg",
            "user_id": "usr_maker_2026",
            "form_data": {
                "registration_office": "市场监管局",
                "company_name": "代开假发票服务工作室",
                "founder_name": "违规人员",
                "biz_scope": "非法经营",
            },
        },
        "context": {},
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code in [200, 400, 422]
    data = resp.json()
    assert data["code"] != 200 or "violation" in str(data).lower() or "prohibited" in str(data).lower()


@pytest.mark.asyncio
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除，"
        "无法在写入后触发下游失败；成功链路由 tests/test_sop_operator_flows.py 覆盖，"
        "通用 Saga 逆序补偿由 tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
async def test_sop_document_saga_rollback_on_downstream_failure():
    """Test that downstream failure triggers Saga reverse compensation to remove rendered document."""
    inputs = {
        "template_id": "tpl_individual_biz_reg",
        "user_id": "usr_rollback_test",
        "form_data": {
            "registration_office": "测试回滚监管局",
            "company_name": "回滚测试有限公司",
            "founder_name": "李回滚",
            "biz_scope": "软件开发",
        },
        "simulate_downstream_failure": True,
    }
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_SOP_DOCUMENT_RENDER_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    # The pipeline should converge to ROLLED_BACK
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0

    # Confirm step_persist trace succeeded in rollback
    persist_trace = next(
        (t for t in res.compensation_traces if t.get("node_id") == "step_persist"), None
    )
    assert persist_trace is not None
    assert persist_trace.get("status") == "SUCCESS"

    # Verify document was physically removed
    doc_id = persist_trace["output"].get("doc_id")
    if doc_id:
        with pytest.raises(KeyError):
            sop_service.get_document(doc_id)
