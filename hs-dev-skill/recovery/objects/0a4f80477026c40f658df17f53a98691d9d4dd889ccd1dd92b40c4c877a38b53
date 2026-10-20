"""Tests for Unified Inbound Gateway Dispatcher and Scenario Routing Engine."""
from fastapi.testclient import TestClient
from src.main import app
from src.core.gateway.router import scenario_router

client = TestClient(app)


def test_list_dispatch_rules():
    """Verify that all default scenario rules are discoverable via API."""
    resp = client.get("/api/welcom/opc_world/rules")
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

    # Also verify alias /api/welcome/opc_world/rules
    alias_resp = client.get("/api/welcome/opc_world/rules")
    assert alias_resp.status_code == 200
    assert len(alias_resp.json()) == len(rules)


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
    pub_resp = client.post("/api/welcom/opc_world", json=pub_req)
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
    list_resp = client.post("/api/welcom/opc_world", json=list_req)
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
    match_resp = client.post("/api/welcom/opc_world", json=match_req)
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
    dmd_resp = client.post("/api/welcom/opc_world", json=dmd_req)
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
        resp = client.post("/api/welcom/opc_world", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["scenario"] == "pricing.custom_calculator"
        assert data["data"]["final_price"] == 400.0
        assert data["data"]["processed_by"] == "custom_domain_dynamic_handler"
        # Identity is enforced from the session token; client-supplied context.user_id is not trusted.
        assert data["data"]["user_id"] == "usr_admin_builtin"
    finally:
        scenario_router.unregister("pricing.custom_calculator")


def test_unknown_scenario_handling():
    """Verify clean 404 response when scenario is not in routing table."""
    req = {
        "scenario": "unregistered.fake_scenario",
        "version": "v1.0.0",
        "payload": {},
        "context": {"trace_id": "trace-fake-01"}
    }
    resp = client.post("/api/welcom/opc_world", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 404
    assert "Unknown scenario" in data["message"]
    assert data["trace_id"] == "trace-fake-01"


def test_code_version_routing_and_coexistence():
    """Verify that request with specific code version executes the corresponding versioned handler."""
    # Register v1 handler
    scenario_router.register(
        scenario="demo.tax_calc",
        handler=lambda p, c: {"rate": 0.03, "version": c.get("version"), "note": "legacy v1"},
        version="v1.0.0",
        domain="finance",
        description="小微征税试算 v1.0.0",
        is_default=True,
    )
    # Register v2 handler (updated tax incentive)
    scenario_router.register(
        scenario="demo.tax_calc",
        handler=lambda p, c: {"rate": 0.01, "version": c.get("version"), "note": "new incentive v2"},
        version="v2.0.0",
        domain="finance",
        description="小微征税试算 v2.0.0 (优惠政策)",
        is_default=False,
    )

    try:
        # 1. Request v1 explicitly
        req_v1 = {
            "scenario": "demo.tax_calc",
            "version": "v1.0.0",
            "payload": {},
            "context": {}
        }
        resp_v1 = client.post("/api/welcom/opc_world", json=req_v1)
        assert resp_v1.status_code == 200
        data_v1 = resp_v1.json()
        assert data_v1["version"] == "v1.0.0"
        assert data_v1["data"]["rate"] == 0.03
        assert data_v1["data"]["note"] == "legacy v1"

        # 2. Request v2 explicitly
        req_v2 = {
            "scenario": "demo.tax_calc",
            "version": "v2.0.0",
            "payload": {},
            "context": {}
        }
        resp_v2 = client.post("/api/welcom/opc_world", json=req_v2)
        assert resp_v2.status_code == 200
        data_v2 = resp_v2.json()
        assert data_v2["version"] == "v2.0.0"
        assert data_v2["data"]["rate"] == 0.01
        assert data_v2["data"]["note"] == "new incentive v2"

        # 3. Default fallback when version is omitted in request (defaults to v1.0.0)
        req_def = {
            "scenario": "demo.tax_calc",
            "payload": {},
            "context": {}
        }
        resp_def = client.post("/api/welcom/opc_world", json=req_def)
        assert resp_def.status_code == 200
        data_def = resp_def.json()
        assert data_def["version"] == "v1.0.0"
        assert data_def["data"]["rate"] == 0.03
    finally:
        scenario_router.unregister("demo.tax_calc")


def test_config_driven_routes_and_reload():
    """Verify that routes are loaded entirely from external configuration with zero hardcoding, and reload works."""
    # Check that rules introspection returns rules loaded from yaml
    resp = client.get("/api/welcom/opc_world/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 20
    scenarios = [r["scenario"] for r in rules]
    assert "products.list" in scenarios
    assert "demands.publish" in scenarios
    assert "compliance.dimensions" in scenarios

    # Check reload endpoint
    reload_resp = client.post("/api/welcom/opc_world/reload")
    assert reload_resp.status_code == 200
    reload_data = reload_resp.json()
    assert reload_data["status"] == "ok"
    assert reload_data["reloaded_routes_count"] >= 20


def test_legacy_version_sunset_policy_rejection():
    """Verify that requests carrying sunset/EOL versions in body are rejected with clean upgrade guidance."""
    req_sunset = {
        "scenario": "products.list",
        "version": "v0.8.0",  # Declared in yaml as sunset_versions
        "payload": {},
        "context": {}
    }
    resp = client.post("/api/welcom/opc_world", json=req_sunset)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 426  # Upgrade Required
    assert "v0.8.0" in data["message"]
    assert "已停运下线" in data["message"]
    assert data["data"]["sunset"] is True
    assert data["data"]["upgrade_required"] is True
    assert data["data"]["min_supported_version"] == "v1.0.0"


def test_legacy_version_deprecation_warning():
    """Verify that requests carrying deprecated versions are serviced with deprecation warning notices."""
    req_deprecated = {
        "scenario": "products.list",
        "version": "v0.9.0",  # Declared in yaml as deprecated_versions
        "payload": {},
        "context": {}
    }
    resp = client.post("/api/welcom/opc_world", json=req_deprecated)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert "warning" in data["message"]
    assert "v0.9.0 即将终止服务" in data["message"]


def test_serve_web_console():
    """Verify that root GET / and /app serve the OpcHub visual console HTML."""
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "text/html" in resp_root.headers.get("content-type", "")
    assert "OpcHub" in resp_root.text

    resp_app = client.get("/app")
    assert resp_app.status_code == 200
    assert "text/html" in resp_app.headers.get("content-type", "")
    assert "OpcHub" in resp_app.text

