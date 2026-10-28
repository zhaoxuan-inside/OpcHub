"""Declarative entity specifications for the compliance domain.

This module contains no business logic and no orchestration. Legacy snapshots
persist laws, pitfall cases and audit checkpoints **mixed in one family**
(``compliance.items``) and mark the type with a ``_kind`` field. To keep that
persistence compatible, the domain declares a single unified entity and carries
the type as an explicit ``kind`` discriminator:

* ``law``        — 法条 / 部门规章白话要点
* ``case``       — 避坑案例
* ``checkpoint`` — 上线自检清单条目

New writes always persist ``kind``; :class:`_LegacyKindAdapter` promotes the old
``_kind`` marker (or infers it from the document shape) while hydrating, so old
snapshots stay queryable without a destructive re-shard. The adapter is storage
plumbing only — it contains no business rule.
"""
from dataclasses import replace
from typing import Any

from src.core.entity import EntitySpec, SnapshotAdapter, entity_store
from src.domains.compliance.models import ComplianceItem

ENTITY_COMPLIANCE_ITEM = "compliance.item"

KIND_LAW = "law"
KIND_CASE = "case"
KIND_CHECKPOINT = "checkpoint"
COMPLIANCE_KINDS = (KIND_LAW, KIND_CASE, KIND_CHECKPOINT)


def _legacy_kind(row: dict[str, Any]) -> str:
    """Map a legacy persisted row onto the explicit ``kind`` discriminator."""
    raw = str(row.get("_kind") or "").strip().lower()
    if raw in COMPLIANCE_KINDS:
        return raw
    if "law_ref" in row or "content" in row:
        return KIND_LAW
    if "lesson" in row or "consequence" in row:
        return KIND_CASE
    if "weight" in row or "legal_basis" in row:
        return KIND_CHECKPOINT
    return KIND_LAW


class _LegacyKindAdapter(SnapshotAdapter):
    """Snapshot adapter that adds the missing ``kind`` field while hydrating."""

    def hydrate(self, rows) -> int:
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            doc = dict(row)
            if not doc.get("kind"):
                doc["kind"] = _legacy_kind(doc)
            normalized.append(doc)
        return super().hydrate(normalized)


_COMPLIANCE_ITEM_SPEC = EntitySpec(
    name=ENTITY_COMPLIANCE_ITEM,
    family="compliance.items",
    model=ComplianceItem,
    key_fields=("id",),
    id_prefix="cmp",
    search_fields=(
        "title",
        "summary",
        "content",
        "name",
        "code",
        "industry",
        "lesson",
        "badge",
    ),
    owner_field="author_id",
    default_order="-created_at",
    defaults={
        "kind": KIND_LAW,
        "code": "",
        "name": "",
        "title": "",
        "summary": "",
        "content": "",
        "level": "国家级",
        "issuer": "",
        "published_at": "",
        "penalties": "",
        "law_ref": "",
        "icon_name": "shield",
        "hot_score": 0,
        "badge": "",
        "industry": "",
        "violation": "",
        "consequence": "",
        "lesson": "",
        "badge_color": "#5B6472",
        "dimension_id": "",
        "description": "",
        "severity": "",
        "weight": 0,
        "advice": "",
        "legal_basis": "",
        "author_id": "",
        "author_name": None,
        "is_official": False,
    },
)

compliance_item_entity = replace(
    _COMPLIANCE_ITEM_SPEC,
    adapter=_LegacyKindAdapter(_COMPLIANCE_ITEM_SPEC),
)

entity_store.register(compliance_item_entity)
