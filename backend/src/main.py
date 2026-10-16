"""OpcHub FastAPI Main Application Gateway."""
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import settings
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


class ScriptValidationRequest(BaseModel):
    code: str
    action_name: str | None = None


class DAGExecutionRequest(BaseModel):
    config: DAGConfig
    inputs: dict[str, Any] | None = None


@app.get("/health", tags=["System"])
async def health_check():
    """System liveness probe."""
    return {
        "status": "HEALTHY",
        "service": settings.app_name,
        "version": settings.app_version,
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
    result = await microkernel_engine.execute_dag(payload.config, payload.inputs)
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

