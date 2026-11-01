"""配置中心控制面算子（MicroFlow 写路径）。

配置写操作（命名空间/配置项/版本/灰度发布）统一经 ``OPC_CONFIGCENTER_PIPELINE``
（guard → persist → telemetry）执行，与编排目录/平台治理/实验域元管线同构。
"""
from __future__ import annotations

from typing import Any

from src.core.operators.sdk import operator

CONFIG_PIPELINE_SCENARIO = "OPC_CONFIGCENTER_PIPELINE"


@operator("configcenter.governance.guard", category="CONTROL", description="Validate a config-center action")
def config_guard(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.configcenter.service import CONFIG_ACTIONS

    action = str(args.get("action") or params.get("action") or "")
    if action not in CONFIG_ACTIONS:
        raise ValueError(f"未知的配置中心操作：{action}")
    if not context.get("user_id"):
        raise PermissionError("该操作需要登录身份")
    return {"action": action, "payload": dict(args.get("payload") or {}), "validated": True}


@operator("configcenter.governance.persist", category="CONTROL", description="Persist one config-center mutation")
def config_persist(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.configcenter.service import dispatch_config_action

    action = str(args.get("action") or "")
    payload = dict(args.get("payload") or {})
    result = dispatch_config_action(action, payload, context)
    return {"config_result": result, "result": result, "action": action}


@operator("configcenter.governance.telemetry.incr", category="CONTROL", description="Record one config metric")
def config_telemetry(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.operators.side_effects import metric_incr

    return metric_incr({}, {"metric": f"configcenter.governance.{args.get('action') or 'mutation'}"}, context)


def ensure_configcenter_pipeline() -> None:
    """Idempotently seed the meta DAG pipeline carrying every config write."""
    from src.domains.orchestration.models import DAGConfigSaveRequest
    from src.domains.orchestration.service import orchestration_service

    if any(
        c.scenario_code == CONFIG_PIPELINE_SCENARIO
        for c in orchestration_service.list_dag_configs()
    ):
        return
    orchestration_service.save_dag_config(
        DAGConfigSaveRequest(
            scenario_code=CONFIG_PIPELINE_SCENARIO,
            version="v1.0.0",
            status="ACTIVE",
            topology_graph={
                "topology": "DAG",
                "entry_node": "step_guard",
                "exit_node": "step_telemetry",
                "enable_saga_compensation": False,
                "nodes": [
                    {"id": "step_guard", "action_handler": "configcenter.governance.guard", "type": "GUARD", "params": {"legacy_inputs": True}},
                    {"id": "step_persist", "action_handler": "configcenter.governance.persist", "type": "BIZ", "params": {"legacy_inputs": True}},
                    {"id": "step_telemetry", "action_handler": "configcenter.governance.telemetry.incr", "type": "BIZ", "params": {"legacy_inputs": True}},
                ],
                "edges": [
                    {"from": "step_guard", "to": "step_persist"},
                    {"from": "step_persist", "to": "step_telemetry"},
                ],
            },
        )
    )
