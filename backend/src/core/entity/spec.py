"""Declarative entity specifications for the generic entity runtime.

An ``EntitySpec`` is *data only*: it names a persisted document family, its key
fields, the optional pydantic model used for validation, and the adapter that
performs storage. It must never contain business rules or orchestration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, Sequence


class EntityAdapter(Protocol):
    """Minimal storage contract consumed by generic entity operators."""

    def all(self) -> list[dict[str, Any]]: ...

    def get(self, key: str) -> Optional[dict[str, Any]]: ...

    def create(self, key: str, doc: dict[str, Any]) -> dict[str, Any]: ...

    def update(self, key: str, doc: dict[str, Any]) -> dict[str, Any]: ...

    def delete(self, key: str) -> bool: ...


@dataclass(frozen=True)
class EntitySpec:
    """Data-only description of one persisted entity type."""

    name: str
    family: str
    key_fields: Sequence[str] = ("id",)
    model: Optional[type] = None
    adapter: Optional[EntityAdapter] = None
    id_prefix: str = "ent"
    timestamps: bool = True
    search_fields: Sequence[str] = ()
    owner_field: Optional[str] = None
    default_order: str = "-created_at"
    defaults: dict[str, Any] = field(default_factory=dict)

    def key_of(self, doc: dict[str, Any]) -> str:
        parts = [str(doc.get(field_name, "")) for field_name in self.key_fields]
        return "::".join(parts)
