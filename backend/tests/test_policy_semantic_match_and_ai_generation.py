"""Test suite verifying Policy Semantic Relevance Ranking and SiliconFlow AI Integration."""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.domains.policies.service import policy_service
from src.domains.policies.models import PolicyMatchRequest

client = TestClient(app)


def test_policy_semantic_match_with_ai_keywords():
    """Verify PolicyService.match_policies computes relevance scores and ranks relevant policies first."""
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
    """Verify web console HTML serves 智能起草 and 白话提炼 actions."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "智能起草" in resp.text
    assert "白话提炼" in resp.text
    assert "generateCharterWithAI" in resp.text
    assert "summarizePolicyWithAI" in resp.text
