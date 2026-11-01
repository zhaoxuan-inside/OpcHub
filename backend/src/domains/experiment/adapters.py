"""实验域场景适配器：网关统一分发的薄壳。

* 写/分流/上报统一经 OPC_EXPERIMENT_PIPELINE（experiment_write_adapter，
  {action, payload} 信封）；
* 读（清单/详情/读出）直连 handler（框架"读直连"约定）。
"""
from typing import Any, Dict

from src.domains.experiment.service import experiment_service


def _actor_display_name(uid: str) -> str:
    from src.domains.user.entities import account_entity

    doc = account_entity.adapter.get(uid) if uid else None
    return str((doc or {}).get("nickname") or (doc or {}).get("email") or uid)


async def experiment_write_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """Execute one experiment action via OPC_EXPERIMENT_PIPELINE."""
    from src.domains.experiment.ops import ensure_experiment_pipeline
    from src.domains.orchestration.models import ScenarioExecuteRequest
    from src.domains.orchestration.service import orchestration_service

    ensure_experiment_pipeline()

    action = str((p or {}).get("action") or "")
    ctx = dict(c or {})
    uid = str(ctx.get("user_id") or "")
    if uid:
        ctx.setdefault("user_name", _actor_display_name(uid))

    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_EXPERIMENT_PIPELINE",
            version="v1.0.0",
            inputs={"action": action, "payload": (p or {}).get("payload") or {}},
            context=ctx,
        )
    )
    if res.status != "SUCCESS":
        message = res.error_message or "Experiment pipeline failed"
        for prefix in (
            "Node step_persist execution error: ",
            "Node step_guard execution error: ",
            "Guard check failed: ",
        ):
            if message.startswith(prefix):
                message = message[len(prefix):]
                break
        # error_type 忠实携带原始异常类，不做消息关键词猜测
        if res.error_type == "PermissionError":
            raise PermissionError(message)
        if res.error_type == "KeyError":
            raise KeyError(message)
        raise ValueError(message)
    return res.final_output.get("experiment_result") or res.final_output


async def experiment_assign_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """宿主客户端数据面分流入口：自然载荷（experiment_key[, user_id]）→ 内部信封。"""
    return await experiment_write_adapter({"action": "assign", "payload": dict(p or {})}, c)


async def experiment_outcome_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    """宿主客户端结果上报入口：自然载荷（experiment_key/metric/value）→ 内部信封。"""
    return await experiment_write_adapter({"action": "outcome.report", "payload": dict(p or {})}, c)


def experiment_list_adapter(p: Dict[str, Any] = None, c: Dict[str, Any] = None) -> Any:
    return experiment_service.list_experiments(p or {}, c or {})


def experiment_detail_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    return experiment_service.get_experiment(p or {}, c or {})


def experiment_readout_adapter(p: Dict[str, Any], c: Dict[str, Any] = None) -> Any:
    return experiment_service.readout(p or {}, c or {})


# 模块导入即幂等种子（flow_engine 启动构建时纳入 release）
from src.domains.experiment.ops import ensure_experiment_pipeline as _ensure  # noqa: E402

_ensure()
