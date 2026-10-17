"""Unified Inbound Gateway Scenario Router.

Accepts any incoming request, parses the scenario identifier,
and dynamically dispatches execution to registered domain handlers or microkernel DAG pipelines
without requiring any HTTP interface modifications.
"""
import inspect
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import logging

from src.core.telemetry import get_current_trace_id
from src.core.gateway.models import (
    DispatchRequest,
    DispatchResponse,
    RouteRuleDescriptor,
)

logger = logging.getLogger("opchub.gateway.router")


class RouteRule:
    """Internal representation of a scenario route rule."""

    def __init__(
        self,
        scenario: str,
        handler: Callable[..., Any],
        domain: str = "general",
        description: str = "",
    ):
        self.scenario = scenario
        self.handler = handler
        self.domain = domain
        self.description = description
        self.is_async = inspect.iscoroutinefunction(handler)
        self.sig = inspect.signature(handler)

    async def execute(self, payload: dict[str, Any], context: dict[str, Any]) -> Any:
        """Dynamically invoke handler matching its signature parameters."""
        params = list(self.sig.parameters.values())

        if len(params) == 0:
            result = self.handler()
        elif len(params) == 1:
            result = self.handler(payload)
        else:
            result = self.handler(payload, context)

        if inspect.iscoroutine(result):
            return await result
        return result


class ScenarioRouter:
    """Dynamic routing engine dispatching incoming scenario requests to backend handlers."""

    def __init__(self):
        self._routes: Dict[str, RouteRule] = {}

    def register(
        self,
        scenario: str,
        handler: Callable[..., Any],
        domain: str = "general",
        description: str = "",
    ) -> None:
        """Register a new scenario routing rule."""
        rule = RouteRule(
            scenario=scenario,
            handler=handler,
            domain=domain,
            description=description,
        )
        self._routes[scenario] = rule
        logger.info(f"Registered scenario route: '{scenario}' -> {domain} ({description})")

    def unregister(self, scenario: str) -> bool:
        """Remove a route rule by scenario code."""
        if scenario in self._routes:
            del self._routes[scenario]
            return True
        return False

    def has_scenario(self, scenario: str) -> bool:
        return scenario in self._routes

    def list_rules(self) -> List[RouteRuleDescriptor]:
        """Return list of all registered scenario descriptors."""
        return [
            RouteRuleDescriptor(
                scenario=r.scenario,
                domain=r.domain,
                description=r.description,
                is_async=r.is_async,
            )
            for r in self._routes.values()
        ]

    async def dispatch(self, req: DispatchRequest) -> DispatchResponse:
        """Process unified request and route to matching domain handler."""
        start_time = time.perf_counter()
        trace_id = req.context.get("trace_id") or get_current_trace_id()
        now_iso = datetime.now(timezone.utc).isoformat()

        if req.scenario not in self._routes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"Unknown scenario '{req.scenario}' received in dispatch gateway")
            return DispatchResponse(
                code=404,
                scenario=req.scenario,
                message=f"Unknown scenario: '{req.scenario}'. No matching route rule registered.",
                data=None,
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )

        rule = self._routes[req.scenario]
        try:
            res_data = await rule.execute(req.payload, req.context)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return DispatchResponse(
                code=200,
                scenario=req.scenario,
                message="success",
                data=res_data,
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(f"Error executing scenario '{req.scenario}': {e}")
            return DispatchResponse(
                code=500,
                scenario=req.scenario,
                message=str(e),
                data=None,
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )


# Global singleton instance of the ScenarioRouter
scenario_router = ScenarioRouter()
