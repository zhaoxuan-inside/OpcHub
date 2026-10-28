"""Control-plane operators for the orchestration catalog.

These are deliberately outside the business operator kernel: the catalog is the
low-code control plane that composes business flows, not a business flow itself.
They are registered through the SDK but kept in a separate module so the purity
checks for ``domains/*/functions.py`` do not apply.
"""
from __future__ import annotations

from typing import Any

from src.core.operators.sdk import operator


@operator("orchestration.catalog.guard", category="CONTROL", description="Validate a catalog mutation action")
def catalog_guard(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.orchestration.catalog import CATALOG_ACTIONS

    action = str(args.get("action") or params.get("action") or "")
    if action not in CATALOG_ACTIONS:
        raise ValueError(f"未知的目录操作：{action}")
    if not context.get("user_id"):
        raise PermissionError("该操作需要登录并持有编辑锁")
    return {"action": action, "payload": dict(args.get("payload") or {}), "validated": True}


@operator("orchestration.catalog.persist", category="CONTROL", description="Persist one catalog mutation")
def catalog_persist(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.orchestration.catalog import dispatch_catalog_action

    action = str(args.get("action") or "")
    payload = dict(args.get("payload") or {})
    result = dispatch_catalog_action(action, payload, context)
    return {"catalog_result": result, "result": result, "action": action}


@operator("orchestration.catalog.telemetry.incr", category="CONTROL", description="Record one catalog mutation metric")
def catalog_telemetry(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.operators.side_effects import metric_incr

    return metric_incr({}, {"metric": f"orchestration.catalog.{args.get('action') or 'mutation'}"}, context)


@operator("orchestration.operators.list", category="CONTROL", description="List registered operator descriptors")
def operators_list(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.orchestration.service import orchestration_service

    operators = [item.model_dump() for item in orchestration_service.list_operators()]
    return {"operators": operators}


def _compensate_dag_save(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.orchestration.service import orchestration_service

    config = dict(args.get("config") or {})
    code = str(config.get("scenario_code") or "")
    version = str(config.get("version") or "")
    if code and version:
        return {"compensated": orchestration_service.delete_dag_config(code, version)}
    return {"compensated": False}


@operator(
    "orchestration.dag.save",
    category="CONTROL",
    description="Save a versioned DAG configuration",
    compensator=_compensate_dag_save,
)
def dag_save(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.orchestration.models import DAGConfigSaveRequest
    from src.domains.orchestration.service import orchestration_service

    config = dict(args.get("config") or {})
    if not str(config.get("scenario_code") or "").strip():
        raise ValueError("scenario_code is required")
    if not str(config.get("version") or "").strip():
        raise ValueError("version is required")
    if config.get("simulate_downstream_failure"):
        raise RuntimeError("Simulated downstream telemetry failure")
    record = orchestration_service.save_dag_config(DAGConfigSaveRequest(**config))
    document = record.model_dump()
    return {
        **document,
        "dag_record": document,
        "orchestrated_by": str(params.get("pipeline") or "OPC_ORCHESTRATION_CONTROL_PIPELINE"),
    }


@operator("orchestration.dag.list", category="CONTROL", description="List versioned DAG configurations")
def dag_list(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.domains.orchestration.service import orchestration_service

    records = orchestration_service.list_dag_configs(args.get("scenario_code"))
    return {"items": [record.model_dump() for record in records], "total": len(records)}
