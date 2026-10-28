"""Dynamic Configuration-Driven Route Loader for Inbound Gateway.

Parses external YAML routing and version policy configurations, resolves handlers
dynamically via reflection, and registers them into ScenarioRouter.
Enables zero-hardcoding architecture: adding/updating routes and managing old/new versions
is achieved purely via configuration edits without touching code.
"""
import os
import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import yaml

from src.core.gateway.router import scenario_router, ScenarioRouter

logger = logging.getLogger("opchub.gateway.config_loader")


def _import_symbol(target_str: str) -> Any:
    """Dynamically resolve module and attribute from target string.
    
    Robustly handles formats like:
      - 'src.domains.products.service:product_service.list_products'
      - 'src.domains.products.service.product_service:list_products'
      - 'src.domains.products.models:ProductCreate'
    """
    if ":" in target_str:
        module_path, attr_path = target_str.split(":", 1)
    else:
        parts = target_str.rsplit(".", 1)
        if len(parts) == 2:
            module_path, attr_path = parts[0], parts[1]
        else:
            raise ValueError(f"Invalid import target specification: {target_str}")

    attrs = [a for a in attr_path.split(".") if a]
    module = None
    curr_mod = module_path
    
    while curr_mod:
        try:
            module = importlib.import_module(curr_mod)
            break
        except ModuleNotFoundError:
            if "." in curr_mod:
                curr_mod, extra_attr = curr_mod.rsplit(".", 1)
                attrs.insert(0, extra_attr)
            else:
                raise ModuleNotFoundError(f"Cannot import module '{module_path}' for target '{target_str}'")

    obj = module
    for a in attrs:
        obj = getattr(obj, a)
    return obj


def _wrap_handler(
    raw_handler: Callable[..., Any],
    model_cls: Optional[Any] = None,
    args_type: Optional[str] = None,
    key_name: Optional[str] = None,
    upgrade_adapter_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Callable[..., Any]:
    """Wrap raw handler with model instantiation, parameter unpacking, and payload upgrades."""

    def wrapped_handler(payload: Dict[str, Any] = None, context: Dict[str, Any] = None):
        if payload is None:
            payload = {}
        if context is None:
            context = {}

        # 1. Apply upgrade adapter if present (e.g. migrating legacy fields to new format)
        data = payload
        if upgrade_adapter_func:
            data = upgrade_adapter_func(payload)

        # 2. Invoke based on handler contract
        if model_cls is not None:
            model_instance = model_cls(**data)
            return raw_handler(model_instance)
        elif args_type == "key":
            val = data.get(key_name) if key_name else None
            return raw_handler(val)
        elif args_type == "kwargs":
            import inspect
            sig = inspect.signature(raw_handler)
            valid_kwargs = {k: v for k, v in data.items() if k in sig.parameters}
            return raw_handler(**valid_kwargs)
        else:
            import inspect
            sig = inspect.signature(raw_handler)
            params = list(sig.parameters.values())
            if len(params) == 0:
                return raw_handler()
            elif len(params) == 1:
                return raw_handler(data)
            else:
                return raw_handler(data, context)

    return wrapped_handler


class GatewayConfigLoader:
    """Loads and registers gateway routes and version policies from external YAML config files."""

    DEFAULT_CONFIG_LOCATIONS = [
        Path("backend/config/gateway_routes.yaml"),
        Path("config/gateway_routes.yaml"),
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "gateway_routes.yaml",
    ]

    @classmethod
    def find_config_file(cls, config_path: Optional[str] = None) -> Path:
        """Find the configuration file from provided path, config setting, env var, or search paths."""
        if config_path and Path(config_path).is_file():
            return Path(config_path)

        # Configuration-driven routes file path (application.yaml gateway.routes_config_file)
        try:
            from src.core.config import settings
            cfg_path = getattr(settings, "gateway_routes_config_file", "")
            if cfg_path:
                candidate = Path(cfg_path)
                if candidate.is_file():
                    return candidate.resolve()
                for base in cls.DEFAULT_CONFIG_LOCATIONS:
                    sibling = base.parent.parent / cfg_path
                    if sibling.is_file():
                        return sibling.resolve()
        except Exception:
            pass

        env_path = os.getenv("OPCHUB_GATEWAY_ROUTES_CONFIG")
        if env_path and Path(env_path).is_file():
            return Path(env_path)

        for loc in cls.DEFAULT_CONFIG_LOCATIONS:
            if loc.is_file():
                return loc.resolve()

        raise FileNotFoundError(
            "Gateway routes configuration file not found in default locations. "
            "Please check backend/config/gateway_routes.yaml or set OPCHUB_GATEWAY_ROUTES_CONFIG."
        )

    @classmethod
    def load_config_dict(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        target_file = cls.find_config_file(config_path)
        with open(target_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data

    @classmethod
    def apply_routes_to_router(
        cls,
        config_path: Optional[str] = None,
        router: ScenarioRouter = scenario_router,
        clear_existing: bool = True,
    ) -> int:
        """Parse configuration and populate the ScenarioRouter with routes and version policies."""
        config_data = cls.load_config_dict(config_path)
        gateway_section = config_data.get("gateway", {})

        default_version = gateway_section.get("default_version", "v1.0.0")
        version_policy = gateway_section.get("version_policy", {})
        routes_list = gateway_section.get("routes", [])

        if clear_existing:
            router.clear()

        # 1. Configure router-level version governance policies
        router.set_version_policy(
            default_version=default_version,
            unknown_strategy=version_policy.get("unknown_version_strategy", "fallback_to_default"),
            sunset_versions=version_policy.get("sunset_versions", {}),
            deprecated_versions=version_policy.get("deprecated_versions", {}),
        )

        # 2. Register each route defined in config
        count = 0
        for entry in routes_list:
            scenario = entry.get("scenario")
            if not scenario:
                continue

            version = entry.get("version", default_version)
            domain = entry.get("domain", "general")
            description = entry.get("description", "")
            is_default = entry.get("is_default", False)
            handler_str = entry.get("handler")
            model_str = entry.get("model")
            args_type = entry.get("args_type")
            key_name = entry.get("key_name")
            upgrade_adapter_str = entry.get("upgrade_adapter")
            required_permission = entry.get("required_permission", "")
            owner_check = entry.get("owner_check")
            pipeline = entry.get("pipeline") or entry.get("scenario_code")

            if pipeline:
                router.register(
                    scenario=scenario,
                    handler=None,
                    version=version,
                    domain=domain,
                    description=description,
                    is_default=is_default,
                    required_permission=required_permission,
                    owner_check=owner_check,
                    pipeline=pipeline,
                )
                count += 1
                continue

            raw_handler = _import_symbol(handler_str) if handler_str else None
            model_cls = _import_symbol(model_str) if model_str else None
            upgrade_func = _import_symbol(upgrade_adapter_str) if upgrade_adapter_str else None

            if not raw_handler:
                logger.warning(f"Skipping route '{scenario}' [{version}]: no handler resolved.")
                continue

            wrapped = _wrap_handler(
                raw_handler=raw_handler,
                model_cls=model_cls,
                args_type=args_type,
                key_name=key_name,
                upgrade_adapter_func=upgrade_func,
            )

            router.register(
                scenario=scenario,
                handler=wrapped,
                version=version,
                domain=domain,
                description=description,
                is_default=is_default,
                required_permission=required_permission,
                owner_check=owner_check,
            )
            count += 1

        logger.info(f"Loaded {count} gateway routes from configuration into ScenarioRouter.")
        return count


def load_scenario_routes_from_yaml(
    router: ScenarioRouter = scenario_router,
    config_path: Optional[str] = None,
    clear_existing: bool = True,
) -> int:
    """Convenience alias to load and register routes into ScenarioRouter."""
    return GatewayConfigLoader.apply_routes_to_router(
        config_path=config_path,
        router=router,
        clear_existing=clear_existing,
    )

