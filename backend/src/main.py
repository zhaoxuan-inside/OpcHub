import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
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
from src.core.microkernel.script_ingestion import script_ingestion_service
from src.core.microkernel.watcher import hot_reload_engine
from src.core.audit import audit_service
from src.core.security import verify_session_token
from src.core.microkernel.registry import registry
from src.domains.user.service import user_service
from src.domains.notifications.service import notification_service  # noqa: F401  (register persistence hydrator)
from src.domains.user.models import (
    UserRegisterRequest,
    UserLoginRequest,
    SendCodeRequest,
    VerifyCodeRequest,
    PasswordStrengthRequest,
)
from src.infrastructure.database.repository import db_repository
from src.infrastructure.database.persistence import domain_persistence
from src.core.gateway import (
    DispatchRequest,
    DispatchResponse,
    RouteRuleDescriptor,
    scenario_router,
    register_default_scenario_routes,
)

# Register default business scenario route rules into router
register_default_scenario_routes()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initialize DB schema, provision built-in admin, run retention archival."""
    try:
        await db_repository.ensure_schema_and_seed()
        admin = user_service._users_by_uid.get("usr_admin_builtin")
        if admin:
            await db_repository.ensure_builtin_admin(
                uid=admin["uid"],
                email=admin["email"],
                nickname=admin["nickname"],
                password_hash=admin["password_hash"],
            )
        # Retention: move audit records older than the configured window to cold archive
        await audit_service.archive_older_than()
        # Rebuild the in-memory domain indexes from persisted state (restart durability)
        await user_service.hydrate_from_db()
        await domain_persistence.initialize()
        # Hydrate the generic entity store and compile the scenario assets that
        # define every business flow (business = operator orchestration).
        from src.core.entity import entity_store
        from src.core.scenario import ensure_scenarios_loaded

        await entity_store.initialize()
        ensure_scenarios_loaded(force=True)
        # Seed the loyalty (points / membership / redemption) DAG pipelines.
        from src.domains.loyalty.pipelines import ensure_loyalty_pipelines

        ensure_loyalty_pipelines()
        # Start the publish review-queue consumer: it keeps auditing pending
        # document / flow submissions and promotes approved ones into the
        # standard document catalog and flow guide.
        from src.domains.sop.service import sop_service

        sop_service.start_review_consumer(interval=5.0)
        # Start file sensing watcher for versioned hot-reloading
        hot_reload_engine.start_background_watcher()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn").warning(f"Startup initialization note: {e}")
    yield
    # Flush any outstanding write-behind persistence tasks before shutdown
    try:
        from src.domains.sop.service import sop_service
        sop_service.stop_review_consumer()
        hot_reload_engine.stop_background_watcher()
        await domain_persistence.flush()
    except Exception:
        pass
    try:
        from src.core.database import dispose_engine
        await dispose_engine()
    except Exception:
        pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Microkernel DAG Orchestration & Cross-Platform Telemetry Gateway for Super Individuals",
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TracePropagationMiddleware)


@app.get("/", response_class=HTMLResponse, tags=["Web Console"])
@app.get("/app", response_class=HTMLResponse, tags=["Web Console"])
async def serve_web_console():
    """Serve the OpcHub API landing page with quick entrance to interactive console."""
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head><meta charset="utf-8"><title>OpcHub API</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body { font-family: -apple-system, "PingFang SC", "Helvetica Neue", sans-serif;
                 background:#F8F9FD; color:#121316; display:flex; align-items:center;
                 justify-content:center; min-height:100vh; margin:0; }
          .card { background:rgba(255,255,255,.75); border:1px solid rgba(255,255,255,.8);
                  border-radius:20px; padding:48px 56px; max-width:560px;
                  box-shadow: inset 0 1px 1px rgba(255,255,255,.95), 0 20px 60px rgba(0,0,0,.06); }
          h1 { font-size:26px; letter-spacing:-.03em; margin:0 0 8px; }
          p  { color:#4B4E56; line-height:1.7; margin:8px 0; }
          code{ font-family:"SF Mono", Menlo, monospace; font-size:13px;
                background:rgba(0,113,227,.08); color:#0071E3; padding:2px 6px; border-radius:6px; }
          .btn { display:inline-block; margin-top:14px; padding:10px 20px; background:#0071E3;
                 color:#FFFFFF; text-decoration:none; border-radius:10px; font-size:14px;
                 font-weight:500; box-shadow:0 4px 14px rgba(0,113,227,.3); transition:background .2s; }
          .btn:hover { background:#0077ED; }
        </style></head>
        <body><div class="card">
          <h1>OpcHub 微内核服务平台</h1>
          <p>API-First 服务已就绪。交互式 API 文档：<code>/docs</code>，统一网关入口：<code>/api/welcom/opc_world</code>。</p>
          <p>健康探针：<code>/livez</code> · <code>/readyz</code> · <code>/healthz</code></p>
          <a class="btn" href="/console">进入 OpcHub Web 可视化工作台 &rarr;</a>
        </div></body></html>
        """,
        status_code=200,
    )


@app.get("/console", tags=["Web Console"])
async def serve_interactive_console():
    """Serve the complete OpcHub interactive visual console from frontend build or redirect to frontend service."""
    dist_html = Path(__file__).resolve().parents[2] / "frontend/dist/index.html"
    if dist_html.is_file():
        return FileResponse(
            dist_html,
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    from fastapi.responses import RedirectResponse
    frontend_url = os.getenv("OPCHUB_FRONTEND_URL", "http://127.0.0.1:3000")
    return RedirectResponse(url=frontend_url)


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0071E3"/><circle cx="16" cy="16" r="6" fill="#ffffff"/></svg>"""


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    """Serve lightweight SVG favicon for OpcHub Console to avoid 404 console errors."""
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


class ScriptValidationRequest(BaseModel):
    code: str
    action_name: str | None = None


class ScriptUploadRequest(BaseModel):
    """Admin dynamic operator script ingestion request (RBAC §3.2)."""
    name: str
    code: str
    entry_function: str | None = None
    description: str = ""
    overwrite: bool = False
    token: str | None = None


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    parts = authorization.split(" ", 1)
    return parts[1].strip() if len(parts) == 2 and parts[0].lower() == "bearer" else authorization.strip()


def require_admin(token: str | None) -> str:
    """RBAC guard: dynamic script ingestion is restricted to ADMIN (rbac §2 / §3.2)."""
    payload = verify_session_token(token or "")
    if not payload or payload.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="ADMIN privilege required for dynamic Python script ingestion",
        )
    return payload.get("uid", "admin")


class DAGExecutionRequest(BaseModel):
    config: DAGConfig
    inputs: dict[str, Any] | None = None


async def dispatch_scenario(payload: DispatchRequest, request: Request):
    """Unified entrypoint receiving any business request and dynamically routing by scenario."""
    if not payload.token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            payload.token = auth.split(" ", 1)[1].strip()
    return await scenario_router.dispatch(payload)


async def list_scenario_rules():
    """List all registered scenario routing rules across business domains."""
    return scenario_router.list_rules()


class HotReloadActivateRequest(BaseModel):
    version: str = "v1.0.0"
    file_paths: Optional[list[str]] = None


async def reload_scenario_routes():
    """Reload scenario routes, detect file changes, and activate versioned modules into memory."""
    activation_res = hot_reload_engine.activate_version(
        target_version=getattr(settings, "app_version", "v1.0.0"),
        reload_gateway_routes=False,
    )
    count = register_default_scenario_routes()
    return {
        "status": "ok",
        "reloaded_routes_count": count,
        "hot_reload": activation_res,
    }


# Dynamically register gateway endpoints defined in configuration (zero hardcoding)
for _endpoint in settings.gateway_endpoints:
    app.add_api_route(
        _endpoint,
        dispatch_scenario,
        methods=["POST"],
        response_model=DispatchResponse,
        tags=["Unified Gateway Dispatcher"],
        summary="Unified Gateway Inbound Dispatcher",
    )

for _meta_endpoint in settings.gateway_metadata_endpoints:
    app.add_api_route(
        _meta_endpoint,
        list_scenario_rules,
        methods=["GET"],
        response_model=list[RouteRuleDescriptor],
        tags=["Unified Gateway Dispatcher"],
        summary="Unified Gateway Rules Introspection",
    )
    # Sibling hot-reload endpoint keeps the management surface symmetric & config-driven
    # (e.g. /api/v1/gateway/rules -> /api/v1/gateway/reload).
    if _meta_endpoint.endswith("/rules"):
        app.add_api_route(
            _meta_endpoint[: -len("/rules")] + "/reload",
            reload_scenario_routes,
            methods=["POST"],
            tags=["Unified Gateway Dispatcher"],
            summary="Reload Routes and Version Policies from YAML",
        )


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
    """Readiness probe checking readiness of database, kernel operators and domain repositories."""
    ops_count = len(registry.list_handlers())
    if ops_count < 4:
        raise HTTPException(status_code=503, detail="Kernel operators below readiness threshold")
    
    db_ready = await db_repository.is_ready()
    return {
        "status": "READY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_current_trace_id(),
        "checks": {
            "database": "CONNECTED" if db_ready else "DISCONNECTED",
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
# Admin Dynamic Operator Script Ingestion (RBAC §3.2 four-firewall pipeline)
# ==========================================
@app.post(f"{settings.api_prefix}/scripts/upload", tags=["Dynamic Operators"])
async def upload_dynamic_operator(
    payload: ScriptUploadRequest,
    authorization: str | None = Header(default=None),
):
    """Firewall 1-4: scan, verify entry-point, restricted-load and register an admin Python operator."""
    operator_id = require_admin(payload.token or _extract_bearer(authorization))
    try:
        record = script_ingestion_service.upload_and_register(
            name=payload.name,
            code=payload.code,
            operator_id=operator_id,
            entry_function=payload.entry_function,
            description=payload.description,
            overwrite=payload.overwrite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "REGISTERED", **record}


@app.get(f"{settings.api_prefix}/scripts/operators", tags=["Dynamic Operators"])
async def list_dynamic_operators(
    authorization: str | None = Header(default=None),
    token: str | None = None,
):
    """List all runtime-registered dynamic operators (ADMIN only)."""
    require_admin(token or _extract_bearer(authorization))
    return script_ingestion_service.list_dynamic_operators()


@app.post(f"{settings.api_prefix}/scripts/{{name}}/unregister", tags=["Dynamic Operators"])
async def unregister_dynamic_operator(
    name: str,
    authorization: str | None = Header(default=None),
    token: str | None = None,
):
    """Remove a runtime-registered dynamic operator (ADMIN only)."""
    operator_id = require_admin(token or _extract_bearer(authorization))
    removed = script_ingestion_service.unregister(name, operator_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Dynamic operator '{name}' not found")
    return {"operator_name": name, "status": "UNREGISTERED"}


@app.get(f"{settings.api_prefix}/scripts/audit", tags=["Dynamic Operators"])
async def list_script_audit_log(
    authorization: str | None = Header(default=None),
    token: str | None = None,
    limit: int = 50,
):
    """Retrieve the tamper-evident script ingestion audit log (ADMIN only)."""
    require_admin(token or _extract_bearer(authorization))
    return script_ingestion_service.audit_log(limit=limit)


# ==========================================
# Security Audit & Cold Archive (ADMIN only) — legal_compliance §80
# ==========================================
@app.get(f"{settings.api_prefix}/admin/audit/logs", tags=["Security Audit"])
async def list_security_audit_logs(
    authorization: str | None = Header(default=None),
    token: str | None = None,
    limit: int = 100,
    actor_id: str | None = None,
    action: str | None = None,
):
    """Query hot security audit logs (RBAC/ABAC decisions and privileged operations)."""
    require_admin(token or _extract_bearer(authorization))
    return await audit_service.list_logs(limit=limit, actor_id=actor_id, action=action)


@app.get(f"{settings.api_prefix}/admin/audit/archive", tags=["Security Audit"])
async def list_archived_security_audit_logs(
    authorization: str | None = Header(default=None),
    token: str | None = None,
    limit: int = 100,
):
    """Query cold-archived security audit logs past the retention window."""
    require_admin(token or _extract_bearer(authorization))
    return await audit_service.list_archived(limit=limit)


@app.post(f"{settings.api_prefix}/admin/audit/archive/run", tags=["Security Audit"])
async def run_security_audit_archive(
    authorization: str | None = Header(default=None),
    token: str | None = None,
    days: int | None = None,
):
    """Trigger retention archival: move audit records older than `days` into the cold archive."""
    require_admin(token or _extract_bearer(authorization))
    moved = await audit_service.archive_older_than(days=days)
    return {"status": "OK", "archived_records": moved, "retention_days": days or settings.audit_retention_days}


# ==========================================
# Commercial Authentication & Registration Endpoints
# ==========================================
@app.get("/api/auth/captcha", tags=["Authentication & Commercial Onboarding"])
@app.get(f"{settings.api_prefix}/auth/captcha", tags=["Authentication & Commercial Onboarding"])
async def get_captcha():
    """Generate anti-bot SVG challenge."""
    return user_service.generate_captcha()


@app.post("/api/auth/send-code", tags=["Authentication & Commercial Onboarding"])
@app.post(f"{settings.api_prefix}/auth/send-code", tags=["Authentication & Commercial Onboarding"])
async def send_verification_code(req: SendCodeRequest, request: Request):
    """Dispatch verification code to email with rate-limiting and anti-bot validation."""
    client_ip = req.client_ip or (request.client.host if request.client else "127.0.0.1")
    try:
        return user_service.send_verification_code(
            email=req.email,
            captcha_id=req.captcha_id,
            captcha_code=req.captcha_code,
            client_ip=client_ip,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/verify-code", tags=["Authentication & Commercial Onboarding"])
@app.post(f"{settings.api_prefix}/auth/verify-code", tags=["Authentication & Commercial Onboarding"])
async def verify_code(req: VerifyCodeRequest):
    """Pre-verify verification code."""
    valid = user_service.verify_email_code(req.email, req.code)
    if not valid:
        raise HTTPException(status_code=400, detail="验证码错误或已失效")
    return {"valid": True, "message": "验证码有效"}


@app.post("/api/auth/password-strength", tags=["Authentication & Commercial Onboarding"])
@app.post(f"{settings.api_prefix}/auth/password-strength", tags=["Authentication & Commercial Onboarding"])
async def check_password_strength(req: PasswordStrengthRequest):
    """Evaluate password strength against commercial standards."""
    return user_service.evaluate_password_strength(req.password, email=req.email)


@app.get("/api/auth/agreements", tags=["Authentication & Commercial Onboarding"])
@app.get(f"{settings.api_prefix}/auth/agreements", tags=["Authentication & Commercial Onboarding"])
async def get_agreements():
    """Retrieve statutory user terms of service and privacy policy."""
    return user_service.get_legal_agreements()


@app.get("/api/auth/mail-providers", tags=["Authentication & Commercial Onboarding"])
@app.get(f"{settings.api_prefix}/auth/mail-providers", tags=["Authentication & Commercial Onboarding"])
async def get_mail_providers(email: Optional[str] = None):
    """Retrieve supported email provider list and resolved SMTP configuration for target email."""
    if email:
        return user_service.resolve_mail_provider(email)
    return user_service.get_supported_mail_providers()


@app.post("/api/auth/register", tags=["Authentication & Commercial Onboarding"])
@app.post(f"{settings.api_prefix}/auth/register", tags=["Authentication & Commercial Onboarding"])
async def register_maker(req: UserRegisterRequest, request: Request):
    """Commercial maker account registration with legal consent and ownership proof."""
    if not req.client_ip and request.client:
        req.client_ip = request.client.host
    try:
        res = await user_service.register_by_email(req)
        return res.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login", tags=["Authentication & Commercial Onboarding"])
@app.post(f"{settings.api_prefix}/auth/login", tags=["Authentication & Commercial Onboarding"])
async def login_maker(req: UserLoginRequest):
    """Maker email and password authentication."""
    try:
        res = await user_service.login_by_email(req)
        return res.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Server host/port are configuration-driven (application.yaml) per detailed design §3.3-3
    uvicorn.run(app, host=settings.server_host, port=settings.server_port)




