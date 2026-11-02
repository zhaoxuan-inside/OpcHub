"""运维域服务：运行记录的落库、内存检索与指标聚合。

* 采集点：``orchestration_service._execute_via_microflow`` 的唯一收口（每次
  场景执行一条，含 SUCCESS/FAILED/GUARD_REJECTED）；写后异步落 domain_snapshots
  （family ``ops.run_records``，key=trace_id）。
* 内存索引为运行时读路径，容量封顶（超出丢弃最旧）；保留期外的记录启动时清理。
* 节点 output 截断（单节点 2KB）避免大输出撑爆快照 —— 瀑布图只需要
  node_id/status/duration_ms/error，业务输出详情以 final_output 为准。
* 指标（list 侧 metrics）读时计算：窗口内按场景聚合调用量/成功率/P95 —— 不
  预存时间序列，诚实用已落库的记录说话。
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.domains.ops.models import RunRecord
from src.infrastructure.database.persistence import domain_persistence

FAMILY_RUNS = "ops.run_records"

MAX_MEMORY_RECORDS = 5000
NODE_OUTPUT_MAX_CHARS = 2000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpsRunService:
    """运行记录注册表（内存索引 + write-behind 快照）。"""

    def __init__(self) -> None:
        self._records: Dict[str, RunRecord] = {}  # trace_id → record
        self._order: List[str] = []  # 插入序（容量封顶用）

    # ------------------------------------------------------------------
    # 采集（orchestration 收口调用）
    # ------------------------------------------------------------------
    def record(
        self,
        scenario_code: str,
        status: str,
        execution_time_ms: float,
        trace_id: str,
        node_traces: Optional[List[Dict[str, Any]]],
        final_output_error: str = "",
        error_type: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not trace_id:
            return
        traces: List[Dict[str, Any]] = []
        failed: List[str] = []
        for t in node_traces or []:
            trimmed = dict(t)
            output = trimmed.get("output")
            if isinstance(output, str) and len(output) > NODE_OUTPUT_MAX_CHARS:
                trimmed["output"] = output[:NODE_OUTPUT_MAX_CHARS] + "…(截断)"
            traces.append(trimmed)
            if trimmed.get("status") not in ("SUCCESS", "SKIPPED"):
                failed.append(str(trimmed.get("node_id") or ""))
        record = RunRecord(
            trace_id=trace_id,
            scenario_code=scenario_code,
            status=status,
            execution_time_ms=float(execution_time_ms or 0.0),
            user_id=str((context or {}).get("user_id") or ""),
            project_id=str((context or {}).get("project_id") or ""),
            env_key=str((context or {}).get("env_key") or ""),
            started_at=_now_iso(),
            error_type=str(error_type or ""),
            error_message=str(final_output_error or "")[:500],
            node_count=len(traces),
            failed_nodes=[f for f in failed if f],
            node_traces=traces,
        )
        self._records[trace_id] = record
        self._order.append(trace_id)
        # 容量封顶：丢弃最旧（DB 快照保留给保留期清理兜底）
        while len(self._order) > MAX_MEMORY_RECORDS:
            oldest = self._order.pop(0)
            self._records.pop(oldest, None)
        domain_persistence.write(FAMILY_RUNS, trace_id, record)

    # ------------------------------------------------------------------
    # 查询（ops 平台数据面）
    # ------------------------------------------------------------------
    def list_runs(
        self,
        scenario_code: str = "",
        status: str = "",
        env_key: str = "",
        limit: int = 100,
    ) -> Dict[str, Any]:
        rows = list(self._records.values())
        if scenario_code:
            rows = [r for r in rows if r.scenario_code == scenario_code]
        if status:
            rows = [r for r in rows if r.status == status]
        if env_key:
            rows = [r for r in rows if r.env_key == env_key]
        rows.sort(key=lambda r: r.started_at, reverse=True)
        rows = rows[: max(1, min(int(limit or 100), 500))]
        return {
            "runs": [r.model_dump(exclude={"node_traces"}) for r in rows],
            "total": len(rows),
        }

    def get_run(self, trace_id: str) -> RunRecord:
        record = self._records.get(str(trace_id or ""))
        if record is None:
            raise KeyError(f"运行记录 {trace_id} 不存在（可能已超出保留期或内存容量）")
        return record

    def metrics(self, window_minutes: int = 60) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, min(int(window_minutes or 60), 24 * 60)))
        per_scenario: Dict[str, Dict[str, Any]] = {}
        for r in self._records.values():
            try:
                started = datetime.fromisoformat(r.started_at)
            except ValueError:
                continue
            if started < cutoff:
                continue
            slot = per_scenario.setdefault(
                r.scenario_code, {"scenario_code": r.scenario_code, "count": 0, "errors": 0, "durations": []}
            )
            slot["count"] += 1
            if r.status != "SUCCESS":
                slot["errors"] += 1
            slot["durations"].append(r.execution_time_ms)
        rows = []
        for slot in per_scenario.values():
            durations = sorted(slot.pop("durations"))
            count = slot["count"]
            p95 = durations[min(len(durations) - 1, int(len(durations) * 0.95))] if durations else 0.0
            rows.append({
                **slot,
                "error_rate": round(slot["errors"] / count, 4) if count else 0.0,
                "p95_ms": round(p95, 2),
                "avg_ms": round(sum(durations) / len(durations), 2) if durations else 0.0,
            })
        rows.sort(key=lambda s: -s["count"])
        return {"window_minutes": max(1, min(int(window_minutes or 60), 24 * 60)), "scenarios": rows}

    # ------------------------------------------------------------------
    # 保留期清理（启动时调用）
    # ------------------------------------------------------------------
    def prune(self, retention_days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(retention_days)))
        removed = 0
        for trace_id, r in list(self._records.items()):
            try:
                started = datetime.fromisoformat(r.started_at)
            except ValueError:
                continue
            if started < cutoff:
                self._records.pop(trace_id, None)
                domain_persistence.delete(FAMILY_RUNS, trace_id)
                removed += 1
        self._order = [t for t in self._order if t in self._records]
        return removed

    # ------------------------------------------------------------------
    # Hydration
    # ------------------------------------------------------------------
    def hydrate_runs(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows or []:
            try:
                record = RunRecord(**row)
            except Exception:
                continue
            self._records[record.trace_id] = record
            self._order.append(record.trace_id)
        while len(self._order) > MAX_MEMORY_RECORDS:
            self._records.pop(self._order.pop(0), None)
        return len(rows or [])


ops_run_service = OpsRunService()

domain_persistence.register(FAMILY_RUNS, ops_run_service.hydrate_runs)
