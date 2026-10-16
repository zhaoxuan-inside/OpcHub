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
