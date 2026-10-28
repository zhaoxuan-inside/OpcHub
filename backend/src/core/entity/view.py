"""Mapping views over the generic entity store (compatibility shims only).

Legacy domain services expose dictionaries such as ``service._products``. The
view keeps those read/write access patterns working while the single source of
truth becomes the declarative entity store.
"""
from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import Any

from src.core.entity.store import entity_store


class EntityMapping(MutableMapping):
    def __init__(self, entity: str, key_field: str = "id"):
        self.entity = entity
        self.key_field = key_field

    def _dump(self, value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return dict(value)

    def __getitem__(self, key: str) -> dict[str, Any]:
        row = entity_store.get(self.entity, {"key": str(key)})
        if row is None:
            raise KeyError(key)
        return row

    def __setitem__(self, key: str, value: Any) -> None:
        doc = self._dump(value)
        doc.setdefault(self.key_field, str(key))
        spec = entity_store.spec(self.entity)
        existing = entity_store.get(self.entity, {"key": str(doc.get(self.key_field))})
        if existing is not None:
            entity_store.update(self.entity, doc, partial=False)
        else:
            try:
                entity_store.create(self.entity, doc)
            except ValueError:
                entity_store.update(self.entity, doc, partial=False)

    def __delitem__(self, key: str) -> None:
        if not entity_store.delete(self.entity, {"key": str(key)}):
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        rows, _total = entity_store.list(self.entity, {"limit": 0})
        return iter([str(row.get(self.key_field)) for row in rows])

    def __len__(self) -> int:
        return entity_store.count(self.entity)
