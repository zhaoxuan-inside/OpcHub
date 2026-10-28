"""Thin compatibility layer for the content-moderation domain.

Reporting, take-down, restore, queue listing and the NLP pre-screen are *business
flows* and now live entirely in ``config/scenarios/moderation.yaml`` (operators +
the generic entity store). This module only keeps the historical import surface
alive:

* read/query shims (``list_items`` / ``get_item``) backed by the entity store,
* a data-level ``report`` repository shim for legacy callers and test fixtures,
* the legacy ``_items`` mapping, which mirrors writes into the entity store so
  fixtures seeded the old way stay visible to the operator scenarios,
* a persistence hydrator so existing write-behind bookkeeping keeps working.

It must never re-implement a flow. ``moderation_service`` remains importable by
other modules exactly as before.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.entity import entity_store
from src.domains.moderation.entities import ENTITY_MODERATION_ITEM
from src.domains.moderation.models import (
    ContentReportRequest,
    ModerationItemResponse,
    REPORTABLE_TARGET_TYPES,
)
from src.infrastructure.database.persistence import domain_persistence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity_items() -> Dict[str, ModerationItemResponse]:
    """Read every moderation document currently held by the entity store."""
    try:
        rows, _total = entity_store.list(ENTITY_MODERATION_ITEM, {"limit": 0})
    except KeyError:  # pragma: no cover - entity specs not booted
        return {}
    docs: Dict[str, ModerationItemResponse] = {}
    for row in rows:
        try:
            docs[str(row.get("id"))] = ModerationItemResponse(**row)
        except Exception:  # pragma: no cover - defensive against legacy rows
            continue
    return docs


class _ModerationIndex(dict):
    """Legacy ``_items`` mapping that mirrors writes into the entity store.

    Historical fixtures seed ``moderation_service._items["mod-101"] = ...``
    directly. Mirrored writes keep those seeds visible to the operator scenarios,
    while reads merge both sources so operator-written items are visible to
    legacy callers too.
    """

    def merged(self) -> Dict[str, ModerationItemResponse]:
        # Entity store is the authoritative source; the legacy cache only adds
        # rows that were never migrated to the operator kernel.
        docs = dict(dict.items(self))
        docs.update(_entity_items())
        return docs

    def __setitem__(self, key: str, value: Any) -> None:
        dict.__setitem__(self, key, value)
        try:
            payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
            payload["id"] = payload.get("id") or key
            if entity_store.get(ENTITY_MODERATION_ITEM, {"key": payload["id"]}) is None:
                entity_store.create(ENTITY_MODERATION_ITEM, payload)
            else:
                entity_store.update(ENTITY_MODERATION_ITEM, payload, partial=True)
        except Exception:  # pragma: no cover - entity layer is best-effort here
            pass

    def __delitem__(self, key: str) -> None:
        dict.pop(self, key, None)
        try:
            entity_store.delete(ENTITY_MODERATION_ITEM, {"key": key})
        except Exception:  # pragma: no cover
            pass

    def pop(self, key: str, default: Any = None) -> Any:
        value = self.merged().get(key, default)
        dict.pop(self, key, None)
        try:
            entity_store.delete(ENTITY_MODERATION_ITEM, {"key": key})
        except Exception:  # pragma: no cover
            pass
        return value

    def clear(self) -> None:
        keys = list(_entity_items().keys())
        dict.clear(self)
        for key in keys:
            try:
                entity_store.delete(ENTITY_MODERATION_ITEM, {"key": key})
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


class ModerationService:
    """Data / query shim for content-moderation items."""

    def __init__(self) -> None:
        # Legacy id -> item index; the entity store remains authoritative.
        self._items: _ModerationIndex = _ModerationIndex()

    # ------------------------------------------------------------------
    # Query shims (read path)
    # ------------------------------------------------------------------
    def list_items(self, status: Optional[str] = None) -> List[ModerationItemResponse]:
        items = list(self._items.values())
        if status:
            wanted = str(status).upper()
            items = [item for item in items if item.status.upper() == wanted]
        return sorted(items, key=lambda item: item.reported_at or "", reverse=True)

    def get_item(self, item_id: str) -> Optional[ModerationItemResponse]:
        return self._items.get(item_id)

    # ------------------------------------------------------------------
    # Data-level repository shim (no take-down / restore flow)
    # ------------------------------------------------------------------
    def report(self, req: ContentReportRequest) -> ModerationItemResponse:
        """Legacy data-level report writer.

        The business flow lives in ``OPC_MODERATION_REPORT_PIPELINE``; this shim
        only reuses the same pure normalisation/merge functions so old callers
        still persist through the entity store. New code must call the scenario.
        """
        from src.domains.moderation.functions import normalize_report, report_merge

        report_input = normalize_report(
            {},
            req.model_dump(mode="json"),
            {"user_id": req.reporter_id},
        )
        rows, _total = entity_store.list(
            ENTITY_MODERATION_ITEM,
            {
                "filters": {
                    "target_type": report_input["target_type"],
                    "target_id": report_input["target_id"],
                    "status": "FLAGGED",
                },
                "limit": 1,
            },
        )
        merged = report_merge({}, {"existing": rows, "report": report_input}, {})
        document = merged["document"]
        if merged["merged"]:
            stored = entity_store.update(ENTITY_MODERATION_ITEM, document, partial=True)
        else:
            stored = entity_store.create(ENTITY_MODERATION_ITEM, document)
        item = ModerationItemResponse(**stored)
        dict.__setitem__(self._items, item.id, item)
        return item

    # ------------------------------------------------------------------
    # Persistence hydration (entity store owns the runtime truth)
    # ------------------------------------------------------------------
    def hydrate_items(self, rows: List[Dict]) -> int:
        for row in rows:
            item = ModerationItemResponse(**row)
            dict.__setitem__(self._items, item.id, item)
        return len(rows)


moderation_service = ModerationService()

domain_persistence.register("moderation.items", moderation_service.hydrate_items)

# Kept for callers that imported the enum from the service historically.
__all__ = [
    "ModerationService",
    "moderation_service",
    "utc_now_iso",
    "REPORTABLE_TARGET_TYPES",
]
