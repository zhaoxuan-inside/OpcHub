"""Declarative entity specifications for the SOP (合规文书 / 流程模板) domain.

This module contains no business logic and no orchestration. It only declares
which documents exist, how they are keyed, validated and searched.

Persistence compatibility
-------------------------
The workflow graph, the document/flow catalogs and the publish-review queue were
historically owned by :class:`~src.domains.sop.service.SOPService` in-memory
indexes (mirrored to ``domain_snapshots`` by ``domain_persistence``). To keep old
snapshots readable **and** let the generic ``entity.*`` operators write the same
business state, every spec is bound to a small storage adapter that delegates to
that legacy index. The adapter is pure plumbing: it validates the row with the
declared pydantic model, stores it back into the index and mirrors it through the
existing write-behind persistence layer. It contains no business rule.
"""
from __future__ import annotations

from typing import Any, Optional

from src.core.entity import EntitySpec, entity_store
from src.domains.sop.models import (
    SOPDocumentResponse,
    SOPEdge,
    SOPFlow,
    SOPFlowTemplate,
    SOPGoal,
    SOPNode,
    SOPReviewItem,
    SOPStage,
    SOPTemplate,
)
from src.infrastructure.database.persistence import domain_persistence

ENTITY_SOP_STAGE = "sop.stage"
ENTITY_SOP_NODE = "sop.node"
ENTITY_SOP_EDGE = "sop.edge"
ENTITY_SOP_GOAL = "sop.goal"
ENTITY_SOP_TEMPLATE = "sop.template"
ENTITY_SOP_FLOW_TEMPLATE = "sop.flow_template"
ENTITY_SOP_DOCUMENT = "sop.document"
ENTITY_SOP_FLOW = "sop.flow"
ENTITY_SOP_REVIEW_ITEM = "sop.review_item"


def _row_document(value: Any, model: Optional[type]) -> dict[str, Any]:
    """Project one stored value (pydantic model or mapping) into a JSON document."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if model is not None:
        return model(**dict(value)).model_dump(mode="json")
    return dict(value)


def _index_of(attribute: str) -> Any:
    """Resolve the legacy in-memory index lazily (avoids an import cycle)."""
    from src.domains.sop.service import sop_service

    return getattr(sop_service, attribute)


class _LegacyIndexAdapter:
    """Storage adapter over one ``SOPService`` in-memory index (data plumbing only)."""

    def __init__(
        self,
        spec_ref: list[EntitySpec],
        attribute: str,
        model: type,
        *,
        persist: bool = True,
        fallback: Optional[Any] = None,
    ):
        # ``spec_ref`` holds the spec being registered (frozen dataclass needs the
        # adapter before the spec exists, so the reference is bound afterwards).
        self._spec_ref = spec_ref
        self.attribute = attribute
        self.model = model
        self.persist = persist
        self.fallback = fallback

    @property
    def spec(self) -> EntitySpec:
        return self._spec_ref[0]

    # -- helpers --------------------------------------------------------
    def _index(self) -> Any:
        return _index_of(self.attribute)

    def _doc(self, value: Any) -> dict[str, Any]:
        return _row_document(value, self.model)

    def _key_of(self, value: Any) -> str:
        return self.spec.key_of(self._doc(value))

    # -- EntityAdapter contract -----------------------------------------
    def all(self) -> list[dict[str, Any]]:
        index = self._index()
        values = list(index.values()) if isinstance(index, dict) else list(index)
        return [self._doc(value) for value in values]

    def get(self, key: str) -> Optional[dict[str, Any]]:
        index = self._index()
        if isinstance(index, dict):
            value = index.get(key)
            if value is not None:
                return self._doc(value)
        else:
            for value in index:
                if self._key_of(value) == key:
                    return self._doc(value)
        if self.fallback is not None:
            return self.fallback(key)
        return None

    def create(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        return self._write(key, doc)

    def update(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        return self._write(key, doc)

    def delete(self, key: str) -> bool:
        index = self._index()
        removed = False
        if isinstance(index, dict):
            removed = index.pop(key, None) is not None
        else:
            for position, value in enumerate(list(index)):
                if self._key_of(value) == key:
                    index.pop(position)
                    removed = True
                    break
        if removed and self.persist:
            domain_persistence.delete(self.spec.family, key)
        return removed

    # -- write ----------------------------------------------------------
    def _write(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        stored = self.model(**dict(doc)) if self.model is not None else dict(doc)
        index = self._index()
        if isinstance(index, dict):
            index[key] = stored
        else:
            for position, value in enumerate(index):
                if self._key_of(value) == key:
                    index[position] = stored
                    break
            else:
                index.append(stored)
        if self.persist:
            domain_persistence.write(self.spec.family, key, stored)
        return self._doc(stored)


def _spec(
    name: str,
    family: str,
    model: type,
    *,
    attribute: str,
    id_prefix: str,
    key_fields: tuple[str, ...] = ("id",),
    order: str,
    search_fields: tuple[str, ...] = (),
    owner_field: Optional[str] = None,
    timestamps: bool = False,
    persist: bool = True,
    defaults: Optional[dict[str, Any]] = None,
    fallback: Optional[Any] = None,
) -> EntitySpec:
    """Build one spec whose storage is the matching legacy service index."""
    spec_ref: list[EntitySpec] = []
    adapter = _LegacyIndexAdapter(spec_ref, attribute, model, persist=persist, fallback=fallback)
    spec = EntitySpec(
        name=name,
        family=family,
        model=model,
        key_fields=key_fields,
        adapter=adapter,
        id_prefix=id_prefix,
        timestamps=timestamps,
        search_fields=search_fields,
        owner_field=owner_field,
        default_order=order,
        defaults=dict(defaults or {}),
    )
    spec_ref.append(spec)
    entity_store.register(spec)
    return spec


# ---------------------------------------------------------------------------
# Workflow graph: stages / nodes / edges / goals
# ---------------------------------------------------------------------------
sop_stage_entity = _spec(
    ENTITY_SOP_STAGE,
    "sop.stages",
    SOPStage,
    attribute="_stages",
    id_prefix="stage",
    key_fields=("code",),
    order="stage",
    search_fields=("name", "code"),
    persist=False,
)

sop_node_entity = _spec(
    ENTITY_SOP_NODE,
    "sop.nodes",
    SOPNode,
    attribute="_nodes",
    id_prefix="tpl",
    order="-published_at",
    search_fields=("name", "code", "summary", "description"),
    defaults={"kind": "document", "is_active": True},
)

sop_edge_entity = _spec(
    ENTITY_SOP_EDGE,
    "sop.edges",
    SOPEdge,
    attribute="_edges",
    id_prefix="edge",
    key_fields=("from_node", "to_node"),
    order="from_node",
    search_fields=("rationale",),
)

sop_goal_entity = _spec(
    ENTITY_SOP_GOAL,
    "sop.goals",
    SOPGoal,
    attribute="_goals",
    id_prefix="goal",
    order="id",
    search_fields=("title", "description"),
)

# ---------------------------------------------------------------------------
# Document templates & platform flow templates
# ---------------------------------------------------------------------------
def _template_from_document_node(key: str) -> Optional[dict[str, Any]]:
    """Re-project a document graph node into the template catalog (storage plumbing).

    The graph is the historical source of truth: document nodes double as
    renderable templates, so a reset template index is rebuilt on demand.
    """
    from src.domains.sop.service import sop_service

    node = sop_service._nodes.get(key)
    if node is None or node.kind != "document":
        return None
    sop_service._register_template_from_node(node)
    template = sop_service._templates.get(key)
    return template.model_dump(mode="json") if template is not None else None


sop_template_entity = _spec(
    ENTITY_SOP_TEMPLATE,
    "sop.templates",
    SOPTemplate,
    attribute="_templates",
    id_prefix="tpl",
    order="stage",
    search_fields=("name", "code", "description"),
    defaults={"is_active": True},
    fallback=_template_from_document_node,
)

sop_flow_template_entity = _spec(
    ENTITY_SOP_FLOW_TEMPLATE,
    "sop.flow_templates",
    SOPFlowTemplate,
    attribute="_flow_templates",
    id_prefix="flowpub",
    order="id",
    search_fields=("name", "summary", "description"),
)

# ---------------------------------------------------------------------------
# Maker-owned documents & flows
# ---------------------------------------------------------------------------
sop_document_entity = _spec(
    ENTITY_SOP_DOCUMENT,
    "sop.documents",
    SOPDocumentResponse,
    attribute="_documents",
    id_prefix="doc",
    order="-created_at",
    search_fields=("document_title", "rendered_content"),
    owner_field="user_id",
    timestamps=True,
)

sop_flow_entity = _spec(
    ENTITY_SOP_FLOW,
    "sop.flows",
    SOPFlow,
    attribute="_flows",
    id_prefix="flow",
    order="-updated_at",
    search_fields=("name", "description"),
    owner_field="owner_id",
    timestamps=True,
)

# ---------------------------------------------------------------------------
# Publish review queue
# ---------------------------------------------------------------------------
sop_review_item_entity = _spec(
    ENTITY_SOP_REVIEW_ITEM,
    "sop.review_queue",
    SOPReviewItem,
    attribute="_review_queue",
    id_prefix="rev",
    order="-submitted_at",
    search_fields=("title", "content"),
    owner_field="author_id",
    defaults={"status": "PENDING_REVIEW"},
)
