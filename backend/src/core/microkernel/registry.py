"""Atomic operator registry for the business-agnostic operator kernel.

The registry only assembles operators; it contains no business logic and no
domain-specific operator implementations. Two sources are attached:

1. ``src.core.operators`` – generic primitives (guard / validate / entity /
   transform / notify / audit / metric / render / external / response).
2. ``src.domains.registry`` – single-responsibility domain function operators
   (pure calculations and assemblers only).

Every operator is checked by ``tests/test_operator_contract.py``: domain
registrations may not perform orchestration and generic operators may not import
``src.domains``.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from src.core.microkernel.dispatcher import DispatchMode, dispatcher

ActionHandler = Callable[[dict[str, Any], dict[str, Any]], Any]


class AtomicRegistry:
    """Holds atomic action handlers, their compensators and descriptors."""

    def __init__(self, auto_register: bool = True):
        self._handlers: dict[str, ActionHandler] = {}
        self._compensators: dict[str, ActionHandler] = {}
        if auto_register:
            self._register_all()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def register(
        self,
        name: str,
        handler: ActionHandler,
        domain: str = "core",
        description: str = "",
        dispatch_mode: DispatchMode = DispatchMode.IN_PROCESS,
        remote_endpoint: Optional[str] = None,
        compensator: Optional[ActionHandler] = None,
    ) -> None:
        """Register one atomic handler, optional compensator and metadata."""
        self._handlers[name] = handler
        if compensator is not None:
            self._compensators[name] = compensator
        else:
            self._compensators.pop(name, None)
        try:
            dispatcher.register_descriptor(
                name=name,
                domain=domain,
                description=description,
                mode=dispatch_mode,
                remote_endpoint=remote_endpoint,
            )
        except Exception:  # pragma: no cover - descriptors are best effort
            pass

    def unregister(self, name: str) -> bool:
        existed = self._handlers.pop(name, None) is not None
        self._compensators.pop(name, None)
        try:
            dispatcher.unregister_descriptor(name)
        except Exception:  # pragma: no cover
            pass
        return existed

    def get(self, name: str) -> Optional[ActionHandler]:
        return self._handlers.get(name)

    def get_compensator(self, name: str) -> Optional[ActionHandler]:
        return self._compensators.get(name)

    def list_handlers(self) -> list[str]:
        return sorted(self._handlers)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------
    def _register_all(self) -> None:
        from src.core.operators import register_operators

        # Importing a domain function module declares its operators in the SDK
        # registry. Import failures are tolerated so the kernel can boot while a
        # domain is still being migrated.
        try:
            from src.domains.registry import import_domain_functions

            import_domain_functions()
        except ImportError:  # pragma: no cover - bootstrap tolerance
            pass

        register_operators(self)


registry = AtomicRegistry()
