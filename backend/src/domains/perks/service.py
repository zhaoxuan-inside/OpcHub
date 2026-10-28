"""Thin compatibility layer for the perks (生态特权) domain.

Publishing and claiming are *business flows* and now live entirely in the
scenario asset ``config/scenarios/perks.yaml`` (operators + entity store).
This module only keeps the historical import surface alive:

* read/query shims (``list_perks`` / ``list_all`` / ``get_perk``) backed by the
  generic entity store,
* a data-level ``create_perk`` / ``delete_perk`` repository shim for legacy
  callers and test fixtures,
* persistence hydrators so existing write-behind bookkeeping keeps working.

It must never re-implement a flow. ``perk_service`` remains importable by other
modules (interactions / telemetry) exactly as before.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.entity import entity_store
from src.domains.perks.entities import ENTITY_PERK, ENTITY_PERK_CLAIM
from src.domains.perks.models import (
    PerkClaimResponse,
    PerkCreate,
    PerkResponse,
)
from src.infrastructure.database.persistence import domain_persistence

# 生态优惠公告分类与状态枚举统一从 backend/config/application.yaml 加载（代码/配置/数据三分离）
PERK_CATEGORIES = set(settings.perk_categories)
PERK_STATUSES = set(settings.perk_statuses)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity_perks() -> Dict[str, PerkResponse]:
    """Read every announcement currently held by the generic entity store."""
    try:
        rows, _total = entity_store.list(ENTITY_PERK, {"limit": 0})
    except KeyError:
        return {}
    docs: Dict[str, PerkResponse] = {}
    for row in rows:
        try:
            docs[str(row.get("id"))] = PerkResponse(**row)
        except Exception:  # pragma: no cover - defensive against legacy rows
            continue
    return docs


class _PerkIndex(dict):
    """Legacy ``_perks`` mapping that mirrors writes into the entity store.

    Historical fixtures seed ``perk_service._perks[pid] = PerkResponse(...)``
    directly. Mirrored writes keep those seeds visible to the operator
    scenarios, while reads merge both sources so freshly published
    announcements are visible to legacy modules too.
    """

    def merged(self) -> Dict[str, PerkResponse]:
        docs = dict(dict.items(self))
        docs.update(_entity_perks())
        return docs

    def __setitem__(self, key: str, value: Any) -> None:
        dict.__setitem__(self, key, value)
        try:
            payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
            payload["id"] = payload.get("id") or key
            if entity_store.get(ENTITY_PERK, {"key": payload["id"]}) is None:
                entity_store.create(ENTITY_PERK, payload)
            else:
                entity_store.update(ENTITY_PERK, payload)
        except Exception:  # pragma: no cover - entity layer is best-effort here
            pass

    def __delitem__(self, key: str) -> None:
        dict.pop(self, key, None)
        try:
            entity_store.delete(ENTITY_PERK, {"key": key})
        except Exception:  # pragma: no cover
            pass

    def clear(self) -> None:
        keys = list(dict.keys(self))
        dict.clear(self)
        for key in keys:
            try:
                entity_store.delete(ENTITY_PERK, {"key": key})
            except Exception:  # pragma: no cover
                pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.merged().get(key, default)

    def values(self):
        return self.merged().values()

    def items(self):
        return self.merged().items()

    def keys(self):
        return self.merged().keys()

    def __len__(self) -> int:
        return len(self.merged())

    def __iter__(self):
        return iter(self.merged())

    def __contains__(self, key: object) -> bool:
        return key in self.merged()


class PerkService:
    """Data / query shim for ecosystem privilege announcements and claims."""

    def __init__(self) -> None:
        self._perks: _PerkIndex = _PerkIndex()
        # Key: (user_id, perk_id) — hydrated legacy cache, entity store is authoritative.
        self._claims: Dict[Tuple[str, str], PerkClaimResponse] = {}

    def _require_db(self) -> None:
        """Perk content is database-backed; refuse memory-only mutations."""
        domain_persistence.require("perks")

    # ------------------------------------------------------------------
    # Query shims (read path)
    # ------------------------------------------------------------------
    def list_perks(self, payload: Optional[Dict[str, Any]] = None) -> List[PerkResponse]:
        """List published discount announcements for the public board."""
        # Imported lazily: the operator SDK imports the microkernel registry, which
        # must not be triggered while the domain service module is still loading.
        from src.domains.perks.functions import board as assemble_board

        category = ""
        if isinstance(payload, dict):
            category = str(payload.get("category", "") or "").strip()
        items = [
            perk.model_dump(mode="json") if hasattr(perk, "model_dump") else dict(perk)
            for perk in self._perks.values()
        ]
        result = assemble_board({}, {"items": items, "category": category}, {})
        return [PerkResponse(**item) for item in result.get("items") or []]

    def list_all(self) -> List[PerkResponse]:
        """Return every announcement regardless of status (admin / management views)."""
        return sorted(
            self._perks.values(),
            key=lambda p: (p.priority, p.effective_start or ""),
            reverse=True,
        )

    def get_perk(self, perk_id: str) -> Optional[PerkResponse]:
        return self._perks.get(perk_id)

    # ------------------------------------------------------------------
    # Data-level repository shims (no business flow)
    # ------------------------------------------------------------------
    def create_perk(self, req: PerkCreate) -> PerkResponse:
        """Insert one announcement document. Business rules live in the scenario."""
        self._require_db()
        payload = req.model_dump(mode="json")
        payload.setdefault("id", f"perk_{uuid.uuid4().hex[:8]}")
        try:
            doc = entity_store.create(ENTITY_PERK, payload)
        except KeyError:  # pragma: no cover - entity specs not booted
            doc = payload
        perk = PerkResponse(**doc)
        self._perks[perk.id] = perk
        return perk

    def delete_perk(self, perk_id: str) -> bool:
        """Delete one announcement document (data only)."""
        self._require_db()
        deleted = False
        try:
            deleted = entity_store.delete(ENTITY_PERK, {"key": perk_id})
        except KeyError:  # pragma: no cover
            deleted = False
        in_cache = perk_id in dict.keys(self._perks)
        if in_cache:
            dict.pop(self._perks, perk_id, None)
        return bool(deleted or in_cache)

    # ------------------------------------------------------------------
    # Persistence hydration (entity store owns the runtime truth)
    # ------------------------------------------------------------------
    def hydrate_perks(self, rows: List[Dict]) -> int:
        for row in rows:
            perk = PerkResponse(**row)
            dict.__setitem__(self._perks, perk.id, perk)
        return len(rows)

    def hydrate_claims(self, rows: List[Dict]) -> int:
        for row in rows:
            claim = PerkClaimResponse(**row)
            self._claims[(claim.user_id, claim.perk_id)] = claim
        return len(rows)


perk_service = PerkService()

domain_persistence.register("perks.items", perk_service.hydrate_perks)
domain_persistence.register("perks.claims", perk_service.hydrate_claims)
