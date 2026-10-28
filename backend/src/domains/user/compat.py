"""Compatibility bridge: run a declarative scenario from legacy sync/async APIs.

The user / auth domain kept a few synchronous call sites (``generate_captcha``,
``send_verification_code``, …) for backward compatibility. Business flow now
lives exclusively in the scenario assets, so this module only provides the
transport used by the compatibility shims to execute those scenarios.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Optional

from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service


async def execute_scenario(
    scenario_code: str,
    inputs: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
    version: str = "v1.0.0",
):
    """Execute one scenario asset and return the raw execution result."""
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario_code,
            version=version,
            inputs=dict(inputs or {}),
            context=dict(context or {}),
        )
    )


def execute_scenario_sync(
    scenario_code: str,
    inputs: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
    version: str = "v1.0.0",
):
    """Synchronous facade used by legacy sync API surfaces.

    When called from inside a running event loop the scenario runs on a private
    thread with its own loop, so sync shims stay usable from async tests and
    async adapters without re-entering the caller's loop.
    """
    coroutine = execute_scenario(scenario_code, inputs, context, version)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coroutine).result()


def raise_for_failure(result: Any) -> dict[str, Any]:
    """Translate a non-success execution result into the legacy exception types."""
    if getattr(result, "status", None) == "SUCCESS":
        return dict(result.final_output or {})
    message = getattr(result, "error_message", None) or "场景执行失败"
    cleaned = message.replace("Guard check failed: ", "")
    if cleaned.startswith("Node ") and " execution error: " in cleaned:
        cleaned = cleaned.split(" execution error: ", 1)[1]
    cleaned = cleaned.strip()
    if "权限" in cleaned or "需要登录" in cleaned:
        raise PermissionError(cleaned)
    if " not found" in cleaned:
        raise KeyError(cleaned)
    raise ValueError(cleaned)
