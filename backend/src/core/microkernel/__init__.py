"""Microkernel DAG orchestration and atomic method pool.

The registry / dispatcher / engine are exported lazily: operator modules import
``src.core.microkernel.expr`` while the operator package is still initialising,
so eager imports here would create a circular dependency.
"""
from src.core.microkernel.models import (
    CompensationTrace,
    DAGConfig,
    EdgeDef,
    ExecutionGraph,
    ExecutionResult,
    ExecutionStatus,
    NodeDef,
    NodeExecutionTrace,
    NodeType,
)

__all__ = [
    "NodeType",
    "NodeDef",
    "EdgeDef",
    "ExecutionGraph",
    "DAGConfig",
    "ExecutionStatus",
    "NodeExecutionTrace",
    "CompensationTrace",
    "ExecutionResult",
    "AtomicRegistry",
    "registry",
    "DispatchMode",
    "DualModeDispatcher",
    "dispatcher",
    "MicrokernelEngine",
    "microkernel_engine",
]


def __getattr__(name: str):
    if name in ("AtomicRegistry", "registry"):
        from src.core.microkernel.registry import AtomicRegistry, registry

        return {"AtomicRegistry": AtomicRegistry, "registry": registry}[name]
    if name in ("DispatchMode", "DualModeDispatcher", "dispatcher"):
        from src.core.microkernel.dispatcher import DispatchMode, DualModeDispatcher, dispatcher

        return {
            "DispatchMode": DispatchMode,
            "DualModeDispatcher": DualModeDispatcher,
            "dispatcher": dispatcher,
        }[name]
    if name in ("MicrokernelEngine", "microkernel_engine"):
        from src.core.microkernel.engine import MicrokernelEngine, microkernel_engine

        return {"MicrokernelEngine": MicrokernelEngine, "microkernel_engine": microkernel_engine}[name]
    raise AttributeError(name)
