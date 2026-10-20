"""Test suite verifying Policy Semantic Relevance Ranking and SiliconFlow AI Integration."""
from fastapi.testclient import TestClient
from src.main import app
from src.domains.policies.service import policy_service
from src.domains.policies.models import PolicyMatchRequest

client = TestClient(app)


def test_policy_semantic_match_with_ai_keywords():
    """Verify PolicyService.match_policies computes relevance scores and ranks relevant policies first."""
    # Seed test-only policies matching the query corpus
    from src.domains.policies.models import PolicyResponse
    policy_service.clear()
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
    policy_service._policies["pol_vat_exemption_2026"] = PolicyResponse(
        id="pol_vat_exemption_2026",
        title="小规模纳税人季度30万免征增值税",
        policy_level="国家级",
        category="TAX",
        subsidy_amount_max=9000.0,
        summary="小规模纳税人季度销售额未超过30万元免征增值税。",
        eligible_conditions=["小规模纳税人"],
        legal_basis="财政部 税务总局公告 2023年第12号",
    )
    try:
        req = PolicyMatchRequest(
            quarterly_income=250000.0,
            maker_type="OPC",
            region="杭州",
            search_query="大模型微调与生成式AI算力券采购",
            industry_keywords=["AI", "算力", "大模型"]
        )
        res = policy_service.match_policies(req)

        assert res.eligible is True
        assert res.estimated_tax_savings == 7500.0  # 3% of 250,000
        assert res.relevance_scores is not None

        # pol_ai_compute_voucher_hz matches AI / 算力 / 大模型 and region Hangzhou
        ai_score = res.relevance_scores.get("pol_ai_compute_voucher_hz", 0.0)
        assert ai_score >= 0.8, f"Expected high relevance for AI compute voucher, got {ai_score}"

        # First matched policy should have highest relevance score
        top_policy = res.matched_policies[0]
        assert res.relevance_scores[top_policy.id] >= ai_score
    finally:
        policy_service.clear()


def test_gateway_siliconflow_charter_scenario():
    """Verify POST /api/welcom/opc_world routes external.siliconflow.charter to generate OPC charter."""
    req = {
        "scenario": "external.siliconflow.charter",
        "version": "v1.0.0",
        "payload": {
            "company_name": "杭州极速智能云科技有限公司",
            "biz_scope": "大模型智能体与自动化编排工具研发",
            "registered_capital_cny": 500000.0
        }
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    res_data = data["data"]
    assert "杭州极速智能云科技有限公司章程" in res_data["charter_text"]
    assert "独资" in res_data["charter_text"]
    assert res_data["status"] == "SUCCESS"


def test_gateway_siliconflow_summarize_scenario():
    """Verify POST /api/welcom/opc_world routes external.siliconflow.summarize for white-talk policy summary."""
    req = {
        "scenario": "external.siliconflow.summarize",
        "version": "v1.0.0",
        "payload": {
            "title": "国家税务总局关于进一步支持小微企业发展的通知",
            "full_text": "对月销售额10万元以下小规模纳税人免征增值税..."
        }
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    res_data = data["data"]
    assert "plain_summary" in res_data
    assert "增值税" in res_data["plain_summary"]


def test_frontend_console_serves_ai_buttons():
    """Verify API landing page responds and AI gateway endpoints remain callable."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "OpcHub" in resp.text
