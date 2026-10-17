"""Tests for RBAC/ABAC enforcement, built-in admin bootstrap, and audit archival (TASK-030)."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.config import settings
from src.core.security import create_session_token
from src.core.rbac import has_permission
from src.core.audit import audit_service


def _client(role: str = "ADMIN", uid: str = "usr_admin_builtin", must_change: bool = False) -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + create_session_token({
        "uid": uid, "role": role, "must_change_password": must_change,
    })
    return c


def _guest_client() -> TestClient:
    c = TestClient(app)
    c.headers.pop("Authorization", None)
    return c


# ---------------------------------------------------------------------------
# RBAC permission matrix (design §1.1)
# ---------------------------------------------------------------------------
def test_rbac_permission_matrix():
    assert has_permission("ADMIN", "script:upload_python") is True
    assert has_permission("ADMIN", "anything:at:all") is True          # wildcard
    assert has_permission("MAKER", "forum:post_comment") is True
    assert has_permission("MAKER", "script:upload_python") is False
    assert has_permission("MAKER", "review:audit_all") is False
    assert has_permission("GUEST", "policy:read_public") is True
    assert has_permission("GUEST", "policy:calc_ephemeral") is True
    assert has_permission("GUEST", "forum:post_comment") is False
    assert has_permission("GUEST", None) is True                        # public scenario
    assert has_permission("MAKER", "") is True                          # no permission declared


# ---------------------------------------------------------------------------
# Gateway RBAC enforcement
# ---------------------------------------------------------------------------
def test_gateway_rbac_guest_requires_login():
    c = _guest_client()
    r = c.post("/api/welcom/opc_world", json={
        "scenario": "forum.threads.publish", "version": "v1.0.0",
        "payload": {"title": "游客尝试发帖测试标题", "content": "游客未登录不应允许发帖内容", "category_code": "DEV"},
    })
    body = r.json()
    assert body["code"] == 401
    assert body["data"]["login_required"] is True


def test_gateway_rbac_maker_denied_admin_scenario():
    c = _client(role="MAKER", uid="maker_rbac_001")
    r = c.post("/api/welcom/opc_world", json={
        "scenario": "orchestration.operators.list", "version": "v1.0.0", "payload": {},
    })
    body = r.json()
    assert body["code"] == 403
    assert body["data"]["required_permission"] == "page:orchestrate"


def test_gateway_rbac_admin_allowed():
    c = _client()
    r = c.post("/api/welcom/opc_world", json={
        "scenario": "orchestration.operators.list", "version": "v1.0.0", "payload": {},
    })
    assert r.json()["code"] == 200


def test_gateway_rbac_maker_allowed_user_scenario():
    c = _client(role="MAKER", uid="maker_rbac_002")
    r = c.post("/api/welcom/opc_world", json={
        "scenario": "forum.threads.publish", "version": "v1.0.0",
        "payload": {"title": "已登录创客允许发帖标题", "content": "已登录创客发帖内容足够长度", "category_code": "DEV"},
    })
    assert r.json()["code"] == 200


# ---------------------------------------------------------------------------
# ABAC ownership enforcement (design §2)
# ---------------------------------------------------------------------------
def test_abac_owner_check_blocks_modifying_others():
    c = _client(role="MAKER", uid="maker_owner_a")
    r = c.post("/api/welcom/opc_world", json={
        "scenario": "user.profile.update", "version": "v1.0.0",
        "payload": {"user_id": "maker_owner_b", "nickname": "越权修改"},
    })
    body = r.json()
    assert body["code"] == 403
    assert body["data"]["abac_denied"] is True


def test_abac_owner_check_allows_self_and_admin():
    c_self = _client(role="MAKER", uid="maker_owner_self")
    r_self = c_self.post("/api/welcom/opc_world", json={
        "scenario": "user.profile.update", "version": "v1.0.0",
        "payload": {"user_id": "maker_owner_self", "nickname": "本人修改"},
    })
    assert r_self.json()["code"] == 200

    # ADMIN bypasses ownership check
    c_admin = _client()
    r_admin = c_admin.post("/api/welcom/opc_world", json={
        "scenario": "user.profile.update", "version": "v1.0.0",
        "payload": {"user_id": "maker_owner_other", "nickname": "管理员修改"},
    })
    assert r_admin.json()["code"] == 200


# ---------------------------------------------------------------------------
# Built-in admin bootstrap + forced credential rotation
# ---------------------------------------------------------------------------
def _login_admin() -> dict:
    c = _guest_client()
    r = c.post("/api/welcom/opc_world", json={
        "scenario": "auth.login", "version": "v1.0.0",
        "payload": {"email": settings.admin_email, "password": settings.admin_initial_password},
    })
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_builtin_admin_login_flags_password_rotation():
    data = _login_admin()
    assert data["role"] == "ADMIN"
    assert data["must_change_password"] is True


def test_builtin_admin_high_risk_blocked_until_rotation():
    token = _login_admin()["token"]
    c = _guest_client()
    c.headers["Authorization"] = f"Bearer {token}"
    r = c.post("/api/welcom/opc_world", json={
        "scenario": "orchestration.operators.list", "version": "v1.0.0", "payload": {},
    })
    body = r.json()
    assert body["code"] == 403
    assert "首次登录" in body["message"]


def test_password_rotation_clears_flag_and_unblocks():
    token = _login_admin()["token"]
    c = _guest_client()
    new_password = "OpcHub@Rotated#2026"
    r = c.post("/api/v1/auth/change-password", json={
        "token": token,
        "old_password": settings.admin_initial_password,
        "new_password": new_password,
    })
    assert r.status_code == 200, r.text
    new_token = r.json()["token"]
    assert r.json()["must_change_password"] is False

    c.headers["Authorization"] = f"Bearer {new_token}"
    r2 = c.post("/api/welcom/opc_world", json={
        "scenario": "orchestration.operators.list", "version": "v1.0.0", "payload": {},
    })
    assert r2.json()["code"] == 200

    # Restore the bootstrap credential so the suite remains deterministic
    c.post("/api/v1/auth/change-password", json={
        "token": new_token, "old_password": new_password,
        "new_password": settings.admin_initial_password,
    })


def test_change_password_rejects_wrong_old_password():
    token = _login_admin()["token"]
    c = _guest_client()
    r = c.post("/api/v1/auth/change-password", json={
        "token": token, "old_password": "wrong-old-password", "new_password": "WhateverNew#2026",
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Audit log + cold archive
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rbac_denial_is_audited_and_queryable():
    c = _guest_client()
    c.post("/api/welcom/opc_world", json={
        "scenario": "forum.threads.publish", "version": "v1.0.0",
        "payload": {"title": "审计用未登录发帖", "content": "该请求应被拒绝并产生审计记录", "category_code": "DEV"},
    })
    logs = await audit_service.list_logs(limit=100)
    assert any(l["action"].startswith("rbac.denied:forum.threads.publish") for l in logs)

    admin = _client()
    resp = admin.get("/api/v1/admin/audit/logs?limit=100")
    assert resp.status_code == 200
    assert any("rbac.denied" in row["action"] for row in resp.json())


@pytest.mark.asyncio
async def test_audit_archive_moves_expired_records():
    await audit_service.record(action="test.archivable", actor_id="tester", actor_role="ADMIN")
    audit_service._mem_logs[-1]["created_at"] = "2020-01-01T00:00:00+00:00"
    moved = await audit_service.archive_older_than(days=settings.audit_retention_days)
    assert moved >= 1
    archived = await audit_service.list_archived(limit=100)
    assert any(r["action"] == "test.archivable" for r in archived)


def test_audit_endpoints_require_admin():
    guest = _guest_client()
    assert guest.get("/api/v1/admin/audit/logs").status_code == 403
    assert guest.post("/api/v1/admin/audit/archive/run").status_code == 403
    admin = _client()
    assert admin.get("/api/v1/admin/audit/logs").status_code == 200
    assert admin.post("/api/v1/admin/audit/archive/run").status_code == 200
