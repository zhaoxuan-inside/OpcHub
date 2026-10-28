"""Operator-kernel v2 flow tests for the compliance domain.

Every business flow is executed through the declarative scenario assets
(``config/scenarios/compliance.yaml``); the legacy service is used only to prove
it still exposes the data/query surface other modules import.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from src.core.config import settings
from src.core.entity import entity_store
from src.core.scenario import ensure_scenarios_loaded
from src.domains.compliance.entities import ENTITY_COMPLIANCE_ITEM
from src.domains.compliance.service import compliance_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

MAKER_CONTEXT = {"user_id": "usr_compliance_flow_maker", "user_role": "MAKER"}
ADMIN_CONTEXT = {
    "user_id": "usr_compliance_flow_admin",
    "user_role": "ADMIN",
    "nickname": "平台合规运营",
}

PUBLISH_PIPELINE = "OPC_COMPLIANCE_PUBLISH_PIPELINE"
LAW_LIST_PIPELINE = "OPC_COMPLIANCE_LAW_LIST_PIPELINE"
CASE_LIST_PIPELINE = "OPC_COMPLIANCE_CASE_LIST_PIPELINE"
CHECKPOINT_LIST_PIPELINE = "OPC_COMPLIANCE_CHECKPOINT_LIST_PIPELINE"
AUDIT_PIPELINE = "OPC_COMPLIANCE_AUDIT_PIPELINE"

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


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


def _law_payload(**overrides) -> dict:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "kind": "law",
        "title": f"个人信息处理告知义务指引 {suffix}",
        "summary": "处理个人信息前应以显著方式告知处理目的、方式与范围。",
        "content": "依据个人信息保护相关规定，处理者应遵循最小必要原则。",
        "level": "国家级",
        "issuer": "国家网信办",
        "law_ref": "《个人信息保护法》第十七条",
        "icon_name": "shield",
    }
    payload.update(overrides)
    return payload


def _case_payload(**overrides) -> dict:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "kind": "case",
        "title": f"未做实名认证导致支付通道冻结 {suffix}",
        "badge": "支付合规踩坑",
        "industry": "电商",
        "violation": "平台未落实商户实名制与二清隔离。",
        "consequence": "支付通道被冻结 30 天并处以罚款。",
        "lesson": "上线前完成商户实名与资金分账合规评审。",
        "badge_color": "#C0392B",
    }
    payload.update(overrides)
    return payload


def _checkpoint_docs() -> list[dict]:
    rows, _total = entity_store.list(
        ENTITY_COMPLIANCE_ITEM,
        {"filters": {"kind": "checkpoint"}, "order": "dimension_id", "limit": 0},
    )
    return rows


def _clear_checkpoints() -> None:
    adapter = entity_store.adapter(ENTITY_COMPLIANCE_ITEM)
    for row in list(adapter.all()):
        if str(row.get("kind")) == "checkpoint":
            adapter.delete(str(row["id"]))


def _restore_catalog() -> None:
    """Re-seed the shared entity store from the test-only catalog fixture."""
    from catalog_fixtures import load_catalog

    for payload in load_catalog("compliance.json").get("checkpoints", []):
        doc = dict(payload)
        doc["kind"] = "checkpoint"
        if entity_store.get(ENTITY_COMPLIANCE_ITEM, {"key": str(doc["id"])}) is None:
            entity_store.create(ENTITY_COMPLIANCE_ITEM, doc)


# ---------------------------------------------------------------------------
# 1. Publish laws / cases through the scenario asset
# ---------------------------------------------------------------------------
async def test_publish_law_binds_gateway_identity_and_is_queryable():
    payload = _law_payload()
    res = await _run(PUBLISH_PIPELINE, payload, MAKER_CONTEXT)
    assert res.status == "SUCCESS", res.error_message

    entry = res.final_output["created_entry"]
    assert entry["id"].startswith("law_")
    assert entry["kind"] == "law"
    assert entry["author_id"] == MAKER_CONTEXT["user_id"]
    assert entry["is_official"] is False
    assert entry["title"] == payload["title"]

    # Legacy service shim must read the same entity store the scenario wrote to.
    assert any(law.id == entry["id"] for law in compliance_service.get_laws())
    assert any(law.id == entry["id"] for law in compliance_service.get_dimensions())

    listed = await _run(LAW_LIST_PIPELINE, {"search": payload["title"]})
    assert listed.status == "SUCCESS", listed.error_message
    ids = [item["id"] for item in listed.final_output["response"]]
    assert entry["id"] in ids
    assert all(item["kind"] == "law" for item in listed.final_output["response"])


async def test_publish_case_uses_case_defaults_and_industry_filter():
    payload = _case_payload(industry=f"测试行业-{uuid.uuid4().hex[:6]}")
    res = await _run(PUBLISH_PIPELINE, payload, MAKER_CONTEXT)
    assert res.status == "SUCCESS", res.error_message

    entry = res.final_output["created_entry"]
    assert entry["id"].startswith("case_")
    assert entry["kind"] == "case"
    assert entry["badge"] == payload["badge"]
    assert any(case.id == entry["id"] for case in compliance_service.get_cases())

    listed = await _run(CASE_LIST_PIPELINE, {"industry": payload["industry"]})
    assert listed.status == "SUCCESS", listed.error_message
    items = listed.final_output["response"]
    assert [item["id"] for item in items] == [entry["id"]]
    assert all(item["kind"] == "case" for item in items)


async def test_admin_publish_is_tagged_official():
    res = await _run(
        PUBLISH_PIPELINE,
        _law_payload(title=f"平台官方合规指引 {uuid.uuid4().hex[:6]}"),
        ADMIN_CONTEXT,
    )
    assert res.status == "SUCCESS", res.error_message
    entry = res.final_output["created_entry"]
    assert entry["is_official"] is True
    # author is context.user_id, never the payload
    assert entry["author_id"] == ADMIN_CONTEXT["user_id"]


# ---------------------------------------------------------------------------
# 2. Publish failures
# ---------------------------------------------------------------------------
async def test_publish_rejects_unknown_kind():
    res = await _run(PUBLISH_PIPELINE, _law_payload(kind="banner"), MAKER_CONTEXT)
    assert res.status != "SUCCESS"
    assert "kind" in (res.error_message or "").lower()


async def test_publish_rejects_sensitive_keywords():
    res = await _run(
        PUBLISH_PIPELINE,
        _law_payload(
            title="跨境洗钱通道合规操作指引",
            summary="介绍如何通过境外账户完成资金转移。",
        ),
        MAKER_CONTEXT,
    )
    assert res.status != "SUCCESS"
    assert "合规" in (res.error_message or "")


async def test_publish_requires_authenticated_identity():
    res = await _run(PUBLISH_PIPELINE, _law_payload(), {})
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


async def test_publish_rejects_title_that_is_too_short():
    res = await _run(PUBLISH_PIPELINE, _law_payload(title="x"), MAKER_CONTEXT)
    assert res.status != "SUCCESS"
    assert "title" in (res.error_message or "")


# ---------------------------------------------------------------------------
# 3. Checkpoint listing + self-audit scoring
# ---------------------------------------------------------------------------
async def test_checkpoint_list_returns_seeded_checkpoints():
    res = await _run(CHECKPOINT_LIST_PIPELINE, {})
    assert res.status == "SUCCESS", res.error_message
    items = res.final_output["response"]
    assert items, "conftest must seed representative compliance checkpoints"
    assert all(item["kind"] == "checkpoint" for item in items)
    assert all(item["id"] for item in items)


async def test_audit_scores_by_weight_and_returns_ranked_risks():
    checkpoints = _checkpoint_docs()
    assert len(checkpoints) >= 3
    passed_ids = [row["id"] for row in checkpoints[:-2]]
    failed_ids = [row["id"] for row in checkpoints[-2:]]

    res = await _run(
        AUDIT_PIPELINE,
        {"passed_item_ids": passed_ids, "strict_mode": False},
    )
    assert res.status == "SUCCESS", res.error_message

    report = res.final_output["audit_report"]
    total_weight = sum(int(row["weight"]) for row in checkpoints)
    earned = sum(int(row["weight"]) for row in checkpoints if row["id"] in passed_ids)
    expected_score = int(round(earned / total_weight * 100))

    assert report["score"] == expected_score
    assert report["total_items"] == len(checkpoints)
    assert report["passed_items_count"] == len(passed_ids)
    assert report["failed_items_count"] == len(failed_ids)
    assert {item["id"] for item in report["risk_items"]} == set(failed_ids)
    assert report["remedy_suggestions"]
    assert report["legal_help_recommendation"]

    expected_grade = (
        "EXCELLENT"
        if expected_score >= settings.compliance_grade_excellent
        else "GOOD"
        if expected_score >= settings.compliance_grade_good
        else "WARNING"
        if expected_score >= settings.compliance_grade_warning
        else "CRITICAL"
    )
    assert report["grade"] == expected_grade

    risks = report["risk_items"]
    assert risks == sorted(
        risks,
        key=lambda item: (
            SEVERITY_ORDER.get(str(item.get("severity")).upper(), 0),
            int(item.get("weight") or 0),
            str(item.get("title") or ""),
        ),
        reverse=True,
    )

    dimension_total = sum(card["total_items"] for card in report["dimension_scores"])
    assert dimension_total == len(checkpoints)
    assert report["dimension_count"] == len(report["dimension_scores"])


async def test_audit_all_passed_yields_full_score():
    checkpoints = _checkpoint_docs()
    res = await _run(
        AUDIT_PIPELINE,
        {"passed_item_ids": [row["id"] for row in checkpoints], "strict_mode": False},
    )
    assert res.status == "SUCCESS", res.error_message
    report = res.final_output["audit_report"]
    assert report["score"] == 100
    assert report["grade"] == "EXCELLENT"
    assert report["failed_items_count"] == 0
    assert report["legal_help_recommendation"] is None


async def test_audit_strict_mode_blocks_critical_result():
    res = await _run(AUDIT_PIPELINE, {"passed_item_ids": [], "strict_mode": True})
    assert res.status != "SUCCESS"
    assert "CRITICAL" in (res.error_message or "")


async def test_audit_rejects_non_list_passed_item_ids():
    res = await _run(AUDIT_PIPELINE, {"passed_item_ids": "chk_01"})
    assert res.status != "SUCCESS"
    assert "passed_item_ids" in (res.error_message or "")


async def test_audit_fails_when_checklist_is_empty():
    _clear_checkpoints()
    try:
        res = await _run(AUDIT_PIPELINE, {"passed_item_ids": []})
        assert res.status != "SUCCESS"
        assert "清单为空" in (res.error_message or "")
    finally:
        _restore_catalog()


# ---------------------------------------------------------------------------
# 4. Route asset
# ---------------------------------------------------------------------------
def test_route_asset_maps_every_compliance_gateway():
    route_file = Path(__file__).resolve().parents[1] / "config" / "routes" / "compliance.yaml"
    payload = yaml.safe_load(route_file.read_text(encoding="utf-8"))
    mapping = {entry["gateway"]: entry["pipeline"] for entry in payload["routes"]}
    assert mapping == {
        "compliance.laws": LAW_LIST_PIPELINE,
        "compliance.dimensions": LAW_LIST_PIPELINE,
        "compliance.cases": CASE_LIST_PIPELINE,
        "compliance.checkpoints": CHECKPOINT_LIST_PIPELINE,
        "compliance.publish": PUBLISH_PIPELINE,
        "compliance.audit": AUDIT_PIPELINE,
    }
