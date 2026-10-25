"""Exclusive edit locks for orchestration catalog assets (算子 / 子图 / 场景).

展示（读取）永远开放；所有变更操作（创建 / 删除 / 版本编辑 / 发布）必须先由
操作者持有目标资产的排他锁，避免多人同时编排造成业务异常。锁带 TTL 与心跳
续期：持有者失联后锁自动过期，其他协作者可以接管。
"""
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from src.infrastructure.database.persistence import domain_persistence

ENTITY_TYPES = ("operator", "subgraph", "scenario")
DEFAULT_TTL_SECONDS = 900  # 15 分钟无心跳自动过期
PERSISTENCE_DOMAIN = "orchestration.locks"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class AssetLock(BaseModel):
    """One held exclusive lock over a catalog asset."""
    entity_type: str
    entity_key: str
    holder_id: str
    holder_name: str
    acquired_at: str
    expires_at: str
    ttl_seconds: int = DEFAULT_TTL_SECONDS


class LockConflictError(PermissionError):
    """Raised when an asset is locked by someone else (message prefix is machine-checked)."""

    def __init__(self, lock: AssetLock, remaining_seconds: int):
        self.lock = lock
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"LOCKED:{lock.entity_type}:{lock.entity_key}:{lock.holder_name}"
            f"({lock.holder_id}):{remaining_seconds}"
        )


def conflict_message(exc: LockConflictError) -> str:
    """Human-readable Chinese message shown to the blocked operator."""
    mins, secs = divmod(max(exc.remaining_seconds, 0), 60)
    return (
        f"「{exc.lock.entity_key}」正被 {exc.lock.holder_name}（{exc.lock.holder_id}）"
        f"锁定编辑中，预计 {mins} 分 {secs} 秒后未续期自动释放；请等待对方完成或联系其释放锁"
    )


def humanize_lock_error(message: str) -> Optional[str]:
    """Parse an engine-flattened lock error message back into a Chinese hint.

    The DAG engine flattens node exceptions into plain strings, so the structured
    ``LOCKED:`` prefix is the only survivor. Returns None when the message is not
    a lock-related error.
    """
    if "LOCKED:" in message:
        segment = message.split("LOCKED:", 1)[1]
        head, _, tail = segment.rpartition(":")
        entity_type, _, rest = head.partition(":")
        entity_key, _, holder = rest.partition(":")
        holder_name = holder.split("(")[0] or holder or "其他协作者"
        try:
            remaining = int(tail)
            mins, secs = divmod(max(remaining, 0), 60)
            time_hint = f"预计 {mins} 分 {secs} 秒后未续期自动释放"
        except ValueError:
            time_hint = "等待其续期超时后自动释放"
        return (
            f"「{entity_key or '该资产'}」正被 {holder_name} 锁定编辑中，{time_hint}；"
            f"请等待对方完成或由管理员强制释放锁"
        )
    if "UNLOCKED:" in message:
        return "该资产当前未由您持有排他锁：请先在编辑面板点击「锁定并编辑」，获取锁后再执行变更"
    if "UNAUTHORIZED:" in message:
        return "目录变更操作需要登录后的编排权限"
    return None


class LockManager:
    """In-memory exclusive lock registry mirrored into domain persistence."""

    def __init__(self):
        self._locks: Dict[Tuple[str, str], AssetLock] = {}
        self._guard = threading.Lock()

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    @staticmethod
    def _is_expired(lock: AssetLock, now: Optional[datetime] = None) -> bool:
        try:
            return parse_iso(lock.expires_at) <= (now or utc_now())
        except ValueError:
            return True

    def _drop_expired(self) -> None:
        now = utc_now()
        for key in [k for k, v in self._locks.items() if self._is_expired(v, now)]:
            del self._locks[key]
            domain_persistence.delete(PERSISTENCE_DOMAIN, f"{key[0]}@@{key[1]}")

    @staticmethod
    def _doc_id(entity_type: str, entity_key: str) -> str:
        return f"{entity_type}@@{entity_key}"

    # ------------------------------------------------------------------
    # operations
    # ------------------------------------------------------------------
    def acquire(
        self,
        entity_type: str,
        entity_key: str,
        holder_id: str,
        holder_name: str = "",
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> AssetLock:
        """Acquire (or idempotently renew) the exclusive lock for one asset."""
        if entity_type not in ENTITY_TYPES:
            raise ValueError(f"未知的资产类型：{entity_type}")
        if not entity_key or not holder_id:
            raise ValueError("entity_key 与 holder_id 不能为空")

        with self._guard:
            self._drop_expired()
            key = (entity_type, entity_key)
            existing = self._locks.get(key)
            if existing and existing.holder_id != holder_id:
                remaining = int((parse_iso(existing.expires_at) - utc_now()).total_seconds())
                raise LockConflictError(existing, remaining)

            now = utc_now()
            lock = AssetLock(
                entity_type=entity_type,
                entity_key=entity_key,
                holder_id=holder_id,
                holder_name=holder_name or holder_id,
                acquired_at=(existing.acquired_at if existing and existing.holder_id == holder_id else now.isoformat()),
                expires_at=(now + timedelta(seconds=max(ttl_seconds, 30))).isoformat(),
                ttl_seconds=max(ttl_seconds, 30),
            )
            self._locks[key] = lock
            domain_persistence.write(PERSISTENCE_DOMAIN, self._doc_id(entity_type, entity_key), lock)
            return lock

    def release(self, entity_type: str, entity_key: str, holder_id: str, force: bool = False) -> bool:
        """Release a lock. The holder always may release; others need force (ADMIN)."""
        with self._guard:
            self._drop_expired()
            key = (entity_type, entity_key)
            lock = self._locks.get(key)
            if not lock:
                return False
            if lock.holder_id != holder_id and not force:
                remaining = int((parse_iso(lock.expires_at) - utc_now()).total_seconds())
                raise LockConflictError(lock, remaining)
            del self._locks[key]
            domain_persistence.delete(PERSISTENCE_DOMAIN, self._doc_id(entity_type, entity_key))
            return True

    def require(self, entity_type: str, entity_key: str, holder_id: str) -> AssetLock:
        """Assert the caller holds a live lock; raise LockConflictError otherwise."""
        with self._guard:
            self._drop_expired()
            lock = self._locks.get((entity_type, entity_key))
            if not lock:
                raise PermissionError(
                    f"UNLOCKED:{entity_type}:{entity_key}:操作前需先在编辑面板获取该资产的排他锁"
                )
            if lock.holder_id != holder_id:
                remaining = int((parse_iso(lock.expires_at) - utc_now()).total_seconds())
                raise LockConflictError(lock, remaining)
            return lock

    def status(self, entity_type: str, entity_key: str) -> Optional[AssetLock]:
        with self._guard:
            self._drop_expired()
            return self._locks.get((entity_type, entity_key))

    def list_active(self) -> List[AssetLock]:
        with self._guard:
            self._drop_expired()
            return list(self._locks.values())

    def hydrate(self, rows: List[Dict]) -> int:
        count = 0
        for r in rows or []:
            try:
                lock = AssetLock(**r)
            except Exception:
                continue
            self._locks[(lock.entity_type, lock.entity_key)] = lock
            count += 1
        return count


lock_manager = LockManager()

domain_persistence.register(PERSISTENCE_DOMAIN, lock_manager.hydrate)
