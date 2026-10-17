"""Unified Inbound Gateway package."""
from src.core.gateway.models import DispatchRequest, DispatchResponse, RouteRuleDescriptor
from src.core.gateway.router import scenario_router
from src.core.gateway.registry import register_default_scenario_routes

__all__ = [
    "DispatchRequest",
    "DispatchResponse",
    "RouteRuleDescriptor",
    "scenario_router",
    "register_default_scenario_routes",
]
