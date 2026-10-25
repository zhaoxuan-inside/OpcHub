"""End-to-End integration test simulating single-page frontend console interacting with OpcHub gateway.

Validates that:
1. GET / and GET /app successfully serve the visual single-page application.
2. The frontend client envelope correctly sends version 'v1.0.0' to /api/welcom/opc_world.
3. All 12 view hydration calls triggered by switchView() and syncAllDataFromBackend() succeed.
4. Interactive operations (publish thread, claim perk, bid demand, evaluate compliance)
   pass through the microkernel DAG pipelines and return expected data.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def seed_e2e_dependencies():
    """Seed test-only perk and compliance checkpoints for interactive e2e actions."""
    from src.domains.perks.service import perk_service
    from src.domains.perks.models import PerkResponse
    from src.domains.compliance.service import compliance_service
    from src.domains.compliance.models import AuditCheckItem
    from src.domains.sop.service import sop_service
    from src.domains.sop.models import SOPTemplate, SOPField

    perk_service._perks.clear()
    perk_service._claims.clear()
    perk_service._perks["perk_aliyun_bailian"] = PerkResponse(
        id="perk_aliyun_bailian",
        name="阿里云百炼大模型专属算力包",
        provider="阿里云",
        value_cny=12000.0,
        category="AI",
        summary="测试用算力包",
        quota_remaining=150,
    )

    compliance_service._checkpoints = [
        AuditCheckItem(
            id=f"chk_{i:02d}", dimension_id=f"dim_{i}",
            title=f"测试检查点 {i}", description="d",
            severity="HIGH", weight=10, advice="a", legal_basis="l",
        )
        for i in range(1, 11)
    ]

    sop_service._templates.clear()
    sop_service._documents.clear()
    sop_service._templates["tpl_e2e_charter"] = SOPTemplate(
        id="tpl_e2e_charter",
        stage=1,
        code="E2E_CHARTER",
        name="测试章程模板",
        category="LEGAL",
        description="测试模板",
        template_content="{company_name} 章程\n唯一股东：{founder_name}\n核验流水号: {verify_serial}",
        required_fields=[
            SOPField(key="company_name", label="公司全称", default=""),
            SOPField(key="founder_name", label="股东姓名", default=""),
        ],
        is_active=True,
    )
    yield
    perk_service._perks.clear()
    perk_service._claims.clear()
    compliance_service._checkpoints = []
    sop_service._templates.clear()
    sop_service._documents.clear()


def test_frontend_console_served():
    """Verify that root GET / and /app serve the OpcHub API landing page."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "OpcHub" in resp.text
    resp_app = client.get("/app")
    assert resp_app.status_code == 200


def test_frontend_all_views_hydration_via_gateway():
    """Simulate switchView() and syncAllDataFromBackend() across all 12 views."""
    scenarios_to_test = [
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


def test_frontend_user_icon_and_auth_state_integration():
    """Verify root page serves and auth gateway scenarios function properly."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "OpcHub" in html

    # Verify auth gateway scenarios function properly
    # Register test user
    test_email = "test_icon_maker@opchub.cn"
    reg_res = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.register",
        "version": "v1.0.0",
        "payload": {
            "email": test_email,
            "password": "password123",
            "nickname": "图标测试员",
            "company_name": "极客视界"
        }
    })
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["code"] == 200
    token = reg_data["data"]["token"]
    assert token

    # Session verification
    session_res = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.session",
        "version": "v1.0.0",
        "payload": {
            "token": token
        }
    })
    assert session_res.status_code == 200
    assert session_res.json()["data"]["email"] == test_email


def test_frontend_no_fake_data_and_profile_persistence_e2e():
    """Verify newly registered users have genuine registered data (no fake placeholders) and can update profile."""
    # 1. Verify served HTML has no hardcoded placeholder identity
    html_resp = client.get("/")
    assert html_resp.status_code == 200
    html = html_resp.text
    assert 'value="赵玄"' not in html
    assert 'value="138-0010-8888"' not in html
    assert 'value="92330106MA2XXXXXX"' not in html
    assert 'value="zhaoxuan@opchub.com"' not in html
    assert 'UID: usr_2026_opc_9981' not in html
    assert 'opc_live_9981' not in html
    assert 'ROLE: SUPER INDIVIDUAL' not in html
    assert '切换管理' not in html

    # 2. Register fresh end-to-end testing user
    e2e_email = f"e2e_tester_{uuid.uuid4().hex[:6]}@example.com"
    reg_resp = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.register",
        "version": "v1.0.0",
        "payload": {
            "email": e2e_email,
            "password": "tester_secure_password_99",
            "nickname": "实测创客",
            "company_name": "杭州实测云软工作室"
        }
    })
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["code"] == 200
    reg_payload = reg_data["data"]
    test_uid = reg_payload["uid"]
    test_token = reg_payload["token"]
    assert test_uid
    # Verify UID is in standard UUID format
    assert uuid.UUID(test_uid)
    assert test_token

    # 3. Retrieve user profile via user.profile gateway scenario
    prof_resp = client.post("/api/welcom/opc_world", json={
        "scenario": "user.profile",
        "version": "v1.0.0",
        "payload": {
            "user_id": test_uid,
            "token": test_token
        }
    })
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()["data"]
    assert prof_data["uid"] == test_uid
    assert prof_data["email"] == e2e_email
    assert prof_data["nickname"] == "实测创客"
    assert prof_data["company_name"] == "杭州实测云软工作室"
    assert prof_data["credit_code"] == ""  # Zero fake random credit code
    assert prof_data["phone"] == ""        # Zero fake phone
    # 创始创客活动下新注册用户可能落在配额内获赠黑钻 VIP，档案等级须与注册响应一致
    assert prof_data["tier_name"] == reg_payload["tier_name"]

    # 4. Update profile via user.profile.update
    update_resp = client.post("/api/welcom/opc_world", json={
        "scenario": "user.profile.update",
        "version": "v1.0.0",
        "payload": {
            "user_id": test_uid,
            "token": test_token,
            "nickname": "实测创客升级版",
            "phone": "13900001111",
            "company_name": "杭州实测云软超级科技有限公司",
            "credit_code": "91330100MA2ABCDEF1"
        }
    })
    assert update_resp.status_code == 200
    upd_data = update_resp.json()["data"]
    assert upd_data["nickname"] == "实测创客升级版"
    assert upd_data["phone"] == "13900001111"
    assert upd_data["company_name"] == "杭州实测云软超级科技有限公司"
    assert upd_data["credit_code"] == "91330100MA2ABCDEF1"

    # 5. Verify persisted profile
    re_prof_resp = client.post("/api/welcom/opc_world", json={
        "scenario": "user.profile",
        "version": "v1.0.0",
        "payload": {
            "user_id": test_uid,
            "token": test_token
        }
    })
    assert re_prof_resp.status_code == 200
    persisted = re_prof_resp.json()["data"]
    assert persisted["nickname"] == "实测创客升级版"
    assert persisted["phone"] == "13900001111"
    assert persisted["company_name"] == "杭州实测云软超级科技有限公司"
    assert persisted["credit_code"] == "91330100MA2ABCDEF1"
