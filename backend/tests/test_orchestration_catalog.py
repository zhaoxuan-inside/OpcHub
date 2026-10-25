"""Tests for the three-tier orchestration catalog (算子/子图/场景) with exclusive locks.

覆盖：
* 排他锁生命周期：获取 / 冲突（含锁定人提示）/ 心跳续期 / 过期接管 / 强制释放
* 读展示完全开放（无凭证可读），写操作需要 page:orchestrate 且持锁
* 算子生命周期：创建（沙箱校验）→ 草稿版本 → 发布进运行时算子池 → 删除（引用保护）
* 子图生命周期：创建 → 编排算子 → 发布编译（无环 / 唯一入口 / 唯一出口校验）
* 场景生命周期：创建 → 算子+子图混合编排 → 发布（子图内联展开 + 物化 ACTIVE DAG）
  → 新版本发布取代旧版 → 执行走最新版本 → 删除清理运行时配置
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.core.microkernel.registry import registry
from src.core.microkernel.dispatcher import dispatcher
from src.domains.orchestration.catalog import catalog_service
from src.domains.orchestration.locks import lock_manager
from src.domains.orchestration.service import orchestration_service

client = TestClient(app)

ADMIN_UID = "admin_catalog_001"
MAKER_UID = "maker_catalog_002"
ADMIN2_UID = "admin_catalog_003"

VALID_SCRIPT = '''
async def action_entry(inputs, context):
    return {"doubled": inputs.get("x", 0) * 2}
'''

FORBIDDEN_SCRIPT = '''
import os

async def action_entry(inputs, context):
    return {"leak": os.environ}
'''


def _token(uid: str, role: str) -> str:
    return create_session_token({"uid": uid, "role": role, "nickname": f"测试{role}"})


def _admin_token() -> str:
    return _token(ADMIN_UID, "ADMIN")


def _admin2_token() -> str:
    return _token(ADMIN2_UID, "ADMIN")


def _maker_token() -> str:
    return _token(MAKER_UID, "MAKER")


def gw(scenario: str, payload: dict, token: str = None) -> dict:
    body = {
        "scenario": scenario,
        "version": "v1.0.0",
        "payload": payload,
        "context": {},
    }
    # conftest 的 TestClient 默认带内置管理员 Bearer 头；显式 token 走请求体
    # 顶层字段（端点优先级最高），未登录场景用空头覆盖默认凭证。
    if token:
        body["token"] = token
    resp = client.post(
        "/api/welcom/opc_world",
        json=body,
        headers={"Authorization": ""} if not token else {},
    )
    assert resp.status_code == 200
    return resp.json()


def ok(scenario: str, payload: dict, token: str = None) -> dict:
    res = gw(scenario, payload, token)
    assert res["code"] == 200, res.get("message")
    return res["data"]


def fail(scenario: str, payload: dict, token: str = None) -> dict:
    res = gw(scenario, payload, token)
    assert res["code"] >= 400, res
    return res


@pytest.fixture(autouse=True)
def clean_catalog():
    """Isolate catalog/lock/pool state between tests."""
    yield
    for lk in lock_manager.list_active():
        lock_manager.release(lk.entity_type, lk.entity_key, lk.holder_id, force=True)
    for name in list(catalog_service._operators.keys()):
        if catalog_service._operators[name].current_version:
            from src.core.microkernel.script_ingestion import script_ingestion_service

            script_ingestion_service.unregister(name, ADMIN_UID)
        catalog_service._operators.pop(name)
    catalog_service._subgraphs.clear()
    codes = list(catalog_service._scenarios.keys())
    for cfg in list(orchestration_service.list_dag_configs()):
        if cfg.scenario_code in codes:
            orchestration_service.delete_dag_config(cfg.scenario_code, cfg.version)
    catalog_service._scenarios.clear()


def acquire_lock(entity_type: str, entity_key: str, token: str = None, **extra) -> dict:
    return ok(
        "orchestration.locks.acquire",
        {"entity_type": entity_type, "entity_key": entity_key, **extra},
        token or _admin_token(),
    )


# ======================================================================
# 1. 排他锁
# ======================================================================
def test_lock_acquire_conflict_shows_holder():
    """第二人获取同一资产锁被拒，错误信息展示锁定人；原持有人续期成功。"""
    lock = acquire_lock("scenario", "OPC_LOCK_DEMO", _admin_token())
    assert lock["holder_id"] == ADMIN_UID
    assert lock["holder_name"]  # 展示锁定人

    res = fail("orchestration.locks.acquire", {"entity_type": "scenario", "entity_key": "OPC_LOCK_DEMO"}, _admin2_token())
    assert res["code"] == 403
    assert "锁定" in res["message"]
    assert lock["holder_name"] in res["message"]

    # 持有人心跳续期是幂等的
    renewed = acquire_lock("scenario", "OPC_LOCK_DEMO", _admin_token())
    assert renewed["holder_id"] == ADMIN_UID


def test_lock_release_rules_and_force():
    """非持有人释放被拒；管理员 force 释放成功。"""
    acquire_lock("operator", "dynamic.lockdemo", _admin_token())
    res = fail(
        "orchestration.locks.release",
        {"entity_type": "operator", "entity_key": "dynamic.lockdemo"},
        _admin2_token(),
    )
    assert res["code"] == 403

    released = ok(
        "orchestration.locks.release",
        {"entity_type": "operator", "entity_key": "dynamic.lockdemo", "force": True},
        _admin2_token(),
    )
    assert released["released"] is True
    assert lock_manager.status("operator", "dynamic.lockdemo") is None


def test_lock_expiry_takeover():
    """锁过期后其他协作者可直接接管。"""
    lock_manager.acquire("subgraph", "SG_EXPIRE", ADMIN_UID, "管理员甲", ttl_seconds=60)
    stale = lock_manager.status("subgraph", "SG_EXPIRE")
    stale.expires_at = "2000-01-01T00:00:00+00:00"  # 直接老化，模拟 TTL 流逝
    taken = acquire_lock("subgraph", "SG_EXPIRE", _admin2_token())
    assert taken["holder_id"] == ADMIN2_UID


def test_locks_dashboard_public():
    """锁看板展示开放，且能看到锁定人。"""
    acquire_lock("scenario", "OPC_LOCK_BOARD", _admin_token())
    res = ok("orchestration.catalog.locks", {})
    locks = res["locks"]
    match = [lk for lk in locks if lk["entity_key"] == "OPC_LOCK_BOARD"]
    assert match and match[0]["holder_id"] == ADMIN_UID


# ======================================================================
# 2. 读开放 / 写权限
# ======================================================================
def test_catalog_reads_public():
    """四类目录读取接口无凭证即可访问（展示无限制）。"""
    for scenario in (
        "orchestration.catalog.operators",
        "orchestration.catalog.subgraphs",
        "orchestration.catalog.scenarios",
        "orchestration.catalog.locks",
    ):
        res = gw(scenario, {})
        assert res["code"] == 200, (scenario, res.get("message"))


def test_catalog_writes_need_permission_and_lock():
    """未登录 401；普通创客 403；管理员未持锁时被锁校验拒绝。"""
    payload = {"action": "operators.create", "payload": {"name": "dynamic.perm", "code": VALID_SCRIPT}}

    res = fail("orchestration.operators.create", payload)
    assert res["code"] == 401

    res = fail("orchestration.operators.create", payload, _maker_token())
    assert res["code"] == 403

    res = fail("orchestration.operators.create", payload, _admin_token())
    assert res["code"] == 403
    assert "排他锁" in res["message"] or "锁定" in res["message"]


# ======================================================================
# 3. 算子生命周期
# ======================================================================
def test_operator_create_publish_version_delete():
    """创建→发布→新版本→再发布→删除，全程需持锁，发布后进入运行时算子池。"""
    acquire_lock("operator", "dynamic.lifecycles", _admin_token())

    asset = ok(
        "orchestration.operators.create",
        {
            "action": "operators.create",
            "payload": {
                "name": "dynamic.lifecycles",
                "display_name": "倍增算子",
                "description": "把 x 翻倍",
                "code": VALID_SCRIPT,
            },
        },
        _admin_token(),
    )
    assert asset["source"] == "custom"
    assert asset["versions"][0]["status"] == "DRAFT"
    assert registry.get("dynamic.lifecycles") is None  # 草稿未注册

    published = ok(
        "orchestration.operators.publish",
        {"action": "operators.publish", "payload": {"name": "dynamic.lifecycles", "version": "v1.0.0"}},
        _admin_token(),
    )
    assert published["current_version"] == "v1.0.0"
    assert registry.get("dynamic.lifecycles") is not None  # 已注册进算子池
    handler = registry.get("dynamic.lifecycles")
    out = asyncio.run(handler({"x": 21}, {}))
    assert out["doubled"] == 42

    # 已发布版本不可直接编辑
    res = fail(
        "orchestration.operators.version.save",
        {
            "action": "operators.version.save",
            "payload": {"name": "dynamic.lifecycles", "version": "v1.0.0", "definition": {"code": VALID_SCRIPT}},
        },
        _admin_token(),
    )
    assert res["code"] == 400

    # 新草稿（自动版本号）→ 发布 → 旧版本 SUPERSEDED
    updated = ok(
        "orchestration.operators.version.save",
        {
            "action": "operators.version.save",
            "payload": {
                "name": "dynamic.lifecycles",
                "definition": {"code": "async def action_entry(inputs, context):\n    return {'tripled': inputs.get('x', 0) * 3}\n"},
                "changelog": "升级为三倍",
            },
        },
        _admin_token(),
    )
    assert updated["versions"][-1]["version"] == "v1.0.1"
    ok(
        "orchestration.operators.publish",
        {"action": "operators.publish", "payload": {"name": "dynamic.lifecycles", "version": "v1.0.1"}},
        _admin_token(),
    )
    detail = ok("orchestration.catalog.operator", {"name": "dynamic.lifecycles"})
    statuses = {v["version"]: v["status"] for v in detail["versions"]}
    assert statuses["v1.0.0"] == "SUPERSEDED"
    assert statuses["v1.0.1"] == "PUBLISHED"
    assert detail["current_version"] == "v1.0.1"

    # 删除成功（未被引用）
    deleted = ok(
        "orchestration.operators.delete",
        {"action": "operators.delete", "payload": {"name": "dynamic.lifecycles"}},
        _admin_token(),
    )
    assert deleted["deleted"] is True
    assert registry.get("dynamic.lifecycles") is None
    names = [o["name"] for o in ok("orchestration.catalog.operators", {})["operators"]]
    assert "dynamic.lifecycles" not in names


def test_operator_create_sandbox_rejects_forbidden_script():
    """危险脚本在创建时即被四防火墙沙箱拒绝。"""
    acquire_lock("operator", "dynamic.evil", _admin_token())
    res = fail(
        "orchestration.operators.create",
        {"action": "operators.create", "payload": {"name": "dynamic.evil", "code": FORBIDDEN_SCRIPT}},
        _admin_token(),
    )
    assert res["code"] == 400
    assert "沙箱" in res["message"]


def test_operator_builtin_not_deletable():
    """内置算子（代码注册）不可删除。"""
    acquire_lock("operator", "gateway_ingress", _admin_token())
    res = fail(
        "orchestration.operators.delete",
        {"action": "operators.delete", "payload": {"name": "gateway_ingress"}},
        _admin_token(),
    )
    assert res["code"] == 400
    assert "内置" in res["message"]


# ======================================================================
# 4. 子图生命周期
# ======================================================================
def _create_subgraph(code: str, token: str = None) -> dict:
    acquire_lock("subgraph", code, token or _admin_token())
    return ok(
        "orchestration.subgraphs.create",
        {"action": "subgraphs.create", "payload": {"code": code, "display_name": "税务校验子图"}},
        token or _admin_token(),
    )


def _tax_guard_graph() -> dict:
    return {
        "entry_node": "n_auth",
        "exit_node": "n_tax",
        "nodes": [
            {"id": "n_auth", "operator": "auth_guard", "type": "GUARD"},
            {"id": "n_tax", "operator": "invoice_tax_calc", "type": "BIZ"},
        ],
        "edges": [{"from_node": "n_auth", "to_node": "n_tax"}],
    }


def test_subgraph_create_compose_publish():
    asset = _create_subgraph("SG_TAX_GUARD")
    assert asset["versions"][0]["status"] == "DRAFT"

    saved = ok(
        "orchestration.subgraphs.version.save",
        {"action": "subgraphs.version.save", "payload": {"code": "SG_TAX_GUARD", "graph": _tax_guard_graph()}},
        _admin_token(),
    )
    assert saved["versions"][0]["graph"]["nodes"][0]["operator"] == "auth_guard"

    published = ok(
        "orchestration.subgraphs.publish",
        {"action": "subgraphs.publish", "payload": {"code": "SG_TAX_GUARD", "version": "v1.0.0"}},
        _admin_token(),
    )
    compiled = published["versions"][0]["compiled"]
    assert [n["action_handler"] for n in compiled["nodes"]] == ["auth_guard", "invoice_tax_calc"]
    assert published["current_version"] == "v1.0.0"

    # 子图引用未发布算子时拒绝发布
    acquire_lock("operator", "dynamic.unpub", _admin_token())
    ok(
        "orchestration.operators.create",
        {"action": "operators.create", "payload": {"name": "dynamic.unpub", "code": VALID_SCRIPT}},
        _admin_token(),
    )
    acquire_lock("subgraph", "SG_USE_UNPUB", _admin_token())
    ok(
        "orchestration.subgraphs.create",
        {"action": "subgraphs.create", "payload": {"code": "SG_USE_UNPUB"}},
        _admin_token(),
    )
    ok(
        "orchestration.subgraphs.version.save",
        {
            "action": "subgraphs.version.save",
            "payload": {
                "code": "SG_USE_UNPUB",
                "graph": {
                    "entry_node": "a",
                    "exit_node": "b",
                    "nodes": [
                        {"id": "a", "operator": "auth_guard"},
                        {"id": "b", "operator": "dynamic.unpub"},
                    ],
                    "edges": [{"from_node": "a", "to_node": "b"}],
                },
            },
        },
        _admin_token(),
    )
    res = fail(
        "orchestration.subgraphs.publish",
        {"action": "subgraphs.publish", "payload": {"code": "SG_USE_UNPUB", "version": "v1.0.0"}},
        _admin_token(),
    )
    assert res["code"] == 400
    assert "尚未发布" in res["message"]


def test_subgraph_publish_rejects_cycle_and_multi_entry():
    _create_subgraph("SG_BAD_CYCLE")
    ok(
        "orchestration.subgraphs.version.save",
        {
            "action": "subgraphs.version.save",
            "payload": {
                "code": "SG_BAD_CYCLE",
                "graph": {
                    "entry_node": "a",
                    "exit_node": "b",
                    "nodes": [
                        {"id": "a", "operator": "auth_guard"},
                        {"id": "b", "operator": "invoice_tax_calc"},
                    ],
                    "edges": [{"from_node": "a", "to_node": "b"}, {"from_node": "b", "to_node": "a"}],
                },
            },
        },
        _admin_token(),
    )
    res = fail(
        "orchestration.subgraphs.publish",
        {"action": "subgraphs.publish", "payload": {"code": "SG_BAD_CYCLE", "version": "v1.0.0"}},
        _admin_token(),
    )
    assert res["code"] == 400

    _create_subgraph("SG_MULTI_SRC")
    ok(
        "orchestration.subgraphs.version.save",
        {
            "action": "subgraphs.version.save",
            "payload": {
                "code": "SG_MULTI_SRC",
                "graph": {
                    "entry_node": "a",
                    "exit_node": "c",
                    "nodes": [
                        {"id": "a", "operator": "auth_guard"},
                        {"id": "b", "operator": "auth_guard"},
                        {"id": "c", "operator": "invoice_tax_calc"},
                    ],
                    "edges": [{"from_node": "b", "to_node": "c"}],
                },
            },
        },
        _admin_token(),
    )
    res = fail(
        "orchestration.subgraphs.publish",
        {"action": "subgraphs.publish", "payload": {"code": "SG_MULTI_SRC", "version": "v1.0.0"}},
        _admin_token(),
    )
    assert res["code"] == 400
    assert "入口" in res["message"]


# ======================================================================
# 5. 场景生命周期（算子 + 子图混合编排 → 编译部署 → 执行 → 删除）
# ======================================================================
def _create_scenario(code: str, token: str = None) -> dict:
    acquire_lock("scenario", code, token or _admin_token())
    return ok(
        "orchestration.scenarios.create",
        {"action": "scenarios.create", "payload": {"code": code, "display_name": "综合申报场景"}},
        token or _admin_token(),
    )


def _mixed_graph() -> dict:
    return {
        "entry_node": "ingress",
        "exit_node": "audit",
        "enable_saga_compensation": False,
        "nodes": [
            {"id": "ingress", "kind": "OPERATOR", "operator": "gateway_ingress", "type": "GATEWAY"},
            {"id": "guard", "kind": "SUBGRAPH", "subgraph": "SG_TAX_GUARD", "type": "GUARD"},
            {"id": "audit", "kind": "OPERATOR", "operator": "es_audit_sync", "type": "STORAGE"},
        ],
        "edges": [
            {"from_node": "ingress", "to_node": "guard"},
            {"from_node": "guard", "to_node": "audit"},
        ],
    }


def test_scenario_full_lifecycle_compose_publish_execute():
    _create_subgraph("SG_TAX_GUARD")
    ok(
        "orchestration.subgraphs.version.save",
        {"action": "subgraphs.version.save", "payload": {"code": "SG_TAX_GUARD", "graph": _tax_guard_graph()}},
        _admin_token(),
    )
    ok(
        "orchestration.subgraphs.publish",
        {"action": "subgraphs.publish", "payload": {"code": "SG_TAX_GUARD", "version": "v1.0.0"}},
        _admin_token(),
    )

    _create_scenario("OPC_CATALOG_DEMO_FLOW")
    ok(
        "orchestration.scenarios.version.save",
        {"action": "scenarios.version.save", "payload": {"code": "OPC_CATALOG_DEMO_FLOW", "graph": _mixed_graph()}},
        _admin_token(),
    )
    published = ok(
        "orchestration.scenarios.publish",
        {"action": "scenarios.publish", "payload": {"code": "OPC_CATALOG_DEMO_FLOW", "version": "v1.0.0"}},
        _admin_token(),
    )
    compiled = published["versions"][0]["compiled"]
    # 子图节点内联展开为 guard::n_auth / guard::n_tax
    flat_ids = [n["id"] for n in compiled["nodes"]]
    assert flat_ids == ["ingress", "guard::n_auth", "guard::n_tax", "audit"]
    assert compiled["entry_node"] == "ingress" and compiled["exit_node"] == "audit"
    assert published["deployed_dag"]["scenario_code"] == "OPC_CATALOG_DEMO_FLOW"

    # 物化的运行时配置为 ACTIVE，且执行走编译后的扁平 DAG
    record = orchestration_service.get_dag_config("OPC_CATALOG_DEMO_FLOW", "v1.0.0")
    assert record.status == "ACTIVE"
    run = ok(
        "orchestration.scenarios.execute",
        {"scenario_code": "OPC_CATALOG_DEMO_FLOW", "inputs": {"quarterly_income": 260000}},
        _admin_token(),
    )
    assert run["status"] == "SUCCESS", run
    assert [t["node_id"] for t in run["node_traces"]] == flat_ids

    # 新版本发布后：旧运行时配置被取代，执行解析到最新 ACTIVE
    ok(
        "orchestration.scenarios.version.save",
        {"action": "scenarios.version.save", "payload": {"code": "OPC_CATALOG_DEMO_FLOW", "graph": _mixed_graph()}},
        _admin_token(),
    )
    ok(
        "orchestration.scenarios.publish",
        {"action": "scenarios.publish", "payload": {"code": "OPC_CATALOG_DEMO_FLOW", "version": "v1.0.1"}},
        _admin_token(),
    )
    v1 = orchestration_service.get_dag_config("OPC_CATALOG_DEMO_FLOW", "v1.0.0")
    v11 = orchestration_service.get_dag_config("OPC_CATALOG_DEMO_FLOW", "v1.0.1")
    assert v1.status == "SUPERSEDED" and v11.status == "ACTIVE"
    run2 = ok(
        "orchestration.scenarios.execute",
        {"scenario_code": "OPC_CATALOG_DEMO_FLOW", "inputs": {"quarterly_income": 100000}},
        _admin_token(),
    )
    assert run2["status"] == "SUCCESS"

    # 删除场景：连同运行时配置一并清理
    deleted = ok(
        "orchestration.scenarios.delete",
        {"action": "scenarios.delete", "payload": {"code": "OPC_CATALOG_DEMO_FLOW"}},
        _admin_token(),
    )
    assert deleted["deleted"] is True
    assert set(deleted["removed_runtime_versions"]) == {"v1.0.0", "v1.0.1"}
    assert orchestration_service.list_dag_configs("OPC_CATALOG_DEMO_FLOW") == []


def test_operator_delete_blocked_by_published_subgraph():
    """已发布子图引用的自建算子不可删除。"""
    acquire_lock("operator", "dynamic.blocked", _admin_token())
    ok(
        "orchestration.operators.create",
        {"action": "operators.create", "payload": {"name": "dynamic.blocked", "code": VALID_SCRIPT}},
        _admin_token(),
    )
    ok(
        "orchestration.operators.publish",
        {"action": "operators.publish", "payload": {"name": "dynamic.blocked", "version": "v1.0.0"}},
        _admin_token(),
    )
    acquire_lock("subgraph", "SG_HOLDS_OP", _admin_token())
    ok(
        "orchestration.subgraphs.create",
        {"action": "subgraphs.create", "payload": {"code": "SG_HOLDS_OP"}},
        _admin_token(),
    )
    ok(
        "orchestration.subgraphs.version.save",
        {
            "action": "subgraphs.version.save",
            "payload": {
                "code": "SG_HOLDS_OP",
                "graph": {
                    "entry_node": "a",
                    "exit_node": "b",
                    "nodes": [
                        {"id": "a", "operator": "auth_guard"},
                        {"id": "b", "operator": "dynamic.blocked"},
                    ],
                    "edges": [{"from_node": "a", "to_node": "b"}],
                },
            },
        },
        _admin_token(),
    )
    ok(
        "orchestration.subgraphs.publish",
        {"action": "subgraphs.publish", "payload": {"code": "SG_HOLDS_OP", "version": "v1.0.0"}},
        _admin_token(),
    )
    res = fail(
        "orchestration.operators.delete",
        {"action": "operators.delete", "payload": {"name": "dynamic.blocked"}},
        _admin_token(),
    )
    assert res["code"] == 400
    assert "SG_HOLDS_OP" in res["message"]


def test_scenario_runtime_rows_visible():
    """场景目录同时展示运行时内置管线（只读）与管理场景。"""
    rows = ok("orchestration.catalog.scenarios", {})["scenarios"]
    codes = {r["code"] for r in rows}
    assert "OPC_FORUM_THREAD_PUBLISH" in codes  # 运行时管线可见
    assert all(r["source"] in ("managed", "runtime") for r in rows)


def test_catalog_write_reseeds_missing_pipeline():
    """元管线配置缺失时（懒加载进程的首个写调用），写适配器应幂等自愈。"""
    from src.domains.orchestration.catalog import CATALOG_PIPELINE_SCENARIO

    orchestration_service.delete_dag_config(CATALOG_PIPELINE_SCENARIO, "v1.0.0")
    acquire_lock("subgraph", "SG_RESEED", _admin_token())
    asset = ok(
        "orchestration.subgraphs.create",
        {"action": "subgraphs.create", "payload": {"code": "SG_RESEED"}},
        _admin_token(),
    )
    assert asset["code"] == "SG_RESEED"
    assert any(
        c.scenario_code == CATALOG_PIPELINE_SCENARIO
        for c in orchestration_service.list_dag_configs()
    )


def test_operator_builtin_version_and_usage():
    """预置算子统一带平台版本 v1.0.0；使用状态覆盖子图/场景/系统流程三类引用。"""
    ops = {o["name"]: o for o in ok("orchestration.catalog.operators", {})["operators"]}
    guard = ops["auth_guard"]
    assert guard["source"] == "builtin"
    assert guard["current_version"] == "v1.0.0"
    assert guard["versions"][0]["version"] == "v1.0.0"
    assert guard["versions"][0]["status"] == "PUBLISHED"
    # auth_guard 被系统预置流程（如税务测算管线）引用 → 使用中
    assert guard["in_use"] is True
    assert any(ref.startswith("流程 ") for ref in guard["referenced_by"])

    # 自建算子发布后未被引用 → 未使用
    acquire_lock("operator", "dynamic.usage.lonely", _admin_token())
    ok(
        "orchestration.operators.create",
        {"action": "operators.create", "payload": {"name": "dynamic.usage.lonely", "code": VALID_SCRIPT}},
        _admin_token(),
    )
    ok(
        "orchestration.operators.publish",
        {"action": "operators.publish", "payload": {"name": "dynamic.usage.lonely", "version": "v1.0.0"}},
        _admin_token(),
    )
    lonely = {o["name"]: o for o in ok("orchestration.catalog.operators", {})["operators"]}["dynamic.usage.lonely"]
    assert lonely["in_use"] is False

    # 发布引用 auth_guard 的子图后 → 引用方新增子图条目
    acquire_lock("subgraph", "SG_USAGE_PROBE", _admin_token())
    ok(
        "orchestration.subgraphs.create",
        {"action": "subgraphs.create", "payload": {"code": "SG_USAGE_PROBE"}},
        _admin_token(),
    )
    ok(
        "orchestration.subgraphs.version.save",
        {
            "action": "subgraphs.version.save",
            "payload": {
                "code": "SG_USAGE_PROBE",
                "graph": {
                    "entry_node": "a",
                    "exit_node": "b",
                    "nodes": [
                        {"id": "a", "operator": "auth_guard"},
                        {"id": "b", "operator": "invoice_tax_calc"},
                    ],
                    "edges": [{"from_node": "a", "to_node": "b"}],
                },
            },
        },
        _admin_token(),
    )
    ok(
        "orchestration.subgraphs.publish",
        {"action": "subgraphs.publish", "payload": {"code": "SG_USAGE_PROBE", "version": "v1.0.0"}},
        _admin_token(),
    )
    ops2 = {o["name"]: o for o in ok("orchestration.catalog.operators", {})["operators"]}
    refs = ops2["auth_guard"]["referenced_by"]
    assert any("SG_USAGE_PROBE" in ref for ref in refs)
    assert any(ref.startswith("流程 ") for ref in refs)
    assert ops2["invoice_tax_calc"]["in_use"] is True
    # 详情接口同样返回使用状态
    detail = ok("orchestration.catalog.operator", {"name": "auth_guard"})
    assert detail["in_use"] is True and detail["current_version"] == "v1.0.0"
