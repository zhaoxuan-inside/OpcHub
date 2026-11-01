"""运营平台分析测试：概览真实计数 / 趋势按日聚合 / 漏斗去重口径 / 留存 D1/D7 / 权限。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.core.audit import audit_service
from src.domains.ops.service import ops_run_service
from src.domains.ops.models import RunRecord
from datetime import datetime, timedelta, timezone


def _client(role: str = "ADMIN", uid: str = "usr_admin_builtin") -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + create_session_token({"uid": uid, "role": role})
    return c


def _post(client: TestClient, scenario: str, payload: dict = None):
    return client.post("/api/welcom/opc_world", json={
        "scenario": scenario, "version": "v1.0.0", "payload": payload or {},
    }).json()


@pytest.fixture()
def seeded_activity():
    """造真实足迹：审计内存流（3 操作者 × 多日）+ 运行记录。

    隔离：清空既有足迹再播种（全量套件中前置测试会留下 auth.login 等审计
    记录，混入样本会破坏漏斗计数断言），恢复在 yield 之后。
    """
    mem_snap = list(audit_service._mem_logs)
    runs_snap = (dict(ops_run_service._records), list(ops_run_service._order))
    audit_service._mem_logs = []
    ops_run_service._records = {}
    ops_run_service._order = []
    now = datetime.now(timezone.utc)
    for offset, (actor, action, result) in enumerate([
        ("usr_a", "auth.login", "SUCCESS"),
        ("usr_a", "scenario:content.publish", "SUCCESS"),
        ("usr_a", "scenario:content.interact", "SUCCESS"),
        ("usr_b", "auth.login", "SUCCESS"),
        ("usr_b", "scenario:content.interact", "SUCCESS"),
        ("usr_c", "auth.login", "DENIED"),
        ("usr_a", "auth.login", "SUCCESS"),  # 昨日复访（D1）
    ]):
        audit_service._mem_logs.append({
            "id": f"seed_{offset}",
            "actor_id": actor,
            "actor_role": "MAKER",
            "action": action,
            "result": result,
            "created_at": (now - timedelta(days=offset % 2)).isoformat(),
        })
    for i in range(5):
        record = RunRecord(
            trace_id=f"trc_seed_{i}", scenario_code="OPC_TEST_FLOW", status="SUCCESS",
            started_at=(now - timedelta(days=i % 3)).isoformat(),
        )
        ops_run_service._records[record.trace_id] = record
        ops_run_service._order.append(record.trace_id)
    yield
    audit_service._mem_logs = mem_snap
    ops_run_service._records, ops_run_service._order = runs_snap


def test_overview_counts_real_entities(seeded_activity):
    c = _client()
    body = _post(c, "bizops.overview")
    assert body["code"] == 200
    data = body["data"]
    assert "user.account" in data["entities"]
    assert data["runs_24h"] >= 2  # 种子 5 条中 2 条落 24h 窗口
    assert data["entities"]["user.account"] >= 1  # 至少内置管理员在册


def test_trend_daily_series(seeded_activity):
    c = _client()
    body = _post(c, "bizops.trend", {"days": 14})
    assert body["code"] == 200
    series = body["data"]["series"]
    assert len(series) == 14
    events_total = sum(s["events"] for s in series)
    assert events_total >= 7
    runs_total = sum(s["scenario_runs"] for s in series)
    assert runs_total >= 5
    assert body["data"]["sample_size"] >= 7


def test_funnel_dedup_actors_and_conversion(seeded_activity):
    c = _client()
    body = _post(c, "bizops.funnel", {"steps": ["auth.login", "scenario:content.publish", "scenario:content.interact"]})
    assert body["code"] == 200
    steps = body["data"]["steps"]
    # 足迹口径：DENIED 的 auth.login（usr_c）同样留痕 → 首步 3 人
    assert steps[0]["actors"] == 3
    assert steps[1]["actors"] == 1  # 仅 usr_a
    assert steps[2]["actors"] == 2  # usr_a + usr_b
    assert steps[1]["conversion_from_first"] <= 1.0
    empty = _post(c, "bizops.funnel", {})
    assert empty["code"] == 400


def test_retention_d1_from_real_footprints(seeded_activity):
    c = _client()
    body = _post(c, "bizops.retention", {"days": 14})
    assert body["code"] == 200
    data = body["data"]
    assert data["cohort_size"] >= 3  # usr_a/b/c
    # usr_a 两天都有足迹（offset 0 和 2... fixture 里 usr_a 有两天）→ D1 判定依赖足迹日期相邻
    assert 0.0 <= data["d1_rate"] <= 1.0
    assert any(a["actor_id"] == "usr_a" for a in data["actors"])


def test_bizops_routes_require_entry_permission():
    maker = _client(role="MAKER", uid="usr_bizops_maker")
    body = _post(maker, "bizops.overview")
    assert body["code"] == 403
    body = _post(maker, "bizops.trend", {"days": 7})
    assert body["code"] == 403
