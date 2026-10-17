"""Dual-mode dispatcher for microkernel DAG operators.

Supports:
- IN_PROCESS: Monolith stage direct memory async method call (zero network latency)
- HTTP_REMOTE: Microservices stage remote HTTP POST to independent microservice endpoint
"""
from enum import Enum
from typing import Any, Callable, Awaitable, Optional, Dict, Tuple
import inspect
import logging
import httpx
from pydantic import BaseModel

from src.core.telemetry import get_current_trace_id

logger = logging.getLogger("opchub.microkernel.dispatcher")

ActionHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]


class DispatchMode(str, Enum):
    IN_PROCESS = "IN_PROCESS"
    HTTP_REMOTE = "HTTP_REMOTE"


class OperatorDescriptor(BaseModel):
    name: str
    domain: str
    description: str
    mode: DispatchMode = DispatchMode.IN_PROCESS
    remote_endpoint: Optional[str] = None


class DualModeDispatcher:
    """Dispatches operator execution according to configured mode (In-Process vs HTTP Remote)."""

    def __init__(self, default_mode: DispatchMode = DispatchMode.IN_PROCESS):
        self.default_mode = default_mode
        self._operator_modes: Dict[str, Tuple[DispatchMode, Optional[str]]] = {}
        self._descriptors: Dict[str, OperatorDescriptor] = {}
        self._stats = {
            "in_process_count": 0,
            "http_remote_count": 0,
        }

    def register_descriptor(
        self,
        name: str,
        domain: str,
        description: str,
        mode: DispatchMode = DispatchMode.IN_PROCESS,
        remote_endpoint: Optional[str] = None,
    ):
        """Register metadata descriptor for an atomic operator."""
        desc = OperatorDescriptor(
            name=name,
            domain=domain,
            description=description,
            mode=mode,
            remote_endpoint=remote_endpoint,
        )
        self._descriptors[name] = desc
        self._operator_modes[name] = (mode, remote_endpoint)

    def set_operator_mode(
        self,
        name: str,
        mode: DispatchMode,
        remote_endpoint: Optional[str] = None,
    ):
        """Override execution mode for a specific operator (e.g. switching to microservice)."""
        if name in self._descriptors:
            self._descriptors[name].mode = mode
            if remote_endpoint:
                self._descriptors[name].remote_endpoint = remote_endpoint
        self._operator_modes[name] = (mode, remote_endpoint)
        logger.info(f"Operator '{name}' dispatch mode set to {mode.value} (endpoint={remote_endpoint})")

    def get_operator_mode(self, name: str) -> Tuple[DispatchMode, Optional[str]]:
        return self._operator_modes.get(name, (self.default_mode, None))

    def list_descriptors(self) -> list[OperatorDescriptor]:
        return list(self._descriptors.values())

    def unregister_descriptor(self, name: str) -> bool:
        """Remove a previously registered operator descriptor and its mode override."""
        existed = name in self._descriptors
        self._descriptors.pop(name, None)
        self._operator_modes.pop(name, None)
        return existed

    async def dispatch(
        self,
        name: str,
        handler: Optional[ActionHandler],
        inputs: dict[str, Any],
        context: dict[str, Any],
        timeout_sec: float = 30.0,
    ) -> dict[str, Any]:
        """Dispatches operator call to either in-process local handler or remote HTTP service."""
        mode, endpoint = self.get_operator_mode(name)
        trace_id = context.get("trace_id") or get_current_trace_id()

        if mode == DispatchMode.IN_PROCESS:
            if not handler:
                raise KeyError(f"In-process handler for action '{name}' not found in registry")
            self._stats["in_process_count"] += 1
            logger.debug(f"[IN_PROCESS] Dispatching '{name}' locally (TraceID: {trace_id})")
            res = handler(inputs, context)
            if inspect.iscoroutine(res):
                return await res
            return res

        elif mode == DispatchMode.HTTP_REMOTE:
            self._stats["http_remote_count"] += 1
            target_endpoint = endpoint or f"http://svc-{name.replace('.', '-')}:8080/api/v1/operators/execute"
            logger.info(f"[HTTP_REMOTE] Dispatching '{name}' to remote endpoint '{target_endpoint}' (TraceID: {trace_id})")

            # Microservice HTTP remote invocation with X-Trace-ID header injection
            headers = {
                "X-Trace-ID": trace_id,
                "Content-Type": "application/json",
            }
            payload = {
                "operator": name,
                "inputs": inputs,
                "context": context,
            }

            try:
                async with httpx.AsyncClient(timeout=timeout_sec) as client:
                    resp = await client.post(target_endpoint, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data.get("result", data)
                    elif resp.status_code == 403:
                        raise PermissionError(f"Remote operator {name} rejected execution: {resp.text}")
                    else:
                        raise RuntimeError(f"Remote operator {name} failed with status {resp.status_code}: {resp.text}")
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                # If remote microservice is unreachable in development/testing, fallback to local handler if available
                if handler:
                    logger.warning(
                        f"[HTTP_REMOTE FALLBACK] Remote endpoint {target_endpoint} unreachable ({exc}), falling back to in-process handler for '{name}'"
                    )
                    return await handler(inputs, context)
                raise RuntimeError(f"Remote microservice {target_endpoint} unreachable and no local fallback available: {exc}")


dispatcher = DualModeDispatcher()
