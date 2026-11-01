"""平台治理控制面算子（MicroFlow 写路径）。

支撑平台的治理写操作与编排目录同构：所有变更统一经
``OPC_PLATFORM_GOVERNANCE_PIPELINE``（guard → persist → telemetry）的
算子链执行，符合框架"写走 DAG · 读直连"约定。这些算子注册在 SDK 但独立
成模块，使 ``domains/*/functions.py`` 的纯度检查不适用。
"""
from __future__ import annotations

from typing import Any

from src.core.operators.sdk import operator

# 平台治理元管线（与 OPC_ORCHESTRATION_CATALOG_PIPELINE 同构）
PLATFORM_PIPELINE_SCENARIO = "OPC_PLATFORM_GOVERNANCE_PIPELINE"


@operator("platform.governance.guard", category="CONTROL", description="Validate a platform governance action")
def platform_guard(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.platform.service import PLATFORM_ACTIONS

    action = str(args.get("action") or params.get("action") or "")
    if action not in PLATFORM_ACTIONS:
        raise ValueError(f"未知的平台治理操作：{action}")
    if not context.get("user_id"):
        raise PermissionError("该操作需要登录身份")
    return {"action": action, "payload": dict(args.get("payload") or {}), "validated": True}


@operator("platform.governance.persist", category="CONTROL", description="Persist one platform governance mutation")
def platform_persist(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.platform.service import dispatch_platform_action

    action = str(args.get("action") or "")
    payload = dict(args.get("payload") or {})
    result = dispatch_platform_action(action, payload, context)
    return {"platform_result": result, "result": result, "action": action}


@operator("platform.governance.telemetry.incr", category="CONTROL", description="Record one platform governance metric")
def platform_telemetry(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.operators.side_effects import metric_incr

    return metric_incr({}, {"metric": f"platform.governance.{args.get('action') or 'mutation'}"}, context)


def ensure_platform_pipeline() -> None:
    """Idempotently seed the meta DAG pipeline carrying every governance write.

    本模块可能在进程内被懒加载（平台写适配器每次写操作前显式重调本种子）。
    """
    from src.domains.orchestration.models import DAGConfigSaveRequest
    from src.domains.orchestration.service import orchestration_service

    if any(
        c.scenario_code == PLATFORM_PIPELINE_SCENARIO
        for c in orchestration_service.list_dag_configs()
    ):
        return
    orchestration_service.save_dag_config(
        DAGConfigSaveRequest(
            scenario_code=PLATFORM_PIPELINE_SCENARIO,
            version="v1.0.0",
            status="ACTIVE",
            topology_graph={
                "topology": "DAG",
                "entry_node": "step_guard",
                "exit_node": "step_telemetry",
                "enable_saga_compensation": False,
                "nodes": [
                    {"id": "step_guard", "action_handler": "platform.governance.guard", "type": "GUARD", "params": {"legacy_inputs": True}},
                    {"id": "step_persist", "action_handler": "platform.governance.persist", "type": "BIZ", "params": {"legacy_inputs": True}},
                    {"id": "step_telemetry", "action_handler": "platform.governance.telemetry.incr", "type": "BIZ", "params": {"legacy_inputs": True}},
                ],
                "edges": [
                    {"from": "step_guard", "to": "step_persist"},
                    {"from": "step_persist", "to": "step_telemetry"},
                ],
            },
        )
    )
