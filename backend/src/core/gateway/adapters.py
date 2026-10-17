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


def demands_bid_adapter(p: Dict[str, Any], c: Dict[str, Any]) -> Any:
    return demand_service.submit_bid(
        demand_id=p.get("demand_id"),
        payload=BidCreate(**p.get("bid_payload", p)),
    )


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
