"""平台治理底座测试：分租户 · 分用户 · 分权限 · 分项目。

覆盖：可配置 RBAC（角色/绑定/scope 授权解析）、租户与项目生命周期、成员管理
（唯一性/最后管理员保护/租户级联）、网关 scope 强制（放行/拒绝/超管直通/
scope 缺失）、用户管理（平台角色/停用/密码重置强制轮换）。
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.rbac import has_permission
from src.core.security import create_session_token
from src.core.gateway.router import scenario_router
from src.domains.platform.service import (
    ROLE_PROJECT_OWNER,
    ROLE_TENANT_ADMIN,
    ROLE_TENANT_MEMBER,
    platform_service,
)
from src.domains.user.entities import account_entity


def _client(role: str = "ADMIN", uid: str = "usr_admin_builtin", must_change: bool = False) -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + create_session_token({
        "uid": uid, "role": role, "must_change_password": must_change,
    })
    return c


def _post(client: TestClient, scenario: str, payload: dict = None, context: dict = None):
    body = {"scenario": scenario, "version": "v1.0.0", "payload": payload or {}}
    if context is not None:
        body["context"] = context
    return client.post("/api/welcom/opc_world", json=body).json()


_TEST_USER_DOC = {
    "uid": "usr_member_test",
    "email": "member_test@opchub.cn",
    "nickname": "治理测试成员",
    "role": "MAKER",
    "account_type": "MAKER",
    "company_name": "",
    "is_active": True,
    "password_hash": "",
}


@pytest.fixture()
def clean_platform():
    """Isolate platform registry mutations and the synthetic test user per test."""
    snap = (
        dict(platform_service._tenants),
        dict(platform_service._projects),
        dict(platform_service._roles),
        dict(platform_service._bindings),
    )
    route_snap = dict(scenario_router._routes)
    created = not account_entity.adapter.get("usr_member_test")
    if created:
        account_entity.adapter.create("usr_member_test", dict(_TEST_USER_DOC))
    yield platform_service
    platform_service._tenants, platform_service._projects = snap[0], snap[1]
    platform_service._roles, platform_service._bindings = snap[2], snap[3]
    scenario_router._routes.clear()
    scenario_router._routes.update(route_snap)
    if created:
        account_entity.adapter.delete("usr_member_test")


@pytest.fixture()
def scope_route():
    """Synthetic project-scoped route to exercise dispatch-level isolation (S3 lands later)."""
    async def _handler(payload, context):
        return {"project_id": context.get("project_id", ""), "user_id": context.get("user_id", "")}

    scenario_router.register(
        scenario="test.scope.project",
        handler=_handler,
        required_permission="orchestration:read",
        scope="project",
    )
    yield "test.scope.project"


# ---------------------------------------------------------------------------
# 可配置 RBAC：内置角色 / 权限点目录 / 静态矩阵不回归
# ---------------------------------------------------------------------------
def test_builtin_roles_seeded(clean_platform):
    roles = {r.code: r for r in platform_service._roles.values()}
    assert "platform_admin" in roles and roles["platform_admin"].permissions == ["*"]
    assert "tenant_admin" in roles and "project_owner" in roles and "project_viewer" in roles
    assert all(r.builtin for r in roles.values())


def test_permission_catalog_lists_all_points(clean_platform):
    c = _client()
    body = _post(c, "platform.permissions.list")
    assert body["code"] == 200
    perms = {item["permission"] for item in body["data"]["permissions"]}
    assert "orchestration:read" in perms and "platform:tenant_manage" in perms
    assert "page:ops_console" in perms


def test_legacy_matrix_unaffected_by_new_points():
    # 新权限点只经可配置绑定授予，legacy 静态矩阵保持不变
    assert has_permission("MAKER", "orchestration:read") is False
    assert has_permission("MAKER", "platform:user_manage") is False
    assert has_permission("GUEST", "orchestration:write") is False


# ---------------------------------------------------------------------------
# 租户生命周期
# ---------------------------------------------------------------------------
def test_tenant_create_by_admin_and_creator_becomes_tenant_admin(clean_platform):
    c = _client()
    body = _post(c, "platform.tenants.create", {"code": "acme", "name": "Acme 公司"})
    assert body["code"] == 200, body
    tenant_id = body["data"]["tenant_id"]
    admins = [
        b for b in platform_service._bindings.values()
        if b.tenant_id == tenant_id and b.role_id == ROLE_TENANT_ADMIN and b.status == "ACTIVE"
    ]
    assert len(admins) == 1 and admins[0].user_id == "usr_admin_builtin"


def test_tenant_create_duplicate_code_rejected(clean_platform):
    c = _client()
    assert _post(c, "platform.tenants.create", {"code": "acme", "name": "A"})["code"] == 200
    body = _post(c, "platform.tenants.create", {"code": "acme", "name": "B"})
    assert body["code"] == 400 and "已存在" in body["message"]


def test_tenant_create_requires_platform_permission(clean_platform):
    c = _client(role="MAKER", uid="usr_member_test")
    body = _post(c, "platform.tenants.create", {"code": "nope", "name": "无权租户"})
    assert body["code"] == 403


def test_tenant_list_scoped_for_plain_user(clean_platform):
    admin = _client()
    created = _post(admin, "platform.tenants.create", {"code": "mine", "name": "我的租户"})["data"]
    # 平台在册成员（非租户成员）看不到
    other = _client(role="MAKER", uid="usr_member_test")
    body = _post(other, "platform.tenants.list")
    assert all(t["tenant_id"] != created["tenant_id"] for t in body["data"]["tenants"])
    # 加入租户后可见
    _post(admin, "platform.tenants.members.add", {"tenant_id": created["tenant_id"], "user_id": "usr_member_test"})
    body = _post(other, "platform.tenants.list")
    assert any(t["tenant_id"] == created["tenant_id"] for t in body["data"]["tenants"])


# ---------------------------------------------------------------------------
# 成员管理
# ---------------------------------------------------------------------------
def _make_tenant(client: TestClient, code: str) -> str:
    return _post(client, "platform.tenants.create", {"code": code, "name": f"租户 {code}"})["data"]["tenant_id"]


def test_add_tenant_member_and_duplicate_idempotent(clean_platform):
    c = _client()
    tenant_id = _make_tenant(c, "mem")
    body = _post(c, "platform.tenants.members.add", {"tenant_id": tenant_id, "user_id": "usr_member_test"})
    assert body["code"] == 200
    again = _post(c, "platform.tenants.members.add", {"tenant_id": tenant_id, "user_id": "usr_member_test", "role_id": ROLE_TENANT_MEMBER})
    assert again["code"] == 200
    members = _post(c, "platform.tenants.members.list", {"tenant_id": tenant_id})["data"]["members"]
    assert len(members) == 2  # 平台管理员（创建人）+ 测试成员，去重不重复发放
    assert {m["user_id"] for m in members} == {"usr_admin_builtin", "usr_member_test"}


def test_remove_last_tenant_admin_rejected(clean_platform):
    c = _client()
    tenant_id = _make_tenant(c, "last")
    body = _post(c, "platform.tenants.members.set_role", {
        "tenant_id": tenant_id, "user_id": "usr_admin_builtin", "role_id": ROLE_TENANT_MEMBER,
    })
    assert body["code"] == 400 and "至少保留一名" in body["message"]


def test_remove_tenant_member_cascades_project_bindings(clean_platform):
    c = _client()
    tenant_id = _make_tenant(c, "casc")
    _post(c, "platform.tenants.members.add", {"tenant_id": tenant_id, "user_id": "usr_member_test"})
    project_id = _post(c, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "core", "name": "级联项目",
    }, context={"tenant_id": tenant_id})["data"]["project_id"]
    _post(c, "platform.projects.members.add", {"project_id": project_id, "user_id": "usr_member_test"})
    body = _post(c, "platform.tenants.members.remove", {"tenant_id": tenant_id, "user_id": "usr_member_test"})
    assert body["code"] == 200
    active = [
        b for b in platform_service._bindings.values()
        if b.user_id == "usr_member_test" and b.status == "ACTIVE"
    ]
    assert active == []


# ---------------------------------------------------------------------------
# 项目生命周期 + dispatch scope 强制
# ---------------------------------------------------------------------------
def test_project_create_by_tenant_admin_via_dispatch(clean_platform):
    admin = _client()
    tenant_id = _make_tenant(admin, "prj")
    # 测试成员加入租户并升为租户管理员
    _post(admin, "platform.tenants.members.add", {
        "tenant_id": tenant_id, "user_id": "usr_member_test", "role_id": ROLE_TENANT_ADMIN,
    })
    maker = _client(role="MAKER", uid="usr_member_test")
    body = _post(maker, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "alpha", "name": "Alpha 项目",
    }, context={"tenant_id": tenant_id})
    assert body["code"] == 200, body
    project_id = body["data"]["project_id"]
    owners = [
        b for b in platform_service._bindings.values()
        if b.project_id == project_id and b.role_id == ROLE_PROJECT_OWNER and b.status == "ACTIVE"
    ]
    assert len(owners) == 1 and owners[0].user_id == "usr_member_test"


def test_project_scope_requires_project_context(clean_platform, scope_route):
    """有租户授权但未选择活动项目 → 403 scope_required（缺上下文分支）。"""
    admin = _client()
    tenant_id = _make_tenant(admin, "ctx")
    _post(admin, "platform.tenants.members.add", {
        "tenant_id": tenant_id, "user_id": "usr_member_test", "role_id": ROLE_TENANT_ADMIN,
    })
    maker = _client(role="MAKER", uid="usr_member_test")
    body = _post(maker, scope_route)
    assert body["code"] == 403 and body["data"].get("scope_required") == "project"


def test_project_member_must_belong_to_tenant(clean_platform):
    c = _client()
    tenant_id = _make_tenant(c, "guard")
    project_id = _post(c, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "g1", "name": "守卫项目",
    }, context={"tenant_id": tenant_id})["data"]["project_id"]
    body = _post(c, "platform.projects.members.add", {"project_id": project_id, "user_id": "usr_member_test"})
    assert body["code"] == 400 and "尚未加入项目所属租户" in body["message"]


def test_dispatch_project_scope_isolation(clean_platform, scope_route):
    scenario = scope_route
    admin = _client()
    tenant_id = _make_tenant(admin, "iso")
    _post(admin, "platform.tenants.members.add", {"tenant_id": tenant_id, "user_id": "usr_member_test"})
    pa = _post(admin, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "proja", "name": "项目A",
    }, context={"tenant_id": tenant_id})["data"]["project_id"]
    pb = _post(admin, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "projb", "name": "项目B",
    }, context={"tenant_id": tenant_id})["data"]["project_id"]
    _post(admin, "platform.projects.members.add", {"project_id": pa, "user_id": "usr_member_test"})
    maker = _client(role="MAKER", uid="usr_member_test")

    # 未选项目 → 403 scope_required
    body = _post(maker, scenario)
    assert body["code"] == 403 and body["data"].get("scope_required") == "project"
    # 项目 A 成员（默认查看者，含 orchestration:read）→ 放行并注入 project_id
    body = _post(maker, scenario, context={"project_id": pa})
    assert body["code"] == 200 and body["data"]["project_id"] == pa
    # 项目 B 非成员 → 403 scope_denied（完全隔离）
    body = _post(maker, scenario, context={"project_id": pb})
    assert body["code"] == 403 and body["data"].get("scope_denied") is True
    # 平台超管无项目上下文直通
    body = _post(_client(), scenario)
    assert body["code"] == 200
    # 无任何绑定的创客 → 拒绝
    stranger = _client(role="MAKER", uid="usr_stranger_gov")
    body = _post(stranger, scenario, context={"project_id": pa})
    assert body["code"] == 403


def test_dispatch_project_scope_write_requires_write_grant(clean_platform):
    """查看者能读不能写：orchestration:write 不在查看者角色权限内。"""
    async def _handler(payload, context):
        return {"ok": True}

    scenario_router.register(
        scenario="test.scope.write", handler=_handler,
        required_permission="orchestration:write", scope="project",
    )
    admin = _client()
    tenant_id = _make_tenant(admin, "wonly")
    _post(admin, "platform.tenants.members.add", {"tenant_id": tenant_id, "user_id": "usr_member_test"})
    pid = _post(admin, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "w1", "name": "只读项目",
    }, context={"tenant_id": tenant_id})["data"]["project_id"]
    _post(admin, "platform.projects.members.add", {"project_id": pid, "user_id": "usr_member_test"})
    maker = _client(role="MAKER", uid="usr_member_test")
    body = _post(maker, "test.scope.write", context={"project_id": pid})
    assert body["code"] == 403 and body["data"].get("scope_denied") is True


# ---------------------------------------------------------------------------
# 角色管理（可配置 RBAC）
# ---------------------------------------------------------------------------
def test_custom_tenant_role_lifecycle(clean_platform):
    admin = _client()
    tenant_id = _make_tenant(admin, "role")
    _post(admin, "platform.tenants.members.add", {
        "tenant_id": tenant_id, "user_id": "usr_member_test", "role_id": ROLE_TENANT_ADMIN,
    })
    tenant_admin = _client(role="MAKER", uid="usr_member_test")
    body = _post(tenant_admin, "platform.roles.create", {
        "scope": "PROJECT", "code": "release_manager", "name": "发布管理员",
        "tenant_id": tenant_id, "permissions": ["orchestration:read", "orchestration:write"],
    })
    assert body["code"] == 200, body
    role_id = body["data"]["role_id"]
    # 勾选未知权限点 → 400
    body = _post(tenant_admin, "platform.roles.create", {
        "scope": "PROJECT", "code": "bad", "name": "坏角色",
        "tenant_id": tenant_id, "permissions": ["not:a:permission"],
    })
    assert body["code"] == 400 and "未知权限点" in body["message"]
    # 内置角色不可删除
    body = _post(tenant_admin, "platform.roles.delete", {"role_id": ROLE_PROJECT_OWNER})
    assert body["code"] == 403
    # 自定义角色可删
    body = _post(tenant_admin, "platform.roles.delete", {"role_id": role_id})
    assert body["code"] == 200


def test_custom_role_grant_enables_scoped_dispatch(clean_platform, scope_route):
    admin = _client()
    tenant_id = _make_tenant(admin, "grant")
    _post(admin, "platform.tenants.members.add", {"tenant_id": tenant_id, "user_id": "usr_member_test"})
    pid = _post(admin, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "g2", "name": "授权项目",
    }, context={"tenant_id": tenant_id})["data"]["project_id"]
    role = _post(admin, "platform.roles.create", {
        "scope": "PROJECT", "code": "reader_plus", "name": "自定义读取者",
        "tenant_id": tenant_id, "permissions": ["orchestration:read", "project:member_manage"],
    })["data"]
    body = _post(admin, "platform.projects.members.add", {
        "project_id": pid, "user_id": "usr_member_test", "role_id": role["role_id"],
    })
    assert body["code"] == 200, body
    maker = _client(role="MAKER", uid="usr_member_test")
    assert _post(maker, scope_route, context={"project_id": pid})["code"] == 200
    # 自定义角色含 project:member_manage → 可加项目成员（目标须先在册于租户）
    account_entity.adapter.create("usr_member_test2", dict(_TEST_USER_DOC, uid="usr_member_test2", email="member2_test@opchub.cn"))
    try:
        _post(admin, "platform.tenants.members.add", {"tenant_id": tenant_id, "user_id": "usr_member_test2"})
        body = _post(maker, "platform.projects.members.add", {"project_id": pid, "user_id": "usr_member_test2"})
        assert body["code"] == 200, body
    finally:
        account_entity.adapter.delete("usr_member_test2")


# ---------------------------------------------------------------------------
# 用户管理（平台级）
# ---------------------------------------------------------------------------
def test_set_user_role_and_self_demotion_guard(clean_platform):
    c = _client()
    body = _post(c, "platform.users.set_role", {"user_id": "usr_member_test", "role": "ADMIN"})
    assert body["code"] == 200 and body["data"]["role"] == "ADMIN"
    body = _post(c, "platform.users.set_role", {"user_id": "usr_member_test", "role": "SUPER"})
    assert body["code"] == 400
    # 内置管理员角色不可变更
    body = _post(c, "platform.users.set_role", {"user_id": "usr_admin_builtin", "role": "MAKER"})
    assert body["code"] == 400
    # 不能降级自己
    body = _post(c, "platform.users.set_role", {"user_id": "usr_admin_builtin", "role": "ADMIN"})
    assert body["code"] == 400
    body = _post(c, "platform.users.set_role", {"user_id": "usr_member_test", "role": "MAKER"})
    assert body["code"] == 200


def test_user_management_requires_platform_permission(clean_platform):
    maker = _client(role="MAKER", uid="usr_member_test")
    body = _post(maker, "platform.users.list")
    assert body["code"] == 403
    body = _post(maker, "platform.users.set_role", {"user_id": "usr_admin_builtin", "role": "MAKER"})
    assert body["code"] == 403


def test_reset_password_forces_rotation(clean_platform):
    c = _client()
    body = _post(c, "platform.users.reset_password", {
        "user_id": "usr_member_test", "new_password": "RotateMe2026!",
    })
    assert body["code"] == 200 and body["data"]["must_change_password"] is True
    doc = account_entity.adapter.get("usr_member_test")
    assert doc["must_change_password"] is True and doc["password_hash"]


def test_set_user_active_and_builtin_admin_guard(clean_platform):
    c = _client()
    body = _post(c, "platform.users.set_active", {"user_id": "usr_member_test", "is_active": False})
    assert body["code"] == 200 and body["data"]["is_active"] is False
    body = _post(c, "platform.users.set_active", {"user_id": "usr_admin_builtin", "is_active": False})
    assert body["code"] == 400


# ---------------------------------------------------------------------------
# 我的 scope（切换器）
# ---------------------------------------------------------------------------
def test_my_scope_shape(clean_platform):
    admin = _client()
    tenant_id = _make_tenant(admin, "scope")
    _post(admin, "platform.projects.create", {
        "tenant_id": tenant_id, "key": "s1", "name": "范围项目",
    }, context={"tenant_id": tenant_id})
    body = _post(admin, "platform.scope.my")
    assert body["code"] == 200
    data = body["data"]
    assert data["is_platform_super"] is True
    assert any(t["tenant_id"] == tenant_id and t["role"]["code"] == "tenant_admin" for t in data["tenants"])
    assert any(p["key"] == "s1" and p["role"]["code"] == "project_owner" for p in data["projects"])


def test_my_scope_requires_login():
    c = TestClient(app)
    c.headers.pop("Authorization", None)
    body = _post(c, "platform.scope.my")
    assert body["code"] == 403
