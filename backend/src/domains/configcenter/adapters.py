"""配置中心场景适配器：写/发布走元管线（{action,payload} 信封），读直连。

resolve 为宿主运行时数据面高频调用：自然载荷（namespace/key/user_id），
读直连 handler（框架约定）。
"""
from typing import Any, Dict

from src.domains.configcenter.service import config_center_service


async def configcenter_write_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Execute one config-center mutation via OPC_CONFIGCENTER_PIPELINE."""
    from src.domains.configcenter.ops import ensure_configcenter_pipeline
    from src.domains.orchestration.models import ScenarioExecuteRequest
    from src.domains.orchestration.service import orchestration_service

    ensure_configcenter_pipeline()

    action = str((p or {}).get("action") or "")
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_CONFIGCENTER_PIPELINE",
            version="v1.0.0",
            inputs={"action": action, "payload": (p or {}).get("payload") or {}},
            context=dict(c or {}),
        )
    )
    if res.status != "SUCCESS":
        message = res.error_message or "Config-center pipeline failed"
        for prefix in (
            "Node step_persist execution error: ",
            "Node step_guard execution error: ",
            "Guard check failed: ",
        ):
            if message.startswith(prefix):
                message = message[len(prefix):]
                break
        # error_type 忠实携带原始异常类
        if res.error_type == "PermissionError":
            raise PermissionError(message)
        if res.error_type == "KeyError":
            raise KeyError(message)
        raise ValueError(message)
    return res.final_output.get("config_result") or res.final_output


def config_namespaces_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    return config_center_service.list_namespaces(p or {}, c or {})


def config_items_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    return config_center_service.list_items(p or {}, c or {})


def config_history_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    return config_center_service.item_history(p or {}, c or {})


def config_resolve_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """宿主运行时生效值解析：自然载荷（namespace/key/user_id），读直连。"""
    return config_center_service.resolve(p or {}, c or {})
