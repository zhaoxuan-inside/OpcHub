"""Operator-kernel v2 flow tests: platform infrastructure scenarios.

Covers the migrated ``external`` / ``framework`` / ``telemetry`` / ``home``
domains. Business flows are executed through the declarative scenario assets;
third-party gateways and framework side effects are replaced with deterministic
test doubles so no network or file activation is required.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.core.entity import entity_store
from src.core.scenario import ensure_scenarios_loaded
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

ADMIN_CONTEXT = {
    "user_id": "usr_platform_flow_admin",
    "user_role": "ADMIN",
    "nickname": "平台运维管理员",
}
MAKER_CONTEXT = {"user_id": "usr_platform_flow_maker", "user_role": "MAKER"}

HOME_PIPELINE = "OPC_HOME_OVERVIEW_PIPELINE"
OPS_PIPELINE = "OPC_OPS_DASHBOARD_PIPELINE"
RULES_PIPELINE = "OPC_GATEWAY_RULES_PIPELINE"
SCAN_PIPELINE = "OPC_FRAMEWORK_HOT_RELOAD_SCAN_PIPELINE"
STATUS_PIPELINE = "OPC_FRAMEWORK_HOT_RELOAD_STATUS_PIPELINE"


async def _run(scenario: str, inputs: dict[str, Any] | None = None, context: dict[str, Any] | None = None):
    ensure_scenarios_loaded()
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=dict(inputs or {}),
            context=dict(context or {}),
        )
    )


# ---------------------------------------------------------------------------
# Home overview
# ---------------------------------------------------------------------------
async def test_home_overview_aggregates_live_entity_counts():
    products = entity_store.count("product.item")
    threads = entity_store.count("forum.thread")
    policies = entity_store.count("policy.item")
    demands = entity_store.count("demands.item")

    perk_rows, _ = entity_store.list("perk.item", {"limit": 0})
    expected_perks = round(
        sum(float(row.get("value_cny") or 0) for row in perk_rows if row.get("status") == "PUBLISHED"),
        2,
    )

    res = await _run(HOME_PIPELINE, {"region": "浙江"})
    assert res.status == "SUCCESS", res.error_message

    overview = res.final_output["response"]
    assert overview["region"] == "浙江"
    assert overview["products_count"] == products
    assert overview["forum_threads_count"] == threads
    assert overview["matched_policies_count"] == policies
    assert overview["demands_orders_count"] == demands
    assert overview["perks_saved_cny"] == expected_perks
    assert overview["orchestrated"] is True
    assert overview["orchestrated_by"] == HOME_PIPELINE
    assert len(overview["quick_links"]) >= 7

    # The legacy adapter returns final_output directly, so flat fields must exist too.
    assert res.final_output["products_count"] == products
    assert res.final_output["forum_threads_count"] == threads

    interaction_rows, _ = entity_store.list("interaction.record", {"limit": 0})
    expected_makers = len({row.get("user_id") for row in interaction_rows if row.get("user_id")})
    assert overview["active_makers_count"] == expected_makers


async def test_home_overview_adapter_returns_zero_fallback_on_failure(monkeypatch):
    from src.core.gateway import adapters

    class _FailedResult:
        status = "FAILED"
        final_output = {}
        error_message = "pipeline exploded"

    async def _failed(_request):
        return _FailedResult()

    monkeypatch.setattr(adapters.orchestration_service, "execute_scenario", _failed)
    payload = await adapters.home_overview_adapter({}, {})

    assert payload["orchestrated"] is False
    for field in (
        "active_makers_count",
        "active_dags_count",
        "matched_policies_count",
        "demands_orders_count",
        "products_count",
        "forum_threads_count",
    ):
        assert payload[field] == 0
    assert payload["perks_saved_cny"] == 0.0
    assert payload["quick_links"] == []


# ---------------------------------------------------------------------------
# Telemetry dashboard
# ---------------------------------------------------------------------------
async def test_telemetry_dashboard_aggregates_module_counts():
    expected_counts = {
        "POLICY": entity_store.count("policy.item"),
        "SOP": entity_store.count("sop.template"),
        "FORUM": entity_store.count("forum.thread"),
        "MARKET": entity_store.count("demands.item"),
        "GALLERY": entity_store.count("product.item"),
        "PERKS": entity_store.count("perk.item"),
        "COMPLIANCE": entity_store.count("compliance.item", {"filters": {"kind": "law"}}),
    }
    interaction_rows, _ = entity_store.list("interaction.record", {"limit": 0})
    expected_makers = len({row.get("user_id") for row in interaction_rows if row.get("user_id")})

    res = await _run(OPS_PIPELINE, {"time_range": "30D", "terminal_filter": "ALL"}, ADMIN_CONTEXT)
    assert res.status == "SUCCESS", res.error_message

    dashboard = res.final_output["response"]
    assert dashboard["time_range"] == "30D"
    assert dashboard["is_live"] is True
    assert dashboard["orchestrated_by"] == OPS_PIPELINE
    assert dashboard["dau"]["value"] == str(expected_makers)
    assert dashboard["uv"]["value"] == "0"
    assert dashboard["pv"]["value"] == "0"
    assert dashboard["terminal_distribution"] == {
        "ios_percentage": 0.0,
        "android_percentage": 0.0,
        "desktop_web_percentage": 0.0,
    }
    assert len(dashboard["daily_trends"]) == 1

    heatmap_counts = {item["code"]: item["pv_count"] for item in dashboard["module_heatmaps"]}
    assert heatmap_counts == {code: count for code, count in expected_counts.items() if count > 0}


async def test_telemetry_dashboard_rejects_non_admin():
    res = await _run(OPS_PIPELINE, {}, MAKER_CONTEXT)
    assert res.status == "GUARD_REJECTED"
    assert "权限" in (res.error_message or "")


# ---------------------------------------------------------------------------
# External ecosystem (gateway calls mocked)
# ---------------------------------------------------------------------------
async def test_external_siliconflow_chat_preserves_reply_fields(monkeypatch):
    from src.infrastructure.external_gateway import siliconflow_gateway

    async def fake_chat(messages, model=None, temperature=0.3, max_tokens=1024):
        return {
            "status": "SUCCESS",
            "id": "chatcmpl_test_001",
            "model": model or "mock-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "mocked answer"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            "reply_text": "mocked answer",
        }

    monkeypatch.setattr(siliconflow_gateway, "chat_completion", fake_chat)
    res = await _run(
        "OPC_EXTERNAL_SILICONFLOW_CHAT_PIPELINE",
        {"prompt": "如何合规运营一人公司？", "model": "mock-model"},
    )
    assert res.status == "SUCCESS", res.error_message
    data = res.final_output["response"]
    assert data["status"] == "SUCCESS"
    assert data["reply_text"] == "mocked answer"
    assert data["model"] == "mock-model"
    assert data["usage"]["total_tokens"] == 3


async def test_external_payment_split_preserves_settlement_fields(monkeypatch):
    from src.infrastructure.external_gateway import payment_gateway

    async def fake_split(order_id, amount_cny, merchant_account, maker_account, channel="WECHAT"):
        return {
            "status": "SUCCESS",
            "order_id": order_id,
            "channel": "WECHAT_PAY_V3",
            "escrow_channel": "LICENSED_WECHAT_SPLIT",
            "total_amount": amount_cny,
            "maker_share": round(amount_cny * 0.95, 2),
            "platform_fee": round(amount_cny * 0.05, 2),
            "escrow_verified": True,
            "mocked": True,
        }

    monkeypatch.setattr(payment_gateway, "create_split_order", fake_split)
    res = await _run(
        "OPC_EXTERNAL_PAYMENT_SPLIT_PIPELINE",
        {"order_id": "ord_flow_001", "amount_cny": 1000.0, "channel": "WECHAT"},
    )
    assert res.status == "SUCCESS", res.error_message
    data = res.final_output["response"]
    assert data["order_id"] == "ord_flow_001"
    assert data["escrow_channel"] == "LICENSED_WECHAT_SPLIT"
    assert data["maker_share"] == 950.0
    assert data["platform_fee"] == 50.0
    assert data["escrow_verified"] is True


async def test_external_rag_forum_qa_preserves_answer_fields(monkeypatch):
    from src.core.rag import forum_rag_service

    async def fake_ask(question, top_k=3):
        return {
            "status": "SUCCESS",
            "question": question,
            "ai_answer": "先完成税务登记再开设对公户。",
            "model_used": "mock-model",
            "referenced_threads": [{"thread_id": "thr_demo"}],
            "tokens_consumed": 12,
        }

    monkeypatch.setattr(forum_rag_service, "ask_forum_rag", fake_ask)
    res = await _run(
        "OPC_EXTERNAL_RAG_FORUM_QA_PIPELINE",
        {"question": "一人公司如何报税？", "top_k": 2},
    )
    assert res.status == "SUCCESS", res.error_message
    data = res.final_output["response"]
    assert data["question"] == "一人公司如何报税？"
    assert data["ai_answer"] == "先完成税务登记再开设对公户。"
    assert data["referenced_threads"] == [{"thread_id": "thr_demo"}]


# ---------------------------------------------------------------------------
# Framework governance
# ---------------------------------------------------------------------------
async def test_framework_gateway_rules_reads_mounted_routes():
    from src.core.gateway.config_loader import GatewayConfigLoader

    GatewayConfigLoader.apply_routes_to_router()

    res = await _run(RULES_PIPELINE, {}, ADMIN_CONTEXT)
    assert res.status == "SUCCESS", res.error_message

    rules = res.final_output["response"]
    assert isinstance(rules, list) and rules
    scenarios = {rule["scenario"] for rule in rules}
    assert {"products.list", "external.siliconflow.chat", "home.overview"} <= scenarios
    assert all({"scenario", "version", "domain"} <= set(rule) for rule in rules)


async def test_framework_hot_reload_scan_returns_staged_count(monkeypatch):
    from src.core.microkernel.watcher import hot_reload_engine

    class _Change:
        def model_dump(self) -> dict[str, Any]:
            return {
                "file_path": "/tmp/example.py",
                "module_name": "example",
                "change_type": "MODIFIED",
                "status": "STAGED",
            }

    monkeypatch.setattr(hot_reload_engine, "scan_changes", lambda: [_Change()])
    monkeypatch.setattr(
        hot_reload_engine,
        "get_status",
        lambda: {"staged_changes_count": 1, "monitored_files_count": 10},
    )

    res = await _run(SCAN_PIPELINE, {}, ADMIN_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    data = res.final_output["response"]
    assert data["status"] == "ok"
    assert data["newly_detected_count"] == 1
    assert data["staged_count"] == 1
    assert data["detected_changes"][0]["status"] == "STAGED"


async def test_framework_operations_reject_non_admin():
    res = await _run(STATUS_PIPELINE, {}, MAKER_CONTEXT)
    assert res.status == "GUARD_REJECTED"
    assert "权限" in (res.error_message or "")


# ---------------------------------------------------------------------------
# Route asset mapping
# ---------------------------------------------------------------------------
def test_route_assets_map_every_platform_gateway():
    routes_dir = Path(__file__).resolve().parents[1] / "config" / "routes"

    def _mapping(name: str) -> dict[str, str]:
        payload = yaml.safe_load((routes_dir / name).read_text(encoding="utf-8"))
        return {entry["gateway"]: entry["pipeline"] for entry in payload["routes"]}

    assert _mapping("external.yaml") == {
        "external.siliconflow.chat": "OPC_EXTERNAL_SILICONFLOW_CHAT_PIPELINE",
        "external.siliconflow.summarize": "OPC_EXTERNAL_SILICONFLOW_SUMMARIZE_PIPELINE",
        "external.siliconflow.charter": "OPC_EXTERNAL_SILICONFLOW_CHARTER_PIPELINE",
        "external.payment.split": "OPC_EXTERNAL_PAYMENT_SPLIT_PIPELINE",
        "external.gov.sat_policy": "OPC_EXTERNAL_GOV_SAT_POLICY_PIPELINE",
        "external.rag.policy_search": "OPC_EXTERNAL_RAG_POLICY_SEARCH_PIPELINE",
        "external.rag.forum_qa": "OPC_EXTERNAL_RAG_FORUM_QA_PIPELINE",
    }
    assert _mapping("framework.yaml") == {
        "framework.hot-reload.status": "OPC_FRAMEWORK_HOT_RELOAD_STATUS_PIPELINE",
        "framework.hot-reload.scan": "OPC_FRAMEWORK_HOT_RELOAD_SCAN_PIPELINE",
        "framework.hot-reload.activate": "OPC_FRAMEWORK_HOT_RELOAD_ACTIVATE_PIPELINE",
        "framework.gateway.reload": "OPC_FRAMEWORK_GATEWAY_RELOAD_PIPELINE",
        "gateway.rules": RULES_PIPELINE,
    }
    assert _mapping("telemetry.yaml") == {
        "telemetry.dashboard": OPS_PIPELINE,
        "ops.dashboard": OPS_PIPELINE,
    }
    assert _mapping("home.yaml") == {"home.overview": HOME_PIPELINE}
