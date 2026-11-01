"""运维运行记录测试：采集收口 / 节点迹时长 / 检索过滤 / 指标聚合 / 保留期清理。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.domains.ops.service import ops_run_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


def _client(role: str = "ADMIN", uid: str = "usr_admin_builtin") -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + create_session_token({"uid": uid, "role": role})
    return c


def _post(client: TestClient, scenario: str, payload: dict):
    return client.post("/api/welcom/opc_world", json={
        "scenario": scenario, "version": "v1.0.0", "payload": payload,
    }).json()


@pytest.fixture()
def clean_runs():
    snap = (dict(ops_run_service._records), list(ops_run_service._order))
    yield ops_run_service
    ops_run_service._records, ops_run_service._order = snap


def test_execution_is_recorded_with_node_durations(clean_runs):
    c = _client()
    # 执行一个真实场景（实验清单：直连 handler? → 该场景无 pipeline 不经 execute_scenario；
    # 用 meta 管线直执保证走 execute_scenario 收口）
    import asyncio

    async def run():
        return await orchestration_service.execute_scenario(ScenarioExecuteRequest(
            scenario_code="OPC_EXPERIMENT_PIPELINE", version="v1.0.0",
            inputs={"action": "assign", "payload": {"experiment_key": "no_such", "user_id": "usr_probe"}},
            context={"user_id": "usr_admin_builtin", "user_role": "ADMIN"},
        ))

    res = asyncio.run(run())
    assert res.status == "SUCCESS"
    record = ops_run_service.get_run(res.trace_id)
    assert record.scenario_code == "OPC_EXPERIMENT_PIPELINE"
    assert record.status == "SUCCESS"
    assert record.node_count >= 3  # guard → persist → telemetry
    assert record.user_id == "usr_admin_builtin"
    # 节点级时长已由框架写入（瀑布图数据源，不再恒 0）
    timed = [t for t in record.node_traces if t.get("duration_ms", 0) > 0]
    assert len(timed) >= 1, "节点 duration_ms 应来自框架 meta（真实时长）"


def test_failed_execution_recorded_with_error(clean_runs):
    c = _client()
    import asyncio

    async def run():
        return await orchestration_service.execute_scenario(ScenarioExecuteRequest(
            scenario_code="OPC_EXPERIMENT_PIPELINE", version="v1.0.0",
            inputs={"action": "nonexistent", "payload": {}},
            context={"user_id": "usr_admin_builtin", "user_role": "ADMIN"},
        ))

    res = asyncio.run(run())
    assert res.status != "SUCCESS"
    record = ops_run_service.get_run(res.trace_id)
    assert record.status == res.status
    assert record.error_message


def test_runs_list_filters_and_metrics(clean_runs):
    c = _client()
    import asyncio

    async def run():
        await orchestration_service.execute_scenario(ScenarioExecuteRequest(
            scenario_code="OPC_EXPERIMENT_PIPELINE", version="v1.0.0",
            inputs={"action": "assign", "payload": {"experiment_key": "no_such", "user_id": "u1"}},
            context={"user_id": "usr_admin_builtin", "user_role": "ADMIN"},
        ))
        await orchestration_service.execute_scenario(ScenarioExecuteRequest(
            scenario_code="OPC_EXPERIMENT_PIPELINE", version="v1.0.0",
            inputs={"action": "nonexistent", "payload": {}},
            context={"user_id": "usr_admin_builtin", "user_role": "ADMIN"},
        ))

    asyncio.run(run())
    body = _post(c, "ops.runs.list", {"scenario_code": "OPC_EXPERIMENT_PIPELINE"})
    assert body["code"] == 200
    runs = body["data"]["runs"]
    assert len(runs) >= 2
    assert all("node_traces" not in r for r in runs)  # 列表不带节点迹（详情才给）
    only_failed = _post(c, "ops.runs.list", {"status": "FAILED"})
    assert all(r["status"] == "FAILED" for r in only_failed["data"]["runs"])

    metrics = _post(c, "ops.runs.metrics", {"window_minutes": 60})
    slot = next((s for s in metrics["data"]["scenarios"] if s["scenario_code"] == "OPC_EXPERIMENT_PIPELINE"), None)
    assert slot is not None and slot["count"] >= 2 and slot["errors"] >= 1
    assert "p95_ms" in slot and "error_rate" in slot


def test_runs_detail_unknown_trace_404(clean_runs):
    c = _client()
    body = _post(c, "ops.runs.detail", {"trace_id": "trc_missing"})
    assert body["code"] == 404


def test_prune_removes_expired(clean_runs):
    from datetime import datetime, timedelta, timezone

    old_trace = "trc_old_record"
    # 直接造一条过期记录
    from src.domains.ops.models import RunRecord

    expired = RunRecord(
        trace_id=old_trace, scenario_code="X", status="SUCCESS",
        started_at=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
    )
    ops_run_service._records[old_trace] = expired
    ops_run_service._order.append(old_trace)
    removed = ops_run_service.prune(retention_days=14)
    assert removed >= 1 and old_trace not in ops_run_service._records


def test_ops_routes_require_audit_read():
    maker = _client(role="MAKER", uid="usr_ops_maker")
    body = _post(maker, "ops.runs.list", {})
    assert body["code"] == 403
    body = _post(maker, "ops.runs.metrics", {})
    assert body["code"] == 403
