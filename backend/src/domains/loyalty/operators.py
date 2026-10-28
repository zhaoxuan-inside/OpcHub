"""Deprecated operator registry shim for the loyalty domain.

The legacy ``loyalty.identity_guard`` / ``points_settle`` / ``redeem_settle`` ...
handlers were removed by the operator-kernel v2 migration. Every loyalty flow is
now a declarative scenario (``config/scenarios/loyalty.yaml``) over generic
``guard.*`` / ``entity.*`` / ``metric.*`` operators plus the pure
``calc.loyalty.*`` / ``assemble.loyalty.*`` functions.

No handler is registered here; the module is kept importable for backwards
compatibility with older deployment scripts.
"""
from __future__ import annotations

from typing import Any


def register_loyalty_operators(registry: Any) -> None:  # pragma: no cover - compatibility
    """No-op: loyalty no longer registers private operators."""
    return None
