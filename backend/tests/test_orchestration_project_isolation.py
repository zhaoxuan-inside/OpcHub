"""编排目录项目隔离测试：资产挂项目、可见性过滤、写权限边界、跨项目显式复制。

口径：编码全局唯一（运行时算子池按名注册的既有约束），隔离体现在
可见性与可操作性 —— 项目成员只见/只操作本项目资产 + 平台内置资产；
无项目上下文的平台超管保持 legacy 全局行为（存量零回归）。
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.domains.orchestration.catalog import catalog_service
from src.domains.orchestration.locks import lock_manager
from src.domains.platform.service import (
    ROLE_PROJECT_EDITOR,
    ROLE_PROJECT_VIEWER,
    ROLE_TENANT_ADMIN,
    platform_service,
)
from src.domains.user.entities import account_entity


def _client(role: str = "ADMIN", uid: str = "usr_admin_builtin") -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + create_session_token({"uid": uid, "role": role})
    return c


def _post(client: TestClient, scenario: str, payload: dict = None, context: dict = None):
    body = {"scenario": scenario, "version": "v1.0.0", "payload": payload or {}}
    if context is not None:
        body["context"] = context
    return client.post("/api/welcom/opc_world", json=body).json()


_MEMBER_DOC = {
    "uid": "usr_iso_member",
    "email": "iso_member@opchub.cn",
    "nickname": "隔离测试成员",
    "role": "MAKER",
    "is_active": True,
    "password_hash": "",
}


@pytest.fixture()
def isolated_env():
    """两个项目（A/B）：成员是 A 的查看者 + B 的编辑者；快照恢复目录状态。"""
    snap = (
        dict(catalog_service._operators),
        dict(catalog_service._subgraphs),
        dict(catalog_service._scenarios),
        dict(catalog_service._release_approvals),
    )
    platform_snap = (
        dict(platform_service._tenants),
        dict(platform_service._projects),
        dict(platform_service._roles),
        dict(platform_service._bindings),
    )
    lock_snap = dict(lock_manager._locks) if hasattr(lock_manager, "_locks") else {}
    user_created = not account_entity.adapter.get("usr_iso_member")
    if user_created:
        account_entity.adapter.create("usr_iso_member", dict(_MEMBER_DOC))

    admin_ctx = {"user_id": "usr_admin_builtin", "user_role": "ADMIN"}
    tenant = platform_service.create_tenant({"code": "iso-t", "name": "隔离租户"}, admin_ctx)
    tenant_id = tenant["tenant_id"]
    platform_service.add_tenant_member({"tenant_id": tenant_id, "user_id": "usr_iso_member"}, admin_ctx)
    pa = platform_service.create_project(
        {"tenant_id": tenant_id, "key": "pa", "name": "项目A"}, {**admin_ctx, "tenant_id": tenant_id}
    )
    pb = platform_service.create_project(
        {"tenant_id": tenant_id, "key": "pb", "name": "项目B"}, {**admin_ctx, "tenant_id": tenant_id}
    )
    platform_service.add_project_member(
        {"project_id": pa["project_id"], "user_id": "usr_iso_member", "role_id": ROLE_PROJECT_VIEWER}, admin_ctx
    )
    platform_service.add_project_member(
        {"project_id": pb["project_id"], "user_id": "usr_iso_member", "role_id": ROLE_PROJECT_EDITOR}, admin_ctx
    )
    yield {
        "tenant_id": tenant_id,
        "project_a": pa["project_id"],
        "project_b": pb["project_id"],
        "admin_ctx": admin_ctx,
        "member_a_ctx": {"user_id": "usr_iso_member", "user_role": "MAKER", "project_id": pa["project_id"]},
        "member_b_ctx": {"user_id": "usr_iso_member", "user_role": "MAKER", "project_id": pb["project_id"]},
    }

    catalog_service._operators, catalog_service._subgraphs = snap[0], snap[1]
    catalog_service._scenarios, catalog_service._release_approvals = snap[2], snap[3]
    platform_service._tenants, platform_service._projects = platform_snap[0], platform_snap[1]
    platform_service._roles, platform_service._bindings = platform_snap[2], platform_snap[3]
    lock_manager._locks.clear()
    lock_manager._locks.update(lock_snap)
    if user_created:
        account_entity.adapter.delete("usr_iso_member")


def _locked(uid: str):
    return _LockedCtx(uid)


class _LockedCtx:
    """Context manager: hold every needed lock as the given actor."""

    def __init__(self, uid: str):
        self.uid = uid

    def __enter__(self):
        self._held = []
        return self

    def acquire(self, entity_type: str, key: str):
        lock_manager.acquire(entity_type, key, self.uid)
        self._held.append((entity_type, key))
        return self

    def __exit__(self, *exc):
        for entity_type, key in self._held:
            lock_manager.release(entity_type, key, self.uid, force=True)
        return False


# ---------------------------------------------------------------------------
# 可见性隔离
# ---------------------------------------------------------------------------
def test_asset_stamped_with_project_and_filtered_for_members(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("operator", "iso_op_a")
        catalog_service.create_operator(
            {"name": "iso_op_a", "display_name": "A项目算子", "domain": "custom",
             "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
            env["admin_ctx"] | {"project_id": env["project_a"]},
        )
    # A 项目成员可见（项目资产 + 内置），B 项目成员不可见
    names_a = {o.name for o in catalog_service.list_operators(env["member_a_ctx"])}
    assert "iso_op_a" in names_a
    names_b = {o.name for o in catalog_service.list_operators(env["member_b_ctx"])}
    assert "iso_op_a" not in names_b
    assert "guard.authn" in names_b  # 内置算子全局可见
    # 详情同样隔离（不泄露存在性）
    with pytest.raises(KeyError):
        catalog_service.get_operator("iso_op_a", env["member_b_ctx"])
    assert catalog_service.get_operator("iso_op_a", env["member_a_ctx"]).name == "iso_op_a"


def test_admin_without_project_context_keeps_legacy_global_view(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("operator", "iso_op_legacy")
        catalog_service.create_operator(
            {"name": "iso_op_legacy", "display_name": "未归属算子", "domain": "custom",
             "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
            env["admin_ctx"],
        )
    # 无项目上下文的管理员：全部可见（legacy 行为）
    names = {o.name for o in catalog_service.list_operators(env["admin_ctx"])}
    assert "iso_op_legacy" in names
    # 项目成员：未归属资产只读可见
    assert "iso_op_legacy" in {o.name for o in catalog_service.list_operators(env["member_b_ctx"])}


def test_member_cannot_write_other_projects_asset(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("operator", "iso_op_b")
        catalog_service.create_operator(
            {"name": "iso_op_b", "display_name": "B项目算子", "domain": "custom",
             "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
            env["admin_ctx"] | {"project_id": env["project_b"]},
        )
    # B 项目编辑者可写自己的资产（编辑者持锁）
    lock_manager.acquire("operator", "iso_op_b", "usr_iso_member")
    try:
        catalog_service.save_operator_version(
            {"name": "iso_op_b", "changelog": "编辑者保存"},
            env["member_b_ctx"],
        )
    finally:
        lock_manager.release("operator", "iso_op_b", "usr_iso_member", force=True)
    # A 项目查看者对 B 资产不可见 → 写报不存在
    with pytest.raises(KeyError):
        catalog_service.save_operator_version({"name": "iso_op_b"}, env["member_a_ctx"])


def test_member_write_without_project_context_denied(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("operator", "iso_op_ctx")
        catalog_service.create_operator(
            {"name": "iso_op_ctx", "display_name": "上下文算子", "domain": "custom",
             "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
            env["admin_ctx"] | {"project_id": env["project_a"]},
        )
    # 项目成员缺项目上下文 → 拒绝（纵深防御；正常由网关 scope 强制先行拦截）
    with pytest.raises(PermissionError):
        catalog_service.save_operator_version(
            {"name": "iso_op_ctx"}, {"user_id": "usr_iso_member", "user_role": "MAKER"}
        )


# ---------------------------------------------------------------------------
# 跨项目显式复制（唯一复用通道）
# ---------------------------------------------------------------------------
def test_copy_asset_to_target_project(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("operator", "iso_op_src")
        catalog_service.create_operator(
            {"name": "iso_op_src", "display_name": "源算子", "domain": "custom",
             "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
            env["admin_ctx"] | {"project_id": env["project_a"]},
        )
        catalog_service.publish_operator({"name": "iso_op_src", "version": "v1.0.0"}, env["admin_ctx"] | {"project_id": env["project_a"]})
    # 成员是 A 查看者（可读源）+ B 编辑者（可写目标）→ 复制成功（同名占用时自动派生编码）
    result = catalog_service.copy_asset(
        {"asset_kind": "operator", "code": "iso_op_src", "target_project_id": env["project_b"]},
        env["member_b_ctx"],
    )
    assert result["project_id"] == env["project_b"]
    assert result["name"].startswith("iso_op_src")  # 编码全局唯一 → 副本自动派生新编码
    assert result["versions"][0]["status"] == "PUBLISHED"  # 版本机原样保留
    assert result["name"] in {o.name for o in catalog_service.list_operators(env["member_b_ctx"])}
    # 源仍在 A 项目
    assert catalog_service.get_operator("iso_op_src", env["member_a_ctx"]).project_id == env["project_a"]


def test_copy_asset_requires_target_write_permission(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("operator", "iso_op_src2")
        catalog_service.create_operator(
            {"name": "iso_op_src2", "display_name": "源算子2", "domain": "custom",
             "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
            env["admin_ctx"] | {"project_id": env["project_a"]},
        )
    # 成员对 B 是编辑者，但对未授权项目 C（新建的）无权限
    pc = platform_service.create_project(
        {"tenant_id": env["tenant_id"], "key": "pc", "name": "项目C"},
        env["admin_ctx"] | {"tenant_id": env["tenant_id"]},
    )
    with pytest.raises(PermissionError):
        catalog_service.copy_asset(
            {"asset_kind": "operator", "code": "iso_op_src2", "target_project_id": pc["project_id"]},
            env["member_b_ctx"],
        )


def test_copy_asset_code_collision_auto_derives(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("operator", "iso_op_dup")
        catalog_service.create_operator(
            {"name": "iso_op_dup", "display_name": "重复算子", "domain": "custom",
             "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
            env["admin_ctx"] | {"project_id": env["project_a"]},
        )
    # 未指定 new_code → 自动派生空闲编码（编码全局唯一）
    first = catalog_service.copy_asset(
        {"asset_kind": "operator", "code": "iso_op_dup", "target_project_id": env["project_b"]},
        env["member_b_ctx"],
    )
    assert first["name"].startswith("iso_op_dup") and first["name"] != "iso_op_dup"
    second = catalog_service.copy_asset(
        {"asset_kind": "operator", "code": "iso_op_dup", "target_project_id": env["project_b"]},
        env["member_b_ctx"],
    )
    assert second["name"] != first["name"]
    # 显式 new_code 尊重指定；占用时拒绝
    result = catalog_service.copy_asset(
        {"asset_kind": "operator", "code": "iso_op_dup", "new_code": "iso_op_dupx",
         "target_project_id": env["project_b"]},
        env["member_b_ctx"],
    )
    assert result["name"] == "iso_op_dupx"
    with pytest.raises(ValueError):
        catalog_service.copy_asset(
            {"asset_kind": "operator", "code": "iso_op_dup", "new_code": first["name"],
             "target_project_id": env["project_b"]},
            env["member_b_ctx"],
        )


# ---------------------------------------------------------------------------
# 审批单挂项目 + 按上下文过滤
# ---------------------------------------------------------------------------
def test_release_approvals_stamped_and_filtered_by_project(isolated_env):
    env = isolated_env
    with _locked("usr_admin_builtin") as lk:
        lk.acquire("scenario", "ISO_SC_A")
        catalog_service.create_scenario(
            {"code": "ISO_SC_A", "display_name": "A项目场景"},
            env["admin_ctx"] | {"project_id": env["project_a"]},
        )
        catalog_service.save_scenario_version(
            {"code": "ISO_SC_A", "version": "v1.0.0",
             "graph": {"entry_node": "n1", "exit_node": "n1",
                        "nodes": [{"id": "n1", "kind": "OPERATOR", "operator": "guard.authn"}], "edges": []}},
            env["admin_ctx"] | {"project_id": env["project_a"]},
        )
    approval = catalog_service.request_release_approval(
        {"asset_kind": "scenario", "code": "ISO_SC_A", "version": "v1.0.0"},
        env["member_a_ctx"],
    )
    assert approval["project_id"] == env["project_a"]
    # B 项目上下文看不到 A 的审批单
    rows_b = catalog_service.list_release_approvals({}, env["member_b_ctx"])["approvals"]
    assert all(r["id"] != approval["id"] for r in rows_b)
    rows_a = catalog_service.list_release_approvals({}, env["member_a_ctx"])["approvals"]
    assert any(r["id"] == approval["id"] for r in rows_a)


# ---------------------------------------------------------------------------
# dispatch 层：项目成员经网关读取目录（scope: project）
# ---------------------------------------------------------------------------
def test_dispatch_member_reads_catalog_with_project_context(isolated_env):
    env = isolated_env
    maker = _client(role="MAKER", uid="usr_iso_member")
    body = _post(maker, "orchestration.catalog.operators", context={"project_id": env["project_a"]})
    assert body["code"] == 200, body
    # 缺项目上下文 → scope_required
    body = _post(maker, "orchestration.catalog.operators")
    assert body["code"] == 403 and body["data"].get("scope_required") == "project"
    # 未登录 → 401（目录读取从"展示开放"收敛为项目成员可见）
    guest = TestClient(app)
    guest.headers.pop("Authorization", None)
    body = _post(guest, "orchestration.catalog.operators", context={"project_id": env["project_a"]})
    assert body["code"] == 401
    # 管理员无项目上下文直通（legacy 全局视角）
    body = _post(_client(), "orchestration.catalog.operators")
    assert body["code"] == 200


def test_dispatch_member_create_operator_in_project(isolated_env):
    env = isolated_env
    maker = _client(role="MAKER", uid="usr_iso_member")
    ctx = {"project_id": env["project_b"]}
    # 先取排他锁（目录写约定）
    body = _post(maker, "orchestration.locks.acquire",
                 {"entity_type": "operator", "entity_key": "iso_op_net"}, context=ctx)
    assert body["code"] == 200, body
    try:
        body = _post(maker, "orchestration.operators.create", {
            "action": "operators.create",
            "payload": {"name": "iso_op_net", "display_name": "网络算子", "domain": "custom",
                        "code": "async def action_entry(ctx):\n    return ctx", "version": "v1.0.0"},
        }, context=ctx)
        assert body["code"] == 200, body
    finally:
        _post(maker, "orchestration.locks.release",
              {"entity_type": "operator", "entity_key": "iso_op_net"}, context=ctx)
    # 资产归属项目 B
    asset = catalog_service.get_operator("iso_op_net", env["member_b_ctx"])
    assert asset.project_id == env["project_b"]
    catalog_service._operators.pop("iso_op_net", None)
