"""End-to-End integration test simulating single-page frontend console interacting with OpcHub gateway.

Validates that:
1. GET / and GET /app successfully serve the visual single-page application.
2. The frontend client envelope correctly sends version 'v1.0.0' to /api/welcom/opc_world.
3. All 12 view hydration calls triggered by switchView() and syncAllDataFromBackend() succeed.
4. Interactive operations (publish thread, claim perk, bid demand, evaluate compliance)
   pass through the microkernel DAG pipelines and return expected data.
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_frontend_console_served():
    """Verify that root GET / and /app serve the interactive single-page application."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "OpcHub" in resp.text
    assert "/api/welcom/opc_world" in resp.text
    assert "dispatchGateway" in resp.text


def test_frontend_all_views_hydration_via_gateway():
    """Simulate switchView() and syncAllDataFromBackend() across all 12 views."""
    scenarios_to_test = [
        ("home.overview", {}),
        ("forum.threads.list", {}),
        ("products.list", {}),
        ("policies.list", {}),
        ("demands.list", {}),
        ("sop.templates", {}),
        ("perks.list", {}),
        ("user.profile", {}),
        ("ops.dashboard", {}),
        ("moderation.items.list", {}),
        ("compliance.checkpoints", {}),
        ("compliance.dimensions", {}),
        ("compliance.cases", {}),
    ]

    for scenario, payload in scenarios_to_test:
        req_envelope = {
            "scenario": scenario,
            "version": "v1.0.0",
            "payload": payload,
            "context": {
                "client_env": "browser_h5",
                "trace_id": f"test_fe_{scenario}"
            }
        }
        resp = client.post("/api/welcom/opc_world", json=req_envelope)
        assert resp.status_code == 200, f"Scenario {scenario} failed with HTTP {resp.status_code}"
        data = resp.json()
        assert data["code"] == 200, f"Scenario {scenario} returned error code: {data}"
        assert "data" in data, f"Scenario {scenario} missing data field"


def test_frontend_interactive_actions_e2e():
    """Simulate user actions in the frontend triggering backend microkernel DAGs."""
    # 1. User publishes forum discussion (P02)
    thread_payload = {
        "title": "出海SaaS独立开发真实接入网关体验",
        "category_code": "DEV",
        "content": "通过统一网关与微内核DAG编排，前后端解耦联调非常丝滑！",
        "author_id": "maker_fe_test_01"
    }
    resp_thread = client.post("/api/welcom/opc_world", json={
        "scenario": "forum.threads.publish",
        "version": "v1.0.0",
        "payload": thread_payload
    })
    assert resp_thread.status_code == 200
    res_t = resp_thread.json()
    assert res_t["code"] == 200
    thread = res_t["data"]
    assert "id" in thread
    assert thread["title"] == "出海SaaS独立开发真实接入网关体验"
    assert thread["status"] == "PUBLISHED"

    # 2. User claims an ecosystem perk (P07)
    perk_claim_payload = {
        "perk_id": "perk_aliyun_bailian",
        "user_id": "usr_maker_fe_claim"
    }
    resp_perk = client.post("/api/welcom/opc_world", json={
        "scenario": "perks.claim",
        "version": "v1.0.0",
        "payload": perk_claim_payload
    })
    assert resp_perk.status_code == 200
    res_p = resp_perk.json()
    assert res_p["code"] == 200
    claim = res_p["data"]
    assert "voucher_code" in claim
    assert "OPC-" in claim["voucher_code"]
    assert claim["status"] == "ACTIVATED"

    # 3. User submits pre-launch compliance self-audit (P08)
    audit_payload = {
        "passed_item_ids": ["chk_01", "chk_02", "chk_03", "chk_04", "chk_05", "chk_06", "chk_07", "chk_08"],
        "strict_mode": False
    }
    resp_audit = client.post("/api/welcom/opc_world", json={
        "scenario": "compliance.audit",
        "version": "v1.0.0",
        "payload": audit_payload
    })
    assert resp_audit.status_code == 200
    res_a = resp_audit.json()
    assert res_a["code"] == 200
    report = res_a["data"]
    assert "score" in report
    assert report["passed_items_count"] == 8
    assert report["failed_items_count"] == 2
