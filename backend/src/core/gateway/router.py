"""Unified Inbound Gateway Scenario Router.

Accepts any incoming request, parses the scenario identifier and code version,
evaluates version governance policies (sunset, deprecation, fallback),
and dynamically dispatches execution to registered domain handlers or microkernel DAG pipelines
without requiring any HTTP interface modifications. Zero-hardcoding configuration-driven.
"""
import inspect
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

from src.core.telemetry import get_current_trace_id
from src.core.gateway.models import (
    DispatchRequest,
    DispatchResponse,
    RouteRuleDescriptor,
)

logger = logging.getLogger("opchub.gateway.router")


class RouteRule:
    """Internal representation of a scenario route rule with version."""

    def __init__(
        self,
        scenario: str,
        handler: Callable[..., Any],
        version: str = "v1.0.0",
        domain: str = "general",
        description: str = "",
    ):
        self.scenario = scenario
        self.handler = handler
        self.version = version
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
        # Key: (scenario, version)
        self._routes: Dict[Tuple[str, str], RouteRule] = {}
        # Default version for a scenario
        self._default_versions: Dict[str, str] = {}
        # Router-level version governance policies
        self.default_version: str = "v1.0.0"
        self.unknown_strategy: str = "fallback_to_default"  # fallback_to_default | reject
        self.sunset_versions: Dict[str, Dict[str, Any]] = {}
        self.deprecated_versions: Dict[str, Dict[str, Any]] = {}

    def clear(self) -> None:
        """Clear all registered routes and reset version configuration."""
        self._routes.clear()
        self._default_versions.clear()
        self.sunset_versions.clear()
        self.deprecated_versions.clear()

    def set_version_policy(
        self,
        default_version: str = "v1.0.0",
        unknown_strategy: str = "fallback_to_default",
        sunset_versions: Optional[Dict[str, Any]] = None,
        deprecated_versions: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set dynamic version governance policies loaded from configuration."""
        self.default_version = default_version
        self.unknown_strategy = unknown_strategy
        self.sunset_versions = sunset_versions or {}
        self.deprecated_versions = deprecated_versions or {}
        logger.info(
            f"Configured router version policy: default={default_version}, "
            f"unknown_strategy={unknown_strategy}, sunset_versions={list(self.sunset_versions.keys())}"
        )

    def register(
        self,
        scenario: str,
        handler: Callable[..., Any],
        version: str = "v1.0.0",
        domain: str = "general",
        description: str = "",
        is_default: bool = True,
    ) -> None:
        """Register a new scenario routing rule under a specific code version."""
        rule = RouteRule(
            scenario=scenario,
            handler=handler,
            version=version,
            domain=domain,
            description=description,
        )
        self._routes[(scenario, version)] = rule
        if is_default or scenario not in self._default_versions:
            self._default_versions[scenario] = version
        logger.info(f"Registered scenario route: '{scenario}' [ver: {version}] -> {domain} ({description})")

    def unregister(self, scenario: str, version: Optional[str] = None) -> bool:
        """Remove a route rule by scenario code and optional version."""
        if version:
            key = (scenario, version)
            if key in self._routes:
                del self._routes[key]
                if self._default_versions.get(scenario) == version:
                    remaining = [v for s, v in self._routes.keys() if s == scenario]
                    if remaining:
                        self._default_versions[scenario] = remaining[0]
                    else:
                        self._default_versions.pop(scenario, None)
                return True
            return False
        else:
            removed = False
            keys_to_del = [k for k in self._routes.keys() if k[0] == scenario]
            for k in keys_to_del:
                del self._routes[k]
                removed = True
            self._default_versions.pop(scenario, None)
            return removed

    def get_rule(self, scenario: str, version: Optional[str] = None) -> Optional[RouteRule]:
        """Resolve route rule supporting exact version matching, wildcard '*', and policy fallback."""
        req_ver = version or self.default_version

        # 1. Exact match (scenario, requested_version)
        if (scenario, req_ver) in self._routes:
            return self._routes[(scenario, req_ver)]

        # 2. Wildcard rule (scenario, "*")
        if (scenario, "*") in self._routes:
            return self._routes[(scenario, "*")]

        # If strategy is reject unknown versions for this scenario, don't fall back
        if self.unknown_strategy == "reject":
            # Only match if requested version is explicitly present
            return None

        # 3. Default version fallback
        if scenario in self._default_versions:
            def_ver = self._default_versions[scenario]
            if (scenario, def_ver) in self._routes:
                return self._routes[(scenario, def_ver)]

        # 4. Any registered version for this scenario
        for (s, v), rule in self._routes.items():
            if s == scenario:
                return rule

        return None

    def has_scenario(self, scenario: str, version: Optional[str] = None) -> bool:
        return self.get_rule(scenario, version) is not None

    def list_rules(self) -> List[RouteRuleDescriptor]:
        """Return list of all registered scenario descriptors with version info."""
        return [
            RouteRuleDescriptor(
                scenario=r.scenario,
                version=r.version,
                domain=r.domain,
                description=r.description,
                is_async=r.is_async,
            )
            for r in self._routes.values()
        ]

    async def dispatch(self, req: DispatchRequest) -> DispatchResponse:
        """Process unified request and route to matching domain handler by scenario & version.
        
        Evaluates lifecycle policies (sunset, deprecation) and gracefully resolves legacy requests.
        """
        start_time = time.perf_counter()
        trace_id = req.context.get("trace_id") or get_current_trace_id()
        now_iso = datetime.now(timezone.utc).isoformat()
        requested_ver = req.version or self.default_version

        # 1. Check Sunset / EOL Policy for old versions
        if requested_ver in self.sunset_versions:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            sunset_info = self.sunset_versions[requested_ver]
            code = sunset_info.get("code", 426)
            min_ver = sunset_info.get("min_supported_version", self.default_version)
            msg = sunset_info.get(
                "message",
                f"Client code version '{requested_ver}' has been sunset. Minimum supported version is '{min_ver}'."
            )
            logger.warning(f"Request rejected by Sunset Policy: version '{requested_ver}' on scenario '{req.scenario}'")
            return DispatchResponse(
                code=code,
                scenario=req.scenario,
                version=requested_ver,
                message=msg,
                data={
                    "sunset": True,
                    "requested_version": requested_ver,
                    "min_supported_version": min_ver,
                    "upgrade_required": True,
                },
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )

        # 2. Resolve Route Rule
        rule = self.get_rule(req.scenario, requested_ver)
        if not rule:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                f"No matching route for scenario '{req.scenario}' [version: '{requested_ver}']"
            )
            return DispatchResponse(
                code=404,
                scenario=req.scenario,
                version=requested_ver,
                message=f"Unknown scenario '{req.scenario}' version '{requested_ver}'. No matching route rule registered.",
                data=None,
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )

        # 3. Context Injection & Deprecation Inspection
        ctx = dict(req.context)
        ctx["requested_version"] = requested_ver
        ctx["matched_version"] = rule.version
        ctx["is_fallback"] = (rule.version != requested_ver and rule.version != "*")

        if requested_ver in self.deprecated_versions:
            deprec_info = self.deprecated_versions[requested_ver]
            ctx["deprecation_warning"] = deprec_info.get("message", f"Version '{requested_ver}' is deprecated.")

        # 4. Handler Execution
        try:
            res_data = await rule.execute(req.payload, ctx)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # If deprecated, include deprecation hint in response message or data
            msg = "success"
            if "deprecation_warning" in ctx:
                msg = f"success (warning: {ctx['deprecation_warning']})"

            return DispatchResponse(
                code=200,
                scenario=req.scenario,
                version=rule.version,
                message=msg,
                data=res_data,
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(f"Error executing scenario '{req.scenario}' [{rule.version}]: {e}")
            return DispatchResponse(
                code=500,
                scenario=req.scenario,
                version=rule.version,
                message=str(e),
                data=None,
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )


# Global singleton instance of the ScenarioRouter
scenario_router = ScenarioRouter()
