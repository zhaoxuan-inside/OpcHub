"""Tests for Unified Inbound Gateway Dispatcher and Scenario Routing Engine."""
from fastapi.testclient import TestClient
from src.main import app
from src.core.gateway.router import scenario_router

client = TestClient(app)


def test_list_dispatch_rules():
    """Verify that all default scenario rules are discoverable via API."""
    resp = client.get("/api/v1/dispatch/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 15
    scenarios = [r["scenario"] for r in rules]
    assert "products.list" in scenarios
    assert "products.publish" in scenarios
    assert "policies.list" in scenarios
    assert "policies.publish" in scenarios
    assert "demands.list" in scenarios
    assert "demands.publish" in scenarios
    assert "sop.templates" in scenarios
    assert "perks.list" in scenarios
    assert "perks.publish" in scenarios
    assert "forum.threads.list" in scenarios
    assert "telemetry.dashboard" in scenarios
    assert "compliance.checkpoints" in scenarios


def test_unified_dispatch_products_flow():
    """Test products list and publish via unified dispatch gateway."""
    # 1. Publish product
    pub_req = {
        "scenario": "products.publish",
        "payload": {
            "title": "SoloAudit 一键合规审计雷达",
            "tagline": "专为一人公司打造的代码与协议合规检测器",
            "description": "基于微内核 AST 静态沙箱与政策库，快速分析软件代码侵权与隐私违规红线。",
            "category": "DEV",
            "pricing_model": "SUBSCRIPTION",
            "price_cny": 129.0,
            "demo_url": "https://audit.opchub.dev",
            "author_id": "usr_maker_audit_01",
        },
        "context": {"user_id": "usr_maker_audit_01", "trace_id": "test-trace-prod-01"}
    }
    pub_resp = client.post("/api/v1/dispatch", json=pub_req)
    assert pub_resp.status_code == 200
    res_data = pub_resp.json()
    assert res_data["code"] == 200
    assert res_data["scenario"] == "products.publish"
    assert res_data["data"]["title"] == "SoloAudit 一键合规审计雷达"
    assert res_data["trace_id"] == "test-trace-prod-01"

    # 2. List products
    list_req = {
        "scenario": "products.list",
        "payload": {},
        "context": {}
    }
    list_resp = client.post("/api/v1/dispatch", json=list_req)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["code"] == 200
    titles = [p["title"] for p in list_data["data"]]
    assert "SoloAudit 一键合规审计雷达" in titles


def test_unified_dispatch_policies_and_demands():
    """Test policy retrieval and demand publishing through unified dispatch gateway."""
    # 1. Policy match
    match_req = {
        "scenario": "policies.match",
        "payload": {
            "quarterly_income": 200000.0,
            "maker_type": "INDIVIDUAL",
            "region": "杭州",
        },
        "context": {}
    }
    match_resp = client.post("/api/v1/dispatch", json=match_req)
    assert match_resp.status_code == 200
    match_data = match_resp.json()
    assert match_data["code"] == 200
    assert match_data["data"]["eligible"] is True
    assert match_data["data"]["estimated_tax_savings"] == 6000.0

    # 2. Demand publish
    dmd_req = {
        "scenario": "demands.publish",
        "payload": {
            "title": "需要独立开发者搭建跨境出海支付网关与风控路由",
            "description": "集成 Stripe、PayPal 与 LemonSqueezy，支持中国内地对公银行收结汇。",
            "budget_cny": 25000.0,
            "category": "DEV",
            "deadline_days": 15,
            "creator_id": "usr_corp_client_99",
        },
        "context": {}
    }
    dmd_resp = client.post("/api/v1/dispatch", json=dmd_req)
    assert dmd_resp.status_code == 200
    dmd_data = dmd_resp.json()
    assert dmd_data["code"] == 200
    assert dmd_data["data"]["title"] == "需要独立开发者搭建跨境出海支付网关与风控路由"


def test_dynamic_scenario_registration_without_http_code_change():
    """Verify that backend can add new business capability by only adding route rule, 0 HTTP route changes."""
    # Register dynamic calculator rule
    def custom_order_pricing_calculator(payload: dict, context: dict):
        base = payload.get("base_price", 100)
        discount = payload.get("discount_percent", 10)
        final_price = base * (1 - discount / 100.0)
        return {
            "final_price": final_price,
            "processed_by": "custom_domain_dynamic_handler",
            "user_id": context.get("user_id"),
        }

    scenario_router.register(
        "pricing.custom_calculator",
        custom_order_pricing_calculator,
        domain="finance",
        description="动态订单定价测算场景",
    )

    try:
        # Client calls unified dispatch endpoint with the newly registered scenario
        req = {
            "scenario": "pricing.custom_calculator",
            "payload": {"base_price": 500, "discount_percent": 20},
            "context": {"user_id": "usr_maker_alice"}
        }
        resp = client.post("/api/v1/dispatch", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["scenario"] == "pricing.custom_calculator"
        assert data["data"]["final_price"] == 400.0
        assert data["data"]["processed_by"] == "custom_domain_dynamic_handler"
        assert data["data"]["user_id"] == "usr_maker_alice"
    finally:
        scenario_router.unregister("pricing.custom_calculator")


def test_unknown_scenario_handling():
    """Verify clean 404 response when scenario is not in routing table."""
    req = {
        "scenario": "unregistered.fake_scenario",
        "payload": {},
        "context": {"trace_id": "trace-fake-01"}
    }
    resp = client.post("/api/v1/dispatch", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 404
    assert "Unknown scenario" in data["message"]
    assert data["trace_id"] == "trace-fake-01"
