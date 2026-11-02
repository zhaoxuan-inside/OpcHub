"""运维域场景适配器：运行记录检索（读直连，platform:audit_read 把守）。"""
from typing import Any, Dict

from src.domains.ops.service import ops_run_service


def ops_runs_list_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    payload = p or {}
    return ops_run_service.list_runs(
        scenario_code=str(payload.get("scenario_code") or ""),
        status=str(payload.get("status") or ""),
        env_key=str(payload.get("env_key") or ""),
        limit=int(payload.get("limit") or 100),
    )


def ops_runs_detail_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    return ops_run_service.get_run(str((p or {}).get("trace_id") or "")).model_dump()


def ops_runs_metrics_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    return ops_run_service.metrics(window_minutes=int((p or {}).get("window_minutes") or 60))
