"""实验域控制面算子（MicroFlow 写路径）。

实验写操作（生命周期/分流/结果上报）统一经 ``OPC_EXPERIMENT_PIPELINE``
（guard → persist → telemetry）执行，与编排目录/平台治理元管线同构。
"""
from __future__ import annotations

from typing import Any

from src.core.operators.sdk import operator

EXPERIMENT_PIPELINE_SCENARIO = "OPC_EXPERIMENT_PIPELINE"


@operator("experiment.governance.guard", category="CONTROL", description="Validate an experiment action")
def experiment_guard(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.experiment.service import EXPERIMENT_ACTIONS

    action = str(args.get("action") or params.get("action") or "")
    if action not in EXPERIMENT_ACTIONS:
        raise ValueError(f"未知的实验操作：{action}")
    if not context.get("user_id"):
        raise PermissionError("该操作需要登录身份")
    return {"action": action, "payload": dict(args.get("payload") or {}), "validated": True}


@operator("experiment.governance.persist", category="CONTROL", description="Persist one experiment mutation")
def experiment_persist(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.experiment.service import dispatch_experiment_action

    action = str(args.get("action") or "")
    payload = dict(args.get("payload") or {})
    result = dispatch_experiment_action(action, payload, context)
    return {"experiment_result": result, "result": result, "action": action}


@operator("experiment.governance.telemetry.incr", category="CONTROL", description="Record one experiment metric")
def experiment_telemetry(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.operators.side_effects import metric_incr

    return metric_incr({}, {"metric": f"experiment.governance.{args.get('action') or 'mutation'}"}, context)


def ensure_experiment_pipeline() -> None:
    """Idempotently seed the meta DAG pipeline carrying every experiment action.

    本模块可能在进程内被懒加载（实验写适配器每次写操作前显式重调本种子）。
    """
    from src.domains.orchestration.models import DAGConfigSaveRequest
    from src.domains.orchestration.service import orchestration_service

    if any(
        c.scenario_code == EXPERIMENT_PIPELINE_SCENARIO
        for c in orchestration_service.list_dag_configs()
    ):
        return
    orchestration_service.save_dag_config(
        DAGConfigSaveRequest(
            scenario_code=EXPERIMENT_PIPELINE_SCENARIO,
            version="v1.0.0",
            status="ACTIVE",
            topology_graph={
                "topology": "DAG",
                "entry_node": "step_guard",
                "exit_node": "step_telemetry",
                "enable_saga_compensation": False,
                "nodes": [
                    {"id": "step_guard", "action_handler": "experiment.governance.guard", "type": "GUARD", "params": {"legacy_inputs": True}},
                    {"id": "step_persist", "action_handler": "experiment.governance.persist", "type": "BIZ", "params": {"legacy_inputs": True}},
                    {"id": "step_telemetry", "action_handler": "experiment.governance.telemetry.incr", "type": "BIZ", "params": {"legacy_inputs": True}},
                ],
                "edges": [
                    {"from": "step_guard", "to": "step_persist"},
                    {"from": "step_persist", "to": "step_telemetry"},
                ],
            },
        )
    )
