"""Framework governance operators (hot reload / gateway introspection).

These operators expose infrastructure controls only: they translate declarative
node arguments into calls on the versioned hot-reload engine, the scenario
router and the gateway configuration loader. They contain no business rule and
never import ``src.domains``.
"""
from __future__ import annotations

from typing import Any

from src.core.operators.sdk import operator


@operator(
    "query.framework.hot_reload_status",
    category="QUERY",
    description="Read file-sensing watcher status and staged/activated code versions",
)
def hot_reload_status(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.microkernel.watcher import hot_reload_engine

    return {"status": hot_reload_engine.get_status()}


@operator(
    "transform.framework.hot_reload_scan",
    category="TRANSFORM",
    description="Trigger one file-system scan and stage detected python changes",
)
def hot_reload_scan(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.microkernel.watcher import hot_reload_engine

    changes = hot_reload_engine.scan_changes()
    status = hot_reload_engine.get_status()
    return {
        "scan": {
            "status": "ok",
            "newly_detected_count": len(changes),
            "staged_count": int(status.get("staged_changes_count") or 0),
            "detected_changes": [change.model_dump() for change in changes],
        }
    }


@operator(
    "transform.framework.hot_reload_activate",
    category="TRANSFORM",
    description="Atomically load staged python changes for one target version",
)
def hot_reload_activate(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.microkernel.watcher import hot_reload_engine

    target_version = str(args.get("version") or params.get("version") or "v1.0.0")
    file_paths = args.get("file_paths")
    if file_paths is None:
        file_paths = params.get("file_paths")
    return {
        "activation": hot_reload_engine.activate_version(
            target_version=target_version,
            file_paths=file_paths,
            reload_gateway_routes=True,
        )
    }


@operator(
    "transform.framework.gateway_reload",
    category="TRANSFORM",
    description="Activate pending modules and reload gateway routing rules from configuration",
)
def gateway_reload(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.config import settings
    from src.core.gateway.config_loader import GatewayConfigLoader
    from src.core.gateway.router import scenario_router
    from src.core.microkernel.watcher import hot_reload_engine

    target_version = str(
        args.get("version") or params.get("version") or getattr(settings, "app_version", "v1.0.0")
    )
    activation = hot_reload_engine.activate_version(
        target_version=target_version,
        reload_gateway_routes=False,
    )
    reloaded = GatewayConfigLoader.apply_routes_to_router(router=scenario_router)
    return {
        "reload": {
            "status": "ok",
            "reloaded_routes_count": int(reloaded),
            "hot_reload": activation,
        }
    }


@operator(
    "query.framework.gateway_rules",
    category="QUERY",
    description="List every scenario routing rule currently mounted on the gateway",
)
def gateway_rules(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from src.core.gateway.router import scenario_router

    return {"rules": [rule.model_dump() for rule in scenario_router.list_rules()]}
