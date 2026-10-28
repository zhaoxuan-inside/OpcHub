"""Compatibility shim for the compliance domain.

Business flow now lives in ``config/scenarios/compliance.yaml`` (operator
orchestration), pure calculations in ``src.domains.compliance.functions`` and
documents in the generic entity store (``src.domains.compliance.entities``).
This module only keeps the legacy data/query surface that other modules still
import (telemetry counters, test fixtures, old callers).

It deliberately contains **no publishing or scoring flow**: ``publish_entry``
and ``evaluate_audit`` are thin adapters over the shared pure functions and the
entity store, and exist only for backward compatibility.
"""
from __future__ import annotations

from collections.abc import Iterator, MutableSequence
from typing import Any, List

from src.core.entity import entity_store
from src.domains.compliance import entities as _entities  # noqa: F401 - registers the EntitySpec
from src.domains.compliance.entities import (
    ENTITY_COMPLIANCE_ITEM,
    KIND_CASE,
    KIND_CHECKPOINT,
    KIND_LAW,
)
from src.domains.compliance.models import (
    AuditCheckItem,
    AuditEvaluateRequest,
    AuditReportResponse,
    ComplianceCase,
    ComplianceLaw,
    CompliancePublishRequest,
)
from src.infrastructure.database.persistence import domain_persistence

_MODEL_BY_KIND = {
    KIND_LAW: ComplianceLaw,
    KIND_CASE: ComplianceCase,
    KIND_CHECKPOINT: AuditCheckItem,
}


def _row_document(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


class _KindCatalog(MutableSequence):
    """Legacy list-like view over one ``kind`` of the shared entity store.

    Tests and older modules still append/iterate ``compliance_service._laws``
    (etc.). This sequence keeps that surface without owning a second copy of the
    data: every read and write goes through ``entity_store``.
    """

    def __init__(self, kind: str):
        self._kind = kind
        self._model = _MODEL_BY_KIND[kind]

    # -- read ------------------------------------------------------------
    def _docs(self) -> list[dict[str, Any]]:
        rows, _total = entity_store.list(
            ENTITY_COMPLIANCE_ITEM,
            {"filters": {"kind": self._kind}, "order": "created_at", "limit": 0},
        )
        return rows

    def _rows(self) -> list[Any]:
        return [self._model(**row) for row in self._docs()]

    def __len__(self) -> int:
        return len(self._docs())

    def __getitem__(self, index):
        return self._rows()[index]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._rows())

    # -- write -----------------------------------------------------------
    def __setitem__(self, index, value) -> None:
        rows = self._docs()
        current = rows[index]
        entity_store.delete(ENTITY_COMPLIANCE_ITEM, {"key": str(current["id"])})
        self.insert(index, value)

    def __delitem__(self, index) -> None:
        rows = self._docs()
        current = rows[index] if isinstance(index, int) else rows[index][0]
        entity_store.delete(ENTITY_COMPLIANCE_ITEM, {"key": str(current["id"])})

    def insert(self, index: int, value: Any) -> None:
        doc = _row_document(value)
        doc["kind"] = self._kind
        entity_id = str(doc.get("id") or "").strip()
        if not entity_id:
            raise ValueError("compliance 文档必须提供 id")
        if entity_store.get(ENTITY_COMPLIANCE_ITEM, {"key": entity_id}) is None:
            entity_store.create(ENTITY_COMPLIANCE_ITEM, doc)
        else:
            entity_store.update(ENTITY_COMPLIANCE_ITEM, doc)


class ComplianceService:
    """Legacy accessors over the generic compliance entity store."""

    def __init__(self) -> None:
        # Live views; new writes belong to ``entity.*`` scenario operators.
        self._laws = _KindCatalog(KIND_LAW)
        self._cases = _KindCatalog(KIND_CASE)
        self._checkpoints = _KindCatalog(KIND_CHECKPOINT)

    def _require_db(self) -> None:
        """Compliance content is database-backed; refuse memory-only mutations."""
        domain_persistence.require("compliance")

    # ---------------------------------------------------------------- read
    def _documents(self, kind: str) -> list[dict[str, Any]]:
        rows, _total = entity_store.list(
            ENTITY_COMPLIANCE_ITEM,
            {"filters": {"kind": kind}, "order": "created_at", "limit": 0},
        )
        return rows

    def get_laws(self) -> List[ComplianceLaw]:
        return [ComplianceLaw(**row) for row in self._documents(KIND_LAW)]

    def get_cases(self) -> List[ComplianceCase]:
        return [ComplianceCase(**row) for row in self._documents(KIND_CASE)]

    def get_checkpoints(self) -> List[AuditCheckItem]:
        return [AuditCheckItem(**row) for row in self._documents(KIND_CHECKPOINT)]

    # Backward-compatible alias (existing callers / telemetry)
    def get_dimensions(self) -> List[ComplianceLaw]:
        return self.get_laws()

    # ---------------------------------------------------------------- data shims
    def publish_entry(self, payload: Any) -> dict:
        """Data-level insert used by legacy callers (business flow is the scenario).

        Identity is taken from the payload here only because this is the pre-gateway
        compatibility path; ``OPC_COMPLIANCE_PUBLISH_PIPELINE`` reads identity from
        ``context`` and never trusts payload authorship.
        """
        from src.domains.compliance.functions import normalize_publish

        self._require_db()
        req = payload if isinstance(payload, CompliancePublishRequest) else CompliancePublishRequest(**payload)
        context = {
            "user_id": req.author_id or "",
            "user_role": "ADMIN" if req.is_official else "MAKER",
            "nickname": req.author_name,
        }
        doc = normalize_publish({}, req.model_dump(mode="json"), context)
        existing = entity_store.get(ENTITY_COMPLIANCE_ITEM, {"key": doc["id"]})
        if existing is not None:
            return existing
        created = entity_store.create(ENTITY_COMPLIANCE_ITEM, doc)
        return created

    def delete_entry(self, kind: str, entity_id: str) -> bool:
        """Physically remove a published law/case (data only)."""
        self._require_db()
        kind = str(kind or "").strip().lower()
        entity_id = str(entity_id or "").strip()
        if kind not in (KIND_LAW, KIND_CASE) or not entity_id:
            return False
        doc = entity_store.get(ENTITY_COMPLIANCE_ITEM, {"key": entity_id})
        if doc is None or str(doc.get("kind")) != kind:
            return False
        return entity_store.delete(ENTITY_COMPLIANCE_ITEM, {"key": entity_id})

    # ---------------------------------------------------------------- legacy audit shim
    def evaluate_audit(self, req: AuditEvaluateRequest) -> AuditReportResponse:
        """Compatibility adapter over ``calc.compliance.*`` pure functions."""
        from src.domains.compliance.functions import (
            audit_report,
            dimension_scores,
            rank,
            score,
        )

        items = [
            row
            for row in entity_store.adapter(ENTITY_COMPLIANCE_ITEM).all()
            if str(row.get("kind")) == KIND_CHECKPOINT
        ]
        passed = list(getattr(req, "passed_item_ids", None) or [])
        scored = score({}, {"items": items, "passed_item_ids": passed}, {})
        dimensions = dimension_scores({}, {"items": items, "passed_item_ids": passed}, {})
        ranked = rank({}, {"items": scored.get("failed_items") or []}, {})
        assembled = audit_report(
            {},
            {"scored": scored, "dimensions": dimensions, "ranked": ranked},
            {},
        )
        return AuditReportResponse(**assembled["audit_report"])

    # ---------------------------------------------------------------- hydration
    def hydrate_items(self, rows: List[dict]) -> int:
        """Rebuild the entity store from persisted ``compliance.items`` snapshots."""
        return entity_store.adapter(ENTITY_COMPLIANCE_ITEM).hydrate(rows)

    def clear(self) -> None:
        """Reset the compliance catalog for isolated testing."""
        adapter = entity_store.adapter(ENTITY_COMPLIANCE_ITEM)
        for row in list(adapter.all()):
            entity_id = row.get("id")
            if entity_id:
                adapter.delete(str(entity_id))


compliance_service = ComplianceService()

domain_persistence.register("compliance.items", compliance_service.hydrate_items)
