"""DAG pipelines that orchestrate the loyalty atomic operators."""
from __future__ import annotations

from typing import Any, Dict

AWARD_PIPELINE = "OPC_LOYALTY_AWARD_PIPELINE"
REVOKE_PIPELINE = "OPC_LOYALTY_REVOKE_PIPELINE"
REDEEM_PIPELINE = "OPC_LOYALTY_REDEEM_PIPELINE"
SUBSCRIBE_PIPELINE = "OPC_LOYALTY_SUBSCRIBE_PIPELINE"

LOYALTY_PIPELINES: Dict[str, Dict[str, Any]] = {
    AWARD_PIPELINE: {
        "topology": "DAG",
        "entry_node": "step_identity",
        "exit_node": "step_telemetry",
        "enable_saga_compensation": True,
        "nodes": [
            {"id": "step_identity", "action_handler": "loyalty.identity_guard", "type": "GUARD"},
            {"id": "step_event", "action_handler": "loyalty.event_resolve", "type": "BIZ"},
            {"id": "step_guard", "action_handler": "loyalty.award_guard", "type": "GUARD"},
            {"id": "step_settle", "action_handler": "loyalty.points_settle", "type": "STORAGE"},
            {"id": "step_telemetry", "action_handler": "loyalty.telemetry.incr", "type": "BIZ"},
        ],
        "edges": [
            {"from": "step_identity", "to": "step_event"},
            {"from": "step_event", "to": "step_guard"},
            {"from": "step_guard", "to": "step_settle"},
            {"from": "step_settle", "to": "step_telemetry"},
        ],
    },
    REVOKE_PIPELINE: {
        "topology": "DAG",
        "entry_node": "step_identity",
        "exit_node": "step_telemetry",
        "enable_saga_compensation": False,
        "nodes": [
            {"id": "step_identity", "action_handler": "loyalty.identity_guard", "type": "GUARD"},
            {"id": "step_event", "action_handler": "loyalty.event_resolve", "type": "BIZ"},
            {"id": "step_revoke", "action_handler": "loyalty.points_revoke", "type": "STORAGE"},
            {"id": "step_telemetry", "action_handler": "loyalty.telemetry.incr", "type": "BIZ"},
        ],
        "edges": [
            {"from": "step_identity", "to": "step_event"},
            {"from": "step_event", "to": "step_revoke"},
            {"from": "step_revoke", "to": "step_telemetry"},
        ],
    },
    REDEEM_PIPELINE: {
        "topology": "DAG",
        "entry_node": "step_identity",
        "exit_node": "step_telemetry",
        "enable_saga_compensation": False,
        "nodes": [
            {"id": "step_identity", "action_handler": "loyalty.identity_guard", "type": "GUARD"},
            {"id": "step_guard", "action_handler": "loyalty.redeem_guard", "type": "GUARD"},
            {"id": "step_settle", "action_handler": "loyalty.redeem_settle", "type": "STORAGE"},
            {"id": "step_telemetry", "action_handler": "loyalty.telemetry.incr", "type": "BIZ"},
        ],
        "edges": [
            {"from": "step_identity", "to": "step_guard"},
            {"from": "step_guard", "to": "step_settle"},
            {"from": "step_settle", "to": "step_telemetry"},
        ],
    },
    SUBSCRIBE_PIPELINE: {
        "topology": "DAG",
        "entry_node": "step_identity",
        "exit_node": "step_telemetry",
        "enable_saga_compensation": False,
        "nodes": [
            {"id": "step_identity", "action_handler": "loyalty.identity_guard", "type": "GUARD"},
            {"id": "step_guard", "action_handler": "loyalty.subscribe_guard", "type": "GUARD"},
            {"id": "step_settle", "action_handler": "loyalty.subscribe_settle", "type": "STORAGE"},
            {"id": "step_telemetry", "action_handler": "loyalty.telemetry.incr", "type": "BIZ"},
        ],
        "edges": [
            {"from": "step_identity", "to": "step_guard"},
            {"from": "step_guard", "to": "step_settle"},
            {"from": "step_settle", "to": "step_telemetry"},
        ],
    },
}


def ensure_loyalty_pipelines() -> None:
    """Idempotently seed the loyalty DAG pipelines (never overwrites admin edits)."""
    from src.domains.orchestration.models import DAGConfigSaveRequest
    from src.domains.orchestration.service import orchestration_service

    existing = {config.scenario_code for config in orchestration_service.list_dag_configs()}
    for scenario_code, topology in LOYALTY_PIPELINES.items():
        if scenario_code in existing:
            continue
        orchestration_service.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code=scenario_code,
                version="v1.0.0",
                topology_graph=topology,
                status="ACTIVE",
            )
        )
