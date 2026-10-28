"""Declarative entity specifications for the user / auth domain.

Data only: this module tells the generic entity runtime which documents exist,
how they are keyed and which adapter performs storage. Every business flow lives
in ``config/scenarios/user.yaml`` / ``config/scenarios/auth.yaml``; calculations
live in :mod:`src.domains.user.functions`.

Storage boundaries
------------------
* ``user.account`` is **not** a snapshot family: maker accounts live in the
  canonical ``users`` SQL table. :class:`UserAccountAdapter` wraps the existing
  ``db_repository`` (hydrate on startup, best-effort write-behind on mutation)
  while the generic entity store keeps the in-process working set, exactly like
  the old ``UserService`` in-memory index did.
* Captcha challenges, verification codes and per-IP rate-limit windows are
  short-lived security state. They use :class:`EphemeralAdapter`: memory only,
  never written to ``domain_snapshots`` (credentials must not be persisted).
* Entitlement catalog rows and per-user grants are ordinary documents in
  ``user.entitlements`` / ``user.entitlement_grants``.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from typing import Any, Iterable, Optional

from src.core.entity import EntitySpec, entity_store

logger = logging.getLogger("opchub.user.entities")

ENTITY_USER_ACCOUNT = "user.account"
ENTITY_USER_CAPTCHA = "user.captcha"
ENTITY_USER_VERIFICATION_CODE = "user.verification_code"
ENTITY_USER_RATE_LIMIT = "user.rate_limit"
ENTITY_USER_ENTITLEMENT = "user.entitlement"
ENTITY_USER_ENTITLEMENT_GRANT = "user.entitlement_grant"


class EphemeralAdapter:
    """Memory-only entity adapter for short-lived security documents.

    Implements the same contract as :class:`~src.core.entity.store.SnapshotAdapter`
    but intentionally has no persistence hook: captcha answers, verification
    codes and rate-limit counters must never reach ``domain_snapshots``.
    """

    def __init__(self, spec: EntitySpec):
        self.spec = spec
        self._rows: dict[str, dict[str, Any]] = {}

    def hydrate(self, rows: Iterable[dict[str, Any]]) -> int:
        # Ephemeral entities are never hydrated from persistence.
        return 0

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows.values())

    def get(self, key: str) -> Optional[dict[str, Any]]:
        row = self._rows.get(key)
        return dict(row) if row else None

    def create(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        self._rows[key] = dict(doc)
        return dict(doc)

    def update(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        self._rows[key] = dict(doc)
        return dict(doc)

    def delete(self, key: str) -> bool:
        return self._rows.pop(key, None) is not None


class UserAccountAdapter:
    """Entity adapter over the canonical ``users`` SQL table.

    Read path: :meth:`hydrate_from_repository` projects persisted ``User`` rows
    into the entity working set on startup.
    Write path: mutations update the working set immediately and are mirrored to
    ``db_repository`` through a best-effort write-behind task once the adapter has
    been hydrated against a live database. Unit tests run without PostgreSQL
    (``db_repository.is_ready()`` is patched to ``False``), so they stay purely
    in-memory and deterministic.
    """

    def __init__(self, spec: EntitySpec):
        self.spec = spec
        self._rows: dict[str, dict[str, Any]] = {}
        self._persistent = False
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # Hydration / projection
    # ------------------------------------------------------------------
    @staticmethod
    def document_from_user(db_user: Any) -> dict[str, Any]:
        """Project a persisted ``User`` row into the entity document shape."""
        meta = getattr(db_user, "metadata_payload", None) or {}
        return {
            "uid": str(getattr(db_user, "uid", "") or ""),
            "email": str(getattr(db_user, "email", "") or "").strip().lower(),
            "nickname": str(getattr(db_user, "nickname", "") or ""),
            "role": str(getattr(db_user, "role", "") or "MAKER"),
            "company_name": str(getattr(db_user, "company_name", "") or ""),
            "phone": str(meta.get("phone", "") or ""),
            "credit_code": str(
                getattr(db_user, "unified_social_credit_code", None)
                or meta.get("credit_code", "")
                or ""
            ),
            "tier_name": str(meta.get("tier_name", "标准创客") or "标准创客"),
            "membership_tier": str(meta.get("membership_tier", "STANDARD") or "STANDARD"),
            "membership_expires_at": str(meta.get("membership_expires_at", "") or ""),
            "account_type": str(meta.get("account_type", "MAKER") or "MAKER"),
            "industry_track": str(meta.get("industry_track", "") or ""),
            "password_hash": str(getattr(db_user, "password_hash", "") or ""),
            "active_entitlements": list(meta.get("active_entitlements", []) or []),
            "entitlement_expiries": dict(meta.get("entitlement_expiries", {}) or {}),
            "must_change_password": bool(meta.get("must_change_password", False)),
            "avatar_id": str(meta.get("avatar_id", "") or ""),
            "agreement_consent": dict(meta.get("agreement_consent", {}) or {}),
            "agreement_version": str(
                (meta.get("agreement_consent") or {}).get("version", "") or ""
            ),
            "is_active": bool(getattr(db_user, "is_active", True)),
        }

    def hydrate(self, rows: Iterable[dict[str, Any]]) -> int:
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = self.spec.key_of(row)
            if not key:
                continue
            self._rows[key] = dict(row)
            count += 1
        return count

    async def hydrate_from_repository(self) -> int:
        """Load every persisted account into the working set."""
        from src.infrastructure.database.repository import db_repository

        try:
            ready = await db_repository.is_ready()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("User account repository probe failed: %s", exc)
            ready = False
        self._persistent = ready
        if not ready:
            return 0
        rows = await db_repository.list_users()
        return self.hydrate([self.document_from_user(row) for row in rows])

    # ------------------------------------------------------------------
    # EntityAdapter contract
    # ------------------------------------------------------------------
    def all(self) -> list[dict[str, Any]]:
        return list(self._rows.values())

    def get(self, key: str) -> Optional[dict[str, Any]]:
        row = self._rows.get(str(key))
        return dict(row) if row else None

    # -- legacy live views (compatibility shim only) --------------------
    def live(self, key: str) -> Optional[dict[str, Any]]:
        """Return the working-set document itself (mutations write through)."""
        return self._rows.get(str(key))

    def live_all(self) -> list[dict[str, Any]]:
        return list(self._rows.values())

    def create(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        self._rows[str(key)] = dict(doc)
        if self._persistent:
            self._schedule(self._persist_create(dict(doc)))
        return dict(doc)

    def update(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        self._rows[str(key)] = dict(doc)
        if self._persistent:
            self._schedule(self._persist_update(str(key), dict(doc)))
        return dict(doc)

    def delete(self, key: str) -> bool:
        existed = self._rows.pop(str(key), None) is not None
        if existed and self._persistent:
            self._schedule(self._persist_delete(str(key)))
        return existed

    # ------------------------------------------------------------------
    # Write-behind persistence (storage plumbing, no business logic)
    # ------------------------------------------------------------------
    def _schedule(self, coroutine: Any) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # pragma: no cover - no loop => memory-only
            return
        task = loop.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @staticmethod
    def _metadata_of(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "tier": doc.get("membership_tier", "STANDARD"),
            "tier_name": doc.get("tier_name", "标准创客"),
            "membership_tier": doc.get("membership_tier", "STANDARD"),
            "membership_expires_at": doc.get("membership_expires_at", ""),
            "account_type": doc.get("account_type", "MAKER"),
            "industry_track": doc.get("industry_track", ""),
            "phone": doc.get("phone", ""),
            "credit_code": doc.get("credit_code", ""),
            "avatar_id": doc.get("avatar_id", ""),
            "active_entitlements": sorted(doc.get("active_entitlements") or []),
            "entitlement_expiries": dict(doc.get("entitlement_expiries") or {}),
            "must_change_password": bool(doc.get("must_change_password", False)),
            "agreement_consent": dict(doc.get("agreement_consent") or {}),
        }

    async def _persist_create(self, doc: dict[str, Any]) -> None:
        from src.infrastructure.database.repository import db_repository

        try:
            await db_repository.create_user(
                email=str(doc.get("email") or ""),
                password_plain="",
                nickname=str(doc.get("nickname") or ""),
                company_name=str(doc.get("company_name") or ""),
                role=str(doc.get("role") or "MAKER"),
                credit_code=str(doc.get("credit_code") or "") or None,
                metadata=self._metadata_of(doc),
                uid=str(doc.get("uid") or "") or None,
                password_hash=str(doc.get("password_hash") or "") or None,
            )
        except Exception as exc:  # pragma: no cover - persistence is best effort
            logger.warning("User account persist failed for %s: %s", doc.get("uid"), exc)

    async def _persist_update(self, key: str, doc: dict[str, Any]) -> None:
        from src.infrastructure.database.repository import db_repository

        try:
            await db_repository.update_user_fields(
                key,
                nickname=str(doc.get("nickname") or ""),
                company_name=str(doc.get("company_name") or ""),
                password_hash=str(doc.get("password_hash") or "") or None,
                metadata_patch=self._metadata_of(doc),
            )
        except Exception as exc:  # pragma: no cover - persistence is best effort
            logger.warning("User account update failed for %s: %s", key, exc)

    async def _persist_delete(self, key: str) -> None:
        from src.infrastructure.database.repository import db_repository

        try:
            await db_repository.delete_user_by_uid(key)
        except Exception as exc:  # pragma: no cover - persistence is best effort
            logger.warning("User account delete failed for %s: %s", key, exc)


_ACCOUNT_SPEC = EntitySpec(
    name=ENTITY_USER_ACCOUNT,
    family="user.accounts",
    key_fields=("uid",),
    id_prefix="usr",
    search_fields=("email", "nickname", "uid"),
    owner_field="uid",
    default_order="-created_at",
    defaults={
        "email": "",
        "nickname": "",
        "role": "MAKER",
        "company_name": "",
        "phone": "",
        "credit_code": "",
        "tier_name": "标准创客",
        "membership_tier": "STANDARD",
        "membership_expires_at": "",
        "account_type": "MAKER",
        "industry_track": "",
        "password_hash": "",
        "active_entitlements": [],
        "entitlement_expiries": {},
        "must_change_password": False,
        "avatar_id": "",
        "agreement_consent": {},
        "agreement_version": "",
        "is_active": True,
    },
)

account_entity = replace(_ACCOUNT_SPEC, adapter=UserAccountAdapter(_ACCOUNT_SPEC))

captcha_entity = EntitySpec(
    name=ENTITY_USER_CAPTCHA,
    family="user.captchas",
    key_fields=("captcha_id",),
    id_prefix="cap",
    timestamps=False,
    defaults={"answer": "", "expires_at": 0.0, "used": False},
)

verification_code_entity = EntitySpec(
    name=ENTITY_USER_VERIFICATION_CODE,
    family="user.verification_codes",
    key_fields=("email",),
    id_prefix="vcode",
    timestamps=False,
    defaults={
        "code": "",
        "channel": "EMAIL",
        "created_at": 0.0,
        "expires_at": 0.0,
        "attempts": 0,
        "verified": False,
    },
)

rate_limit_entity = EntitySpec(
    name=ENTITY_USER_RATE_LIMIT,
    family="user.rate_limits",
    key_fields=("scope", "key"),
    id_prefix="rlim",
    timestamps=False,
    defaults={"count": 0, "window_start": 0.0},
)

entitlement_entity = EntitySpec(
    name=ENTITY_USER_ENTITLEMENT,
    family="user.entitlements",
    key_fields=("id",),
    id_prefix="ent",
    timestamps=False,
    search_fields=("name", "description"),
    default_order="id",
    defaults={
        "name": "",
        "tier": "STANDARD",
        "price_cny": 0.0,
        "description": "",
        "is_active": False,
        "quota_desc": "",
    },
)

entitlement_grant_entity = EntitySpec(
    name=ENTITY_USER_ENTITLEMENT_GRANT,
    family="user.entitlement_grants",
    key_fields=("user_id", "entitlement_id"),
    id_prefix="ugr",
    owner_field="user_id",
    default_order="-created_at",
    defaults={
        "status": "ACTIVE",
        "receipt_no": "",
        "expires_at": "",
        "activated_at": "",
    },
)

entity_store.register(account_entity)
entity_store.register(
    replace(captcha_entity, adapter=EphemeralAdapter(captcha_entity))
)
entity_store.register(
    replace(verification_code_entity, adapter=EphemeralAdapter(verification_code_entity))
)
entity_store.register(
    replace(rate_limit_entity, adapter=EphemeralAdapter(rate_limit_entity))
)
entity_store.register(entitlement_entity)
entity_store.register(entitlement_grant_entity)
