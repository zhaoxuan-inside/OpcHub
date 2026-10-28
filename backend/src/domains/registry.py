"""Domain function operator assembly.

Only single-responsibility *pure function* operators belong here: calculations,
normalisers, assemblers and state-transition policies. Storage, guards,
validation, notifications, audit and metrics are provided by the generic
operator kernel.

A domain module must expose ``register_<domain>_operators(registry)`` only if it
registers directly; the default convention is that importing
``src.domains.<domain>.functions`` declares operators through
``src.core.operators.sdk.operator``.
"""
from __future__ import annotations

import importlib
import logging

logger = logging.getLogger("opchub.domains.registry")

DOMAIN_FUNCTION_MODULES = [
    "src.domains.products.functions",
    "src.domains.policies.functions",
    "src.domains.demands.functions",
    "src.domains.perks.functions",
    "src.domains.compliance.functions",
    "src.domains.moderation.functions",
    "src.domains.forum.functions",
    "src.domains.sop.functions",
    "src.domains.loyalty.functions",
    "src.domains.interactions.functions",
    "src.domains.notifications.functions",
    "src.domains.user.functions",
    "src.domains.orchestration.functions",
    "src.domains.telemetry.functions",
    "src.domains.home.functions",
]

DOMAIN_CONTROL_MODULES = [
    "src.domains.orchestration.control_ops",
]

DOMAIN_ENTITY_MODULES = [
    "src.domains.products.entities",
    "src.domains.policies.entities",
    "src.domains.demands.entities",
    "src.domains.perks.entities",
    "src.domains.compliance.entities",
    "src.domains.moderation.entities",
    "src.domains.forum.entities",
    "src.domains.sop.entities",
    "src.domains.loyalty.entities",
    "src.domains.interactions.entities",
    "src.domains.notifications.entities",
    "src.domains.user.entities",
    "src.domains.orchestration.entities",
    "src.domains.telemetry.entities",
    "src.domains.home.entities",
]


def _import_optional(module_name: str, imported: list[str]) -> None:
    try:
        importlib.import_module(module_name)
        imported.append(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if module_name == missing or module_name.startswith(f"{missing}."):
            logger.debug("Domain module not available yet: %s", module_name)
            return
        raise


def import_entity_specs() -> list[str]:
    """Import domain entity specs so the generic store can resolve them."""
    imported: list[str] = []
    for module_name in DOMAIN_ENTITY_MODULES:
        _import_optional(module_name, imported)
    return imported


def import_domain_functions() -> list[str]:
    imported: list[str] = []
    import_entity_specs()
    for module_name in DOMAIN_CONTROL_MODULES:
        _import_optional(module_name, imported)
    for module_name in DOMAIN_FUNCTION_MODULES:
        _import_optional(module_name, imported)
    return imported
