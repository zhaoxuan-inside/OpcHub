"""Dynamic Operator Script Ingestion Service (RBAC §3.2 four-firewall pipeline).

Firewalls 1-3 (AST scan / entry-point convention / restricted-namespace load) are
delegated to ``core.microkernel.sandbox``. This service performs Firewall 4:
registration into the AtomicRegistry plus tamper-evident audit logging.
"""
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.microkernel.registry import registry
from src.core.microkernel.sandbox import load_operator_from_source

logger = logging.getLogger("opchub.microkernel.script_ingestion")

DYNAMIC_DOMAIN = "dynamic"
OPERATOR_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.]{1,62}[a-zA-Z0-9]$")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScriptIngestionService:
    """Ingests admin-uploaded Python operator scripts into the microkernel method pool."""

    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []
        self._dynamic_operators: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Audit (tamper-evident structured records; emitted to the log pipeline)
    # ------------------------------------------------------------------
    def _record(
        self,
        operator_name: str,
        operator_id: str,
        action: str,
        status: str,
        reason: str = "",
        entry_function: str = "",
        signature_hash: str = "",
        source_bytes: int = 0,
    ) -> Dict[str, Any]:
        record = {
            "audit_id": f"aud_script_{uuid.uuid4().hex[:10]}",
            "operator_name": operator_name,
            "entry_function": entry_function,
            "signature_hash": signature_hash,
            "operator_id": operator_id,
            "action": action,
            "status": status,
            "reason": reason,
            "source_bytes": source_bytes,
            "created_at": utc_now_iso(),
        }
        self._audit_log.append(record)
        logger.info(
            f"[ScriptIngestion] {action} operator='{operator_name}' admin='{operator_id}' "
            f"status={status} sig={signature_hash} reason={reason or '-'}"
        )
        return record

    # ------------------------------------------------------------------
    # Firewall 4: upload -> register + audit
    # ------------------------------------------------------------------
    def upload_and_register(
        self,
        name: str,
        code: str,
        operator_id: str,
        entry_function: Optional[str] = None,
        description: str = "",
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Validate and register a dynamic operator. Raises ValueError on any firewall failure."""
        clean_name = (name or "").strip()

        # Name hygiene + protection of built-in operators
        if not OPERATOR_NAME_PATTERN.match(clean_name):
            self._record(clean_name, operator_id, "REJECTED", "REJECTED", "invalid operator name format")
            raise ValueError(
                "Invalid operator name: must start with a letter and contain only "
                "letters, digits, '_' or '.' (2-64 chars)"
            )
        if clean_name in registry.list_handlers() and clean_name not in self._dynamic_operators:
            self._record(clean_name, operator_id, "REJECTED", "REJECTED", "name collides with a built-in operator")
            raise ValueError(f"Operator name '{clean_name}' already exists as a built-in operator")
        if clean_name in self._dynamic_operators and not overwrite:
            self._record(clean_name, operator_id, "REJECTED", "REJECTED", "operator already registered")
            raise ValueError(
                f"Dynamic operator '{clean_name}' already exists; pass overwrite=true to replace it"
            )

        # Firewalls 1-3: scan, entry convention, restricted load
        try:
            loaded = load_operator_from_source(code, entry_function)
        except ValueError as exc:
            self._record(clean_name, operator_id, "REJECTED", "REJECTED", str(exc),
                         entry_function=entry_function or "", source_bytes=len((code or "").encode("utf-8")))
            raise

        # Firewall 4: register into the atomic method pool
        registry.register(
            clean_name,
            loaded.handler,
            domain=DYNAMIC_DOMAIN,
            description=description or f"Dynamic operator uploaded by {operator_id}",
        )
        record = self._record(
            clean_name, operator_id, "REGISTERED", "SUCCESS", "",
            entry_function=loaded.entry_function,
            signature_hash=loaded.signature_hash,
            source_bytes=loaded.source_bytes,
        )
        self._dynamic_operators[clean_name] = {
            "name": clean_name,
            "operator_name": clean_name,
            "entry_function": loaded.entry_function,
            "signature_hash": loaded.signature_hash,
            "operator_id": operator_id,
            "description": description,
            "registered_at": record["created_at"],
            "audit_id": record["audit_id"],
            "source_bytes": loaded.source_bytes,
        }
        return dict(self._dynamic_operators[clean_name])

    def unregister(self, name: str, operator_id: str) -> bool:
        """Remove a dynamic operator and record the action in the audit log."""
        clean_name = (name or "").strip()
        if clean_name not in self._dynamic_operators:
            self._record(clean_name, operator_id, "UNREGISTERED", "REJECTED", "not a dynamic operator")
            return False
        registry.unregister(clean_name)
        self._dynamic_operators.pop(clean_name, None)
        self._record(clean_name, operator_id, "UNREGISTERED", "SUCCESS")
        return True

    def list_dynamic_operators(self) -> List[Dict[str, Any]]:
        return list(self._dynamic_operators.values())

    def audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self._audit_log[-limit:])


script_ingestion_service = ScriptIngestionService()
