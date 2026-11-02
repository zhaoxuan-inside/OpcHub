"""环境维度测试：内置四环境种子 / 保护级闸门 / 配置按环境解析 / 实验环境门控 / 运行记录环境标签。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.domains.platform.service import (
    ROLE_PROJECT_EDITOR, ROLE_PROJECT_OWNER, platform_service,
)
from src.domains.configcenter.service import config_center_service
from src.domains.experiment.service import experiment_service
from src.domains.ops.service import ops_run_service
from src.domains.user.entities import account_entity

_MAKER_DOC = {"uid": "usr_env_maker", "email": "env_maker@opchub.cn", "nickname": "环境编辑者",
              "role": "MAKER", "is_active": True, "password_hash": ""}


def _client(role: str = "ADMIN", uid: str = "usr_admin_builtin") -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + create_session_token({"uid": uid, "role": role})
    return c


def _post(client, scenario, payload, action=None, context=None):
    body_payload = {"action": action, "payload": payload} if action else payload
    body = {"scenario": scenario, "version": "v1.0.0", "payload": body_payload}
    if context is not None:
        body["context"] = context
    return client.post("/api/welcom/opc_world", json=body).json()


@pytest.fixture()
def env_setup():
    snaps = (
        dict(platform_service._tenants), dict(platform_service._projects),
        dict(platform_service._roles), dict(platform_service._bindings),
        dict(platform_service._environments),
        dict(config_center_service._namespaces), dict(config_center_service._items),
        dict(experiment_service._experiments), dict(experiment_service._assignments),
        dict(ops_run_service._records), list(ops_run_service._order),
    )
    maker_created = not account_entity.adapter.get("usr_env_maker")
    if maker_created:
        account_entity.adapter.create("usr_env_maker", dict(_MAKER_DOC))
    c = _client()
    tenant = _post(c, "platform.tenants.create", {"code": "env-t", "name": "环境租户"}, action="tenants.create")["data"]
    project = _post(c, "platform.projects.create",
                    {"tenant_id": tenant["tenant_id"], "key": "env", "name": "环境项目"},
                    action="projects.create", context={"tenant_id": tenant["tenant_id"]})["data"]
    # 编辑者成员
    _post(c, "platform.tenants.members.add", {"tenant_id": tenant["tenant_id"], "user_id": "usr_env_maker"},
          action="tenants.members.add")
    _post(c, "platform.projects.members.add",
          {"project_id": project["project_id"], "user_id": "usr_env_maker", "role_id": ROLE_PROJECT_EDITOR},
          action="projects.members.add")
    yield c, project["project_id"]
    platform_service._tenants, platform_service._projects = snaps[0], snaps[1]
    platform_service._roles, platform_service._bindings = snaps[2], snaps[3]
    platform_service._environments = snaps[4]
    config_center_service._namespaces, config_center_service._items = snaps[5], snaps[6]
    experiment_service._experiments, experiment_service._assignments = snaps[7], snaps[8]
    ops_run_service._records, ops_run_service._order = snaps[9], snaps[10]
    if maker_created:
        account_entity.adapter.delete("usr_env_maker")


def test_builtin_four_environments_seeded(env_setup):
    c, project_id = env_setup
    body = _post(c, "platform.envs.list", {"project_id": project_id})
    assert body["code"] == 200
    keys = [e["key"] for e in body["data"]["environments"]]
    assert keys == ["dev", "test", "staging", "online"]
    protected = {e["key"]: e["protected"] for e in body["data"]["environments"]}
    assert protected == {"dev": False, "test": False, "staging": True, "online": True}


def test_config_resolve_differs_per_environment(env_setup):
    c, project_id = env_setup
    ctx = {"project_id": project_id}
    _post(c, "configcenter.namespaces.create", {"key": "feat", "name": "特性"}, action="namespaces.create", context=ctx)
    _post(c, "configcenter.items.create", {"namespace": "feat", "key": "greeting", "content": '"hi"', "value_type": "TEXT"},
          action="items.create", context=ctx)
    _post(c, "configcenter.items.version.save",
          {"namespace": "feat", "key": "greeting", "version": "v2.0.0", "content": '"hello-v2"'},
          action="items.version.save", context=ctx)
    # v1 全量发 dev；v2 全量发 online —— 两环境生效值不同（真实环境差异）
    _post(c, "configcenter.items.publish",
          {"namespace": "feat", "key": "greeting", "version": "v1.0.0", "env": "dev", "gray": {"percent": 100}},
          action="items.publish", context=ctx)
    _post(c, "configcenter.items.publish",
          {"namespace": "feat", "key": "greeting", "version": "v2.0.0", "env": "online", "gray": {"percent": 100}},
          action="items.publish", context=ctx)
    dev = _post(c, "configcenter.resolve", {"namespace": "feat", "key": "greeting", "user_id": "usr_x", "env": "dev"})
    online = _post(c, "configcenter.resolve", {"namespace": "feat", "key": "greeting", "user_id": "usr_x", "env": "online"})
    assert dev["data"]["value"] == '"hi"' and dev["data"]["version"] == "v1.0.0"
    assert online["data"]["value"] == '"hello-v2"' and online["data"]["version"] == "v2.0.0"


def test_protected_env_gate_editor_denied_owner_allowed(env_setup):
    c, project_id = env_setup
    ctx = {"project_id": project_id}
    _post(c, "configcenter.namespaces.create", {"key": "gate", "name": "闸门"}, action="namespaces.create", context=ctx)
    _post(c, "configcenter.items.create", {"namespace": "gate", "key": "toggle", "content": "1", "value_type": "TEXT"},
          action="items.create", context=ctx)
    _post(c, "configcenter.items.publish",
          {"namespace": "gate", "key": "toggle", "version": "v1.0.0", "env": "dev", "gray": {"percent": 100}},
          action="items.publish", context=ctx)
    _post(c, "configcenter.items.version.save",
          {"namespace": "gate", "key": "toggle", "version": "v2.0.0", "content": "2"},
          action="items.version.save", context=ctx)
    # 编辑者向线上发布 → 保护级拒绝
    editor_ctx = {"project_id": project_id, "env_key": "online"}
    maker = _client(role="MAKER", uid="usr_env_maker")
    denied = _post(maker, "configcenter.items.publish",
                   {"namespace": "gate", "key": "toggle", "version": "v2.0.0", "gray": {"percent": 100}},
                   action="items.publish", context=editor_ctx)
    assert denied["code"] == 403 and "保护级" in denied["message"]
    # 所有者向线上发布 → 放行
    owner_ctx = {**editor_ctx}
    allowed = _post(c, "configcenter.items.publish",
                    {"namespace": "gate", "key": "toggle", "version": "v2.0.0", "gray": {"percent": 100}},
                    action="items.publish", context=owner_ctx)
    assert allowed["code"] == 200
    # dev 环境编辑者可发布（非保护级）
    dev_ok = _post(maker, "configcenter.items.publish",
                   {"namespace": "gate", "key": "toggle", "version": "v2.0.0", "env": "dev", "gray": {"percent": 100}},
                   action="items.publish", context={"project_id": project_id})
    assert dev_ok["code"] == 200


def test_experiment_env_gating(env_setup):
    c, project_id = env_setup
    ctx = {"project_id": project_id}
    _post(c, "experiment.create", {
        "key": "online_only", "name": "仅线上生效",
        "variants": [{"key": "a", "weight": 1}], "env_key": "online",
    }, action="experiments.create", context=ctx)
    _post(c, "experiment.status", {"experiment_key": "online_only", "status": "RUNNING"},
          action="experiments.status", context=ctx)
    maker = _client(role="MAKER", uid="usr_env_maker")
    # dev 上下文分流 → 环境不匹配
    dev = _post(maker, "experiment.assign", {"experiment_key": "online_only"}, context={"env_key": "dev"})
    assert dev["data"]["in_experiment"] is False and dev["data"]["reason"] == "ENV_MISMATCH"
    # online 上下文 → 入实验
    online = _post(maker, "experiment.assign", {"experiment_key": "online_only"}, context={"env_key": "online"})
    assert online["data"]["in_experiment"] is True


def test_run_records_tagged_and_filtered_by_env(env_setup):
    import asyncio
    from src.domains.orchestration.service import orchestration_service
    from src.domains.orchestration.models import ScenarioExecuteRequest
    c, project_id = env_setup

    async def run(env):
        return await orchestration_service.execute_scenario(ScenarioExecuteRequest(
            scenario_code="OPC_EXPERIMENT_PIPELINE", version="v1.0.0",
            inputs={"action": "assign", "payload": {"experiment_key": "none", "user_id": "u"}},
            context={"user_id": "usr_admin_builtin", "user_role": "ADMIN", "env_key": env},
        ))
    r1 = asyncio.run(run("dev"))
    r2 = asyncio.run(run("online"))
    assert ops_run_service.get_run(r1.trace_id).env_key == "dev"
    dev_only = ops_run_service.list_runs(env_key="dev")
    assert all(r["env_key"] == "dev" for r in dev_only["runs"]) and dev_only["runs"]
