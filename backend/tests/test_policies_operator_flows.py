"""Operator-kernel v2 flow tests for the policy domain.

Every business flow is executed through the declarative scenario assets
(``config/scenarios/policies.yaml``); no legacy service business method is used
to set up the assertions.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from src.core.scenario import ensure_scenarios_loaded
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

MAKER_CONTEXT = {"user_id": "usr_policy_flow_maker", "user_role": "MAKER"}

PUBLISH_PIPELINE = "OPC_POLICY_PUBLISH_PIPELINE"
LIST_PIPELINE = "OPC_POLICY_LIST_PIPELINE"
MATCH_PIPELINE = "OPC_POLICY_MATCH_PIPELINE"


async def _run(scenario: str, inputs: dict, context: dict | None = None):
    ensure_scenarios_loaded()
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=inputs,
            context=dict(context or {}),
        )
    )


def _publish_payload(**overrides) -> dict:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "title": f"杭州市人工智能算力券补贴 {suffix}",
        "policy_level": "省市级",
        "category": "SUBSIDY",
        "subsidy_amount_max": 50000.0,
        "summary": "面向杭州市注册的超级个体提供算力券补贴与生成式AI研发扶持。",
        "eligible_conditions": ["在杭州市完成注册登记", "开展大模型与生成式AI研发"],
        "legal_basis": "杭高新发〔2026〕18号",
        "region": "杭州",
        "deadline": "2026-12-31",
        "action_text": "匹配资格",
    }
    payload.update(overrides)
    return payload


async def _publish(**overrides) -> dict:
    res = await _run(PUBLISH_PIPELINE, _publish_payload(**overrides), MAKER_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["created_policy"]


async def test_publish_scenario_persists_policy_with_gateway_identity():
    policy = await _publish()

    assert policy["id"].startswith("pol")
    assert policy["author_id"] == MAKER_CONTEXT["user_id"]
    assert policy["is_official"] is False
    assert policy["code"].startswith("POL-")
    assert policy["category"] == "SUBSIDY"

    listed = await _run(LIST_PIPELINE, {"search": policy["title"]})
    assert listed.status == "SUCCESS", listed.error_message
    ids = [item["id"] for item in listed.final_output["items"]]
    assert policy["id"] in ids
    assert listed.final_output["total"] >= 1


async def test_admin_publish_is_tagged_official():
    res = await _run(
        PUBLISH_PIPELINE,
        _publish_payload(title=f"国家级创业补贴指引 {uuid.uuid4().hex[:6]}"),
        {"user_id": "usr_policy_flow_admin", "user_role": "ADMIN"},
    )
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["created_policy"]["is_official"] is True


async def test_list_scenario_filters_by_category():
    policy = await _publish(category="RENT", title=f"园区租金减免政策 {uuid.uuid4().hex[:6]}")

    res = await _run(LIST_PIPELINE, {"category": "RENT", "page": 1, "page_size": 50})
    assert res.status == "SUCCESS", res.error_message
    items = res.final_output["items"]
    assert items, "expected at least one RENT policy"
    assert all(item["category"] == "RENT" for item in items)
    assert policy["id"] in [item["id"] for item in items]


async def test_match_scenario_calculates_tax_and_ranks_policies():
    policy = await _publish(title=f"杭州市算力券与AI研发补贴 {uuid.uuid4().hex[:6]}")

    res = await _run(
        MATCH_PIPELINE,
        {
            "quarterly_income": 100000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
            "search_query": "算力券",
            "industry_keywords": ["AI", "大模型"],
        },
    )
    assert res.status == "SUCCESS", res.error_message

    output = res.final_output
    assert output["eligible"] is True
    assert output["applicable_tax_rate"] == 0.0
    assert output["estimated_tax_savings"] == 3000.0
    assert output["is_vat_exempt"] is True

    matched_ids = [item["id"] for item in output["matched_policies"]]
    assert policy["id"] in matched_ids
    assert output["relevance_scores"][policy["id"]] >= 0.5
    # Legacy alias is still projected for existing clients.
    assert [item["id"] for item in output["matched_subsidies"]] == matched_ids


async def test_match_scenario_over_threshold_applies_standard_rate():
    res = await _run(
        MATCH_PIPELINE,
        {"quarterly_income": 400000.0, "maker_type": "OPC", "region": "杭州"},
    )
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["eligible"] is False
    assert res.final_output["applicable_tax_rate"] == 0.03
    assert res.final_output["estimated_tax_savings"] == 0.0


async def test_publish_rejects_invalid_payload():
    res = await _run(
        PUBLISH_PIPELINE,
        _publish_payload(title="x", summary="过短"),
        MAKER_CONTEXT,
    )
    assert res.status != "SUCCESS"
    assert "title" in (res.error_message or "")


async def test_publish_rejects_prohibited_content():
    res = await _run(
        PUBLISH_PIPELINE,
        _publish_payload(title="全国范围代开假发票中介通道扶持计划"),
        MAKER_CONTEXT,
    )
    assert res.status != "SUCCESS"
    assert "合规" in (res.error_message or "")


async def test_publish_requires_authenticated_identity():
    res = await _run(PUBLISH_PIPELINE, _publish_payload(), {})
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


async def test_match_rejects_negative_income():
    res = await _run(MATCH_PIPELINE, {"quarterly_income": -50000.0, "region": "杭州"})
    assert res.status != "SUCCESS"
    assert "quarterly_income" in (res.error_message or "")


def test_route_asset_maps_every_policy_scenario():
    route_file = Path(__file__).resolve().parents[1] / "config" / "routes" / "policies.yaml"
    payload = yaml.safe_load(route_file.read_text(encoding="utf-8"))
    mapping = {entry["gateway"]: entry["pipeline"] for entry in payload["routes"]}
    assert mapping == {
        "policies.list": LIST_PIPELINE,
        "policies.publish": PUBLISH_PIPELINE,
        "policies.match": MATCH_PIPELINE,
    }
