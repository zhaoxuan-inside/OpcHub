"""Data models for SOP stages, document templates, workflow graph, and generated materials."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SOPField(BaseModel):
    """A single fillable element inside a document node.

    ``help`` / ``example`` / ``pitfalls`` carry the plain-language guidance that lets a
    first-time maker fill the field correctly without reading regulatory prose.
    """
    key: str
    label: str
    type: str = "string"  # "string", "select", "number", "text", "date", "currency"
    required: bool = True
    options: Optional[List[str]] = None
    default: Optional[str] = None
    help: Optional[str] = None
    example: Optional[str] = None
    pitfalls: List[str] = Field(default_factory=list)
    source: Optional[str] = None


class SOPStage(BaseModel):
    stage: int
    name: str
    code: str
    description: str


class SOPTemplateCreate(BaseModel):
    stage: int = Field(..., ge=1, le=4)
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=255)
    category: str = Field(default="TAX", description="TAX, LEGAL, IP, FINANCE")
    description: str = Field(..., min_length=5)
    template_content: str = Field(..., min_length=5)
    required_fields: List[SOPField] = Field(default_factory=list)


class SOPTemplate(BaseModel):
    id: str
    stage: int
    code: str
    name: str
    category: str
    description: str
    template_content: str
    required_fields: List[SOPField] = Field(default_factory=list)
    is_active: bool = True


class SOPTemplatesResponse(BaseModel):
    stages: List[SOPStage]
    templates: List[SOPTemplate]


# ---------------------------------------------------------------------------
# Workflow graph (nodes / edges / goals)
#
# The graph is the single source of truth behind the three workspace views:
#   * node workbench  -> SOPNode.required_fields
#   * flow guide      -> SOPNode.outcome / unlocks / next_hint + SOPEdge.rationale
#   * goal reverse    -> SOPGoal.required_nodes (reverse index)
#
# A node is EITHER a single document ("kind": "document") OR a composite subgraph
# ("kind": "subgraph") that groups several child nodes to accomplish one business
# outcome. Subgraphs nest: a subgraph's children may themselves be subgraphs.
# ---------------------------------------------------------------------------

SOP_NODE_DOCUMENT = "document"
SOP_NODE_SUBGRAPH = "subgraph"

SOP_EDGE_PREREQUISITE = "prerequisite"   # A must be finished before B
SOP_EDGE_RECOMMENDED = "recommended"     # A is strongly advised before B
SOP_EDGE_OPTIONAL = "optional"           # A is a nice-to-have relative to B


class SOPNode(BaseModel):
    """One addressable unit of work: a single document, or a composite subgraph."""
    id: str
    kind: str = SOP_NODE_DOCUMENT
    code: str
    name: str
    stage: int = Field(..., ge=1, le=4)
    category: str = Field(default="TAX", description="TAX, LEGAL, IP, FINANCE, ENTITY, BANK, CROSS_BORDER")
    description: str = ""

    # --- plain-language guidance (flow guide view) ---
    outcome: str = ""            # after finishing this node, what do you have?
    next_hint: str = ""          # what should the maker do next?
    unlocks: List[str] = Field(default_factory=list)  # capability unlocked (free text)

    # --- document node payload ---
    template_content: str = ""
    required_fields: List[SOPField] = Field(default_factory=list)

    # --- document card provenance (标准文书卡片信息) ---
    summary: str = ""              # 文书摘要：卡片上的一句话概述
    author_name: str = ""          # 发布文书的作者
    author_title: str = ""         # 作者职务/身份说明
    publisher_org: str = ""        # 文书来源机构（发布机构）
    is_official: bool = False      # 官方认证标记
    published_at: str = ""         # 发布日期（发布机构发布文书的日期）
    like_count: int = 0            # 喜欢数（历史字段，对应统一互动 LOVE）
    favorite_count: int = 0        # 收藏数
    praise_count: int = 0          # 点赞数（统一互动 LIKE）
    comment_count: int = 0         # 评论数
    usage_count: int = 0           # 真实使用数（有人用该文书生成过实例）

    # --- subgraph payload ---
    children: List[str] = Field(default_factory=list)  # child node ids (documents or nested subgraphs)

    is_active: bool = True


class SOPEdge(BaseModel):
    """A directed dependency between two nodes."""
    from_node: str
    to_node: str
    relation: str = SOP_EDGE_PREREQUISITE
    rationale: str = ""  # why this ordering matters, in plain language


class SOPGoal(BaseModel):
    """A business outcome a maker wants to reach; reverse-resolved into required nodes."""
    id: str
    title: str
    description: str = ""
    audience_hint: str = ""                    # who this goal is for
    outcome: str = ""                         # what the maker gets once reached
    required_nodes: List[str] = Field(default_factory=list)
    recommended_nodes: List[str] = Field(default_factory=list)


class SOPGraphResponse(BaseModel):
    """The full workflow graph consumed by the SOP workspace."""
    stages: List[SOPStage] = Field(default_factory=list)
    nodes: List[SOPNode] = Field(default_factory=list)
    edges: List[SOPEdge] = Field(default_factory=list)
    goals: List[SOPGoal] = Field(default_factory=list)


class SOPGoalPlanItem(BaseModel):
    """One resolved step inside a goal plan."""
    node_id: str
    name: str
    kind: str
    stage: int
    category: str
    description: str = ""
    outcome: str = ""
    next_hint: str = ""
    required: bool = True
    order: int = 0
    depth: int = 0
    parent_id: Optional[str] = None
    required_fields: List[SOPField] = Field(default_factory=list)


class SOPGoalPlan(BaseModel):
    """Reverse-resolved execution plan for a business goal."""
    goal: SOPGoal
    items: List[SOPGoalPlanItem] = Field(default_factory=list)
    # Dependency edges restricted to the nodes taking part in this plan, so the
    # workspace can draw the flow diagram without re-filtering the global graph.
    edges: List[SOPEdge] = Field(default_factory=list)
    missing_nodes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# User-authored flows
#
# A flow is a maker-owned document set: an ordered list of node references plus
# the edges between them. It is the unit a user creates, revisits and executes.
# ``node_refs`` may reference either a document node or a subgraph node; subgraphs
# are expanded into their constituent documents when the flow is resolved.
# ---------------------------------------------------------------------------

SOP_FLOW_STATUS_DRAFT = "DRAFT"
SOP_FLOW_STATUS_ACTIVE = "ACTIVE"
# Publish-to-platform lifecycle states (发布审核流程).
SOP_FLOW_STATUS_PENDING_REVIEW = "PENDING_REVIEW"
SOP_FLOW_STATUS_PUBLISHED = "PUBLISHED"
SOP_FLOW_STATUS_REJECTED = "REJECTED"

# Document lifecycle states (我的文书 → 标准文书库).
SOP_DOC_STATUS_READY = "READY"
SOP_DOC_STATUS_PENDING_REVIEW = "PENDING_REVIEW"
SOP_DOC_STATUS_PUBLISHED = "PUBLISHED"
SOP_DOC_STATUS_REJECTED = "REJECTED"

# ---------------------------------------------------------------------------
# Publish review queue (发布审核队列)
#
# A maker publishes a private document or flow by submitting it for review. The
# submission is added to this queue in PENDING_REVIEW state; a consumer audits
# every queued item (legality / compliance / sensitive words) and, on approval,
# promotes it into the platform catalogs (标准文书库 / 流程向导).
# ---------------------------------------------------------------------------

SOP_REVIEW_TARGET_DOCUMENT = "DOCUMENT"
SOP_REVIEW_TARGET_FLOW = "FLOW"

SOP_REVIEW_STATUS_PENDING = "PENDING_REVIEW"
SOP_REVIEW_STATUS_APPROVED = "APPROVED"
SOP_REVIEW_STATUS_REJECTED = "REJECTED"


class SOPFlowNodeRef(BaseModel):
    """One position inside a user flow."""
    node_id: str
    required: bool = True
    note: str = ""


class SOPFlowEdge(BaseModel):
    """A user-defined ordering constraint between two flow positions."""
    from_ref: str
    to_ref: str
    rationale: str = ""


class SOPFlowCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = ""
    owner_id: str = ""
    goal_id: Optional[str] = None
    # Present only on update requests: identifies the flow to replace.
    flow_id: Optional[str] = None
    node_refs: List[SOPFlowNodeRef] = Field(default_factory=list)
    edges: List[SOPFlowEdge] = Field(default_factory=list)
    status: str = SOP_FLOW_STATUS_ACTIVE


# ---------------------------------------------------------------------------
# Platform flow templates (平台流程模板)
#
# A flow template is the curated, platform-authored counterpart of a user
# flow: an ordered set of node references that completes one business outcome.
# The "流程向导" workspace lists these; a maker may fork one into a personal
# flow (SOPFlow) and continue from there.
# ---------------------------------------------------------------------------

class SOPFlowTemplateRef(BaseModel):
    """One step inside a platform flow template."""
    node_id: str
    required: bool = True
    note: str = ""


class SOPFlowTemplate(BaseModel):
    """A platform-authored flow: an ordered set of documents that achieves one outcome."""
    id: str
    code: str
    name: str
    summary: str = ""
    description: str = ""
    category: str = "ENTITY"
    stages: List[int] = Field(default_factory=list)
    node_refs: List[SOPFlowTemplateRef] = Field(default_factory=list)
    outcome: str = ""
    unlocks: List[str] = Field(default_factory=list)

    # --- provenance (mirrors the standard document card) ---
    author_name: str = ""
    author_title: str = ""
    publisher_org: str = ""
    is_official: bool = False
    published_at: str = ""
    like_count: int = 0            # 喜欢数（历史字段，对应统一互动 LOVE）
    favorite_count: int = 0        # 收藏数
    praise_count: int = 0          # 点赞数（统一互动 LIKE）
    comment_count: int = 0         # 评论数
    usage_count: int = 0


class SOPFlowTemplateCard(BaseModel):
    """A flow template as shown on the flow-guide workbench card."""
    id: str
    name: str
    summary: str = ""
    description: str = ""
    category: str = "ENTITY"
    stages: List[int] = Field(default_factory=list)
    step_count: int = 0
    doc_count: int = 0
    outcome: str = ""
    unlocks: List[str] = Field(default_factory=list)
    author_name: str = ""
    author_title: str = ""
    publisher_org: str = ""
    is_official: bool = False
    published_at: str = ""
    like_count: int = 0
    favorite_count: int = 0
    usage_count: int = 0
    liked: bool = False
    favorited: bool = False


class SOPMyFlowCard(BaseModel):
    """A maker's own flow as shown on the my-flows card grid.

    Shape-compatible with ``SOPFlowTemplateCard`` so the private workspace can
    reuse the flow-guide card idiom; private flows simply carry no official
    provenance and no community counters.
    """
    id: str
    name: str
    summary: str = ""
    description: str = ""
    goal_id: Optional[str] = None
    category: str = "MY"
    stages: List[int] = Field(default_factory=list)
    step_count: int = 0
    doc_count: int = 0
    status: str = ""
    author_name: str = ""
    publisher_org: str = ""
    is_official: bool = False
    published_at: str = ""


class SOPFlowTemplateCatalogResponse(BaseModel):
    """The platform flow catalog plus the caller's own interactions."""
    items: List[SOPFlowTemplateCard] = Field(default_factory=list)
    total: int = 0


class SOPFlowTemplateInteractionResponse(BaseModel):
    """Result of a like / favourite toggle on a platform flow template."""
    node_id: str
    liked: bool = False
    favorited: bool = False
    like_count: int = 0
    favorite_count: int = 0
    usage_count: int = 0


class SOPFlowTemplateStep(BaseModel):
    """A resolved step inside a platform flow template."""
    node_id: str
    name: str
    kind: str
    stage: int
    category: str
    description: str = ""
    outcome: str = ""
    note: str = ""
    required: bool = True
    order: int = 0
    required_fields: List[SOPField] = Field(default_factory=list)


class SOPFlowTemplateDetail(BaseModel):
    """A flow template with its resolved step list."""
    template: SOPFlowTemplate
    steps: List[SOPFlowTemplateStep] = Field(default_factory=list)
    missing_nodes: List[str] = Field(default_factory=list)


class SOPFlow(BaseModel):
    id: str
    name: str
    description: str = ""
    owner_id: str = ""
    goal_id: Optional[str] = None
    node_refs: List[SOPFlowNodeRef] = Field(default_factory=list)
    edges: List[SOPFlowEdge] = Field(default_factory=list)
    status: str = SOP_FLOW_STATUS_ACTIVE
    created_at: str
    updated_at: str


class SOPFlowItem(BaseModel):
    """A resolved document position inside a user flow."""
    node_id: str
    name: str
    kind: str
    stage: int
    category: str
    description: str = ""
    outcome: str = ""
    next_hint: str = ""
    required: bool = True
    order: int = 0
    depth: int = 0
    parent_id: Optional[str] = None
    required_fields: List[SOPField] = Field(default_factory=list)


class SOPFlowResponse(BaseModel):
    """A stored flow together with its resolved document list."""
    flow: SOPFlow
    items: List[SOPFlowItem] = Field(default_factory=list)
    edges: List[SOPEdge] = Field(default_factory=list)
    missing_nodes: List[str] = Field(default_factory=list)


class SOPDocumentCreate(BaseModel):
    template_id: str
    user_id: str
    form_data: Dict[str, Any]


# ---------------------------------------------------------------------------
# Standard document catalog (标准文书库)
#
# The workbench lists documents only — subgraphs are workflow structures, not
# fillable documents, so they never appear in this catalog.
# ---------------------------------------------------------------------------

class SOPDocumentCard(BaseModel):
    """A standard document as shown on the workbench card."""
    id: str
    name: str
    summary: str = ""
    author_name: str = ""
    author_title: str = ""
    publisher_org: str = ""
    is_official: bool = False
    published_at: str = ""
    stage: int = 1
    category: str = "TAX"
    like_count: int = 0
    favorite_count: int = 0
    usage_count: int = 0
    field_count: int = 0
    liked: bool = False
    favorited: bool = False


class SOPDocumentCatalogResponse(BaseModel):
    """The standard document catalog plus the caller's own interactions."""
    items: List[SOPDocumentCard] = Field(default_factory=list)
    total: int = 0


class SOPInteractionResponse(BaseModel):
    """Result of a like / favourite toggle on a standard document."""
    node_id: str
    liked: bool = False
    favorited: bool = False
    like_count: int = 0
    favorite_count: int = 0
    usage_count: int = 0


class SOPDocumentResponse(BaseModel):
    id: str
    template_id: str
    user_id: str
    document_title: str
    form_data: Dict[str, Any]
    rendered_content: str
    compliance_passed: bool = True
    status: str = "READY"
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Publish review queue (发布审核队列) schemas
# ---------------------------------------------------------------------------

class SOPReviewItem(BaseModel):
    """One queued publish submission (a private document or flow awaiting audit)."""
    id: str
    target_type: str  # SOP_REVIEW_TARGET_DOCUMENT / SOP_REVIEW_TARGET_FLOW
    target_id: str
    title: str
    content: str
    author_id: str
    author_name: str = ""
    status: str = SOP_REVIEW_STATUS_PENDING
    submitted_at: str
    reviewed_at: Optional[str] = None
    review_note: Optional[str] = None
    moderator_id: Optional[str] = None


class SOPReviewQueueResponse(BaseModel):
    """The review queue plus its status breakdown."""
    items: List[SOPReviewItem] = Field(default_factory=list)
    total: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0


class SOPReviewProcessResult(BaseModel):
    """Summary of one consumer run over the pending review queue."""
    processed: int = 0
    approved: int = 0
    rejected: int = 0
    published_documents: List[str] = Field(default_factory=list)
    published_flows: List[str] = Field(default_factory=list)
    details: List[Dict[str, Any]] = Field(default_factory=list)


class SOPPublishResponse(BaseModel):
    """Confirmation returned when a private document/flow is submitted for review."""
    item_id: str
    target_id: str
    target_type: str
    status: str
    submitted_at: str
    message: str = ""
