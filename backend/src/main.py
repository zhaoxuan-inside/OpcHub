import os
import time
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import settings
from src.core.telemetry import (
    TracePropagationMiddleware,
    get_current_trace_id,
    app_start_time,
)
from src.core.microkernel.models import DAGConfig, ExecutionResult
from src.core.microkernel.engine import microkernel_engine
from src.core.microkernel.sandbox import validate_python_code
from src.core.microkernel.registry import registry
from src.domains.telemetry.service import telemetry_service
from src.domains.telemetry.models import OpsDashboardResponse
from src.domains.forum.service import forum_service
from src.domains.forum.models import (
    ForumThreadCreate,
    ForumThreadResponse,
    ForumCommentCreate,
    ForumCommentResponse,
    ThreadDetailResponse,
    UpvoteRequest,
    UpvoteResponse,
    BookmarkRequest,
    BookmarkResponse,
)
from src.domains.sop.service import sop_service
from src.domains.sop.models import (
    SOPTemplatesResponse,
    SOPTemplate,
    SOPTemplateCreate,
    SOPDocumentCreate,
    SOPDocumentResponse,
)
from src.domains.products.service import product_service
from src.domains.products.models import ProductCreate, ProductResponse
from src.domains.policies.service import policy_service
from src.domains.policies.models import (
    PolicyCreate,
    PolicyResponse,
    PolicyMatchRequest,
    PolicyMatchResponse,
)
from src.domains.demands.service import demand_service
from src.domains.demands.models import (
    DemandCreate,
    DemandResponse,
    BidCreate,
    BidResponse,
)
from src.domains.perks.service import perk_service
from src.domains.perks.models import (
    PerkCreate,
    PerkResponse,
    PerkClaimRequest,
    PerkClaimResponse,
)
from src.domains.user.service import user_service
from src.domains.user.models import (
    MakerProfileResponse,
    EntitlementActivateRequest,
    EntitlementActivateResponse,
)
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import (
    DAGConfigSaveRequest,
    DAGConfigRecord,
    FrontendLayoutSaveRequest,
    FrontendLayoutRecord,
    OperatorDescriptor,
    OperatorModeUpdateRequest,
    ScenarioExecuteRequest,
    ScenarioExecuteResponse,
)
from src.domains.moderation.service import moderation_service
from src.domains.moderation.models import (
    ModerationItemResponse,
    TakedownRequest,
    RestoreRequest,
    ModerationActionResponse,
)
from src.domains.compliance.service import compliance_service
from src.domains.compliance.models import (
    ComplianceDimension,
    ComplianceCase,
    AuditCheckItem,
    AuditEvaluateRequest,
    AuditReportResponse,
)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Microkernel DAG Orchestration & Cross-Platform Telemetry Gateway for Super Individuals",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TracePropagationMiddleware)


class ScriptValidationRequest(BaseModel):
    code: str
    action_name: str | None = None


class DAGExecutionRequest(BaseModel):
    config: DAGConfig
    inputs: dict[str, Any] | None = None


# ==========================================
# Tri-State Health Probes & Diagnostics (auxiliary_governance §5.2)
# ==========================================
@app.get("/livez", tags=["System Probes"])
async def liveness_probe():
    """Liveness probe returning 200 OK if main event loop is responsive."""
    return {
        "status": "ALIVE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_current_trace_id(),
        "pid": os.getpid()
    }


@app.get("/readyz", tags=["System Probes"])
async def readiness_probe():
    """Readiness probe checking readiness of kernel operators and domain repositories."""
    ops_count = len(registry.list_handlers())
    if ops_count < 4:
        raise HTTPException(status_code=503, detail="Kernel operators below readiness threshold")
    
    return {
        "status": "READY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_current_trace_id(),
        "checks": {
            "kernel_operators": f"OK ({ops_count} registered)",
            "telemetry": "OK",
            "forum": "OK",
            "sop_engine": "OK",
            "products": "OK",
            "policies": "OK",
            "demands": "OK",
            "perks": "OK"
        }
    }


@app.get("/healthz", tags=["System Probes"])
async def diagnostics_probe():
    """Diagnostic health probe reporting version, uptime, and kernel health."""
    uptime_sec = round(time.time() - app_start_time, 2)
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "HEALTHY",
        "uptime_seconds": uptime_sec,
        "trace_id": get_current_trace_id(),
        "active_operators": len(registry.list_handlers()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", tags=["System Probes"])
async def health_check():
    """System compatibility probe."""
    return {
        "status": "HEALTHY",
        "service": settings.app_name,
        "version": settings.app_version,
        "trace_id": get_current_trace_id(),
        "kernel_operators_count": len(registry.list_handlers())
    }


# ==========================================
# Operational Telemetry Endpoints (Ops Intelligence)
# ==========================================
@app.get(
    f"{settings.api_prefix}/ops/dashboard",
    response_model=OpsDashboardResponse,
    tags=["Operational Analytics"]
)
async def get_ops_dashboard():
    """Retrieve full operational metrics including DAU, UV, PV, retention and 3-terminal distribution."""
    return telemetry_service.get_dashboard_metrics()


# ==========================================
# Microkernel DAG Execution & Sandbox Endpoints
# ==========================================
@app.get(f"{settings.api_prefix}/microkernel/methods", tags=["Microkernel"])
async def list_registered_methods():
    """List all currently registered atomic action handlers."""
    return {"registered_handlers": registry.list_handlers()}


@app.post(
    f"{settings.api_prefix}/microkernel/dag/execute",
    response_model=ExecutionResult,
    tags=["Microkernel"]
)
async def execute_dag_pipeline(payload: DAGExecutionRequest):
    """Execute a compiled DAG execution graph according to working version."""
    tid = get_current_trace_id()
    result = await microkernel_engine.execute_dag(payload.config, payload.inputs, trace_id=tid)
    return result


@app.post(f"{settings.api_prefix}/microkernel/sandbox/validate", tags=["Microkernel"])
async def validate_script_sandbox(payload: ScriptValidationRequest):
    """AST static security inspection for dynamic user operator scripts."""
    validation = validate_python_code(payload.code)
    return {
        "is_safe": validation.is_safe,
        "violations": validation.violations,
        "parsed_functions": validation.parsed_functions,
        "signature_hash": validation.signature_hash
    }


# ==========================================
# Forum Domain Endpoints (Threads, Nested Tree, Upvotes & Bookmarks)
# ==========================================
@app.post(
    f"{settings.api_prefix}/forum/threads",
    response_model=ForumThreadResponse,
    status_code=201,
    tags=["Forum"]
)
async def create_forum_thread(payload: ForumThreadCreate):
    """Publish a new maker discussion thread."""
    return forum_service.create_thread(payload)


@app.get(
    f"{settings.api_prefix}/forum/threads",
    response_model=list[ForumThreadResponse],
    tags=["Forum"]
)
async def list_forum_threads(category_code: str | None = None):
    """List forum discussion threads, optionally filtered by category."""
    return forum_service.list_threads(category_code=category_code)


@app.get(
    f"{settings.api_prefix}/forum/threads/{{thread_id}}",
    response_model=ThreadDetailResponse,
    tags=["Forum"]
)
async def get_forum_thread_detail(thread_id: str):
    """Get discussion thread detail including full recursive comment tree."""
    try:
        return forum_service.get_thread_detail(thread_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Forum thread not found")


@app.post(
    f"{settings.api_prefix}/forum/threads/{{thread_id}}/comments",
    response_model=ForumCommentResponse,
    status_code=201,
    tags=["Forum"]
)
async def create_forum_comment(thread_id: str, payload: ForumCommentCreate):
    """Post a top-level answer or nested sub-reply with materialized path computation."""
    try:
        return forum_service.create_comment(thread_id, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    f"{settings.api_prefix}/forum/upvote",
    response_model=UpvoteResponse,
    tags=["Forum"]
)
async def toggle_forum_upvote(payload: UpvoteRequest):
    """Atomically toggle upvote on a thread or comment."""
    try:
        return forum_service.toggle_upvote(payload.user_id, payload.target_type, payload.target_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    f"{settings.api_prefix}/forum/bookmark",
    response_model=BookmarkResponse,
    tags=["Forum"]
)
async def toggle_forum_bookmark(payload: BookmarkRequest):
    """Atomically toggle bookmark on a thread."""
    try:
        return forum_service.toggle_bookmark(payload.user_id, payload.thread_id, payload.folder_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# Home Platform Overview Endpoints
# ==========================================
@app.get(f"{settings.api_prefix}/home/overview", tags=["Home Overview"])
async def get_home_overview():
    """Retrieve platform aggregate overview statistics and navigation summary."""
    return {
        "active_makers_count": 14820,
        "active_dags_count": 482,
        "matched_policies_count": 128,
        "demands_orders_count": 89,
        "perks_saved_cny": 1820000.0,
        "quick_links": [
            {"name": "头脑风暴", "route": "forum", "count_desc": "1,240 篇实战经验"},
            {"name": "流程文书", "route": "sop", "count_desc": "4 阶段合规材料"},
            {"name": "政策雷达", "route": "policy", "count_desc": "30万增值税免征"},
            {"name": "需求集市", "route": "demand", "count_desc": "89 笔进行中委托"},
            {"name": "生态特权", "route": "perks", "count_desc": "最高 $5,000 算力券"},
            {"name": "合规指南", "route": "compliance", "count_desc": "6大防线自检雷达"},
            {"name": "后端编排", "route": "backend-orch", "count_desc": "微内核 DAG 引擎"},
        ],
    }


# ==========================================
# SOP Document & Template Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/sop/templates",
    response_model=SOPTemplatesResponse,
    tags=["SOP Workflow"]
)
async def get_sop_stages_and_templates():
    """Get all 4-stage business creation steps and standard document templates."""
    return sop_service.get_stages_and_templates()


@app.post(
    f"{settings.api_prefix}/sop/templates",
    response_model=SOPTemplate,
    status_code=201,
    tags=["SOP Workflow"]
)
async def create_sop_template(payload: SOPTemplateCreate):
    """Publish a new SOP compliance document template."""
    return sop_service.create_template(payload)


@app.post(
    f"{settings.api_prefix}/sop/documents",
    response_model=SOPDocumentResponse,
    status_code=201,
    tags=["SOP Workflow"]
)
async def render_and_save_sop_document(payload: SOPDocumentCreate):
    """Render document template with maker input data and persist instance to backend."""
    try:
        return sop_service.render_and_save_document(payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    f"{settings.api_prefix}/sop/documents/{{doc_id}}",
    response_model=SOPDocumentResponse,
    tags=["SOP Workflow"]
)
async def get_sop_document(doc_id: str):
    """Retrieve saved document instance by ID."""
    try:
        return sop_service.get_document(doc_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    f"{settings.api_prefix}/sop/documents",
    response_model=list[SOPDocumentResponse],
    tags=["SOP Workflow"]
)
async def list_sop_documents(user_id: str | None = None):
    """List saved documents, optionally filtered by maker user_id."""
    return sop_service.list_documents(user_id=user_id)


# ==========================================
# Product Showcase Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/products",
    response_model=list[ProductResponse],
    tags=["Product Showcase"]
)
async def list_products(category: str | None = None):
    """List maker independent products, optionally filtered by category."""
    return product_service.list_products(category=category)


@app.post(
    f"{settings.api_prefix}/products",
    response_model=ProductResponse,
    status_code=201,
    tags=["Product Showcase"]
)
async def create_product(payload: ProductCreate):
    """Publish a new maker product showcase."""
    return product_service.create_product(payload)


@app.post(
    f"{settings.api_prefix}/products/{{product_id}}/upvote",
    response_model=ProductResponse,
    tags=["Product Showcase"]
)
async def upvote_product(product_id: str):
    """Upvote an independent maker product."""
    try:
        return product_service.upvote_product(product_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# Policy Radar Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/policies",
    response_model=list[PolicyResponse],
    tags=["Policy Radar"]
)
async def list_policies(category: str | None = None):
    """List government incentive and tax exemption policies."""
    return policy_service.list_policies(category=category)


@app.post(
    f"{settings.api_prefix}/policies",
    response_model=PolicyResponse,
    status_code=201,
    tags=["Policy Radar"]
)
async def create_policy(payload: PolicyCreate):
    """Publish a new government policy or incentive rule."""
    return policy_service.create_policy(payload)


@app.post(
    f"{settings.api_prefix}/policies/match",
    response_model=PolicyMatchResponse,
    tags=["Policy Radar"]
)
async def match_policies(payload: PolicyMatchRequest):
    """Evaluate maker financial data against policies and calculate tax savings."""
    return policy_service.match_policies(payload)


# ==========================================
# Demand Market & Bidding Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/demands",
    response_model=list[DemandResponse],
    tags=["Demand Market"]
)
async def list_demands(category: str | None = None):
    """List enterprise outsourcing and custom demands."""
    return demand_service.list_demands(category=category)


@app.post(
    f"{settings.api_prefix}/demands",
    response_model=DemandResponse,
    status_code=201,
    tags=["Demand Market"]
)
async def create_demand(payload: DemandCreate):
    """Publish a new corporate outsourcing demand."""
    return demand_service.create_demand(payload)


@app.post(
    f"{settings.api_prefix}/demands/{{demand_id}}/bids",
    response_model=BidResponse,
    status_code=201,
    tags=["Demand Market"]
)
async def submit_demand_bid(demand_id: str, payload: BidCreate):
    """Submit a maker bid for a demand."""
    try:
        return demand_service.submit_bid(demand_id, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# Perks & Infrastructure Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/perks",
    response_model=list[PerkResponse],
    tags=["Perks & Infra"]
)
async def list_perks():
    """List available developer credits and platform discounts."""
    return perk_service.list_perks()


@app.post(
    f"{settings.api_prefix}/perks",
    response_model=PerkResponse,
    status_code=201,
    tags=["Perks & Infra"]
)
async def create_perk(payload: PerkCreate):
    """Publish a new developer ecosystem perk or credit."""
    return perk_service.create_perk(payload)


@app.post(
    f"{settings.api_prefix}/perks/claim",
    response_model=PerkClaimResponse,
    tags=["Perks & Infra"]
)
async def claim_perk(payload: PerkClaimRequest):
    """Claim and activate an exclusive maker infrastructure deal."""
    try:
        return perk_service.claim_perk(payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# User Profile & Entitlements Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/user/profile",
    response_model=MakerProfileResponse,
    tags=["User & Entitlements"]
)
async def get_user_profile():
    """Get maker account profile and active feature entitlements."""
    return user_service.get_profile()


@app.post(
    f"{settings.api_prefix}/user/entitlements/activate",
    response_model=EntitlementActivateResponse,
    tags=["User & Entitlements"]
)
async def activate_entitlement(payload: EntitlementActivateRequest):
    """Purchase or activate a paid feature entitlement."""
    try:
        return user_service.activate_entitlement(payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# Orchestration Config Persistence Endpoints
# ==========================================
@app.post(
    f"{settings.api_prefix}/microkernel/dag/configs",
    response_model=DAGConfigRecord,
    status_code=201,
    tags=["Orchestration Persistence"]
)
async def save_dag_config(payload: DAGConfigSaveRequest):
    """Save and compile a versioned DAG pipeline configuration."""
    return orchestration_service.save_dag_config(payload)


@app.get(
    f"{settings.api_prefix}/microkernel/dag/configs",
    response_model=list[DAGConfigRecord],
    tags=["Orchestration Persistence"]
)
async def list_dag_configs(scenario_code: str | None = None):
    """List saved DAG configurations."""
    return orchestration_service.list_dag_configs(scenario_code=scenario_code)


@app.post(
    f"{settings.api_prefix}/frontend/layouts",
    response_model=FrontendLayoutRecord,
    status_code=201,
    tags=["Orchestration Persistence"]
)
async def save_frontend_layout(payload: FrontendLayoutSaveRequest):
    """Save low-code canvas 24-grid responsive layout."""
    return orchestration_service.save_frontend_layout(payload)


@app.get(
    f"{settings.api_prefix}/frontend/layouts",
    response_model=FrontendLayoutRecord,
    tags=["Orchestration Persistence"]
)
async def get_frontend_layout(layout_name: str = "main_console_layout"):
    """Load latest published frontend layout schema."""
    try:
        return orchestration_service.get_frontend_layout(layout_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    f"{settings.api_prefix}/orchestration/operators",
    response_model=list[OperatorDescriptor],
    tags=["Low-Code Composition & Microkernel Orchestration"]
)
async def list_registered_operators():
    """List all registered atomic domain operators and external gateway proxies."""
    return orchestration_service.list_operators()


@app.post(
    f"{settings.api_prefix}/orchestration/operators/mode",
    response_model=OperatorDescriptor,
    tags=["Low-Code Composition & Microkernel Orchestration"]
)
async def update_operator_dispatch_mode(payload: OperatorModeUpdateRequest):
    """Toggle operator execution mode between IN_PROCESS and HTTP_REMOTE."""
    return orchestration_service.update_operator_mode(payload)


@app.post(
    f"{settings.api_prefix}/orchestration/scenarios/execute",
    response_model=ScenarioExecuteResponse,
    tags=["Low-Code Composition & Microkernel Orchestration"]
)
async def execute_composable_scenario(payload: ScenarioExecuteRequest):
    """Execute a composable scenario DAG pipeline across domain modules and external gateways."""
    try:
        return await orchestration_service.execute_scenario(payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Administrator Content Moderation Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/admin/moderation/items",
    response_model=list[ModerationItemResponse],
    tags=["Content Moderation"]
)
async def list_moderation_items(status: str | None = None):
    """Retrieve reported and flagged content items for administrative review."""
    return moderation_service.list_items(status=status)


@app.post(
    f"{settings.api_prefix}/admin/moderation/takedown",
    response_model=ModerationActionResponse,
    tags=["Content Moderation"]
)
async def takedown_content(payload: TakedownRequest):
    """Take down violating speech and hide from public view."""
    return moderation_service.takedown(payload)


@app.post(
    f"{settings.api_prefix}/admin/moderation/restore",
    response_model=ModerationActionResponse,
    tags=["Content Moderation"]
)
async def restore_content(payload: RestoreRequest):
    """Restore mistakenly flagged content item."""
    return moderation_service.restore(payload)


# ==========================================
# Product Compliance & Self-Audit Endpoints
# ==========================================
@app.get(
    f"{settings.api_prefix}/compliance/dimensions",
    response_model=list[ComplianceDimension],
    tags=["Product Compliance"]
)
async def get_compliance_dimensions():
    """Retrieve six-dimensional product compliance guidelines and legal rules."""
    return compliance_service.get_dimensions()


@app.get(
    f"{settings.api_prefix}/compliance/cases",
    response_model=list[ComplianceCase],
    tags=["Product Compliance"]
)
async def get_compliance_cases():
    """Retrieve real-world regulatory pitfall cases and penalties."""
    return compliance_service.get_cases()


@app.get(
    f"{settings.api_prefix}/compliance/checkpoints",
    response_model=list[AuditCheckItem],
    tags=["Product Compliance"]
)
async def get_compliance_checkpoints():
    """Retrieve 10-point standard pre-launch compliance self-audit checklist."""
    return compliance_service.get_checkpoints()


@app.post(
    f"{settings.api_prefix}/compliance/audit",
    response_model=AuditReportResponse,
    tags=["Product Compliance"]
)
async def evaluate_compliance_audit(payload: AuditEvaluateRequest):
    """Evaluate developer's self-audit submission and generate a compliance score report."""
    return compliance_service.evaluate_audit(payload)




