"""Observability & Distributed Tracing subsystem for OpcHub.
Features:
- Global distributed TraceID generation and HTTP header propagation (X-Trace-ID)
- ContextVar-based request-scoped tracing context
- Structured JSON logging contract
- Tri-state standard health probes (/livez, /readyz, /healthz)
"""
import time
import json
import uuid
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable holding current request trace_id
current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="")
app_start_time: float = time.time()


def get_current_trace_id() -> str:
    """Retrieve current request trace_id or generate a local fallback."""
    tid = current_trace_id.get()
    if not tid:
        tid = f"trc_{uuid.uuid4().hex[:16]}"
        current_trace_id.set(tid)
    return tid


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON per auxiliary_governance.md §5.1."""

    def format(self, record: logging.LogRecord) -> str:
        tid = current_trace_id.get() or getattr(record, "trace_id", "")
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "trace_id": tid or "trc_system_kernel",
            "span_id": getattr(record, "span_id", "span_root"),
            "logger": record.name,
            "message": record.getMessage(),
            "context": getattr(record, "context", {}),
        }
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload, ensure_ascii=False)


# Setup logger
logger = logging.getLogger("opchub.telemetry")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    logger.addHandler(handler)


class TracePropagationMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware for X-Trace-ID HTTP Header propagation."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract existing trace ID from client or generate new
        incoming_trace = request.headers.get("X-Trace-ID") or request.headers.get("X-Request-ID")
        if incoming_trace:
            trace_id = incoming_trace
        else:
            trace_id = f"trc_{uuid.uuid4().hex[:16]}"

        token = current_trace_id.set(trace_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach trace ID and latency to response headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "context": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            )
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Unhandled error in {request.method} {request.url.path}: {str(e)}",
                exc_info=True,
                extra={
                    "context": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            )
            raise e
        finally:
            current_trace_id.reset(token)
