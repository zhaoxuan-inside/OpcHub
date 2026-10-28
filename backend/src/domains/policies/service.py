"""Compatibility shim for the policy domain.

Business flow now lives in ``config/scenarios/policies.yaml`` (operator
orchestration), calculations in ``src.domains.policies.functions`` and documents
in the generic entity store (``src.domains.policies.entities``). This module only
keeps the legacy data/query surface that other modules still import.
"""
from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import List, Optional

from src.core.entity import entity_store
from src.domains.policies import entities as _entities  # noqa: F401 - registers the EntitySpec
from src.domains.policies.models import (
    PolicyCreate,
    PolicyMatchRequest,
    PolicyMatchResponse,
    PolicyResponse,
)
from src.infrastructure.database.persistence import domain_persistence

ENTITY_POLICY = _entities.ENTITY_POLICY


class _PolicyCatalog(MutableMapping[str, PolicyResponse]):
    """Legacy ``_policies`` dict view backed by the generic entity store.

    Older modules and tests still read or seed ``policy_service._policies``
    directly. The mapping keeps that surface but never owns a second copy of the
    data: every access goes through ``entity_store``.
    """

    def __getitem__(self, key: str) -> PolicyResponse:
        doc = entity_store.get(ENTITY_POLICY, {"key": str(key)})
        if doc is None:
            raise KeyError(key)
        return PolicyResponse(**doc)

    def __setitem__(self, key: str, value: PolicyResponse) -> None:
        doc = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
        doc["id"] = doc.get("id") or str(key)
        if entity_store.get(ENTITY_POLICY, {"key": doc["id"]}) is None:
            entity_store.create(ENTITY_POLICY, doc)
        else:
            entity_store.update(ENTITY_POLICY, doc)

    def __delitem__(self, key: str) -> None:
        if not entity_store.delete(ENTITY_POLICY, {"key": str(key)}):
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        for row in entity_store.adapter(ENTITY_POLICY).all():
            if row.get("id"):
                yield str(row["id"])

    def __len__(self) -> int:
        return len(entity_store.adapter(ENTITY_POLICY).all())


class PolicyService:
    """Legacy accessors over the generic policy entity store."""

    def __init__(self):
        self._policies = _PolicyCatalog()

    def _require_db(self) -> None:
        """Policy content is database-backed; refuse memory-only mutations."""
        domain_persistence.require("policies")

    def list_policies(self, category: Optional[str] = None) -> List[PolicyResponse]:
        filters = {"category": category} if category else {}
        rows, _total = entity_store.list(ENTITY_POLICY, {"filters": filters, "limit": 0})
        return [PolicyResponse(**row) for row in rows]

    def create_policy(self, req: PolicyCreate) -> PolicyResponse:
        """Persist one policy document through the shared pure normaliser."""
        from src.domains.policies.functions import normalize_publish

        self._require_db()
        context = {
            "user_id": req.author_id or "",
            "user_role": "ADMIN" if req.is_official else "MAKER",
            "nickname": req.author_name,
        }
        doc = normalize_publish({}, req.model_dump(), context)
        created = entity_store.create(ENTITY_POLICY, doc)
        return PolicyResponse(**created)

    def match_policies(self, req: PolicyMatchRequest) -> PolicyMatchResponse:
        """Delegate eligibility matching to the shared pure function operators."""
        from src.domains.policies.functions import match_response, rank_matches, tax_assessment

        rows, _total = entity_store.list(ENTITY_POLICY, {"limit": 0})
        assessment = tax_assessment({}, {"quarterly_income": req.quarterly_income}, {})
        ranking = rank_matches(
            {},
            {
                "policies": rows,
                "region": req.region,
                "is_vat_free": assessment["eligible"],
                "search_query": req.search_query,
                "industry_keywords": req.industry_keywords,
            },
            {},
        )
        assembled = match_response({}, {"assessment": assessment, "ranking": ranking}, {})
        return PolicyMatchResponse(**assembled)

    def delete_policy(self, policy_id: str) -> bool:
        """Physically delete one policy document."""
        self._require_db()
        return entity_store.delete(ENTITY_POLICY, {"key": policy_id})

    def hydrate_items(self, rows: List[dict]) -> int:
        return entity_store.adapter(ENTITY_POLICY).hydrate(rows)

    def clear(self) -> None:
        """Reset policies for isolated testing."""
        adapter = entity_store.adapter(ENTITY_POLICY)
        for row in list(adapter.all()):
            adapter.delete(str(row["id"]))


policy_service = PolicyService()

domain_persistence.register("policies.items", policy_service.hydrate_items)
