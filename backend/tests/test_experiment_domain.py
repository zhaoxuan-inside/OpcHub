"""实验域测试：确定性分流 / 流量门控 / 粘性分配 / 状态机 / 读出聚合 / 项目隔离 / 权限。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.domains.experiment.service import bucket_of, experiment_service, pick_variant
from src.domains.experiment.models import Variant
from src.domains.platform.service import (
    ROLE_PROJECT_EDITOR,
    platform_service,
)
from src.domains.user.entities import account_entity

_VIEWER_DOC = {
    "uid": "usr_exp_viewer",
    "email": "exp_viewer@opchub.cn",
    "nickname": "实验查看者",
    "role": "MAKER",
    "is_active": True,
    "password_hash": "",
}


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
def clean_experiments():
    snap = (dict(experiment_service._experiments), dict(experiment_service._assignments))
    platform_snap = (
        dict(platform_service._tenants),
        dict(platform_service._projects),
        dict(platform_service._roles),
        dict(platform_service._bindings),
    )
    viewer_created = not account_entity.adapter.get("usr_exp_viewer")
    if viewer_created:
        account_entity.adapter.create("usr_exp_viewer", dict(_VIEWER_DOC))
    yield experiment_service
    experiment_service._experiments, experiment_service._assignments = snap
    platform_service._tenants, platform_service._projects = platform_snap[0], platform_snap[1]
    platform_service._roles, platform_service._bindings = platform_snap[2], platform_snap[3]
    if viewer_created:
        account_entity.adapter.delete("usr_exp_viewer")


# ---------------------------------------------------------------------------
# 分流算法（纯函数）
# ---------------------------------------------------------------------------
def test_bucket_is_stable_and_uniform():
    a = bucket_of("checkout_button", "usr_1")
    assert a == bucket_of("checkout_button", "usr_1")  # 稳定
    b = bucket_of("checkout_button", "usr_2")
    assert 0 <= a < 10000 and 0 <= b < 10000
    buckets = {bucket_of("exp", f"usr_{i}") for i in range(2000)}
    assert len(buckets) > 1800  # 覆盖率高（近似均匀）


def test_pick_variant_respects_traffic_and_weights():
    variants = [Variant(key="control", weight=1), Variant(key="treatment", weight=3)]
    # 流量 0：全部控制
    assert all(pick_variant(b, variants, 0) == "" for b in range(10000))
    # 流量 50：桶 %100 < 50 才入流（123%100=23 入流；556%100=56 出流）
    assert pick_variant(556, variants, 50) == "" and pick_variant(123, variants, 50) != ""
    # 入流桶按权重 1:3 切分（近似）
    from collections import Counter

    picks = Counter(
        pick_variant(b, variants, 100) for b in range(10000) if pick_variant(b, variants, 100)
    )
    assert picks["control"] < picks["treatment"] // 2  # 1:3 权重生效
    assert picks["control"] + picks["treatment"] == 10000


# ---------------------------------------------------------------------------
# 全链路（经 OPC_EXPERIMENT_PIPELINE 元管线）
# ---------------------------------------------------------------------------
def _make_project(client: TestClient) -> str:
    tenant = _post(client, "platform.tenants.create", {"code": "exp-t", "name": "实验租户"},
                   action="tenants.create")["data"]
    project = _post(client, "platform.projects.create",
                    {"tenant_id": tenant["tenant_id"], "key": "growth", "name": "增长项目"},
                    action="projects.create", context={"tenant_id": tenant["tenant_id"]})["data"]
    return project["project_id"]


def test_experiment_lifecycle_and_dispatch(clean_experiments):
    c = _client()
    project_id = _make_project(c)
    ctx = {"project_id": project_id}

    body = _post(c, "experiment.create", {
        "key": "cta_color", "name": "按钮颜色实验",
        "variants": [{"key": "control", "weight": 1}, {"key": "red", "weight": 1}],
        "traffic_percent": 100,
    }, action="experiments.create", context=ctx)
    assert body["code"] == 200, body
    assert body["data"]["status"] == "DRAFT"

    # DRAFT 状态分流 → 不入实验
    m = _client(role="MAKER", uid="usr_exp_u1")
    r = _post(m, "experiment.assign", {"experiment_key": "cta_color"})
    assert r["code"] == 200 and r["data"]["in_experiment"] is False and r["data"]["reason"] == "DRAFT"

    # 启动 → 分流（稳定且入实验）
    body = _post(c, "experiment.status", {"experiment_key": "cta_color", "status": "RUNNING"},
                 action="experiments.status", context=ctx)
    assert body["code"] == 200 and body["data"]["status"] == "RUNNING"
    r1 = _post(m, "experiment.assign", {"experiment_key": "cta_color"})
    r2 = _post(m, "experiment.assign", {"experiment_key": "cta_color"})
    assert r1["data"]["in_experiment"] is True
    assert r1["data"] == r2["data"]  # 粘性：同一用户永远同一变体
    assert r1["data"]["variant"] in ("control", "red")

    # 结果上报 + 读出聚合
    variant = r1["data"]["variant"]
    o = _post(m, "experiment.outcome.report", {"experiment_key": "cta_color", "metric": "clicked", "value": 1})
    assert o["code"] == 200 and o["data"]["recorded"] is True
    ro = _post(c, "experiment.readout", {"experiment_key": "cta_color"}, context=ctx)
    assert ro["code"] == 200 and ro["data"]["total_assignments"] == 1
    slot = next(v for v in ro["data"]["variants"] if v["variant"] == variant)
    assert slot["assignments"] == 1 and slot["metrics"]["clicked"]["count"] == 1

    # 停止后分流回到控制；删除前必须停止
    _post(c, "experiment.status", {"experiment_key": "cta_color", "status": "STOPPED"},
          action="experiments.status", context=ctx)
    r3 = _post(m, "experiment.assign", {"experiment_key": "cta_color"})
    assert r3["data"]["reason"] == "STOPPED"
    d = _post(c, "experiment.delete", {"experiment_key": "cta_color"}, action="experiments.delete", context=ctx)
    assert d["code"] == 200


def test_running_experiment_weight_only_edit(clean_experiments):
    c = _client()
    project_id = _make_project(c)
    ctx = {"project_id": project_id}
    _post(c, "experiment.create", {
        "key": "pricing_page", "name": "定价页实验",
        "variants": [{"key": "a", "weight": 1}, {"key": "b", "weight": 1}],
    }, action="experiments.create", context=ctx)
    _post(c, "experiment.status", {"experiment_key": "pricing_page", "status": "RUNNING"},
          action="experiments.status", context=ctx)
    # 运行中只可调权重，不可增删变体
    ok = _post(c, "experiment.update", {"experiment_key": "pricing_page",
                                        "variants": [{"key": "a", "weight": 3}, {"key": "b", "weight": 1}]},
               action="experiments.update", context=ctx)
    assert ok["code"] == 200
    bad = _post(c, "experiment.update", {"experiment_key": "pricing_page",
                                         "variants": [{"key": "a", "weight": 1}]},
                action="experiments.update", context=ctx)
    assert bad["code"] == 400 and "不可增删变体" in bad["message"]


def test_experiment_project_isolation_and_permissions(clean_experiments):
    c = _client()
    pa = _make_project(c)
    # 项目 B：由另一管理员在另一租户创建
    tenant_b = _post(c, "platform.tenants.create", {"code": "exp-t2", "name": "实验租户二"},
                     action="tenants.create")["data"]
    pb = _post(c, "platform.projects.create",
               {"tenant_id": tenant_b["tenant_id"], "key": "other", "name": "另一项目"},
               action="projects.create", context={"tenant_id": tenant_b["tenant_id"]})["data"]["project_id"]
    _post(c, "experiment.create", {"key": "iso_exp", "name": "隔离实验",
                                   "variants": [{"key": "a", "weight": 1}]},
          action="experiments.create", context={"project_id": pa})
    # 先让查看者仅在册于 pb（默认项目查看者角色）
    maker = _client(role="MAKER", uid="usr_exp_viewer")
    _post(c, "platform.tenants.members.add", {"tenant_id": tenant_b["tenant_id"], "user_id": "usr_exp_viewer"},
          action="tenants.members.add")
    _post(c, "platform.projects.members.add", {"project_id": pb, "user_id": "usr_exp_viewer"},
          action="projects.members.add")

    # 非 pa 成员看不到项目 A 的实验（完全隔离，不泄露存在性）
    body = _post(maker, "experiment.list", {}, context={"project_id": pb})
    assert all(e["key"] != "iso_exp" for e in body["data"]["experiments"])
    body = _post(maker, "experiment.readout", {"experiment_key": "iso_exp"}, context={"project_id": pb})
    assert body["code"] == 404

    # 所有者（创建人）跨上下文读自己的项目实验 → 放行（所有权语义）
    body = _post(c, "experiment.readout", {"experiment_key": "iso_exp"}, context={"project_id": pb})
    assert body["code"] == 200

    # 无 experiment:manage 的项目成员（查看者）创建被拒
    body = _post(maker, "experiment.create", {"key": "nope", "name": "无权实验",
                                              "variants": [{"key": "a", "weight": 1}]},
                 action="experiments.create", context={"project_id": pa})
    assert body["code"] == 403

    # 升为编辑者后可管理；分流数据面对登录用户开放
    _post(c, "platform.projects.members.set_role",
          {"project_id": pb, "user_id": "usr_exp_viewer", "role_id": ROLE_PROJECT_EDITOR},
          action="projects.members.set_role")
    _post(c, "experiment.create", {"key": "b_exp", "name": "B 项目实验",
                                   "variants": [{"key": "a", "weight": 1}]},
          action="experiments.create", context={"project_id": pb})
    _post(c, "experiment.status", {"experiment_key": "b_exp", "status": "RUNNING"},
          action="experiments.status", context={"project_id": pb})
    r = _post(maker, "experiment.assign", {"experiment_key": "b_exp"})
    assert r["code"] == 200 and r["data"]["in_experiment"] is True

    # 未登录分流 → 拒绝
    guest = TestClient(app)
    guest.headers.pop("Authorization", None)
    r = _post(guest, "experiment.assign", {"experiment_key": "b_exp"})
    assert r["code"] == 403


def test_unknown_experiment_key_returns_control(clean_experiments):
    m = _client(role="MAKER", uid="usr_exp_u2")
    r = _post(m, "experiment.assign", {"experiment_key": "missing_exp"})
    assert r["code"] == 200 and r["data"]["in_experiment"] is False and r["data"]["reason"] == "NOT_FOUND"
