"""Hot-reload infrastructure for dynamic operator scripts.

The former DAG engine / atomic registry / dual-mode dispatcher were retired
when business execution moved to the MicroFlow4Python framework (see
``src/host/``). What remains here is the dynamic-operator lifecycle: AST
sandbox validation, script ingestion firewalls and the versioned hot-reload
watcher that rebuilds the MicroFlow release after activation.
"""
from src.core.microkernel.sandbox import validate_python_code
from src.core.microkernel.script_ingestion import script_ingestion_service
from src.core.microkernel.watcher import hot_reload_engine

__all__ = [
    "validate_python_code",
    "script_ingestion_service",
    "hot_reload_engine",
]
