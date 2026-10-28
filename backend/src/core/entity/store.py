"""Generic, business-agnostic entity store.

Every entity type is described by an :class:`EntitySpec`. The store owns the
in-memory working set (primary read path), filters/sorts/paginates generically,
and mirrors mutations into PostgreSQL through the existing write-behind
``domain_persistence`` layer.

No business rule lives here. Operators such as ``entity.create`` call this store
with an entity name; the entity name is resolved from the registry, so the
operator code itself stays domain-free.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.core.entity.spec import EntityAdapter, EntitySpec

logger = logging.getLogger("opchub.entity.store")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SnapshotAdapter:
    """Default adapter: in-memory documents mirrored to ``domain_snapshots``."""

    def __init__(self, spec: EntitySpec):
        self.spec = spec
        self._rows: dict[str, dict[str, Any]] = {}

    def hydrate(self, rows: Iterable[dict[str, Any]]) -> int:
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = self.spec.key_of(row)
            if not key or key == "::".join([""] * len(self.spec.key_fields)):
                continue
            self._rows[key] = dict(row)
            count += 1
        return count

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows.values())

    def get(self, key: str) -> Optional[dict[str, Any]]:
        row = self._rows.get(key)
        return dict(row) if row else None

    def create(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        self._rows[key] = dict(doc)
        self._persist(key, doc)
        return dict(doc)

    def update(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        self._rows[key] = dict(doc)
        self._persist(key, doc)
        return dict(doc)

    def delete(self, key: str) -> bool:
        existed = self._rows.pop(key, None) is not None
        if existed:
            self._delete_persisted(key)
        return existed

    def _persist(self, key: str, doc: dict[str, Any]) -> None:
        try:
            from src.infrastructure.database.persistence import domain_persistence

            domain_persistence.write_raw(self.spec.family, key, doc)
        except Exception as exc:  # pragma: no cover - persistence is best effort
            logger.warning("Entity persistence failed for %s/%s: %s", self.spec.family, key, exc)

    def _delete_persisted(self, key: str) -> None:
        try:
            from src.infrastructure.database.persistence import domain_persistence

            domain_persistence.delete(self.spec.family, key)
        except Exception as exc:  # pragma: no cover
            logger.warning("Entity delete failed for %s/%s: %s", self.spec.family, key, exc)


class EntityStore:
    """Registry + generic query engine for all declared entity types."""

    def __init__(self) -> None:
        self._specs: dict[str, EntitySpec] = {}
        self._adapters: dict[str, EntityAdapter] = {}

    # ------------------------------------------------------------------
    # Registration / hydration
    # ------------------------------------------------------------------
    def register(self, spec: EntitySpec) -> None:
        self._specs[spec.name] = spec
        adapter = spec.adapter or SnapshotAdapter(spec)
        self._adapters[spec.name] = adapter

    @property
    def names(self) -> list[str]:
        return list(self._specs)

    def spec(self, name: str) -> EntitySpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise KeyError(f"Unknown entity '{name}'. Register an EntitySpec first.") from exc

    def adapter(self, name: str) -> EntityAdapter:
        self.spec(name)
        return self._adapters[name]

    async def initialize(self) -> dict[str, int]:
        """Hydrate every snapshot-backed entity family from PostgreSQL."""
        counts: dict[str, int] = {}
        try:
            from src.infrastructure.database.repository import db_repository

            ready = await db_repository.is_ready()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Entity store DB probe failed: %s", exc)
            ready = False

        for name, spec in self._specs.items():
            adapter = self._adapters[name]
            if not isinstance(adapter, SnapshotAdapter):
                continue
            if not ready:
                counts[name] = 0
                continue
            from src.infrastructure.database.repository import db_repository

            rows = await db_repository.load_domain_snapshots(spec.family)
            counts[name] = adapter.hydrate(rows) if rows else 0
        logger.info("Entity store hydrated: %s", counts)
        return counts

    # ------------------------------------------------------------------
    # CRUD primitives (called by generic operators)
    # ------------------------------------------------------------------
    def create(self, entity: str, payload: dict[str, Any]) -> dict[str, Any]:
        spec = self.spec(entity)
        adapter = self._adapters[entity]
        doc = dict(spec.defaults)
        doc.update({k: v for k, v in (payload or {}).items() if v is not _UNSET})
        self._apply_identity(spec, doc, create=True)
        self._apply_timestamps(spec, doc, create=True)
        doc = self._validate(spec, doc)
        key = spec.key_of(doc)
        if adapter.get(key) is not None:
            raise ValueError(f"Entity '{entity}' with key '{key}' already exists")
        return adapter.create(key, doc)

    def update(self, entity: str, payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        spec = self.spec(entity)
        adapter = self._adapters[entity]
        key = self._require_key(spec, payload)
        current = adapter.get(key)
        if current is None:
            raise KeyError(f"Entity '{entity}' with key '{key}' not found")
        merged = dict(current)
        merged.update({k: v for k, v in (payload or {}).items() if v is not _UNSET})
        self._apply_identity(spec, merged, create=False)
        self._apply_timestamps(spec, merged, create=False)
        if partial:
            doc = merged
            model = spec.model
            if model is not None:
                doc = model.model_validate(merged).model_dump(mode="json")
        else:
            doc = self._validate(spec, merged)
        return adapter.update(key, doc)

    def delete(self, entity: str, payload: dict[str, Any]) -> bool:
        spec = self.spec(entity)
        key = self._require_key(spec, payload)
        return self._adapters[entity].delete(key)

    def get(self, entity: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        spec = self.spec(entity)
        adapter = self._adapters[entity]
        key_value = payload.get("key")
        if key_value is not None and len(spec.key_fields) == 1:
            return adapter.get(str(key_value))
        key = spec.key_of(payload)
        if key and key != "::".join([""] * len(spec.key_fields)):
            return adapter.get(key)
        return None

    def list(
        self,
        entity: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        spec = self.spec(entity)
        payload = payload or {}
        filters = payload.get("filters") or {}
        search = payload.get("search")
        order = payload.get("order") or spec.default_order
        offset = max(0, int(payload.get("offset") or 0))
        limit = payload.get("limit")
        limit = None if limit in (None, 0, "0") else max(0, int(limit))

        rows = [row for row in self._adapters[entity].all() if self._matches(row, filters)]
        if search and spec.search_fields:
            needle = str(search).lower()
            rows = [
                row
                for row in rows
                if any(needle in str(row.get(f, "")).lower() for f in spec.search_fields)
            ]
        reverse = str(order).startswith("-")
        order_field = str(order).lstrip("-")
        rows.sort(key=lambda r: _sort_key(r.get(order_field)), reverse=reverse)
        total = len(rows)
        if limit is not None:
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]
        return [dict(r) for r in rows], total

    def count(self, entity: str, payload: dict[str, Any] | None = None) -> int:
        _rows, total = self.list(entity, {**(payload or {}), "limit": 0, "offset": 0})
        return total

    def exists(self, entity: str, payload: dict[str, Any] | None = None) -> bool:
        _rows, total = self.list(entity, {**(payload or {}), "limit": 1, "offset": 0})
        return total > 0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _apply_identity(self, spec: EntitySpec, doc: dict[str, Any], *, create: bool) -> None:
        for field_name in spec.key_fields:
            if create and not doc.get(field_name):
                if field_name in ("id",) or len(spec.key_fields) == 1:
                    doc[field_name] = f"{spec.id_prefix}_{uuid.uuid4().hex[:16]}"
                else:
                    raise ValueError(f"Entity '{spec.name}' requires key field '{field_name}'")

    def _apply_timestamps(self, spec: EntitySpec, doc: dict[str, Any], *, create: bool) -> None:
        if not spec.timestamps:
            return
        now = utc_now_iso()
        if create and not doc.get("created_at"):
            doc["created_at"] = now
        doc["updated_at"] = now

    def _validate(self, spec: EntitySpec, doc: dict[str, Any]) -> dict[str, Any]:
        if spec.model is None:
            return doc
        return spec.model.model_validate(doc).model_dump(mode="json")

    @staticmethod
    def _require_key(spec: EntitySpec, payload: dict[str, Any]) -> str:
        key = spec.key_of(payload or {})
        empty = "::".join([""] * len(spec.key_fields))
        if not key or key == empty:
            if payload.get("key") is not None and len(spec.key_fields) == 1:
                return str(payload["key"])
            raise ValueError(f"Entity '{spec.name}' requires key fields {list(spec.key_fields)}")
        return key

    @staticmethod
    def _matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
        for field_name, expected in (filters or {}).items():
            actual = row.get(field_name)
            if isinstance(expected, dict):
                if "in" in expected and actual not in expected["in"]:
                    return False
                if "nin" in expected and actual in expected["nin"]:
                    return False
                if "eq" in expected and actual != expected["eq"]:
                    return False
                if "ne" in expected and actual == expected["ne"]:
                    return False
                if "gte" in expected and (actual is None or actual < expected["gte"]):
                    return False
                if "lte" in expected and (actual is None or actual > expected["lte"]):
                    return False
                if "contains" in expected:
                    if isinstance(actual, (list, tuple, set)):
                        if expected["contains"] not in actual:
                            return False
                    elif expected["contains"] not in str(actual or ""):
                        return False
                if "exists" in expected and bool(actual is not None) is not bool(expected["exists"]):
                    return False
            else:
                if actual != expected:
                    return False
        return True


class _Unset:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<UNSET>"


_UNSET = _Unset()


def _sort_key(value: Any) -> tuple[int, Any]:
    """Sort mixed types deterministically, pushing nulls to the end."""
    if value is None:
        return (1, "")
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, (int, float)):
        return (0, value)
    return (0, str(value))


entity_store = EntityStore()
