"""配置中心测试：版本机 / 灰度确定性 / 白名单 / 全量提升 / 回滚 / 项目隔离 / 权限 / resolve。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.domains.configcenter.service import config_center_service
from src.domains.platform.service import platform_service


def _client(role: str = "ADMIN", uid: str = "usr_admin_builtin") -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + create_session_token({"uid": uid, "role": role})
    return c


def _post(client: TestClient, scenario: str, payload: dict, action: str | None = None, context: dict = None):
    body_payload = {"action": action, "payload": payload} if action else payload
    body = {"scenario": scenario, "version": "v1.0.0", "payload": body_payload}
    if context is not None:
        body["context"] = context
    return client.post("/api/welcom/opc_world", json=body).json()


@pytest.fixture()
def clean_config():
    snap = (dict(config_center_service._namespaces), dict(config_center_service._items))
    platform_snap = (
        dict(platform_service._tenants),
        dict(platform_service._projects),
        dict(platform_service._roles),
        dict(platform_service._bindings),
    )
    yield config_center_service
    config_center_service._namespaces, config_center_service._items = snap
    platform_service._tenants, platform_service._projects = platform_snap[0], platform_snap[1]
    platform_service._roles, platform_service._bindings = platform_snap[2], platform_snap[3]


def _make_project(client: TestClient) -> str:
    tenant = _post(client, "platform.tenants.create", {"code": "cfg-t", "name": "配置租户"},
                   action="tenants.create")["data"]
    return _post(client, "platform.projects.create",
                 {"tenant_id": tenant["tenant_id"], "key": "cfg", "name": "配置项目"},
                 action="projects.create", context={"tenant_id": tenant["tenant_id"]})["data"]["project_id"]


def test_namespace_item_version_and_gray_resolve(clean_config):
    c = _client()
    project_id = _make_project(c)
    ctx = {"project_id": project_id}
    assert _post(c, "configcenter.namespaces.create", {"key": "pricing", "name": "定价配置"},
                 action="namespaces.create", context=ctx)["code"] == 200
    assert _post(c, "configcenter.items.create", {
        "namespace": "pricing", "key": "discount_rate", "name": "折扣率",
        "content": '{"rate": 0.9}', "value_type": "JSON",
    }, action="items.create", context=ctx)["code"] == 200

    # 未发布：resolve 取不到稳定版 → NOT_FOUND（诚实）
    r = _post(c, "configcenter.resolve", {"namespace": "pricing", "key": "discount_rate", "user_id": "usr_x"})
    assert r["code"] == 200 and r["data"]["source"] == "NOT_FOUND"

    # 发布 v1.0.0 全量 → 稳定版
    body = _post(c, "configcenter.items.publish",
                 {"namespace": "pricing", "key": "discount_rate", "version": "v1.0.0", "gray": {"percent": 100}},
                 action="items.publish", context=ctx)
    assert body["code"] == 200
    r = _post(c, "configcenter.resolve", {"namespace": "pricing", "key": "discount_rate", "user_id": "usr_x"})
    assert r["data"]["source"] == "STABLE" and r["data"]["version"] == "v1.0.0"

    # v1.0.1 灰度 20% + 白名单 usr_wl → 白名单直通，普通用户大概率稳定版
    _post(c, "configcenter.items.version.save",
          {"namespace": "pricing", "key": "discount_rate", "version": "v1.0.1",
           "content": '{"rate": 0.8}', "changelog": "灰度新版"},
          action="items.version.save", context=ctx)
    body = _post(c, "configcenter.items.publish",
                 {"namespace": "pricing", "key": "discount_rate", "version": "v1.0.1",
                  "gray": {"percent": 20, "whitelist": ["usr_wl"]}},
                 action="items.publish", context=ctx)
    assert body["code"] == 200
    wl = _post(c, "configcenter.resolve", {"namespace": "pricing", "key": "discount_rate", "user_id": "usr_wl"})
    assert wl["data"]["source"] == "GRAY" and wl["data"]["version"] == "v1.0.1"
    # 白名单外用户：要么稳定要么灰度，但确定性（同一用户永远同一结果）
    r1 = _post(c, "configcenter.resolve", {"namespace": "pricing", "key": "discount_rate", "user_id": "usr_y"})
    r2 = _post(c, "configcenter.resolve", {"namespace": "pricing", "key": "discount_rate", "user_id": "usr_y"})
    assert r1["data"] == r2["data"]
    assert r1["data"]["source"] in ("STABLE", "GRAY")

    # 历史 + 回滚
    hist = _post(c, "configcenter.items.history", {"namespace": "pricing", "key": "discount_rate"}, context=ctx)
    statuses = [v["status"] for v in hist["data"]["versions"]]
    assert "PUBLISHED" in statuses
    rb = _post(c, "configcenter.items.rollback",
               {"namespace": "pricing", "key": "discount_rate", "version": "v1.0.0"},
               action="items.rollback", context=ctx)
    assert rb["code"] == 200
    r = _post(c, "configcenter.resolve", {"namespace": "pricing", "key": "discount_rate", "user_id": "usr_wl"})
    assert r["data"]["source"] == "STABLE" and r["data"]["version"] == "v1.0.0"  # 回滚清除灰度


def test_gray_100_promotes_to_stable(clean_config):
    c = _client()
    project_id = _make_project(c)
    ctx = {"project_id": project_id}
    _post(c, "configcenter.namespaces.create", {"key": "ns2", "name": "NS2"}, action="namespaces.create", context=ctx)
    _post(c, "configcenter.items.create", {"namespace": "ns2", "key": "flag", "content": '"on"'},
          action="items.create", context=ctx)
    _post(c, "configcenter.items.publish",
          {"namespace": "ns2", "key": "flag", "version": "v1.0.0", "gray": {"percent": 100}},
          action="items.publish", context=ctx)
    _post(c, "configcenter.items.version.save",
          {"namespace": "ns2", "key": "flag", "version": "v1.0.1", "content": '"off"'},
          action="items.version.save", context=ctx)
    # 先 10% 灰度，再全量 → 稳定版切到 v1.0.1 且灰度清除
    _post(c, "configcenter.items.publish",
          {"namespace": "ns2", "key": "flag", "version": "v1.0.1", "gray": {"percent": 10}},
          action="items.publish", context=ctx)
    _post(c, "configcenter.items.publish",
          {"namespace": "ns2", "key": "flag", "version": "v1.0.1", "gray": {"percent": 100}},
          action="items.publish", context=ctx)
    item = config_center_service._items["ns2:flag"]
    assert item.stable_version == "v1.0.1" and item.gray is None


def test_json_validation_and_item_key_uniqueness(clean_config):
    c = _client()
    project_id = _make_project(c)
    ctx = {"project_id": project_id}
    _post(c, "configcenter.namespaces.create", {"key": "ns3", "name": "NS3"}, action="namespaces.create", context=ctx)
    bad = _post(c, "configcenter.items.create",
                {"namespace": "ns3", "key": "bad_json", "content": "{not json}", "value_type": "JSON"},
                action="items.create", context=ctx)
    assert bad["code"] == 400 and "JSON" in bad["message"]
    assert _post(c, "configcenter.items.create", {"namespace": "ns3", "key": "plain", "content": "hello", "value_type": "TEXT"},
                 action="items.create", context=ctx)["code"] == 200
    dup = _post(c, "configcenter.items.create", {"namespace": "ns3", "key": "plain", "content": "x", "value_type": "TEXT"},
                action="items.create", context=ctx)
    assert dup["code"] == 400 and "已存在" in dup["message"]


def test_configcenter_isolation_and_permissions(clean_config):
    c = _client()
    pa = _make_project(c)
    tenant_b = _post(c, "platform.tenants.create", {"code": "cfg-t2", "name": "配置租户二"},
                     action="tenants.create")["data"]
    pb = _post(c, "platform.projects.create",
               {"tenant_id": tenant_b["tenant_id"], "key": "other", "name": "另一项目"},
               action="projects.create", context={"tenant_id": tenant_b["tenant_id"]})["data"]["project_id"]
    _post(c, "configcenter.namespaces.create", {"key": "iso_ns", "name": "隔离NS"},
          action="namespaces.create", context={"project_id": pa})

    # 非 pa 成员：清单不含，历史按不存在处理
    r = _post(c, "configcenter.namespaces.list", {}, context={"project_id": pb})
    assert all(n["key"] != "iso_ns" for n in r["data"]["namespaces"])
    # 无 configcenter:write 的 MAKER 创建被拒
    maker = _client(role="MAKER", uid="usr_cfg_maker")
    body = _post(maker, "configcenter.namespaces.create", {"key": "nope", "name": "无权"},
                 action="namespaces.create", context={"project_id": pa})
    assert body["code"] == 403

    # resolve 数据面对登录用户开放（宿主运行时调用）；未登录拒（服务 _actor）
    _post(c, "configcenter.items.create", {"namespace": "iso_ns", "key": "flag", "content": "1", "value_type": "TEXT"},
          action="items.create", context={"project_id": pa})
    _post(c, "configcenter.items.publish",
          {"namespace": "iso_ns", "key": "flag", "version": "v1.0.0", "gray": {"percent": 100}},
          action="items.publish", context={"project_id": pa})
    r = _post(maker, "configcenter.resolve", {"namespace": "iso_ns", "key": "flag", "user_id": "usr_cfg_maker"})
    assert r["code"] == 200 and r["data"]["value"] == "1"
    guest = TestClient(app)
    guest.headers.pop("Authorization", None)
    r = _post(guest, "configcenter.resolve", {"namespace": "iso_ns", "key": "flag", "user_id": "anon"})
    assert r["code"] == 403
