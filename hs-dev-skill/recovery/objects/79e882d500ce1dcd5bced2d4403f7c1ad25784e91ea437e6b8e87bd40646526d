"""Unified Inbound Gateway package."""
from src.core.gateway.models import DispatchRequest, DispatchResponse, RouteRuleDescriptor
from src.core.gateway.router import scenario_router, ScenarioRouter
from src.core.gateway.config_loader import GatewayConfigLoader


def register_default_scenario_routes(config_path: str = None) -> int:
    """Load and register scenario route rules from external configuration into router."""
    return GatewayConfigLoader.apply_routes_to_router(config_path=config_path, router=scenario_router)


__all__ = [
    "DispatchRequest",
    "DispatchResponse",
    "RouteRuleDescriptor",
    "scenario_router",
    "ScenarioRouter",
    "GatewayConfigLoader",
    "register_default_scenario_routes",
]
