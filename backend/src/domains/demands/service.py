"""Compatibility shim for the demand marketplace domain.

Business flows (publish / bidding / closing / deletion / bid withdrawal) now
live in the scenario asset ``config/scenarios/demands.yaml`` and are executed by
the operator kernel. Pure calculations live in
``src.domains.demands.functions`` and documents in the generic entity store
(``src.domains.demands.entities``).

This module therefore only keeps the legacy **data / query** surface that other
modules still import: ``demand_service.get_demand``, ``demand_service.list_demands``,
the ``_demands`` / ``_bids`` collection views and the (empty) read cache.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator, MutableMapping
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.entity import entity_store
from src.domains.demands import entities as _entities  # noqa: F401 - registers the EntitySpecs
from src.domains.demands.models import BidResponse, DemandResponse
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.demands")

ENTITY_DEMAND = _entities.ENTITY_DEMAND
ENTITY_BID = _entities.ENTITY_BID
CACHE_TTL_SECONDS = 120.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value or {})


class _DemandCatalog(MutableMapping[str, DemandResponse]):
    """Legacy ``_demands`` dict view backed by the generic entity store.

    Older modules and tests still read or seed ``demand_service._demands``
    directly. The mapping keeps that surface but never owns a second copy of the
    data: every access goes through ``entity_store``.
    """

    def __init__(self, service: "DemandService"):
        self._service = service

    def __getitem__(self, key: str) -> DemandResponse:
        doc = entity_store.get(ENTITY_DEMAND, {"key": str(key)})
        if doc is None:
            raise KeyError(key)
        return self._service._remember(DemandResponse(**doc))

    def __setitem__(self, key: str, value: DemandResponse) -> None:
        doc = _snapshot(value)
        doc["id"] = doc.get("id") or str(key)
        if entity_store.get(ENTITY_DEMAND, {"key": doc["id"]}) is None:
            entity_store.create(ENTITY_DEMAND, doc)
        else:
            entity_store.update(ENTITY_DEMAND, doc)
        self._service._mirror.pop(str(doc["id"]), None)

    def __delitem__(self, key: str) -> None:
        if not entity_store.delete(ENTITY_DEMAND, {"key": str(key)}):
            raise KeyError(key)
        self._service._mirror.pop(str(key), None)

    def __iter__(self) -> Iterator[str]:
        for row in entity_store.adapter(ENTITY_DEMAND).all():
            if row.get("id"):
                yield str(row["id"])

    def __len__(self) -> int:
        return len(entity_store.adapter(ENTITY_DEMAND).all())


class _BidCatalog(MutableMapping[str, List[BidResponse]]):
    """Legacy ``_bids`` view: demand id -> list of bids, backed by the store."""

    def __getitem__(self, key: str) -> List[BidResponse]:
        return self._load(str(key))

    def __setitem__(self, key: str, value: List[BidResponse]) -> None:
        demand_id = str(key)
        for row in self._rows(demand_id):
            entity_store.delete(ENTITY_BID, {"key": str(row["id"])})
        for bid in value or []:
            doc = _snapshot(bid)
            doc.setdefault("demand_id", demand_id)
            entity_store.create(ENTITY_BID, doc)

    def __delitem__(self, key: str) -> None:
        rows = self._rows(str(key))
        if not rows:
            raise KeyError(key)
        for row in rows:
            entity_store.delete(ENTITY_BID, {"key": str(row["id"])})

    def __iter__(self) -> Iterator[str]:
        seen = {str(row.get("demand_id")) for row in entity_store.adapter(ENTITY_BID).all()}
        yield from sorted(seen)

    def __len__(self) -> int:
        return len(list(iter(self)))

    def _rows(self, demand_id: str) -> List[Dict[str, Any]]:
        rows, _total = entity_store.list(ENTITY_BID, {"filters": {"demand_id": demand_id}, "limit": 0})
        return rows

    def _load(self, demand_id: str) -> List[BidResponse]:
        return [BidResponse(**row) for row in self._rows(demand_id)]


class DemandService:
    """Legacy read surface over the generic demand / bid entity store."""

    def __init__(self) -> None:
        self._cache: Dict[str, tuple[float, Any]] = {}
        # Documents handed out by ``_demands`` may still be mutated in place by
        # legacy counter mirroring; they are flushed back on ``invalidate_cache``.
        self._mirror: Dict[str, DemandResponse] = {}

    @property
    def _demands(self) -> MutableMapping[str, DemandResponse]:
        return _DemandCatalog(self)

    @property
    def _bids(self) -> MutableMapping[str, List[BidResponse]]:
        return _BidCatalog()

    # ------------------------------------------------------------------
    # Read cache (kept for callers that invalidate after writing)
    # ------------------------------------------------------------------
    def invalidate_cache(self) -> int:
        """Evict cached list pages and flush mirrored counter mutations."""
        count = len(self._cache)
        self._cache.clear()
        self._flush_mirror()
        return count

    def get_cache(self, key: str, ttl_seconds: float = CACHE_TTL_SECONDS) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        timestamp, data = entry
        if time.time() - timestamp > ttl_seconds:
            self._cache.pop(key, None)
            return None
        return data

    def set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = (time.time(), data)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def list_demands(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: int = 6,
        **kwargs: Any,
    ) -> Any:
        """List demands as a flat list (unpaged) or a paged envelope."""
        filters: Dict[str, Any] = {}
        if category and str(category).lower() != "all":
            filters["category"] = {"in": [category, str(category).upper(), str(category).lower()]}

        if page is None:
            rows, _total = entity_store.list(
                ENTITY_DEMAND, {"filters": filters, "search": search or None, "limit": 0}
            )
            return [DemandResponse(**row) for row in rows]

        clean_page = max(1, int(page))
        clean_size = max(1, min(100, int(page_size)))
        cache_key = f"{category or 'ALL'}:{search or ''}:{clean_page}:{clean_size}"
        cached = self.get_cache(cache_key)
        if cached is not None:
            cached_res = dict(cached)
            cached_res["from_cache"] = True
            return cached_res

        rows, total = entity_store.list(
            ENTITY_DEMAND,
            {
                "filters": filters,
                "search": search or None,
                "limit": clean_size,
                "offset": (clean_page - 1) * clean_size,
            },
        )
        result = {
            "items": [DemandResponse(**row).model_dump(mode="json") for row in rows],
            "total": total,
            "page": clean_page,
            "page_size": clean_size,
            "total_pages": max(1, (total + clean_size - 1) // clean_size),
            "has_more": clean_page * clean_size < total,
            "from_cache": False,
        }
        self.set_cache(cache_key, result)
        return result

    def get_demand(self, demand_id: str) -> Optional[DemandResponse]:
        doc = entity_store.get(ENTITY_DEMAND, {"key": str(demand_id)})
        return DemandResponse(**doc) if doc else None

    def list_bids(self, demand_id: str) -> List[BidResponse]:
        rows, _total = entity_store.list(
            ENTITY_BID, {"filters": {"demand_id": str(demand_id)}, "limit": 0}
        )
        return [BidResponse(**row) for row in rows]

    # ------------------------------------------------------------------
    # Hydration / test isolation
    # ------------------------------------------------------------------
    def hydrate_demands(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_DEMAND).hydrate(rows)

    def hydrate_bids(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_BID).hydrate(rows)

    def clear(self) -> None:
        """Reset demand state for isolated test execution."""
        for entity in (ENTITY_DEMAND, ENTITY_BID):
            adapter = entity_store.adapter(entity)
            for row in list(adapter.all()):
                adapter.delete(str(row["id"]))
        self._mirror.clear()
        self._cache.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _remember(self, demand: DemandResponse) -> DemandResponse:
        self._mirror[str(demand.id)] = demand
        return demand

    def _flush_mirror(self) -> None:
        """Write back documents mutated in place by legacy counter mirroring."""
        for key, demand in list(self._mirror.items()):
            self._mirror.pop(key, None)
            try:
                if entity_store.get(ENTITY_DEMAND, {"key": key}) is not None:
                    entity_store.update(ENTITY_DEMAND, demand.model_dump(mode="json"), partial=True)
            except Exception as exc:  # pragma: no cover - persistence is best effort
                logger.warning("Demand counter mirror flush failed for %s: %s", key, exc)


demand_service = DemandService()

domain_persistence.register("demands.items", demand_service.hydrate_demands)
domain_persistence.register("demands.bids", demand_service.hydrate_bids)
