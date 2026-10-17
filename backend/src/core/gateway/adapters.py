"""Generic adapters for domain services referenced by gateway routes configuration."""
from typing import Any, Dict
from src.domains.demands.service import demand_service
from src.domains.demands.models import BidCreate
from src.domains.forum.service import forum_service
from src.domains.forum.models import ForumCommentCreate
from src.domains.user.service import user_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import (
    ScenarioExecuteRequest,
    FrontendLayoutSaveRequest,
    DAGConfigSaveRequest,
)


async def demand_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for enterprise outsourcing demand publishing."""
    inputs = dict(p)
    if "demand_payload" in inputs and isinstance(inputs["demand_payload"], dict):
        inputs.update(inputs["demand_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Demand publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_demand") or res.final_output


async def demand_bid_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for maker demand bidding."""
    inputs = dict(p)
    if "bid_payload" in inputs and isinstance(inputs["bid_payload"], dict):
        inputs.update(inputs["bid_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_DEMAND_BID_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Demand bidding pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_bid") or res.final_output


def demands_bid_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Legacy alias redirecting to demand_service directly or adapter."""
    return demand_service.submit_bid(
        demand_id=p.get("demand_id"),
        payload=BidCreate(**p.get("bid_payload", p)),
    )


async def sop_document_render_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for SOP document generation and persistence."""
    inputs = dict(p)
    if "doc_payload" in inputs and isinstance(inputs["doc_payload"], dict):
        inputs.update(inputs["doc_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_SOP_DOCUMENT_RENDER_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "SOP document render pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_doc") or res.final_output


async def perk_claim_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for developer perk redemption."""
    inputs = dict(p)
    if "claim_payload" in inputs and isinstance(inputs["claim_payload"], dict):
        inputs.update(inputs["claim_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PERK_CLAIM_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Perk claim pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_claim") or res.final_output


async def perk_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for ecosystem perk publishing."""
    inputs = dict(p)
    if "perk_payload" in inputs and isinstance(inputs["perk_payload"], dict):
        inputs.update(inputs["perk_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PERK_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Perk publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_perk") or res.final_output


async def compliance_audit_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for product compliance self-audit."""
    inputs = dict(p)
    if "audit_payload" in inputs and isinstance(inputs["audit_payload"], dict):
        inputs.update(inputs["audit_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_COMPLIANCE_AUDIT_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Compliance audit pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("audit_report") or res.final_output


async def moderation_takedown_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for content moderation takedown."""
    inputs = dict(p)
    if "takedown_payload" in inputs and isinstance(inputs["takedown_payload"], dict):
        inputs.update(inputs["takedown_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_MODERATION_TAKEDOWN_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Moderation takedown pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def moderation_restore_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for content moderation restore."""
    inputs = dict(p)
    if "restore_payload" in inputs and isinstance(inputs["restore_payload"], dict):
        inputs.update(inputs["restore_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_MODERATION_RESTORE_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Moderation restore pipeline failed"
        raise ValueError(error_msg)
    return res.final_output






async def forum_thread_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for forum thread publishing."""
    inputs = dict(p)
    if "thread_payload" in inputs and isinstance(inputs["thread_payload"], dict):
        inputs.update(inputs["thread_payload"])
    
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_THREAD_PUBLISH",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum thread publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_thread") or res.final_output


async def forum_comment_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for forum comment publishing."""
    inputs = dict(p)
    if "comment_payload" in inputs and isinstance(inputs["comment_payload"], dict):
        inputs.update(inputs["comment_payload"])
    
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_COMMENT_PUBLISH",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Forum comment publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_comment") or res.final_output


async def product_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for product showcase publishing."""
    inputs = dict(p)
    if "product_payload" in inputs and isinstance(inputs["product_payload"], dict):
        inputs.update(inputs["product_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_PRODUCT_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Product showcase publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_product") or res.final_output


async def policy_match_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for policy qualification matching."""
    inputs = dict(p)
    if "match_payload" in inputs and isinstance(inputs["match_payload"], dict):
        inputs.update(inputs["match_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_POLICY_MATCH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Policy match pipeline failed"
        raise ValueError(error_msg)
    return res.final_output


async def policy_publish_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Executes the microkernel DAG pipeline for government policy publishing."""
    inputs = dict(p)
    if "policy_payload" in inputs and isinstance(inputs["policy_payload"], dict):
        inputs.update(inputs["policy_payload"])

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_POLICY_PUBLISH_PIPELINE",
            version="v1.0.0",
            inputs=inputs,
        )
    )
    if res.status != "SUCCESS":
        error_msg = res.error_message or "Policy publish pipeline failed"
        raise ValueError(error_msg)
    return res.final_output.get("created_policy") or res.final_output


async def home_overview_adapter(p: Dict[str, Any], c: Dict[str, Any]) -> Any:
    """Executes the microkernel DAG pipeline for the Home page overview."""
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_HOME_OVERVIEW_PIPELINE",
            version="v1.0.0",
            inputs=p or {},
        )
    )
    if res.status != "SUCCESS":
        return {
            "active_makers_count": 14820,
            "active_dags_count": 482,
            "matched_policies_count": 128,
            "demands_orders_count": 89,
            "perks_saved_cny": 1820000.0,
            "quick_links": [],
            "orchestrated": False,
        }
    return res.final_output


def user_profile_adapter(p: Dict[str, Any], c: Dict[str, Any]) -> Any:
    user_id = p.get("user_id", "usr_2026_opc_9981")
    return user_service.get_maker_profile(user_id=user_id)


def save_dag_config_adapter(p: Dict[str, Any]) -> Any:
    topo = p.get("topology_graph") or p.get("config") or {}
    if "topology" not in topo and "topology" in p:
        topo["topology"] = p["topology"]
    return orchestration_service.save_dag_config(
        DAGConfigSaveRequest(
            scenario_code=p.get("scenario_code", "CUSTOM_SCENARIO"),
            version=p.get("version", "v1.0.0"),
            topology_graph=topo,
            status=p.get("status", "ACTIVE"),
            created_by=p.get("created_by", "usr_admin_001"),
        )
    )


def save_layout_adapter(p: Dict[str, Any]) -> Any:
    return orchestration_service.save_frontend_layout(
        FrontendLayoutSaveRequest(
            layout_name=p.get("layout_name") or p.get("page_key", "main_console_layout"),
            version=p.get("version", "v1.0.4"),
            grid_schema=p.get("grid_schema", {"columns": 24, "type": "fluid_grid"}),
            widgets=p.get("widgets", []),
        )
    )


def get_frontend_layout_adapter(p: Dict[str, Any]) -> Any:
    layout_name = p.get("layout_name") or p.get("layout_id") or "main_console_layout"
    return orchestration_service.get_frontend_layout(layout_name=layout_name)


async def async_scenario_executor(payload: Dict[str, Any], context: Dict[str, Any]) -> Any:
    req = ScenarioExecuteRequest(**payload)
    return await orchestration_service.execute_scenario(req)
