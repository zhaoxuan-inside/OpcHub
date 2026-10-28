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
from src.core.rbac import has_permission, is_owner_or_admin, parse_identity, HIGH_RISK_PERMISSIONS
from src.core.audit import audit_service
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
        handler: Optional[Callable[..., Any]] = None,
        version: str = "v1.0.0",
        domain: str = "general",
        description: str = "",
        required_permission: str = "",
        owner_check: Optional[Dict[str, Any]] = None,
        pipeline: Optional[str] = None,
    ):
        self.scenario = scenario
        self.handler = handler
        self.version = version
        self.domain = domain
        self.description = description
        self.required_permission = required_permission or ""
        self.owner_check = owner_check or None
        self.pipeline = pipeline or None
        self.is_async = True
        self.sig = inspect.signature(handler) if handler else None

    async def execute(self, payload: dict[str, Any], context: dict[str, Any]) -> Any:
        """Dynamically invoke the configured execution path."""
        if self.pipeline:
            from src.domains.orchestration.models import ScenarioExecuteRequest
            from src.domains.orchestration.service import orchestration_service

            result = await orchestration_service.execute_scenario(
                ScenarioExecuteRequest(
                    scenario_code=self.pipeline,
                    inputs=dict(payload or {}),
                    context=dict(context or {}),
                )
            )
            if result.status != "SUCCESS":
                message = (result.error_message or "场景执行失败").replace("Node ", "节点 ").replace(
                    " execution error: ", " 执行失败："
                )
                if "权限" in message or "登录" in message:
                    raise PermissionError(message)
                raise ValueError(message)
            output = dict(result.final_output or {})
            if "response" in output:
                return output["response"]
            # Legacy response shapes: publish/claim/vote scenarios expose one
            # primary result key. Unwrap it so the gateway envelope stays stable.
            for key in (
                "created_thread", "created_answer", "created_comment", "created_product",
                "created_policy", "created_demand", "created_bid", "created_perk",
                "created_claim", "created_entry", "created_doc", "updated_thread",
                "review_submission", "vote_result", "feed", "feed_result", "profile",
                "activation", "audit_report", "report", "result",
            ):
                if key in output:
                    return output[key]
            return output

        if not self.handler:
            raise KeyError(f"Route '{self.scenario}' has no pipeline or handler")
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
        handler: Optional[Callable[..., Any]] = None,
        version: str = "v1.0.0",
        domain: str = "general",
        description: str = "",
        is_default: bool = True,
        required_permission: str = "",
        owner_check: Optional[Dict[str, Any]] = None,
        pipeline: Optional[str] = None,
    ) -> None:
        """Register a new scenario routing rule under a specific code version."""
        rule = RouteRule(
            scenario=scenario,
            handler=handler,
            version=version,
            domain=domain,
            description=description,
            required_permission=required_permission,
            owner_check=owner_check,
            pipeline=pipeline,
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

        # 2.5 RBAC (declarative permission) + ABAC (ownership) enforcement
        resolved_token = (
            req.token
            or (req.context or {}).get("token")
            or (req.payload or {}).get("token")
        )
        identity = parse_identity(resolved_token)
        client_ip = (req.context or {}).get("client_ip", "")

        if not has_permission(identity["role"], rule.required_permission):
            await audit_service.record(
                action=f"rbac.denied:{req.scenario}",
                actor_id=identity["uid"],
                actor_role=identity["role"],
                permission=rule.required_permission,
                result="DENIED",
                ip_address=client_ip,
                trace_id=trace_id,
                detail={"scenario": req.scenario, "authenticated": identity["authenticated"]},
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if not identity["authenticated"]:
                return DispatchResponse(
                    code=401,
                    scenario=req.scenario,
                    version=rule.version,
                    message="该操作需要登录，请先登录创客账号",
                    data={"login_required": True, "required_permission": rule.required_permission},
                    trace_id=trace_id,
                    timestamp=now_iso,
                    duration_ms=duration_ms,
                )
            return DispatchResponse(
                code=403,
                scenario=req.scenario,
                version=rule.version,
                message=f"权限不足：缺少所需权限 '{rule.required_permission}'",
                data={"required_permission": rule.required_permission, "role": identity["role"]},
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )

        # First-login enforcement: rotate credentials before high-risk operations
        if identity.get("must_change_password") and rule.required_permission in HIGH_RISK_PERMISSIONS:
            await audit_service.record(
                action=f"auth.must_change_password:{req.scenario}",
                actor_id=identity["uid"],
                actor_role=identity["role"],
                permission=rule.required_permission,
                result="DENIED",
                ip_address=client_ip,
                trace_id=trace_id,
                detail={"scenario": req.scenario, "reason": "must_change_password"},
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return DispatchResponse(
                code=403,
                scenario=req.scenario,
                version=rule.version,
                message="首次登录安全策略：请先修改初始密码后再执行该操作",
                data={"must_change_password": True},
                trace_id=trace_id,
                timestamp=now_iso,
                duration_ms=duration_ms,
            )

        if rule.owner_check:
            rt = rule.owner_check.get("resource_type", "")
            id_field = rule.owner_check.get("id_field", "resource_id")
            rid = str(
                (req.payload or {}).get(id_field)
                or (req.context or {}).get(id_field)
                or ""
            )
            if not is_owner_or_admin(identity["uid"], identity["role"], rt, rid):
                await audit_service.record(
                    action=f"abac.denied:{req.scenario}",
                    actor_id=identity["uid"],
                    actor_role=identity["role"],
                    resource_type=rt,
                    resource_id=rid,
                    result="DENIED",
                    ip_address=client_ip,
                    trace_id=trace_id,
                    detail={"scenario": req.scenario, "id_field": id_field},
                )
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return DispatchResponse(
                    code=403,
                    scenario=req.scenario,
                    version=rule.version,
                    message="权限拒绝：您无权修改或操作非本人拥有的资产",
                    data={"abac_denied": True, "resource_type": rt},
                    trace_id=trace_id,
                    timestamp=now_iso,
                    duration_ms=duration_ms,
                )

        # 3. Context Injection & Deprecation Inspection
        ctx = dict(req.context)
        ctx["user_id"] = identity["uid"]
        ctx["user_role"] = identity["role"]
        ctx["token"] = resolved_token or ""
        ctx["nickname"] = identity.get("nickname", "")
        ctx["email"] = identity.get("email", "")
        ctx["account_type"] = identity.get("account_type", "MAKER")
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

            # Audit privileged state-changing scenarios (those declaring a required permission)
            if rule.required_permission:
                await audit_service.record(
                    action=f"scenario:{req.scenario}",
                    actor_id=identity["uid"],
                    actor_role=identity["role"],
                    permission=rule.required_permission,
                    result="SUCCESS",
                    ip_address=client_ip,
                    trace_id=trace_id,
                    detail={"scenario": req.scenario},
                )
            
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
            # Preserve REST-like semantic codes inside the unified envelope
            if isinstance(e, PermissionError):
                err_code = 403
            elif isinstance(e, KeyError):
                err_code = 404
            elif isinstance(e, ValueError):
                err_code = 400
            else:
                err_code = 500
            return DispatchResponse(
                code=err_code,
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
