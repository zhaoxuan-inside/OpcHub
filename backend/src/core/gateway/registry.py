"""Gateway scenario routes registry adapter.

Delegates route loading to GatewayConfigLoader, reading scenario routes and version
governance rules strictly from external configuration files (zero hardcoding).
"""
from typing import Optional
from src.core.gateway.router import scenario_router
from src.core.gateway.config_loader import GatewayConfigLoader


def register_default_scenario_routes(config_path: Optional[str] = None) -> int:
    """Load and register all standard scenario rules from external YAML configuration."""
    return GatewayConfigLoader.apply_routes_to_router(config_path=config_path, router=scenario_router)
