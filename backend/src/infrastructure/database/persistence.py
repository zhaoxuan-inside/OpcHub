"""Write-behind domain persistence with startup hydration.

The domain services keep synchronous in-memory indexes as their primary runtime read
path (fast, lock-free). This module mirrors every mutation into PostgreSQL as a JSONB
document (``domain_snapshots``) and rebuilds those indexes verbatim on startup, so the
platform's working state survives process restarts without forcing every service method
to become ``async``.

Semantics
---------
* ``enabled`` is decided once at startup from a live ``is_ready()`` probe. When no
  database is reachable the whole layer degrades to a no-op (in-memory only) — matching
  the platform's graceful-fallback contract and keeping the test suite hermetic.
* Writes are *write-behind*: they are scheduled onto the running event loop and never
  block the synchronous caller. ``flush()`` awaits outstanding writes (shutdown/tests).
* Reads are never served from this layer; hydration populates the service indexes once
  at startup and the services remain the single source of truth at runtime.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Set

from src.infrastructure.database.repository import db_repository

logger = logging.getLogger("opchub.persistence")

Hydrator = Callable[[List[Dict[str, Any]]], int]


class PersistenceUnavailableError(RuntimeError):
    """Raised when a domain mutation requires a live database but none is available."""


def snapshot(entity: Any) -> Dict[str, Any]:
    """Serialize a pydantic domain entity into a JSON-safe document."""
    if hasattr(entity, "model_dump"):
        return entity.model_dump(mode="json")
    if isinstance(entity, dict):
        return dict(entity)
    raise TypeError(f"Cannot snapshot entity of type {type(entity)!r}")


class DomainPersistence:
    """Registry of domain document families with write-behind + hydration."""

    def __init__(self) -> None:
        self.enabled: bool = False
        # Strict mode refuses domain mutations when PostgreSQL is unavailable instead
        # of silently accepting memory-only state. Tests opt out via ``strict = False``.
        self.strict: bool = True
        self._hydrators: Dict[str, Hydrator] = {}
        self._tasks: Set["asyncio.Task[Any]"] = set()
        self._tail: "asyncio.Task[Any] | None" = None

    def require(self, domain: str) -> None:
        """Fail fast when a DB-backed domain receives a mutation without a database."""
        if self.strict and not self.enabled:
            raise PersistenceUnavailableError(
                f"Database persistence is unavailable; refusing to mutate domain '{domain}' in memory only."
            )

    # -- registration ------------------------------------------------------
    def register(self, domain: str, hydrator: Hydrator) -> None:
        """Register a domain document family with its index-rebuild callable."""
        self._hydrators[domain] = hydrator

    @property
    def domains(self) -> List[str]:
        return list(self._hydrators)

    # -- startup / shutdown ------------------------------------------------
    async def initialize(self) -> Dict[str, int]:
        """Probe the database and hydrate every registered domain index."""
        try:
            self.enabled = await db_repository.is_ready()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Domain persistence probe failed: %s", exc)
            self.enabled = False

        counts: Dict[str, int] = {}
        if not self.enabled:
            logger.info("Domain persistence disabled (no live database); running in-memory only.")
            return counts

        for domain, hydrator in self._hydrators.items():
            rows = await db_repository.load_domain_snapshots(domain)
            counts[domain] = hydrator(rows) if rows else 0
        logger.info("Domain persistence hydrated from PostgreSQL: %s", counts)
        return counts

    async def flush(self) -> None:
        """Await all outstanding write-behind tasks (graceful shutdown / tests)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    # -- write path --------------------------------------------------------
    def write(self, domain: str, entity_id: str, entity: Any) -> None:
        """Persist a domain entity (pydantic model or mapping) write-behind."""
        if not self.enabled:
            return
        self._schedule(
            db_repository.upsert_domain_snapshot(domain, str(entity_id), snapshot(entity))
        )

    def write_raw(self, domain: str, entity_id: str, payload: Dict[str, Any]) -> None:
        """Persist a raw JSON document (for composite / relational join rows)."""
        if not self.enabled:
            return
        self._schedule(
            db_repository.upsert_domain_snapshot(domain, str(entity_id), dict(payload))
        )

    def delete(self, domain: str, entity_id: str) -> None:
        """Remove a persisted domain document write-behind."""
        if not self.enabled:
            return
        self._schedule(db_repository.delete_domain_snapshot(domain, str(entity_id)))

    # -- internals ---------------------------------------------------------
    def _schedule(self, coro: Any) -> None:
        """Schedule a write-behind coroutine, strictly ordered behind earlier writes.

        Ordering matters: the same aggregate is often rewritten within one request
        (e.g. a thread's view/comment count). Chaining each task behind the previous one
        guarantees PostgreSQL observes mutations in the order they happened.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop (import-time seeding / synchronous unit tests): drop.
            coro.close()
            return

        previous = self._tail

        async def _ordered() -> None:
            if previous is not None:
                try:
                    await previous
                except Exception:  # pragma: no cover - predecessor failure already logged
                    pass
            await coro

        task = loop.create_task(_ordered())
        self._tail = task
        self._tasks.add(task)
        task.add_done_callback(self._on_done)

    def _on_done(self, task: "asyncio.Task[Any]") -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:  # pragma: no cover - DB failure is non-fatal
            logger.warning("Domain persistence write failed: %s", exc)


domain_persistence = DomainPersistence()
