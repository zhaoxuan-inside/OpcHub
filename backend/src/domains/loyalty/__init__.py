"""Loyalty domain package for OpcHub."""
from __future__ import annotations

from typing import Any

__all__ = ["loyalty_service"]


def __getattr__(name: str) -> Any:  # pragma: no cover - import convenience
    if name == "loyalty_service":
        from src.domains.loyalty.service import loyalty_service

        return loyalty_service
    raise AttributeError(name)
