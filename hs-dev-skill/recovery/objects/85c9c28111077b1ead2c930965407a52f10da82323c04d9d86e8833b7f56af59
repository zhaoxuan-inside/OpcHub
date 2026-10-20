"""Cross-cutting security & operation audit service with cold archival.

Backs gateway RBAC/ABAC decisions and privileged operations with encrypted,
queryable audit records (``audit_logs``) plus a cold archive
(``audit_logs_archive``) retaining entries past the configured window
(opchub_legal_compliance_spec §80: encrypted retention >= 180 days).
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.crypto import decrypt_text, encrypt_text

logger = logging.getLogger("opchub.audit")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditService:
    """Records tamper-evident audit events and performs retention archival."""

    def __init__(self):
        self._mem_logs: List[Dict[str, Any]] = []
        self._mem_archive: List[Dict[str, Any]] = []
        self._max_mem = 5000

    async def record(
        self,
        action: str,
        actor_id: str = "",
        actor_role: str = "GUEST",
        resource_type: str = "",
        resource_id: str = "",
        permission: str = "",
        result: str = "SUCCESS",
        ip_address: str = "",
        trace_id: str = "",
        detail: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append an audit record (memory always; DB when available) with encrypted detail."""
        record = {
            "id": str(uuid.uuid4()),
            "actor_id": actor_id or "",
            "actor_role": actor_role or "GUEST",
            "action": action,
            "resource_type": resource_type or "",
            "resource_id": resource_id or "",
            "permission": permission or "",
            "result": result,
            "ip_address": ip_address or "",
            "trace_id": trace_id or "",
            "detail_encrypted": encrypt_text(json.dumps(detail or {}, ensure_ascii=False)),
            "created_at": utc_now_iso(),
        }
        self._mem_logs.append(record)
        if len(self._mem_logs) > self._max_mem:
            self._mem_logs = self._mem_logs[-self._max_mem:]
        try:
            from src.infrastructure.database.repository import db_repository
            await db_repository.insert_audit_log(record)
        except Exception as exc:  # pragma: no cover - DB optional
            logger.debug("audit DB write skipped: %s", exc)
        logger.info(
            f"[AUDIT] action={action} actor={actor_id or '-'}({actor_role}) "
            f"result={result} resource={resource_type}:{resource_id or '-'} perm={permission or '-'}"
        )
        return record

    async def list_logs(
        self,
        limit: int = 100,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query hot audit logs (DB when ready, otherwise in-memory), decrypted."""
        rows: Optional[List[Dict[str, Any]]] = None
        try:
            from src.infrastructure.database.repository import db_repository
            if await db_repository.is_ready():
                rows = await db_repository.list_audit_logs(limit=limit, actor_id=actor_id, action=action)
        except Exception:
            rows = None
        if rows is None:
            rows = [
                r for r in self._mem_logs
                if (actor_id is None or r["actor_id"] == actor_id)
                and (action is None or r["action"] == action)
            ][-limit:]
        return [self._decode(r) for r in rows]

    async def archive_older_than(
        self,
        days: Optional[int] = None,
        batch_size: Optional[int] = None,
    ) -> int:
        """Move audit records older than the retention window into the cold archive."""
        days = days if days is not None else settings.audit_retention_days
        batch_size = batch_size or settings.audit_archive_batch_size
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        moved = 0

        try:
            from src.infrastructure.database.repository import db_repository
            if await db_repository.is_ready():
                moved = await db_repository.archive_audit_logs(cutoff, batch_size)
        except Exception as exc:  # pragma: no cover - DB optional
            logger.warning("audit DB archival skipped: %s", exc)

        cutoff_iso = cutoff.isoformat()
        keep: List[Dict[str, Any]] = []
        for r in self._mem_logs:
            if r["created_at"] < cutoff_iso:
                r2 = dict(r)
                r2["archived_at"] = utc_now_iso()
                self._mem_archive.append(r2)
                moved += 1
            else:
                keep.append(r)
        self._mem_logs = keep
        if moved:
            logger.info(f"[AUDIT] archived {moved} records older than {days} days")
        return moved

    async def list_archived(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Query cold-archived audit logs (DB when ready, otherwise in-memory)."""
        try:
            from src.infrastructure.database.repository import db_repository
            if await db_repository.is_ready():
                rows = await db_repository.list_archived_audit_logs(limit=limit)
                if rows:
                    return [self._decode(r) for r in rows]
        except Exception:
            pass
        return [self._decode(r) for r in self._mem_archive[-limit:]]

    def _decode(self, row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row)
        out["detail"] = json.loads(decrypt_text(row.get("detail_encrypted", "")) or "{}")
        out.pop("detail_encrypted", None)
        return out


audit_service = AuditService()
