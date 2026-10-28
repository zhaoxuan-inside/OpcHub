"""Compatibility shim for the SOP (合规文书 / 流程模板 / 发布审核) domain.

Business flow now lives in ``config/scenarios/sop.yaml`` (operator orchestration),
single-responsibility calculations in ``src.domains.sop.functions`` and documents
in the generic entity store (``src.domains.sop.entities``).

This module only keeps the legacy data / query surface that other modules and
the gateway adapters still import:

* in-memory indexes that mirror ``domain_snapshots`` (``_nodes`` / ``_edges`` /
  ``_templates`` / ``_documents`` / ``_flows`` / ``_flow_templates`` /
  ``_review_queue``) plus their ``hydrate_*`` hydrators;
* read-only projections (catalog cards, graph queries, goal plans, flow detail);
* thin synchronous adapters over the shared pure functions for old callers;
* the background publish-review consumer, which periodically executes
  ``OPC_SOP_REVIEW_PROCESS_PIPELINE`` per pending submission.

It contains **no rendering, review decisioning or catalog publishing flow**:
those are computed by the pure operators and persisted by ``entity.*``
operators inside the scenario assets.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.core.entity import entity_store
from src.domains.sop.entities import (
    ENTITY_SOP_DOCUMENT,
    ENTITY_SOP_FLOW,
    ENTITY_SOP_FLOW_TEMPLATE,
    ENTITY_SOP_NODE,
    ENTITY_SOP_REVIEW_ITEM,
    ENTITY_SOP_TEMPLATE,
)
from src.domains.sop.models import (
    SOPDocumentCatalogResponse,
    SOPDocumentCreate,
    SOPDocumentDraftCreate,
    SOPDocumentResponse,
    SOPEdge,
    SOPField,
    SOPFlow,
    SOPFlowCreate,
    SOPFlowItem,
    SOPFlowResponse,
    SOPFlowTemplate,
    SOPFlowTemplateCatalogResponse,
    SOPFlowTemplateDetail,
    SOPFlowTemplateStep,
    SOPGoal,
    SOPGoalPlan,
    SOPGoalPlanItem,
    SOPGraphResponse,
    SOPMyFlowCard,
    SOPNode,
    SOPPublishResponse,
    SOPReviewItem,
    SOPReviewProcessResult,
    SOPReviewQueueResponse,
    SOPStage,
    SOPTemplate,
    SOPTemplateCreate,
    SOPTemplatesResponse,
    SOP_FLOW_STATUS_ACTIVE,
    SOP_NODE_DOCUMENT,
    SOP_NODE_SUBGRAPH,
    SOP_REVIEW_STATUS_APPROVED,
    SOP_REVIEW_STATUS_PENDING,
    SOP_REVIEW_STATUS_REJECTED,
    SOP_REVIEW_TARGET_DOCUMENT,
    SOP_REVIEW_TARGET_FLOW,
)
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.sop")

REVIEW_PROCESS_PIPELINE = "OPC_SOP_REVIEW_PROCESS_PIPELINE"
REVIEW_WITHDRAW_PIPELINE = "OPC_SOP_REVIEW_WITHDRAW_PIPELINE"
REVIEW_ACTOR_ID = "review_engine"


class _LazyFunctions:
    """Resolve ``src.domains.sop.functions`` on first use (breaks an import cycle)."""

    def __getattr__(self, name: str) -> Any:
        from src.domains.sop import functions

        return getattr(functions, name)


fn = _LazyFunctions()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


class SOPService:
    """Legacy data / query surface over the SOP entity store."""

    def __init__(self) -> None:
        self._stages: List[SOPStage] = []
        self._nodes: Dict[str, SOPNode] = {}
        self._edges: List[SOPEdge] = []
        self._goals: Dict[str, SOPGoal] = {}
        self._templates: Dict[str, SOPTemplate] = {}
        self._documents: Dict[str, SOPDocumentResponse] = {}
        self._flows: Dict[str, SOPFlow] = {}
        # Platform flow templates (the curated "流程向导" catalog).
        self._flow_templates: Dict[str, SOPFlowTemplate] = {}
        # Publish review queue: private documents / flows awaiting audit.
        self._review_queue: Dict[str, SOPReviewItem] = {}
        # Background consumer that audits and promotes approved submissions.
        self._review_consumer_task = None
        self._review_consumer_running = False
        self.review_consumer_interval = 5.0

    def _require_db(self) -> None:
        """SOP content is database-backed; refuse memory-only mutations."""
        domain_persistence.require("sop")

    # ------------------------------------------------------------------
    # Template catalog (document nodes are also renderable templates)
    # ------------------------------------------------------------------
    def _register_template_from_node(self, node: SOPNode) -> None:
        """Project a document-kind graph node into the legacy template catalog."""
        self._templates[node.id] = SOPTemplate(
            id=node.id,
            stage=node.stage,
            code=node.code,
            name=node.name,
            category=node.category,
            description=node.description,
            template_content=node.template_content,
            required_fields=list(node.required_fields),
            is_active=node.is_active,
        )

    def _ensure_template_registered(self, template_id: str) -> bool:
        """Re-project a document node into the template catalog if it went missing."""
        if template_id in self._templates:
            return True
        node = self._nodes.get(template_id)
        if node is None or node.kind != SOP_NODE_DOCUMENT:
            return False
        self._register_template_from_node(node)
        return True

    def get_stages_and_templates(self) -> SOPTemplatesResponse:
        """Get all SOP stages and available document templates."""
        # Self-heal: if the template catalog was reset, rebuild it from the graph.
        for node in self._nodes.values():
            if node.kind == SOP_NODE_DOCUMENT and node.id not in self._templates:
                self._register_template_from_node(node)
        return SOPTemplatesResponse(stages=self._stages, templates=list(self._templates.values()))

    def _template_or_none(self, template_id: Optional[str]) -> Optional[SOPTemplate]:
        """Self-healing lookup used by legacy adapters (graph is the source of truth)."""
        if not template_id:
            return None
        try:
            return self.get_template(template_id)
        except KeyError:
            return None

    def get_template(self, template_id: str) -> SOPTemplate:
        """Fetch template by ID (the graph is the source of truth)."""
        if template_id not in self._templates:
            self._ensure_template_registered(template_id)
        if template_id not in self._templates:
            raise KeyError(f"SOP template with ID {template_id} not found")
        return self._templates[template_id]

    def create_template(self, req: SOPTemplateCreate) -> SOPTemplate:
        """Register a new template (thin adapter over ``calc.sop.template_publish``)."""
        self._require_db()
        prepared = fn.template_publish({}, req.model_dump(mode="json"), {})
        template = SOPTemplate(**prepared["template"])
        node = SOPNode(**prepared["node"])
        entity_store.create(ENTITY_SOP_TEMPLATE, template.model_dump(mode="json"))
        entity_store.create(ENTITY_SOP_NODE, node.model_dump(mode="json"))
        return template

    # ------------------------------------------------------------------
    # Workflow graph (read-only)
    # ------------------------------------------------------------------
    def get_graph(self) -> SOPGraphResponse:
        return SOPGraphResponse(
            stages=list(self._stages),
            nodes=list(self._nodes.values()),
            edges=list(self._edges),
            goals=list(self._goals.values()),
        )

    def get_node(self, node_id: str) -> SOPNode:
        if node_id not in self._nodes:
            raise KeyError(f"SOP node with ID {node_id} not found")
        return self._nodes[node_id]

    def get_goals(self) -> List[SOPGoal]:
        return list(self._goals.values())

    def get_goal(self, goal_id: str) -> SOPGoal:
        if goal_id not in self._goals:
            raise KeyError(f"SOP goal with ID {goal_id} not found")
        return self._goals[goal_id]

    def _node_rows(self) -> List[dict[str, Any]]:
        return [_dump(node) for node in self._nodes.values()]

    def _edge_rows(self) -> List[dict[str, Any]]:
        return [_dump(edge) for edge in self._edges]

    # ------------------------------------------------------------------
    # Standard document catalog (标准文书库)
    # ------------------------------------------------------------------
    def list_document_cards(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> SOPDocumentCatalogResponse:
        """List the standard document catalog (projection of ``assemble.sop.document_cards``)."""
        nodes = self._node_rows()
        if category and category.lower() != "all":
            nodes = [node for node in nodes if node.get("category") == category]
        documents = [_dump(doc) for doc in self._documents.values()]
        cards = fn.document_cards({}, {"nodes": nodes, "documents": documents}, {})
        return SOPDocumentCatalogResponse(items=cards["items"], total=cards["total"])

    def _usage_counts(self) -> Dict[str, int]:
        """Count how many generated document instances each template has."""
        counts: Dict[str, int] = {}
        for doc in self._documents.values():
            counts[doc.template_id] = counts.get(doc.template_id, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Platform flow templates (平台流程模板)
    # ------------------------------------------------------------------
    def list_flow_template_cards(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> SOPFlowTemplateCatalogResponse:
        """List the platform flow catalog (projection of ``assemble.sop.flow_template_cards``)."""
        templates = [_dump(flow) for flow in self._flow_templates.values()]
        if category and category.lower() != "all":
            templates = [flow for flow in templates if flow.get("category") == category]
        cards = fn.flow_template_cards(
            {},
            {
                "templates": templates,
                "nodes": self._node_rows(),
                "flows": [_dump(flow) for flow in self._flows.values()],
            },
            {},
        )
        return SOPFlowTemplateCatalogResponse(items=cards["items"], total=cards["total"])

    def _resolve_flow_steps(self, flow: SOPFlowTemplate) -> tuple:
        """Expand a flow template into its ordered document steps."""
        result = fn.steps(
            {"order": "REFERENCE"},
            {"refs": [_dump(ref) for ref in flow.node_refs], "nodes": self._node_rows()},
            {},
        )
        steps = [
            SOPFlowTemplateStep(
                node_id=item["node_id"],
                name=item["name"],
                kind=item["kind"],
                stage=item["stage"],
                category=item["category"],
                description=item["description"],
                outcome=item["outcome"],
                note=item["note"],
                required=item["required"],
                order=item["order"],
                required_fields=list(item["required_fields"]),
            )
            for item in result["items"]
        ]
        return steps, result["missing_nodes"]

    def get_flow_template_detail(self, flow_id: str) -> SOPFlowTemplateDetail:
        """Resolve a flow template into its ordered document steps."""
        flow = self.get_flow_template(flow_id)
        steps, missing = self._resolve_flow_steps(flow)
        detail = fn.flow_template_detail(
            {},
            {"template": _dump(flow), "steps": [_dump(step) for step in steps], "missing_nodes": missing},
            {},
        )
        return SOPFlowTemplateDetail(
            template=flow,
            steps=steps,
            missing_nodes=detail["missing_nodes"],
        )

    def _flow_usage_counts(self) -> Dict[str, int]:
        """Count user flows forked from each platform flow template."""
        counts: Dict[str, int] = {}
        for user_flow in self._flows.values():
            template_id = getattr(user_flow, "template_id", None)
            if template_id:
                counts[template_id] = counts.get(template_id, 0) + 1
        return counts

    def get_flow_template(self, flow_id: str) -> SOPFlowTemplate:
        if flow_id not in self._flow_templates:
            raise KeyError(f"SOP flow template with ID {flow_id} not found")
        return self._flow_templates[flow_id]

    # ------------------------------------------------------------------
    # Graph resolution helpers
    # ------------------------------------------------------------------
    def expand_subgraph(self, node_id: str, _seen: Optional[Set[str]] = None) -> List[SOPNode]:
        """Flatten a node into the document nodes it contains."""
        seen = _seen if _seen is not None else set()
        if node_id in seen:
            return []
        seen.add(node_id)

        node = self.get_node(node_id)
        if node.kind != SOP_NODE_SUBGRAPH:
            return [node]

        expanded: List[SOPNode] = []
        for child_id in node.children:
            expanded.extend(self.expand_subgraph(child_id, seen))
        return expanded

    def resolve_goal_plan(self, goal_id: str) -> SOPGoalPlan:
        """Reverse-resolve a business goal into an ordered list of required documents."""
        goal = self.get_goal(goal_id)
        plan, missing = self._build_plan_items(
            [(node_id, True) for node_id in goal.required_nodes]
            + [(node_id, False) for node_id in goal.recommended_nodes]
        )
        return SOPGoalPlan(
            goal=goal,
            items=plan,
            edges=self._edges_for(plan),
            missing_nodes=missing,
        )

    def _edges_for(self, items: List[Any]) -> List[SOPEdge]:
        node_ids = {item.node_id for item in items}
        return [
            edge
            for edge in self._edges
            if edge.from_node in node_ids and edge.to_node in node_ids
        ]

    def _build_plan_items(self, refs: List[tuple]) -> tuple:
        """Expand node references into ordered plan items via ``calc.sop.steps``."""
        result = fn.steps(
            {},
            {
                "refs": [{"node_id": node_id, "required": required} for node_id, required in refs],
                "nodes": self._node_rows(),
                "edges": self._edge_rows(),
            },
            {},
        )
        plan = [
            SOPGoalPlanItem(
                node_id=item["node_id"],
                name=item["name"],
                kind=item["kind"],
                stage=item["stage"],
                category=item["category"],
                description=item["description"],
                outcome=item["outcome"],
                next_hint=item["next_hint"],
                required=item["required"],
                order=item["order"],
                depth=item["depth"],
                parent_id=item["parent_id"],
                required_fields=[SOPField(**field) for field in item["required_fields"]],
            )
            for item in result["items"]
        ]
        return plan, result["missing_nodes"]

    def get_node_context(self, node_id: str) -> Dict[str, Any]:
        """Collect everything the workspace needs to explain one node to a maker."""
        node = self.get_node(node_id)
        context = fn.node_context(
            {},
            {"node": _dump(node), "nodes": self._node_rows(), "edges": self._edge_rows()},
            {},
        )
        return {
            "node": node,
            "children": [self._nodes[child["id"]] for child in context["children"]],
            "prerequisites": context["prerequisites"],
        }

    # ------------------------------------------------------------------
    # Maker-owned flows
    # ------------------------------------------------------------------
    def create_flow(self, req: SOPFlowCreate) -> SOPFlow:
        """Create a user-owned flow (thin adapter over ``calc.sop.flow_create``)."""
        self._require_db()
        prepared = fn.flow_create({}, req.model_dump(mode="json"), {"user_id": req.owner_id or ""})
        created = entity_store.create(ENTITY_SOP_FLOW, prepared["flow"])
        return self._flows[created["id"]]

    def list_flows(self, owner_id: Optional[str] = None) -> List[SOPFlow]:
        flows = list(self._flows.values())
        if owner_id:
            flows = [flow for flow in flows if flow.owner_id == owner_id]
        flows.sort(key=lambda flow: flow.updated_at, reverse=True)
        return flows

    def list_my_flow_cards(self, owner_id: Optional[str] = None) -> List[SOPMyFlowCard]:
        """List the maker's own flows as cards (projection over the shared assembler)."""
        flows = [
            _dump(flow)
            for flow in self._flows.values()
            if not owner_id or flow.owner_id == owner_id
        ]
        cards = fn.my_flow_cards({}, {"flows": flows, "nodes": self._node_rows()}, {})
        return [SOPMyFlowCard(**card) for card in cards["items"]]

    def get_flow(self, flow_id: str) -> SOPFlow:
        if flow_id not in self._flows:
            raise KeyError(f"SOP flow with ID {flow_id} not found")
        return self._flows[flow_id]

    def update_flow(self, flow_id: str, req: SOPFlowCreate) -> SOPFlow:
        """Replace the content of an existing flow (thin adapter over the pure diff)."""
        self._require_db()
        flow = self.get_flow(flow_id)
        prepared = fn.flow_update(
            {},
            {"flow_id": flow_id, "current": _dump(flow), **req.model_dump(mode="json")},
            {"user_id": req.owner_id or flow.owner_id},
        )
        entity_store.update(ENTITY_SOP_FLOW, prepared["flow"])
        return self._flows[prepared["flow"]["id"]]

    def delete_flow(self, flow_id: str) -> bool:
        self._require_db()
        if flow_id not in self._flows:
            return False
        return entity_store.delete(ENTITY_SOP_FLOW, {"key": flow_id})

    def resolve_flow(self, flow_id: str) -> SOPFlowResponse:
        """Resolve a stored flow into its ordered document list."""
        flow = self.get_flow(flow_id)
        plan, missing = self._build_plan_items(
            [(ref.node_id, ref.required) for ref in flow.node_refs]
        )
        items = [
            SOPFlowItem(
                node_id=item.node_id,
                name=item.name,
                kind=item.kind,
                stage=item.stage,
                category=item.category,
                description=item.description,
                outcome=item.outcome,
                next_hint=item.next_hint,
                required=item.required,
                order=item.order,
                depth=item.depth,
                parent_id=item.parent_id,
                required_fields=list(item.required_fields),
            )
            for item in plan
        ]
        detail = fn.flow_detail(
            {},
            {
                "flow": _dump(flow),
                "items": [_dump(item) for item in items],
                "edges": self._edge_rows(),
                "missing_nodes": missing,
            },
            {},
        )
        return SOPFlowResponse(
            flow=flow,
            items=items,
            edges=[SOPEdge(**edge) for edge in detail["edges"]],
            missing_nodes=detail["missing_nodes"],
        )

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    def validate_render_payload(self, inputs: dict) -> dict:
        template_id = str((inputs or {}).get("template_id") or "").strip()
        if not template_id:
            raise ValueError("template_id is required for document rendering")
        template = self.get_template(template_id)
        form_data = inputs.get("form_data") or {}
        if not isinstance(form_data, dict):
            form_data = {}
        return {
            "guard_passed": True,
            "template_id": template_id,
            "template_name": template.name,
            "user_id": inputs.get("user_id", ""),
            "form_data": form_data,
        }

    def render_and_save_document(self, payload: SOPDocumentCreate) -> SOPDocumentResponse:
        """Render a template and persist the instance (legacy synchronous entry)."""
        self._require_db()
        template = self.get_template(payload.template_id)
        prepared = fn.render_document(
            {"enforce_required": False},
            {
                "template_id": payload.template_id,
                "template": _dump(template),
                "form_data": payload.form_data,
                "user_id": payload.user_id,
            },
            {"user_id": payload.user_id},
        )
        created = entity_store.create(ENTITY_SOP_DOCUMENT, prepared["document"])
        return self._documents[created["id"]]

    def save_draft_document(self, payload: SOPDocumentDraftCreate) -> SOPDocumentResponse:
        """Persist a freely-edited draft (legacy synchronous entry)."""
        self._require_db()
        current = self._documents.get(payload.doc_id) if payload.doc_id else None
        template = self._template_or_none(payload.template_id)
        prepared = fn.document_draft(
            {},
            {
                "doc_id": payload.doc_id,
                "title": payload.title,
                "content": payload.content,
                "template_id": payload.template_id,
                "category": payload.category,
                "current": _dump(current) if current is not None else None,
                "template": _dump(template) if template is not None else None,
            },
            {"user_id": payload.user_id},
        )
        document = prepared["document"]
        if entity_store.get(ENTITY_SOP_DOCUMENT, {"key": document["id"]}) is None:
            entity_store.create(ENTITY_SOP_DOCUMENT, document)
        else:
            entity_store.update(ENTITY_SOP_DOCUMENT, document)
        return self._documents[document["id"]]

    def snapshot_draft(self, doc_id: str) -> dict:
        """Capture the mutable fields of a draft for Saga rollback."""
        doc = self.get_document(doc_id)
        return {
            "document_title": doc.document_title,
            "rendered_content": doc.rendered_content,
            "template_id": doc.template_id,
            "category": doc.category,
            "status": doc.status,
            "updated_at": doc.updated_at,
        }

    def restore_draft_snapshot(self, doc_id: str, snapshot: dict) -> bool:
        """Restore a draft from a snapshot taken before an atomic save."""
        self._require_db()
        if str(doc_id) not in self._documents or not snapshot:
            return False
        entity_store.update(
            ENTITY_SOP_DOCUMENT,
            {"id": str(doc_id), **{key: value for key, value in snapshot.items() if value is not None}},
        )
        return True

    def get_document(self, doc_id: str) -> SOPDocumentResponse:
        if doc_id not in self._documents:
            raise KeyError(f"SOP document with ID {doc_id} not found")
        return self._documents[doc_id]

    def list_documents(self, user_id: Optional[str] = None) -> List[SOPDocumentResponse]:
        docs = list(self._documents.values())
        if user_id:
            docs = [doc for doc in docs if doc.user_id == user_id]
        docs.sort(key=lambda doc: doc.created_at, reverse=True)
        return docs

    def delete_document(self, doc_id: str) -> bool:
        self._require_db()
        if doc_id not in self._documents:
            return False
        return entity_store.delete(ENTITY_SOP_DOCUMENT, {"key": doc_id})

    # ------------------------------------------------------------------
    # Publish review queue (发布审核队列)
    # ------------------------------------------------------------------
    def _resolve_author_name(self, user_id: str) -> str:
        """Resolve a maker's display name for published provenance."""
        if not user_id:
            return "创客"
        try:
            from src.domains.user.service import user_service

            profile = user_service.get_profile(uid=user_id)
            if profile and getattr(profile, "nickname", None):
                return profile.nickname
        except Exception:
            pass
        return "创客"

    @staticmethod
    def _flatten_text(text: str, limit: int = 0) -> str:
        """Collapse whitespace / newlines of a rendered document into one line."""
        flat = " ".join((text or "").split())
        return flat[:limit] if limit else flat

    def _submit_for_review(
        self,
        target_type: str,
        target: dict[str, Any],
        user_id: str,
        is_official: bool,
        extra: Optional[dict[str, Any]] = None,
    ) -> SOPPublishResponse:
        """Shared thin adapter around ``calc.sop.review_submission`` + entity writes."""
        prepared = fn.review_submission(
            {"target_type": target_type},
            {"target_type": target_type, "target": target, "author_name": self._resolve_author_name(user_id), **(extra or {})},
            {"user_id": user_id, "user_role": "ADMIN" if is_official else "MAKER"},
        )
        entity_type = ENTITY_SOP_DOCUMENT if target_type == SOP_REVIEW_TARGET_DOCUMENT else ENTITY_SOP_FLOW
        entity_store.update(entity_type, prepared["target_patch"])
        item = entity_store.create(ENTITY_SOP_REVIEW_ITEM, prepared["review_item"])
        logger.debug("Queued review submission %s for %s", item.get("id"), target.get("id"))
        return SOPPublishResponse(**prepared["response"])

    def submit_document_for_review(self, doc_id: str, user_id: str, is_official: bool = False) -> SOPPublishResponse:
        """Submit one of the maker's own documents for publish review (legacy entry)."""
        self._require_db()
        document = self.get_document(doc_id)
        return self._submit_for_review(
            SOP_REVIEW_TARGET_DOCUMENT, _dump(document), user_id, is_official
        )

    def submit_flow_for_review(self, flow_id: str, user_id: str, is_official: bool = False) -> SOPPublishResponse:
        """Submit one of the maker's own flows for publish review (legacy entry)."""
        self._require_db()
        flow = self.get_flow(flow_id)
        plan, missing = self._build_plan_items(
            [(ref.node_id, ref.required) for ref in flow.node_refs]
        )
        return self._submit_for_review(
            SOP_REVIEW_TARGET_FLOW,
            _dump(flow),
            user_id,
            is_official,
            {"steps": [_dump(step) for step in plan], "missing": missing},
        )

    def withdraw_review_submission(self, item_id: str) -> bool:
        """Legacy Saga compensation: drop the queue item and roll the target back."""
        self._require_db()
        item = self._review_queue.get(str(item_id))
        if item is None:
            return False
        if item.target_type == SOP_REVIEW_TARGET_DOCUMENT:
            if item.target_id in self._documents:
                entity_store.update(ENTITY_SOP_DOCUMENT, {"id": item.target_id, "status": fn.STATUS_READY})
        elif item.target_id in self._flows:
            entity_store.update(ENTITY_SOP_FLOW, {"id": item.target_id, "status": SOP_FLOW_STATUS_ACTIVE})
        entity_store.delete(ENTITY_SOP_REVIEW_ITEM, {"key": item.id})
        return True

    def list_review_queue(self, status: Optional[str] = None) -> SOPReviewQueueResponse:
        """List the publish review queue, optionally filtered by status."""
        items = list(self._review_queue.values())
        if status:
            items = [item for item in items if item.status.upper() == status.upper()]
        items.sort(key=lambda item: item.submitted_at, reverse=True)
        statuses = [item.status for item in self._review_queue.values()]
        return SOPReviewQueueResponse(
            items=items,
            total=len(items),
            pending=statuses.count(SOP_REVIEW_STATUS_PENDING),
            approved=statuses.count(SOP_REVIEW_STATUS_APPROVED),
            rejected=statuses.count(SOP_REVIEW_STATUS_REJECTED),
        )

    def publish_document_to_catalog(self, doc: SOPDocumentResponse, is_official: bool = False) -> str:
        """Promote a document into the standard catalog (legacy synchronous entry)."""
        self._require_db()
        template = self._template_or_none(doc.template_id)
        prepared = fn.published_document(
            {},
            {
                "document": _dump(doc),
                "item": {"is_official": is_official, "author_name": self._resolve_author_name(doc.user_id)},
                "template": _dump(template) if template is not None else None,
            },
            {},
        )
        entity_store.create(ENTITY_SOP_NODE, prepared["node"])
        entity_store.create(ENTITY_SOP_TEMPLATE, prepared["template"])
        return prepared["published_id"]

    def publish_flow_to_catalog(self, flow: SOPFlow, is_official: bool = False) -> str:
        """Promote a flow into the platform flow guide (legacy synchronous entry)."""
        self._require_db()
        plan, _missing = self._build_plan_items(
            [(ref.node_id, ref.required) for ref in flow.node_refs]
        )
        prepared = fn.published_flow(
            {},
            {
                "flow": _dump(flow),
                "item": {"is_official": is_official, "author_name": self._resolve_author_name(flow.owner_id)},
                "steps": [_dump(step) for step in plan],
            },
            {},
        )
        entity_store.create(ENTITY_SOP_FLOW_TEMPLATE, prepared["flow_template"])
        return prepared["published_id"]

    # ------------------------------------------------------------------
    # Review consumer: executes the review scenario per pending submission
    # ------------------------------------------------------------------
    async def _content_safety_gate(self, item: SOPReviewItem) -> Dict[str, Any]:
        """Run the platform content-safety gate (infrastructure) before the scenario.

        The sensitive-word / legality gate is a platform capability, not a SOP
        business decision: it is executed by the shared moderation gateway and its
        verdict is handed to ``OPC_SOP_REVIEW_PROCESS_PIPELINE`` through
        ``gate_passed`` / ``gate_reason`` so the scenario stays free of I/O.
        """
        try:
            from src.infrastructure.external_gateway.content_moderation_gateway import prescreen_and_record

            await prescreen_and_record(
                item.content,
                field_name=f"{item.target_type} 发布审核",
                user_id=item.author_id,
                scene="流程文书审核",
                title=item.title,
                target_type=item.target_type,
                target_id=item.target_id,
            )
            return {"passed": True, "reason": ""}
        except Exception as exc:  # noqa: BLE001 - a failed gate rejects the submission
            return {"passed": False, "reason": str(exc)}

    async def _process_one(self, item: SOPReviewItem) -> Dict[str, Any]:
        from src.domains.orchestration.models import ScenarioExecuteRequest
        from src.domains.orchestration.service import orchestration_service

        gate = await self._content_safety_gate(item)
        result = await orchestration_service.execute_scenario(
            ScenarioExecuteRequest(
                scenario_code=REVIEW_PROCESS_PIPELINE,
                version="v1.0.0",
                inputs={
                    "item_id": item.id,
                    "gate_passed": gate["passed"],
                    "gate_reason": gate["reason"],
                },
                context={
                    "user_id": REVIEW_ACTOR_ID,
                    "user_role": "SYSTEM",
                    "nickname": "审核引擎",
                },
            )
        )
        decision = dict((result.final_output or {}).get("review_decision") or {})
        if result.status != "SUCCESS":
            logger.warning("Review item %s failed: %s", item.id, result.error_message)
            decision.setdefault("item_id", item.id)
            decision.setdefault("target_id", item.target_id)
            decision.setdefault("target_type", item.target_type)
            decision.setdefault("status", "FAILED")
            decision.setdefault("review_note", result.error_message or "审核处理失败")
        return decision

    async def process_review_queue(self, limit: Optional[int] = None) -> SOPReviewProcessResult:
        """Consume the pending review queue through ``OPC_SOP_REVIEW_PROCESS_PIPELINE``."""
        pending = [item for item in self._review_queue.values() if item.status == SOP_REVIEW_STATUS_PENDING]
        pending.sort(key=lambda item: item.submitted_at)
        if limit is not None and int(limit) > 0:
            pending = pending[: int(limit)]

        summary = SOPReviewProcessResult(processed=len(pending))
        for item in pending:
            decision = await self._process_one(item)
            status = str(decision.get("status") or "")
            if status == SOP_REVIEW_STATUS_APPROVED:
                summary.approved += 1
                if str(decision.get("target_type")) == SOP_REVIEW_TARGET_DOCUMENT:
                    summary.published_documents.append(str(decision.get("target_id")))
                else:
                    summary.published_flows.append(str(decision.get("target_id")))
            elif status == SOP_REVIEW_STATUS_REJECTED:
                summary.rejected += 1
            summary.details.append(
                {
                    "item_id": decision.get("item_id") or item.id,
                    "title": item.title,
                    "status": status,
                    "note": decision.get("review_note", ""),
                }
            )
        return summary

    async def _review_consumer_loop(self) -> None:
        logger.info("[SOP Review] Publish review consumer loop started")
        while self._review_consumer_running:
            try:
                await self.process_review_queue()
            except Exception as exc:  # noqa: BLE001 - a cycle failure must not stop the loop
                logger.warning("[SOP Review] Consumer cycle exception: %s", exc)
            try:
                await asyncio.sleep(self.review_consumer_interval)
            except asyncio.CancelledError:
                break

    def start_review_consumer(self, interval: float = 5.0) -> None:
        """Start the non-blocking consumer that drains the publish review queue."""
        self.review_consumer_interval = float(interval)
        if self._review_consumer_running:
            return
        self._review_consumer_running = True
        try:
            loop = asyncio.get_running_loop()
            self._review_consumer_task = loop.create_task(self._review_consumer_loop())
        except RuntimeError:
            self._review_consumer_running = False

    def stop_review_consumer(self) -> None:
        self._review_consumer_running = False
        if self._review_consumer_task and not self._review_consumer_task.done():
            self._review_consumer_task.cancel()
            self._review_consumer_task = None

    def review_consumer_status(self) -> Dict[str, Any]:
        return {
            "running": self._review_consumer_running,
            "interval_seconds": self.review_consumer_interval,
            "queue_size": len(self._review_queue),
            "pending": sum(1 for item in self._review_queue.values() if item.status == SOP_REVIEW_STATUS_PENDING),
            "pipeline": REVIEW_PROCESS_PIPELINE,
        }

    # ------------------------------------------------------------------
    # Hydrators (domain_snapshots -> in-memory indexes)
    # ------------------------------------------------------------------
    def hydrate_templates(self, rows: List[Dict]) -> int:
        for row in rows:
            self._templates[row["id"]] = SOPTemplate(**row)
        return len(rows)

    def hydrate_documents(self, rows: List[Dict]) -> int:
        for row in rows:
            self._documents[row["id"]] = SOPDocumentResponse(**row)
        return len(rows)

    def hydrate_flows(self, rows: List[Dict]) -> int:
        for row in rows:
            self._flows[row["id"]] = SOPFlow(**row)
        return len(rows)

    def hydrate_nodes(self, rows: List[Dict]) -> int:
        for row in rows:
            node = SOPNode(**row)
            self._nodes[node.id] = node
            if node.kind == SOP_NODE_DOCUMENT:
                self._register_template_from_node(node)
        return len(rows)

    def hydrate_edges(self, rows: List[Dict]) -> int:
        for row in rows:
            edge = SOPEdge(**row)
            self._edges.append(edge)
        return len(rows)

    def hydrate_goals(self, rows: List[Dict]) -> int:
        for row in rows:
            goal = SOPGoal(**row)
            self._goals[goal.id] = goal
        return len(rows)

    def hydrate_flow_templates(self, rows: List[Dict]) -> int:
        for row in rows:
            self._flow_templates[row["id"]] = SOPFlowTemplate(**row)
        return len(rows)

    def hydrate_review_queue(self, rows: List[Dict]) -> int:
        for row in rows:
            self._review_queue[row["id"]] = SOPReviewItem(**row)
        return len(rows)


sop_service = SOPService()

domain_persistence.register("sop.templates", sop_service.hydrate_templates)
domain_persistence.register("sop.documents", sop_service.hydrate_documents)
domain_persistence.register("sop.flows", sop_service.hydrate_flows)
domain_persistence.register("sop.nodes", sop_service.hydrate_nodes)
domain_persistence.register("sop.edges", sop_service.hydrate_edges)
domain_persistence.register("sop.goals", sop_service.hydrate_goals)
domain_persistence.register("sop.flow_templates", sop_service.hydrate_flow_templates)
domain_persistence.register("sop.review_queue", sop_service.hydrate_review_queue)
