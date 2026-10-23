"""SOP Service managing workflow stages, document templates, the workflow graph, and generated document instances."""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.domains.sop.models import (
    SOPStage,
    SOPTemplate,
    SOPTemplateCreate,
    SOPTemplatesResponse,
    SOPDocumentCreate,
    SOPDocumentResponse,
    SOPNode,
    SOPEdge,
    SOPGoal,
    SOPGraphResponse,
    SOPGoalPlan,
    SOPGoalPlanItem,
    SOPFlow,
    SOPFlowCreate,
    SOPFlowItem,
    SOPFlowResponse,
    SOPFlowTemplate,
    SOPFlowTemplateCard,
    SOPMyFlowCard,
    SOPFlowTemplateCatalogResponse,
    SOPFlowTemplateDetail,
    SOPFlowTemplateInteractionResponse,
    SOPFlowTemplateStep,
    SOPDocumentCard,
    SOPDocumentCatalogResponse,
    SOPInteractionResponse,
    SOPReviewItem,
    SOPReviewQueueResponse,
    SOPReviewProcessResult,
    SOPPublishResponse,
    SOP_NODE_DOCUMENT,
    SOP_NODE_SUBGRAPH,
    SOP_EDGE_PREREQUISITE,
    SOP_FLOW_STATUS_ACTIVE,
    SOP_FLOW_STATUS_DRAFT,
    SOP_FLOW_STATUS_PENDING_REVIEW,
    SOP_FLOW_STATUS_PUBLISHED,
    SOP_FLOW_STATUS_REJECTED,
    SOP_DOC_STATUS_READY,
    SOP_DOC_STATUS_PENDING_REVIEW,
    SOP_DOC_STATUS_PUBLISHED,
    SOP_DOC_STATUS_REJECTED,
    SOP_REVIEW_TARGET_DOCUMENT,
    SOP_REVIEW_TARGET_FLOW,
    SOP_REVIEW_STATUS_PENDING,
    SOP_REVIEW_STATUS_APPROVED,
    SOP_REVIEW_STATUS_REJECTED,
    SOPFlowTemplateRef,
)
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.sop")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_sop_seeds() -> Dict[str, Any]:
    """Load the workflow graph seeds (stages / nodes / edges / goals) from an external data file.

    Maintains strict code, config, and data separation: zero workflow records hardcoded in source.
    """
    search_paths = [
        Path("backend/data/seeds/sop.json"),
        Path("data/seeds/sop.json"),
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "sop.json",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load SOP seeds from %s: %s", p, e)
    return {}


DEFAULT_SOP_SEEDS: Dict[str, Any] = _load_sop_seeds()


def _load_sop_flow_seeds() -> Dict[str, Any]:
    """Load the platform flow-template seeds from an external data file.

    Kept apart from ``sop.json`` so the authoring data for flows and for the
    document graph can evolve independently.
    """
    search_paths = [
        Path("backend/data/seeds/sop_flows.json"),
        Path("data/seeds/sop_flows.json"),
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "sop_flows.json",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load SOP flow seeds from %s: %s", p, e)
    return {}


DEFAULT_SOP_FLOW_SEEDS: Dict[str, Any] = _load_sop_flow_seeds()


class SOPService:
    """Manages business registration and compliance document templates and generated instances."""

    def __init__(self):
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
        # (user_id, node_id) pairs for likes and favourites.
        self._likes: Set[tuple] = set()
        self._favorites: Set[tuple] = set()
        # (user_id, flow_template_id) pairs for flow likes and favourites.
        self._flow_likes: Set[tuple] = set()
        self._flow_favorites: Set[tuple] = set()
        self._init_seeds()

    # ------------------------------------------------------------------
    # Seed loading
    # ------------------------------------------------------------------
    def _init_seeds(self) -> None:
        """Populate the workflow graph and the template catalog from external seed data."""
        stages = DEFAULT_SOP_SEEDS.get("stages") or []
        for raw in stages:
            stage = SOPStage(**raw)
            self._stages.append(stage)

        for raw in DEFAULT_SOP_SEEDS.get("nodes") or []:
            node = SOPNode(**raw)
            self._nodes[node.id] = node
            if node.kind == SOP_NODE_DOCUMENT:
                self._register_template_from_node(node)

        for raw in DEFAULT_SOP_SEEDS.get("edges") or []:
            self._edges.append(SOPEdge(**raw))

        for raw in DEFAULT_SOP_SEEDS.get("goals") or []:
            goal = SOPGoal(**raw)
            self._goals[goal.id] = goal

        # Platform flow templates: an ordered set of nodes completing one outcome.
        for raw in DEFAULT_SOP_FLOW_SEEDS.values():
            flow = SOPFlowTemplate(**raw)
            self._flow_templates[flow.id] = flow

        # Persist seeded graph documents so they survive a restart.
        for node in self._nodes.values():
            if node.kind == SOP_NODE_DOCUMENT:
                template = self._templates.get(node.id)
                if template is not None:
                    domain_persistence.write("sop.templates", node.id, template)

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
        """Re-project a document node into the template catalog if it went missing.

        The template catalog and the graph are two views of the same data. Isolated
        tests (and future admin tooling) may reset the catalog directly; in that case
        the document node is the surviving source of truth and can rebuild its
        template on demand.
        """
        if template_id in self._templates:
            return True
        node = self._nodes.get(template_id)
        if node is None or node.kind != SOP_NODE_DOCUMENT:
            return False
        self._register_template_from_node(node)
        return True

    # ------------------------------------------------------------------
    # Legacy template accessors (kept for backward compatibility)
    # ------------------------------------------------------------------
    def get_stages_and_templates(self) -> SOPTemplatesResponse:
        """Get all SOP stages and available active document templates."""
        # Self-heal: if the template catalog was reset, rebuild it from the graph.
        for node in self._nodes.values():
            if node.kind == SOP_NODE_DOCUMENT and node.id not in self._templates:
                self._register_template_from_node(node)
        return SOPTemplatesResponse(
            stages=self._stages,
            templates=list(self._templates.values()),
        )

    def get_template(self, template_id: str) -> SOPTemplate:
        """Fetch template by ID."""
        if template_id not in self._templates:
            # The graph is the source of truth; rebuild the template if it was reset.
            self._ensure_template_registered(template_id)
        if template_id not in self._templates:
            raise KeyError(f"SOP template with ID {template_id} not found")
        return self._templates[template_id]

    def create_template(self, req: SOPTemplateCreate) -> SOPTemplate:
        """Create and register a new SOP compliance document template."""
        tid = f"tpl_{uuid.uuid4().hex[:8]}"
        template = SOPTemplate(
            id=tid,
            stage=req.stage,
            code=req.code,
            name=req.name,
            category=req.category,
            description=req.description,
            template_content=req.template_content,
            required_fields=req.required_fields,
            is_active=True,
        )
        self._templates[tid] = template
        # Keep the graph in sync so a runtime-published template is fillable in the workbench.
        self._nodes[tid] = SOPNode(
            id=tid,
            kind=SOP_NODE_DOCUMENT,
            code=req.code,
            name=req.name,
            stage=req.stage,
            category=req.category,
            description=req.description,
            template_content=req.template_content,
            required_fields=list(req.required_fields),
        )
        domain_persistence.write("sop.templates", tid, template)
        return template

    # ------------------------------------------------------------------
    # Workflow graph
    # ------------------------------------------------------------------
    def get_graph(self) -> SOPGraphResponse:
        """Return the whole workflow graph: stages, nodes, edges and goals."""
        return SOPGraphResponse(
            stages=list(self._stages),
            nodes=list(self._nodes.values()),
            edges=list(self._edges),
            goals=list(self._goals.values()),
        )

    def get_node(self, node_id: str) -> SOPNode:
        """Fetch a graph node (document or subgraph) by ID."""
        if node_id not in self._nodes:
            raise KeyError(f"SOP node with ID {node_id} not found")
        return self._nodes[node_id]

    def get_goals(self) -> List[SOPGoal]:
        """List all business goals available for reverse lookup."""
        return list(self._goals.values())

    def get_goal(self, goal_id: str) -> SOPGoal:
        """Fetch a single business goal."""
        if goal_id not in self._goals:
            raise KeyError(f"SOP goal with ID {goal_id} not found")
        return self._goals[goal_id]

    # ------------------------------------------------------------------
    # Standard document catalog (标准文书库)
    #
    # The workbench lists documents only. Subgraphs are workflow structures that
    # bundle several documents; they are not themselves fillable, so they never
    # appear in this catalog.
    # ------------------------------------------------------------------
    def list_document_cards(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> SOPDocumentCatalogResponse:
        """List the standard document catalog with the caller's own interactions."""
        live_usage = self._usage_counts()
        cards: List[SOPDocumentCard] = []

        for node in self._nodes.values():
            if node.kind != SOP_NODE_DOCUMENT or not node.is_active:
                continue
            if category and category.lower() != "all" and node.category != category:
                continue
            cards.append(
                SOPDocumentCard(
                    id=node.id,
                    name=node.name,
                    summary=node.summary or node.description,
                    author_name=node.author_name,
                    author_title=node.author_title,
                    publisher_org=node.publisher_org,
                    is_official=node.is_official,
                    published_at=node.published_at,
                    stage=node.stage,
                    category=node.category,
                    like_count=node.like_count,
                    favorite_count=node.favorite_count,
                    # The seeded baseline is the platform-wide usage figure;
                    # any document instance persisted on this deployment adds to it.
                    usage_count=node.usage_count + live_usage.get(node.id, 0),
                    field_count=len(node.required_fields),
                    liked=bool(user_id) and (user_id, node.id) in self._likes,
                    favorited=bool(user_id) and (user_id, node.id) in self._favorites,
                )
            )

        # Most-liked first; ties broken by the newest publish date.
        cards.sort(key=lambda c: (c.like_count, c.published_at), reverse=True)
        return SOPDocumentCatalogResponse(items=cards, total=len(cards))

    def _usage_counts(self) -> Dict[str, int]:
        """Count how many generated document instances each template has."""
        counts: Dict[str, int] = {}
        for doc in self._documents.values():
            counts[doc.template_id] = counts.get(doc.template_id, 0) + 1
        return counts

    def toggle_like(self, user_id: str, node_id: str) -> SOPInteractionResponse:
        """Toggle the caller's like on a standard document."""
        node = self.get_node(node_id)
        if node.kind != SOP_NODE_DOCUMENT:
            raise ValueError("只有标准文书支持喜欢操作")
        key = (user_id, node_id)
        if key in self._likes:
            self._likes.discard(key)
            node.like_count = max(0, node.like_count - 1)
        else:
            self._likes.add(key)
            node.like_count += 1
        domain_persistence.write("sop.likes", f"{user_id}:{node_id}", {"user_id": user_id, "node_id": node_id})
        return self._interaction_state(user_id, node)

    def toggle_favorite(self, user_id: str, node_id: str) -> SOPInteractionResponse:
        """Toggle the caller's favourite on a standard document."""
        node = self.get_node(node_id)
        if node.kind != SOP_NODE_DOCUMENT:
            raise ValueError("只有标准文书支持收藏操作")
        key = (user_id, node_id)
        if key in self._favorites:
            self._favorites.discard(key)
            node.favorite_count = max(0, node.favorite_count - 1)
        else:
            self._favorites.add(key)
            node.favorite_count += 1
        domain_persistence.write("sop.favorites", f"{user_id}:{node_id}", {"user_id": user_id, "node_id": node_id})
        return self._interaction_state(user_id, node)

    def _interaction_state(self, user_id: str, node: SOPNode) -> SOPInteractionResponse:
        return SOPInteractionResponse(
            node_id=node.id,
            liked=(user_id, node.id) in self._likes,
            favorited=(user_id, node.id) in self._favorites,
            like_count=node.like_count,
            favorite_count=node.favorite_count,
            usage_count=node.usage_count + self._usage_counts().get(node.id, 0),
        )

    def hydrate_likes(self, rows: List[Dict]) -> int:
        for r in rows:
            self._likes.add((r.get("user_id", ""), r.get("node_id", "")))
        return len(rows)

    def hydrate_favorites(self, rows: List[Dict]) -> int:
        for r in rows:
            self._favorites.add((r.get("user_id", ""), r.get("node_id", "")))
        return len(rows)

    # ------------------------------------------------------------------
    # Platform flow templates (平台流程模板)
    #
    # The "流程向导" workspace lists these; the structure mirrors the standard
    # document catalog so both workspaces share one card idiom.
    # ------------------------------------------------------------------
    def list_flow_template_cards(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> SOPFlowTemplateCatalogResponse:
        """List the platform flow catalog with the caller's own interactions."""
        cards: List[SOPFlowTemplateCard] = []

        for flow in self._flow_templates.values():
            if category and category.lower() != "all" and flow.category != category:
                continue
            steps, missing = self._resolve_flow_steps(flow)
            doc_count = sum(
                1 for step in steps if step.kind == SOP_NODE_DOCUMENT
            )
            cards.append(
                SOPFlowTemplateCard(
                    id=flow.id,
                    name=flow.name,
                    summary=flow.summary,
                    description=flow.description,
                    category=flow.category,
                    stages=list(flow.stages),
                    step_count=len(steps),
                    doc_count=doc_count,
                    outcome=flow.outcome,
                    unlocks=list(flow.unlocks),
                    author_name=flow.author_name,
                    author_title=flow.author_title,
                    publisher_org=flow.publisher_org,
                    is_official=flow.is_official,
                    published_at=flow.published_at,
                    like_count=flow.like_count,
                    favorite_count=flow.favorite_count,
                    usage_count=flow.usage_count + self._flow_usage_counts().get(flow.id, 0),
                    liked=bool(user_id) and (user_id, flow.id) in self._flow_likes,
                    favorited=bool(user_id) and (user_id, flow.id) in self._flow_favorites,
                )
            )
            void = missing

        cards.sort(key=lambda c: (c.like_count, c.published_at), reverse=True)
        return SOPFlowTemplateCatalogResponse(items=cards, total=len(cards))

    def _resolve_flow_steps(self, flow: SOPFlowTemplate) -> tuple:
        """Expand a flow template into its ordered document steps."""
        steps: List[SOPFlowTemplateStep] = []
        missing: List[str] = []
        seen: Set[str] = set()

        def walk(node_id: str, note: str, required: bool, depth: int) -> None:
            if node_id in seen:
                return
            seen.add(node_id)
            node = self._nodes.get(node_id)
            if node is None:
                missing.append(node_id)
                return
            if node.kind == SOP_NODE_SUBGRAPH:
                for child_id in node.children:
                    walk(child_id, note, required, depth + 1)
                return
            steps.append(
                SOPFlowTemplateStep(
                    node_id=node.id,
                    name=node.name,
                    kind=node.kind,
                    stage=node.stage,
                    category=node.category,
                    description=node.description,
                    outcome=node.outcome,
                    note=note,
                    required=required,
                    order=0,
                    required_fields=list(node.required_fields),
                )
            )

        for ref in flow.node_refs:
            walk(ref.node_id, ref.note, ref.required, 0)

        for idx, step in enumerate(steps):
            step.order = idx + 1
        return steps, missing

    def get_flow_template_detail(self, flow_id: str) -> SOPFlowTemplateDetail:
        """Resolve a flow template into its ordered document steps."""
        if flow_id not in self._flow_templates:
            raise KeyError(f"SOP flow template with ID {flow_id} not found")
        flow = self._flow_templates[flow_id]
        steps, missing = self._resolve_flow_steps(flow)
        return SOPFlowTemplateDetail(template=flow, steps=steps, missing_nodes=missing)

    def _flow_usage_counts(self) -> Dict[str, int]:
        """Count user flows forked from each platform flow template."""
        counts: Dict[str, int] = {}
        for user_flow in self._flows.values():
            template_id = getattr(user_flow, "template_id", None)
            if template_id:
                counts[template_id] = counts.get(template_id, 0) + 1
        return counts

    def toggle_flow_like(self, user_id: str, flow_id: str) -> SOPFlowTemplateInteractionResponse:
        """Toggle the caller's like on a platform flow template."""
        flow = self.get_flow_template(flow_id)
        key = (user_id, flow_id)
        if key in self._flow_likes:
            self._flow_likes.discard(key)
            flow.like_count = max(0, flow.like_count - 1)
        else:
            self._flow_likes.add(key)
            flow.like_count += 1
        domain_persistence.write(
            "sop.flow_likes", f"{user_id}:{flow_id}",
            {"user_id": user_id, "node_id": flow_id},
        )
        return self._flow_interaction_state(user_id, flow)

    def toggle_flow_favorite(self, user_id: str, flow_id: str) -> SOPFlowTemplateInteractionResponse:
        """Toggle the caller's favourite on a platform flow template."""
        flow = self.get_flow_template(flow_id)
        key = (user_id, flow_id)
        if key in self._flow_favorites:
            self._flow_favorites.discard(key)
            flow.favorite_count = max(0, flow.favorite_count - 1)
        else:
            self._flow_favorites.add(key)
            flow.favorite_count += 1
        domain_persistence.write(
            "sop.flow_favorites", f"{user_id}:{flow_id}",
            {"user_id": user_id, "node_id": flow_id},
        )
        return self._flow_interaction_state(user_id, flow)

    def _flow_interaction_state(
        self, user_id: str, flow: SOPFlowTemplate
    ) -> SOPFlowTemplateInteractionResponse:
        return SOPFlowTemplateInteractionResponse(
            node_id=flow.id,
            liked=(user_id, flow.id) in self._flow_likes,
            favorited=(user_id, flow.id) in self._flow_favorites,
            like_count=flow.like_count,
            favorite_count=flow.favorite_count,
            usage_count=flow.usage_count + self._flow_usage_counts().get(flow.id, 0),
        )

    def get_flow_template(self, flow_id: str) -> SOPFlowTemplate:
        """Fetch a platform flow template by ID."""
        if flow_id not in self._flow_templates:
            raise KeyError(f"SOP flow template with ID {flow_id} not found")
        return self._flow_templates[flow_id]

    def hydrate_flow_templates(self, rows: List[Dict]) -> int:
        for r in rows:
            self._flow_templates[r["id"]] = SOPFlowTemplate(**r)
        return len(rows)

    def hydrate_flow_likes(self, rows: List[Dict]) -> int:
        for r in rows:
            self._flow_likes.add((r.get("user_id", ""), r.get("node_id", "")))
        return len(rows)

    def hydrate_flow_favorites(self, rows: List[Dict]) -> int:
        for r in rows:
            self._flow_favorites.add((r.get("user_id", ""), r.get("node_id", "")))
        return len(rows)

    def expand_subgraph(self, node_id: str, _seen: Optional[Set[str]] = None) -> List[SOPNode]:
        """Flatten a node into the document nodes it contains.

        A subgraph contributes its own children; a document node contributes itself.
        Nested subgraphs are expanded recursively, so a subgraph may itself be
        composed of other subgraphs.
        """
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

    def _incoming_prerequisites(self, node_id: str) -> List[str]:
        """Return prerequisite node ids for a node (excluding optional relations)."""
        return [
            e.from_node
            for e in self._edges
            if e.to_node == node_id and e.relation != "optional"
        ]

    def resolve_goal_plan(self, goal_id: str) -> SOPGoalPlan:
        """Reverse-resolve a business goal into an ordered list of required documents.

        Required and recommended node ids may point at either a single document or a
        composite subgraph; subgraphs are expanded into their constituent documents.
        The resulting set is ordered by the dependency edges so the maker sees the
        documents in an executable sequence.
        """
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
        """Restrict the global dependency edges to the nodes present in a plan."""
        node_ids = {item.node_id for item in items}
        return [
            edge for edge in self._edges
            if edge.from_node in node_ids and edge.to_node in node_ids
        ]

    def _build_plan_items(
        self,
        refs: List[tuple],
    ) -> tuple:
        """Expand node references into ordered plan items.

        ``refs`` is a list of ``(node_id, required)`` pairs. A reference to a subgraph
        is expanded into its constituent documents, which inherit the subgraph's
        required flag and record it as their parent. The expanded set is then ordered
        by the dependency edges.
        """
        plan: List[SOPGoalPlanItem] = []
        seen: Set[str] = set()
        missing: List[str] = []

        def collect(node_id: str, required: bool, parent_id: Optional[str], depth: int) -> None:
            if node_id in seen:
                return
            seen.add(node_id)
            node = self._nodes.get(node_id)
            if node is None:
                missing.append(node_id)
                return
            if node.kind == SOP_NODE_SUBGRAPH:
                for child_id in node.children:
                    collect(child_id, required, node_id, depth + 1)
                return
            plan.append(
                SOPGoalPlanItem(
                    node_id=node.id,
                    name=node.name,
                    kind=node.kind,
                    stage=node.stage,
                    category=node.category,
                    description=node.description,
                    outcome=node.outcome,
                    next_hint=node.next_hint,
                    required=required,
                    order=0,
                    depth=depth,
                    parent_id=parent_id,
                    required_fields=list(node.required_fields),
                )
            )

        for node_id, required in refs:
            collect(node_id, required, None, 0)

        ordered = self._topological_order([item.node_id for item in plan])
        rank = {node_id: idx for idx, node_id in enumerate(ordered)}
        for item in plan:
            item.order = rank.get(item.node_id, 0) + 1
        plan.sort(key=lambda i: (i.order, i.node_id))

        return plan, missing

    # ------------------------------------------------------------------
    # User-authored flows
    # ------------------------------------------------------------------
    def create_flow(self, req: SOPFlowCreate) -> SOPFlow:
        """Create a user-owned flow from an ordered list of node references."""
        fid = f"flow_{uuid.uuid4().hex[:10]}"
        now = utc_now_iso()
        flow = SOPFlow(
            id=fid,
            name=req.name.strip(),
            description=req.description.strip(),
            owner_id=req.owner_id or "",
            goal_id=req.goal_id,
            node_refs=list(req.node_refs),
            edges=list(req.edges),
            status=req.status or SOP_FLOW_STATUS_ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._flows[fid] = flow
        domain_persistence.write("sop.flows", fid, flow)
        return flow

    def list_flows(self, owner_id: Optional[str] = None) -> List[SOPFlow]:
        """List stored flows, optionally filtered by owner."""
        flows = list(self._flows.values())
        if owner_id:
            flows = [f for f in flows if f.owner_id == owner_id]
        flows.sort(key=lambda f: f.updated_at, reverse=True)
        return flows

    def list_my_flow_cards(self, owner_id: Optional[str] = None) -> List[SOPMyFlowCard]:
        """List the maker's own flows as cards for the private my-flows grid.

        Mirrors ``list_flow_template_cards`` so both workspaces share one card
        idiom; a private flow expands its node references into document counts.
        """
        cards: List[SOPMyFlowCard] = []
        for flow in self._flows.values():
            if owner_id and flow.owner_id != owner_id:
                continue
            steps, _missing = self._build_plan_items(
                [(ref.node_id, ref.required) for ref in flow.node_refs]
            )
            stages = sorted({step.stage for step in steps})
            cards.append(
                SOPMyFlowCard(
                    id=flow.id,
                    name=flow.name,
                    summary=(flow.description or "").split("。")[0] if flow.description else "",
                    description=flow.description or "",
                    goal_id=flow.goal_id,
                    category="MY",
                    stages=stages,
                    step_count=len(steps),
                    doc_count=len(steps),
                    status=flow.status,
                    author_name="我",
                    publisher_org="私有流程",
                    is_official=False,
                    published_at=flow.created_at,
                )
            )
        cards.sort(key=lambda c: c.published_at, reverse=True)
        return cards

    def get_flow(self, flow_id: str) -> SOPFlow:
        """Fetch a stored flow by ID."""
        if flow_id not in self._flows:
            raise KeyError(f"SOP flow with ID {flow_id} not found")
        return self._flows[flow_id]

    def update_flow(self, flow_id: str, req: SOPFlowCreate) -> SOPFlow:
        """Replace the content of an existing flow."""
        flow = self.get_flow(flow_id)
        flow.name = req.name.strip()
        flow.description = req.description.strip()
        flow.goal_id = req.goal_id
        flow.node_refs = list(req.node_refs)
        flow.edges = list(req.edges)
        flow.status = req.status or flow.status
        # Editing a published / rejected flow produces a fresh draft so the maker
        # can revise it and submit for review again.
        if flow.status in (SOP_FLOW_STATUS_PUBLISHED, SOP_FLOW_STATUS_REJECTED, SOP_FLOW_STATUS_PENDING_REVIEW):
            flow.status = SOP_FLOW_STATUS_ACTIVE
        flow.updated_at = utc_now_iso()
        domain_persistence.write("sop.flows", flow_id, flow)
        return flow

    def delete_flow(self, flow_id: str) -> bool:
        """Delete a stored flow."""
        if flow_id in self._flows:
            del self._flows[flow_id]
            domain_persistence.delete("sop.flows", flow_id)
            return True
        return False

    def resolve_flow(self, flow_id: str) -> SOPFlowResponse:
        """Resolve a stored flow into its ordered document list.

        The flow's own ordering wins; the global dependency edges are used to derive
        the execution order among the referenced documents.
        """
        flow = self.get_flow(flow_id)
        refs = [(ref.node_id, ref.required) for ref in flow.node_refs]
        plan, missing = self._build_plan_items(refs)

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
        return SOPFlowResponse(
            flow=flow,
            items=items,
            edges=self._edges_for(items),
            missing_nodes=missing,
        )

    def hydrate_flows(self, rows: List[Dict]) -> int:
        for r in rows:
            self._flows[r["id"]] = SOPFlow(**r)
        return len(rows)

    def _topological_order(self, node_ids: List[str]) -> List[str]:
        """Order node ids so that prerequisites come before their dependents."""
        node_set = set(node_ids)
        # Only consider edges whose both endpoints participate in this plan.
        relevant = [
            e for e in self._edges
            if e.from_node in node_set and e.to_node in node_set and e.relation != "optional"
        ]

        # Stage ordering is a stable tie-breaker so the plan reads top-down.
        def stage_of(node_id: str) -> int:
            node = self._nodes.get(node_id)
            return node.stage if node else 99

        indegree: Dict[str, int] = {n: 0 for n in node_set}
        adjacency: Dict[str, List[str]] = {n: [] for n in node_set}
        for edge in relevant:
            adjacency[edge.from_node].append(edge.to_node)
            indegree[edge.to_node] = indegree.get(edge.to_node, 0) + 1

        ready = sorted(
            [n for n in node_set if indegree.get(n, 0) == 0],
            key=lambda n: (stage_of(n), n),
        )
        ordered: List[str] = []
        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for nxt in adjacency.get(current, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)
            ready.sort(key=lambda n: (stage_of(n), n))

        # Cycles or dangling edges: append the rest deterministically.
        if len(ordered) < len(node_set):
            remaining = [n for n in node_set if n not in ordered]
            remaining.sort(key=lambda n: (stage_of(n), n))
            ordered.extend(remaining)
        return ordered

    def get_node_context(self, node_id: str) -> Dict[str, Any]:
        """Collect everything the workspace needs to explain one node to a maker.

        For a subgraph this includes the child documents; for any node it includes
        the plain-language outcome, the next step hint and the prerequisite rationale.
        """
        node = self.get_node(node_id)
        children = [self._nodes[c] for c in node.children if c in self._nodes]
        prerequisites = []
        for edge in self._edges:
            if edge.to_node == node_id and edge.relation != "optional":
                dep = self._nodes.get(edge.from_node)
                if dep is not None:
                    prerequisites.append({
                        "node_id": dep.id,
                        "name": dep.name,
                        "kind": dep.kind,
                        "rationale": edge.rationale,
                    })
        return {
            "node": node,
            "children": children,
            "prerequisites": prerequisites,
        }

    # ------------------------------------------------------------------
    # Document rendering & persistence
    # ------------------------------------------------------------------
    def validate_render_payload(self, inputs: dict) -> dict:
        template_id = inputs.get("template_id", "").strip()
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
        """Render document template with maker input data and persist instance to backend."""
        template = self.get_template(payload.template_id)

        # Merge defaults and inputs
        merged_data: Dict[str, Any] = {}
        for field in template.required_fields:
            val = payload.form_data.get(field.key, field.default or "")
            merged_data[field.key] = val

        # Extra dynamic fields
        merged_data["verify_serial"] = "VER-" + uuid.uuid4().hex[:12].upper()

        # Render template content safely
        try:
            rendered = template.template_content.format(**merged_data)
        except Exception:
            # Fallback simple replacement if formatting tags fail
            rendered = template.template_content
            for k, v in merged_data.items():
                rendered = rendered.replace(f"{{{k}}}", str(v))

        doc_id = str(uuid.uuid4())
        now = utc_now_iso()
        company = merged_data.get("company_name", "创客主体")
        doc_title = f"{template.name} - {company}"

        document = SOPDocumentResponse(
            id=doc_id,
            template_id=template.id,
            user_id=payload.user_id,
            document_title=doc_title,
            form_data=merged_data,
            rendered_content=rendered,
            compliance_passed=True,
            status="READY",
            created_at=now,
            updated_at=now,
        )

        self._documents[doc_id] = document
        domain_persistence.write("sop.documents", doc_id, document)
        return document

    def get_document(self, doc_id: str) -> SOPDocumentResponse:
        """Retrieve persisted document by ID."""
        if doc_id not in self._documents:
            raise KeyError(f"SOP document with ID {doc_id} not found")
        return self._documents[doc_id]

    def list_documents(self, user_id: Optional[str] = None) -> List[SOPDocumentResponse]:
        """List persisted documents, optionally filtered by maker user_id."""
        docs = list(self._documents.values())
        if user_id:
            docs = [d for d in docs if d.user_id == user_id]
        docs.sort(key=lambda d: d.created_at, reverse=True)
        return docs

    def delete_document(self, doc_id: str) -> bool:
        """Physically delete persisted document by ID for Saga rollback."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            domain_persistence.delete("sop.documents", doc_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Publish review queue (发布审核队列)
    #
    # A maker publishes a private document / flow by submitting it for
    # review. The submission enters PENDING_REVIEW and is consumed by
    # ``process_review_queue``, which audits legality / compliance / sensitive
    # words and promotes approved items into the platform catalogs.
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

    def _enqueue_review(
        self,
        target_type: str,
        target_id: str,
        title: str,
        content: str,
        author_id: str,
    ) -> SOPReviewItem:
        """Append one submission to the review queue in PENDING_REVIEW state."""
        item = SOPReviewItem(
            id=f"rev_{uuid.uuid4().hex[:10]}",
            target_type=target_type,
            target_id=target_id,
            title=title,
            content=content,
            author_id=author_id or "",
            author_name=self._resolve_author_name(author_id),
            status=SOP_REVIEW_STATUS_PENDING,
            submitted_at=utc_now_iso(),
        )
        self._review_queue[item.id] = item
        domain_persistence.write("sop.review_queue", item.id, item)
        return item

    def submit_document_for_review(self, doc_id: str, user_id: str) -> SOPPublishResponse:
        """Submit one of the maker's own documents for publish review.

        The document moves to PENDING_REVIEW (待审核) and a review item is
        enqueued for the backend consumer to audit.
        """
        doc = self.get_document(doc_id)
        if doc.user_id and user_id and doc.user_id != user_id:
            raise ValueError("只能发布本人创建的文书")
        if doc.status in (SOP_DOC_STATUS_PENDING_REVIEW, SOP_DOC_STATUS_PUBLISHED):
            raise ValueError("该文书已在审核队列中或已发布，无需重复提交")
        if not doc.rendered_content or not doc.rendered_content.strip():
            raise ValueError("文书正文为空，无法提交审核")

        doc.status = SOP_DOC_STATUS_PENDING_REVIEW
        doc.updated_at = utc_now_iso()
        item = self._enqueue_review(
            target_type=SOP_REVIEW_TARGET_DOCUMENT,
            target_id=doc.id,
            title=doc.document_title,
            content=f"{doc.document_title}\n{self._flatten_text(doc.rendered_content)}",
            author_id=user_id or doc.user_id,
        )
        domain_persistence.write("sop.documents", doc.id, doc)
        return SOPPublishResponse(
            item_id=item.id,
            target_id=doc.id,
            target_type=SOP_REVIEW_TARGET_DOCUMENT,
            status=SOP_DOC_STATUS_PENDING_REVIEW,
            submitted_at=item.submitted_at,
            message="发布成功，文书已进入待审核状态，审核通过后将发布至标准文书库",
        )

    def submit_flow_for_review(self, flow_id: str, user_id: str) -> SOPPublishResponse:
        """Submit one of the maker's own flows for publish review.

        The flow moves to PENDING_REVIEW (待审核) and a review item is
        enqueued for the backend consumer to audit.
        """
        flow = self.get_flow(flow_id)
        if flow.owner_id and user_id and flow.owner_id != user_id:
            raise ValueError("只能发布本人创建的流程")
        if flow.status in (SOP_FLOW_STATUS_PENDING_REVIEW, SOP_FLOW_STATUS_PUBLISHED):
            raise ValueError("该流程已在审核队列中或已发布，无需重复提交")

        steps, missing = self._build_plan_items(
            [(ref.node_id, ref.required) for ref in flow.node_refs]
        )
        step_names = "、".join(step.name for step in steps)
        content = f"{flow.name}\n{flow.description or ''}\n流程步骤：{step_names}"
        if missing:
            content = f"{content}\n失效节点：{'、'.join(missing)}"

        flow.status = SOP_FLOW_STATUS_PENDING_REVIEW
        flow.updated_at = utc_now_iso()
        item = self._enqueue_review(
            target_type=SOP_REVIEW_TARGET_FLOW,
            target_id=flow.id,
            title=flow.name,
            content=content,
            author_id=user_id or flow.owner_id,
        )
        domain_persistence.write("sop.flows", flow.id, flow)
        return SOPPublishResponse(
            item_id=item.id,
            target_id=flow.id,
            target_type=SOP_REVIEW_TARGET_FLOW,
            status=SOP_FLOW_STATUS_PENDING_REVIEW,
            submitted_at=item.submitted_at,
            message="发布成功，流程已进入待审核状态，审核通过后将发布至流程向导",
        )

    def list_review_queue(self, status: Optional[str] = None) -> SOPReviewQueueResponse:
        """List the publish review queue, optionally filtered by status."""
        items = list(self._review_queue.values())
        if status:
            items = [i for i in items if i.status.upper() == status.upper()]
        items.sort(key=lambda i: i.submitted_at, reverse=True)
        statuses = [i.status for i in self._review_queue.values()]
        return SOPReviewQueueResponse(
            items=items,
            total=len(items),
            pending=statuses.count(SOP_REVIEW_STATUS_PENDING),
            approved=statuses.count(SOP_REVIEW_STATUS_APPROVED),
            rejected=statuses.count(SOP_REVIEW_STATUS_REJECTED),
        )

    async def process_review_queue(self, limit: Optional[int] = None) -> SOPReviewProcessResult:
        """Consume the pending review queue.

        For every queued item the consumer audits legality / compliance and
        sensitive words (via the content-moderation gateway). Approved items are
        published into the standard document catalog / flow guide; failed items
        are marked REJECTED with the reason recorded.
        """
        pending = [i for i in self._review_queue.values() if i.status == SOP_REVIEW_STATUS_PENDING]
        pending.sort(key=lambda i: i.submitted_at)
        if limit is not None and limit > 0:
            pending = pending[: int(limit)]

        result = SOPReviewProcessResult(
            processed=len(pending),
            approved=0,
            rejected=0,
            published_documents=[],
            published_flows=[],
            details=[],
        )

        for item in pending:
            try:
                await self._audit_review_item(item)
                self._approve_review_item(item)
                result.approved += 1
                if item.target_type == SOP_REVIEW_TARGET_DOCUMENT:
                    result.published_documents.append(item.target_id)
                else:
                    result.published_flows.append(item.target_id)
                result.details.append({
                    "item_id": item.id,
                    "title": item.title,
                    "status": SOP_REVIEW_STATUS_APPROVED,
                    "note": item.review_note,
                })
            except Exception as e:
                logger.warning("Review item %s rejected: %s", item.id, e)
                self._reject_review_item(item, str(e))
                result.rejected += 1
                result.details.append({
                    "item_id": item.id,
                    "title": item.title,
                    "status": SOP_REVIEW_STATUS_REJECTED,
                    "note": item.review_note,
                })
        return result

    async def _audit_review_item(self, item: SOPReviewItem) -> None:
        """Audit one queued submission: sensitive words + legality/compliance."""
        from src.infrastructure.external_gateway.content_moderation_gateway import check_content_safety

        # 1. Sensitive-word / content-safety gate (敏感词与内容安全).
        await check_content_safety(item.content, field_name=f"{item.target_type} 发布审核")

        # 2. Legality & compliance completeness checks (合法性与合规性).
        if item.target_type == SOP_REVIEW_TARGET_DOCUMENT:
            doc = self.get_document(item.target_id)
            if not doc.compliance_passed:
                raise ValueError("文书合规校验未通过，无法发布")
            body = self._flatten_text(doc.rendered_content)
            if len(body) < 10:
                raise ValueError("文书正文内容过短，缺少可发布的合规条款")
        elif item.target_type == SOP_REVIEW_TARGET_FLOW:
            flow = self.get_flow(item.target_id)
            steps, missing = self._build_plan_items(
                [(ref.node_id, ref.required) for ref in flow.node_refs]
            )
            if missing:
                raise ValueError(f"流程包含失效节点：{'、'.join(missing)}")
            if not steps:
                raise ValueError("流程未包含任何文书步骤，无法发布")
        return None

    def _approve_review_item(self, item: SOPReviewItem) -> None:
        """Promote an audited submission into the platform catalogs."""
        now = utc_now_iso()
        if item.target_type == SOP_REVIEW_TARGET_DOCUMENT:
            doc = self.get_document(item.target_id)
            node_id = self.publish_document_to_catalog(doc)
            doc.status = SOP_DOC_STATUS_PUBLISHED
            doc.updated_at = now
            domain_persistence.write("sop.documents", doc.id, doc)
            item.review_note = f"审核通过：内容合法合规，已发布至标准文书库（{node_id}）"
        else:
            flow = self.get_flow(item.target_id)
            template_id = self.publish_flow_to_catalog(flow)
            flow.status = SOP_FLOW_STATUS_PUBLISHED
            flow.updated_at = now
            domain_persistence.write("sop.flows", flow.id, flow)
            item.review_note = f"审核通过：内容合法合规，已发布至流程向导（{template_id}）"
        item.status = SOP_REVIEW_STATUS_APPROVED
        item.reviewed_at = now
        item.moderator_id = "review_engine"
        domain_persistence.write("sop.review_queue", item.id, item)

    def _reject_review_item(self, item: SOPReviewItem, reason: str) -> None:
        """Mark an audited submission as rejected and roll the source back."""
        now = utc_now_iso()
        if item.target_type == SOP_REVIEW_TARGET_DOCUMENT:
            doc = self.get_document(item.target_id)
            doc.status = SOP_DOC_STATUS_REJECTED
            doc.updated_at = now
            domain_persistence.write("sop.documents", doc.id, doc)
        else:
            flow = self.get_flow(item.target_id)
            flow.status = SOP_FLOW_STATUS_REJECTED
            flow.updated_at = now
            domain_persistence.write("sop.flows", flow.id, flow)
        item.status = SOP_REVIEW_STATUS_REJECTED
        item.reviewed_at = now
        item.review_note = f"审核未通过：{reason}"
        item.moderator_id = "review_engine"
        domain_persistence.write("sop.review_queue", item.id, item)

    def publish_document_to_catalog(self, doc: SOPDocumentResponse) -> str:
        """Promote a maker's document into the standard document catalog (标准文书库).

        The rendered document becomes a fillable document node in the graph, so it
        shows up in the workbench alongside the curated standard documents.
        """
        template = self.get_template(doc.template_id)
        node_id = f"tpl_pub_{uuid.uuid4().hex[:8]}"
        body = self._flatten_text(doc.rendered_content)
        node = SOPNode(
            id=node_id,
            kind=SOP_NODE_DOCUMENT,
            code=f"PUB_{uuid.uuid4().hex[:6].upper()}",
            name=doc.document_title,
            stage=template.stage,
            category=template.category,
            description=body[:120],
            outcome="由创客发布的标准文书，可直接查看与复用",
            next_hint="查看文书正文，按需用于商事与合规申报。",
            summary=body[:90] or "创客发布的合规文书",
            author_name=self._resolve_author_name(doc.user_id),
            author_title="创客发布",
            publisher_org="创客发布",
            is_official=False,
            published_at=utc_now_iso(),
            template_content=doc.rendered_content,
            required_fields=[],
            is_active=True,
        )
        self._nodes[node_id] = node
        self._register_template_from_node(node)
        domain_persistence.write("sop.nodes", node_id, node)
        domain_persistence.write("sop.templates", node_id, self._templates[node_id])
        return node_id

    def publish_flow_to_catalog(self, flow: SOPFlow) -> str:
        """Promote a maker's flow into the platform flow guide (流程向导)."""
        steps, _missing = self._build_plan_items(
            [(ref.node_id, ref.required) for ref in flow.node_refs]
        )
        stages = sorted({step.stage for step in steps})
        summary = (flow.description or "").split("。")[0] if flow.description else flow.name
        template_id = f"flowpub_{uuid.uuid4().hex[:8]}"
        template = SOPFlowTemplate(
            id=template_id,
            code=f"USER_PUB_{uuid.uuid4().hex[:6].upper()}",
            name=flow.name,
            summary=summary or "创客发布的办事流程",
            description=flow.description or summary,
            category=self._derive_flow_category(steps),
            stages=stages,
            node_refs=[
                SOPFlowTemplateRef(node_id=ref.node_id, required=ref.required, note=ref.note)
                for ref in flow.node_refs
            ],
            outcome=f"由创客编排的办事流程，共 {len(steps)} 个步骤",
            author_name=self._resolve_author_name(flow.owner_id),
            author_title="创客发布",
            publisher_org="创客发布",
            is_official=False,
            published_at=utc_now_iso(),
        )
        self._flow_templates[template_id] = template
        domain_persistence.write("sop.flow_templates", template_id, template)
        return template_id

    @staticmethod
    def _derive_flow_category(steps: List[Any]) -> str:
        """Map the majority document category to a flow-guide category."""
        counts: Dict[str, int] = {}
        for step in steps:
            cat = {
                "ENTITY": "ENTITY",
                "IP": "IP",
                "CROSS_BORDER": "CROSS_BORDER",
            }.get(step.category, "COMPLIANCE")
            counts[cat] = counts.get(cat, 0) + 1
        if not counts:
            return "COMPLIANCE"
        return max(counts, key=counts.get)

    def hydrate_review_queue(self, rows: List[Dict]) -> int:
        for r in rows:
            self._review_queue[r["id"]] = SOPReviewItem(**r)
        return len(rows)

    # ------------------------------------------------------------------
    # Background review-queue consumer
    #
    # Mirrors the hot-reload watcher: a lightweight asyncio loop that keeps
    # draining PENDING_REVIEW submissions so approved documents / flows are
    # automatically promoted into the platform catalogs.
    # ------------------------------------------------------------------
    async def _review_consumer_loop(self) -> None:
        logger.info("[SOP Review] Publish review consumer loop started")
        while self._review_consumer_running:
            try:
                await self.process_review_queue()
            except Exception as e:
                logger.warning("[SOP Review] Consumer cycle exception: %s", e)
            try:
                await asyncio.sleep(self.review_consumer_interval)
            except asyncio.CancelledError:
                break

    def start_review_consumer(self, interval: float = 5.0) -> None:
        """Start the non-blocking background consumer of the publish review queue."""
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
        """Stop the background review-queue consumer."""
        self._review_consumer_running = False
        if self._review_consumer_task and not self._review_consumer_task.done():
            self._review_consumer_task.cancel()
            self._review_consumer_task = None

    def review_consumer_status(self) -> Dict[str, Any]:
        """Introspection payload for the background consumer."""
        return {
            "running": self._review_consumer_running,
            "interval_seconds": getattr(self, "review_consumer_interval", 5.0),
            "queue_size": len(self._review_queue),
            "pending": sum(1 for i in self._review_queue.values() if i.status == SOP_REVIEW_STATUS_PENDING),
        }

    def hydrate_templates(self, rows: List[Dict]) -> int:
        for r in rows:
            self._templates[r["id"]] = SOPTemplate(**r)
        return len(rows)

    def hydrate_documents(self, rows: List[Dict]) -> int:
        for r in rows:
            self._documents[r["id"]] = SOPDocumentResponse(**r)
        return len(rows)

    def hydrate_nodes(self, rows: List[Dict]) -> int:
        for r in rows:
            node = SOPNode(**r)
            self._nodes[node.id] = node
            if node.kind == SOP_NODE_DOCUMENT:
                self._register_template_from_node(node)
        return len(rows)

    def hydrate_edges(self, rows: List[Dict]) -> int:
        for r in rows:
            edge = SOPEdge(**r)
            self._edges.append(edge)
        return len(rows)

    def hydrate_goals(self, rows: List[Dict]) -> int:
        for r in rows:
            goal = SOPGoal(**r)
            self._goals[goal.id] = goal
        return len(rows)

    def persist_graph_seeds(self) -> int:
        """Write the workflow graph into PostgreSQL.

        The seed file is the authoring source, but the runtime catalog must live
        in the database so the workbench reads real persisted records. This runs
        after the persistence layer is enabled, because writes are no-ops before
        the database probe succeeds.
        """
        written = 0
        for node in self._nodes.values():
            domain_persistence.write("sop.nodes", node.id, node)
            written += 1
        for idx, edge in enumerate(self._edges):
            key = f"{edge.from_node}->{edge.to_node}"
            domain_persistence.write("sop.edges", key, edge)
            written += 1
        for goal in self._goals.values():
            domain_persistence.write("sop.goals", goal.id, goal)
            written += 1
        for flow in self._flow_templates.values():
            domain_persistence.write("sop.flow_templates", flow.id, flow)
            written += 1
        return written


sop_service = SOPService()

domain_persistence.register("sop.templates", sop_service.hydrate_templates)
domain_persistence.register("sop.documents", sop_service.hydrate_documents)
domain_persistence.register("sop.flows", sop_service.hydrate_flows)
domain_persistence.register("sop.likes", sop_service.hydrate_likes)
domain_persistence.register("sop.favorites", sop_service.hydrate_favorites)
domain_persistence.register("sop.nodes", sop_service.hydrate_nodes)
domain_persistence.register("sop.edges", sop_service.hydrate_edges)
domain_persistence.register("sop.goals", sop_service.hydrate_goals)
domain_persistence.register("sop.flow_templates", sop_service.hydrate_flow_templates)
domain_persistence.register("sop.flow_likes", sop_service.hydrate_flow_likes)
domain_persistence.register("sop.flow_favorites", sop_service.hydrate_flow_favorites)
domain_persistence.register("sop.review_queue", sop_service.hydrate_review_queue)
