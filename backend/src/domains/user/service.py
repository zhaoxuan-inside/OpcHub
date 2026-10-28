"""Compatibility shim for the user / auth domain.

Business flow now lives in the declarative scenario assets
(``config/scenarios/auth.yaml`` / ``config/scenarios/user.yaml``), pure
calculations in :mod:`src.domains.user.functions` and documents in the generic
entity store (:mod:`src.domains.user.entities`).

This module deliberately contains **no registration / login / verification
flow**. It only keeps:

* the legacy data surface other modules still import (``_users_by_uid`` /
  ``_users_by_email`` live views, ``get_profile``, membership mirroring);
* thin compatibility methods that execute the scenarios (main.py, gateway
  adapters and older tests still call them).
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Iterator, MutableMapping
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.core.config import settings
from src.core.entity import entity_store
from src.core.security import hash_password, verify_session_token
from src.domains.user import entities as _entities  # noqa: F401 - registers EntitySpecs
from src.domains.user.compat import execute_scenario, execute_scenario_sync, raise_for_failure
from src.domains.user.entities import (
    ENTITY_USER_ACCOUNT,
    ENTITY_USER_ENTITLEMENT,
    ENTITY_USER_ENTITLEMENT_GRANT,
)
from src.domains.user.functions import (
    BUILTIN_AVATAR_IDS,
    FOUNDING_VIP_ENTITLEMENT_ID,
    FOUNDING_VIP_TIER_NAME,
    MEMBERSHIP_ENTITLEMENT_MAP,
    MEMBERSHIP_TIER_NAMES,
    STANDARD_TIER_NAME,
    profile as calc_profile,
)
from src.domains.user.models import (
    AuthSessionResponse,
    ChangePasswordRequest,
    EntitlementActivateRequest,
    EntitlementActivateResponse,
    MakerProfileResponse,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
)

_ENTITLEMENT_EXPIRY_FORMAT = "%Y-%m-%d %H:%M:%S"

CAPTCHA_PIPELINE = "OPC_AUTH_CAPTCHA_PIPELINE"
SEND_CODE_PIPELINE = "OPC_AUTH_SEND_CODE_PIPELINE"
VERIFY_CODE_PIPELINE = "OPC_AUTH_VERIFY_CODE_PIPELINE"
PASSWORD_STRENGTH_PIPELINE = "OPC_AUTH_PASSWORD_STRENGTH_PIPELINE"
LEGAL_AGREEMENTS_PIPELINE = "OPC_AUTH_LEGAL_AGREEMENTS_PIPELINE"
MAIL_PROVIDERS_PIPELINE = "OPC_AUTH_MAIL_PROVIDERS_PIPELINE"
REGISTER_PIPELINE = "OPC_AUTH_REGISTER_PIPELINE"
LOGIN_PIPELINE = "OPC_AUTH_LOGIN_PIPELINE"
CHANGE_PASSWORD_PIPELINE = "OPC_AUTH_CHANGE_PASSWORD_PIPELINE"
SESSION_PIPELINE = "OPC_AUTH_SESSION_PIPELINE"
PROFILE_PIPELINE = "OPC_USER_PROFILE_PIPELINE"
PROFILE_UPDATE_PIPELINE = "OPC_USER_PROFILE_UPDATE_PIPELINE"
ENTITLEMENT_ACTIVATE_PIPELINE = "OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE"


# ---------------------------------------------------------------------------
# Legacy in-memory index views backed by the shared entity store
# ---------------------------------------------------------------------------
def _legacy_record(doc: dict[str, Any]) -> Dict[str, Any]:
    """Project an entity document into the historical service record shape.

    The projection is applied **in place** so older callers that mutate the
    returned record (e.g. expiring a gift entitlement) still see the change on
    the next profile read.
    """
    record = doc
    record["active_entitlements"] = set(doc.get("active_entitlements") or [])
    record["entitlement_expiries"] = doc.get("entitlement_expiries") or {}
    record["agreement_consent"] = doc.get("agreement_consent") or {}
    return record


def _entity_doc(record: dict[str, Any]) -> dict[str, Any]:
    """Project a historical record back into an entity document."""
    doc = dict(record)
    active = doc.get("active_entitlements")
    if isinstance(active, (set, tuple)):
        doc["active_entitlements"] = sorted(str(v) for v in active)
    expiries = doc.get("entitlement_expiries")
    if expiries is None:
        doc["entitlement_expiries"] = {}
    return doc


class _UserIndexView(MutableMapping):
    """Live mapping over ``user.account`` entities (legacy service surface)."""

    def __init__(self, key_field: str):
        self._key_field = key_field

    def _docs(self) -> list[dict[str, Any]]:
        rows, _total = entity_store.list(ENTITY_USER_ACCOUNT, {"limit": 0, "order": "created_at"})
        return rows

    def _live(self, key: str) -> Optional[dict[str, Any]]:
        key = str(key)
        adapter = entity_store.adapter(ENTITY_USER_ACCOUNT)
        if self._key_field == "uid":
            live = getattr(adapter, "live", None)
            if live is not None:
                return live(key)
            return entity_store.get(ENTITY_USER_ACCOUNT, {"key": key})
        live_all = getattr(adapter, "live_all", None)
        rows = live_all() if live_all is not None else adapter.all()
        for row in rows:
            if str(row.get("email")) == key.lower():
                return row
        return None

    def __getitem__(self, key):
        doc = self._live(key)
        if doc is None:
            raise KeyError(key)
        return _legacy_record(doc)

    def __setitem__(self, key, value) -> None:
        doc = _entity_doc(value)
        doc.setdefault("uid", str(key) if self._key_field == "uid" else "")
        if not doc.get("uid"):
            doc["uid"] = f"usr_{uuid.uuid4().hex[:16]}"
        existing = entity_store.get(ENTITY_USER_ACCOUNT, {"key": doc["uid"]})
        if existing is None:
            entity_store.create(ENTITY_USER_ACCOUNT, doc)
        else:
            entity_store.update(ENTITY_USER_ACCOUNT, doc, partial=True)

    def __delitem__(self, key) -> None:
        doc = self._live(key)
        if doc is None:
            raise KeyError(key)
        entity_store.delete(ENTITY_USER_ACCOUNT, {"key": doc["uid"]})

    def __iter__(self) -> Iterator[str]:
        for row in self._docs():
            yield str(row.get(self._key_field) or "")

    def __len__(self) -> int:
        return len(self._docs())

    def clear(self) -> None:
        adapter = entity_store.adapter(ENTITY_USER_ACCOUNT)
        for row in list(adapter.all()):
            uid = str(row.get("uid") or "")
            if uid:
                adapter.delete(uid)


# ---------------------------------------------------------------------------
# Service shim
# ---------------------------------------------------------------------------
class UserService:
    """Keeps the legacy data/query surface; flows are scenarios."""

    def __init__(self):
        self._users_by_uid = _UserIndexView("uid")
        self._users_by_email = _UserIndexView("email")
        self._active_entitlements: Set[str] = set()
        self.require_email_code: bool = False
        self._seed_default_entitlements()
        self._ensure_builtin_admin()

    # ------------------------------------------------------------------
    # Seeding / hydration (data only)
    # ------------------------------------------------------------------
    def _ensure_builtin_admin(self) -> None:
        """Idempotently provision the built-in administrator account document."""
        admin_uid = "usr_admin_builtin"
        if entity_store.get(ENTITY_USER_ACCOUNT, {"key": admin_uid}) is not None:
            return
        entity_store.create(
            ENTITY_USER_ACCOUNT,
            {
                "uid": admin_uid,
                "email": settings.admin_email.strip().lower(),
                "nickname": settings.admin_nickname,
                "role": "ADMIN",
                "company_name": "OpcHub 平台运营",
                "phone": "",
                "credit_code": "",
                "tier_name": "平台管理员",
                "password_hash": hash_password(settings.admin_initial_password),
                "active_entitlements": [],
                "entitlement_expiries": {},
                "must_change_password": True,
            },
        )

    def _seed_default_entitlements(self) -> None:
        """Load the entitlement catalog from external seed data (data only)."""
        search_paths = [
            Path("backend/data/seeds/entitlements.json"),
            Path("data/seeds/entitlements.json"),
            Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "entitlements.json",
        ]
        items: List[Dict[str, Any]] = []
        for path in search_paths:
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        items = json.load(handle)
                    break
                except Exception:  # pragma: no cover - defensive
                    items = []
        for raw in items:
            ent_id = str(raw.get("id") or "").strip()
            if not ent_id:
                continue
            doc = {
                "id": ent_id,
                "name": raw.get("name", ""),
                "tier": raw.get("tier", "STANDARD"),
                "price_cny": float(raw.get("price_cny", 0.0)),
                "description": raw.get("description", ""),
                "is_active": False,
                "quota_desc": raw.get("quota_desc", ""),
            }
            if entity_store.get(ENTITY_USER_ENTITLEMENT, {"key": ent_id}) is None:
                entity_store.create(ENTITY_USER_ENTITLEMENT, doc)

    async def hydrate_from_db(self) -> int:
        """Rebuild the account working set from the canonical ``users`` table."""
        adapter = entity_store.adapter(ENTITY_USER_ACCOUNT)
        hydrate = getattr(adapter, "hydrate_from_repository", None)
        if hydrate is None:
            return 0
        count = await hydrate()
        self._ensure_builtin_admin()
        return count

    async def _next_registration_ordinal(self) -> int:
        count = await self._maker_count()
        return count + 1

    async def _maker_count(self) -> int:
        rows, _total = entity_store.list(
            ENTITY_USER_ACCOUNT,
            {"filters": {"role": {"ne": "ADMIN"}}, "limit": 0},
        )
        return len(rows)

    # ------------------------------------------------------------------
    # Compatibility surface delegated to scenario assets
    # ------------------------------------------------------------------
    def generate_captcha(self) -> Dict[str, Any]:
        result = execute_scenario_sync(CAPTCHA_PIPELINE)
        return raise_for_failure(result).get("response", {})

    def send_verification_code(
        self,
        email: str,
        captcha_id: Optional[str] = None,
        captcha_code: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = execute_scenario_sync(
            SEND_CODE_PIPELINE,
            {
                "email": email,
                "captcha_id": captcha_id,
                "captcha_code": captcha_code,
                "client_ip": client_ip,
            },
        )
        return raise_for_failure(result).get("response", {})

    def verify_email_code(self, email: str, code: str) -> bool:
        result = execute_scenario_sync(VERIFY_CODE_PIPELINE, {"email": email, "code": code})
        try:
            raise_for_failure(result)
        except ValueError as exc:
            if "连续错误次数超限" in str(exc):
                raise
            return False
        return True

    def evaluate_password_strength(self, password: str, email: Optional[str] = None) -> Dict[str, Any]:
        result = execute_scenario_sync(
            PASSWORD_STRENGTH_PIPELINE, {"password": password, "email": email}
        )
        return raise_for_failure(result).get("response", {})

    def get_legal_agreements(self) -> Dict[str, Any]:
        result = execute_scenario_sync(LEGAL_AGREEMENTS_PIPELINE)
        return raise_for_failure(result).get("response", {})

    def get_supported_mail_providers(self) -> List[Dict[str, Any]]:
        result = execute_scenario_sync(MAIL_PROVIDERS_PIPELINE)
        return raise_for_failure(result).get("response", [])

    def resolve_mail_provider(self, email: str) -> Dict[str, Any]:
        result = execute_scenario_sync(MAIL_PROVIDERS_PIPELINE, {"email": email})
        return raise_for_failure(result).get("response", {})

    async def register_by_email(self, req: UserRegisterRequest) -> AuthSessionResponse:
        payload = req.model_dump()
        result = await execute_scenario(REGISTER_PIPELINE, payload)
        output = raise_for_failure(result)
        response = output.get("response") or {}
        return AuthSessionResponse(**response)

    async def login_by_email(self, req: UserLoginRequest) -> AuthSessionResponse:
        payload = req.model_dump()
        result = await execute_scenario(LOGIN_PIPELINE, payload)
        output = raise_for_failure(result)
        response = output.get("response") or {}
        return AuthSessionResponse(**response)

    login_user = login_by_email

    async def get_session_by_token(self, token: str) -> Optional[AuthSessionResponse]:
        result = await execute_scenario(SESSION_PIPELINE, {"token": token})
        try:
            output = raise_for_failure(result)
        except (ValueError, PermissionError):
            return None
        response = output.get("response") or {}
        if not response:
            return None
        return AuthSessionResponse(
            token=response.get("token", token),
            uid=response.get("uid", ""),
            email=response.get("email", ""),
            nickname=response.get("nickname", "创客"),
            role=response.get("role", "MAKER"),
            tier_name=response.get("tier_name", STANDARD_TIER_NAME),
            message="会话有效",
        )

    async def update_profile(
        self,
        req: UserProfileUpdateRequest,
        token: Optional[str] = None,
    ) -> MakerProfileResponse:
        uid = req.user_id
        if token:
            payload = verify_session_token(token)
            if payload and payload.get("uid"):
                uid = payload.get("uid")
        if not uid or uid == "usr_guest":
            raise ValueError("无法为未登录访客更新档案，请先登录")
        inputs = req.model_dump()
        inputs["token"] = token or ""
        result = await execute_scenario(
            PROFILE_UPDATE_PIPELINE,
            inputs,
            {"user_id": uid, "user_role": "MAKER", "token": token or ""},
        )
        output = raise_for_failure(result)
        return MakerProfileResponse(**output.get("profile", {}))

    async def activate_entitlement(
        self,
        req: EntitlementActivateRequest,
    ) -> EntitlementActivateResponse:
        result = await execute_scenario(
            ENTITLEMENT_ACTIVATE_PIPELINE,
            req.model_dump(),
            {"user_id": req.user_id, "user_role": "MAKER"},
        )
        output = raise_for_failure(result)
        return EntitlementActivateResponse(**output.get("activation", {}))

    async def change_password(self, req: ChangePasswordRequest) -> AuthSessionResponse:
        uid = req.user_id
        if req.token:
            payload = verify_session_token(req.token)
            if payload and payload.get("uid"):
                uid = payload.get("uid")
        if not uid or uid == "usr_guest":
            raise ValueError("无法为未登录访客修改密码，请先登录")
        result = await execute_scenario(
            CHANGE_PASSWORD_PIPELINE,
            {"old_password": req.old_password, "new_password": req.new_password, "token": req.token or ""},
            {"user_id": uid, "user_role": "MAKER", "token": req.token or ""},
        )
        output = raise_for_failure(result)
        return AuthSessionResponse(**output.get("response", {}))

    # ------------------------------------------------------------------
    # Data / query compatibility surface
    # ------------------------------------------------------------------
    def get_profile(self, uid: Optional[str] = None) -> MakerProfileResponse:
        """Fetch a maker profile from the entity store (guest profile when absent)."""
        catalog, _total = entity_store.list(ENTITY_USER_ENTITLEMENT, {"limit": 0, "order": "id"})
        grants: list[dict[str, Any]] = []
        user_doc: Optional[dict[str, Any]] = None
        if uid and uid != "usr_guest":
            user_doc = entity_store.get(ENTITY_USER_ACCOUNT, {"key": uid})
            grants, _grant_total = entity_store.list(
                ENTITY_USER_ENTITLEMENT_GRANT,
                {"filters": {"user_id": uid}, "limit": 0},
            )
        profile_doc = calc_profile(
            {},
            {
                "uid": uid or "usr_guest",
                "user": user_doc,
                "catalog": catalog,
                "grants": grants,
            },
            {},
        )
        profile_doc.pop("orchestrated_by", None)
        return MakerProfileResponse(**profile_doc)

    async def sync_membership(self, uid: str, tier: str, expires_at: str) -> None:
        """Mirror a loyalty membership grant onto the legacy profile fields."""
        doc = entity_store.get(ENTITY_USER_ACCOUNT, {"key": str(uid)})
        if not doc:
            return
        tier = str(tier or "STANDARD").upper()
        if tier not in MEMBERSHIP_ENTITLEMENT_MAP:
            tier = "STANDARD"
        owned = {"ent_ai_tax_assistant", "ent_black_diamond_priority"}
        active = set(doc.get("active_entitlements") or [])
        expiries = dict(doc.get("entitlement_expiries") or {})
        for ent_id in owned:
            active.discard(ent_id)
            expiries.pop(ent_id, None)
            entity_store.delete(
                ENTITY_USER_ENTITLEMENT_GRANT,
                {"user_id": str(uid), "entitlement_id": ent_id, "key": f"{uid}::{ent_id}"},
            )
        for ent_id in MEMBERSHIP_ENTITLEMENT_MAP.get(tier, set()):
            active.add(ent_id)
            expiries[ent_id] = expires_at
            entity_store.upsert(
                ENTITY_USER_ENTITLEMENT_GRANT,
                {
                    "user_id": str(uid),
                    "entitlement_id": ent_id,
                    "status": "ACTIVE",
                    "receipt_no": "",
                    "expires_at": expires_at,
                    "activated_at": datetime.now().strftime(_ENTITLEMENT_EXPIRY_FORMAT),
                },
            )
        entity_store.update(
            ENTITY_USER_ACCOUNT,
            {
                "uid": str(uid),
                "tier_name": MEMBERSHIP_TIER_NAMES.get(tier, STANDARD_TIER_NAME),
                "membership_tier": tier,
                "membership_expires_at": expires_at,
                "active_entitlements": sorted(active),
                "entitlement_expiries": expiries,
            },
            partial=True,
        )

    async def deactivate_entitlement(
        self,
        entitlement_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        ent_id = entitlement_id
        if ent_id not in self._active_entitlements and ent_id == "ENT_VIP":
            ent_id = FOUNDING_VIP_ENTITLEMENT_ID
        removed = ent_id in self._active_entitlements
        self._active_entitlements.discard(ent_id)

        targets = [user_id] if user_id else [str(row.get("uid")) for row in entity_store.adapter(ENTITY_USER_ACCOUNT).all()]
        for uid in targets:
            doc = entity_store.get(ENTITY_USER_ACCOUNT, {"key": uid})
            if not doc:
                continue
            active = set(doc.get("active_entitlements") or [])
            expiries = dict(doc.get("entitlement_expiries") or {})
            if ent_id in active:
                active.discard(ent_id)
                expiries.pop(ent_id, None)
                removed = True
            tier_name = doc.get("tier_name") or STANDARD_TIER_NAME
            if ent_id == FOUNDING_VIP_ENTITLEMENT_ID and tier_name == FOUNDING_VIP_TIER_NAME:
                tier_name = STANDARD_TIER_NAME
            entity_store.update(
                ENTITY_USER_ACCOUNT,
                {
                    "uid": uid,
                    "active_entitlements": sorted(active),
                    "entitlement_expiries": expiries,
                    "tier_name": tier_name,
                },
                partial=True,
            )
            entity_store.delete(
                ENTITY_USER_ENTITLEMENT_GRANT,
                {"user_id": uid, "entitlement_id": ent_id, "key": f"{uid}::{ent_id}"},
            )
        return removed

    # ------------------------------------------------------------------
    # Legacy read-side helpers (kept for older callers)
    # ------------------------------------------------------------------
    @classmethod
    def _record_from_db_user(cls, db_user: Any) -> Dict[str, Any]:
        from src.domains.user.entities import UserAccountAdapter

        return _legacy_record(UserAccountAdapter.document_from_user(db_user))

    @staticmethod
    def _entitlement_window_elapsed(expiries: Dict[str, Any], ent_id: str) -> bool:
        raw = (expiries or {}).get(ent_id, "")
        if not raw:
            return False
        try:
            return datetime.strptime(str(raw), _ENTITLEMENT_EXPIRY_FORMAT) < datetime.now()
        except ValueError:
            return False

    @classmethod
    def _prune_expired_entitlements(cls, record: Dict[str, Any]) -> None:
        expiries = record.get("entitlement_expiries") or {}
        if not expiries:
            return
        active = record.get("active_entitlements") or set()
        for ent_id in [k for k in expiries if cls._entitlement_window_elapsed(expiries, k)]:
            active.discard(ent_id)
            expiries.pop(ent_id, None)
        if FOUNDING_VIP_ENTITLEMENT_ID not in active and record.get("tier_name") == FOUNDING_VIP_TIER_NAME:
            record["tier_name"] = STANDARD_TIER_NAME
        membership_tier = str(record.get("membership_tier") or "").upper()
        if membership_tier == "PRO" and "ent_ai_tax_assistant" not in active:
            if record.get("tier_name") == MEMBERSHIP_TIER_NAMES["PRO"]:
                record["tier_name"] = STANDARD_TIER_NAME
        elif membership_tier == "BLACK_DIAMOND" and FOUNDING_VIP_ENTITLEMENT_ID not in active:
            if record.get("tier_name") == MEMBERSHIP_TIER_NAMES["BLACK_DIAMOND"]:
                record["tier_name"] = STANDARD_TIER_NAME

    def validate_email(self, email: str) -> bool:
        import re

        return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", (email or "").strip()))


user_service = UserService()

__all__ = [
    "BUILTIN_AVATAR_IDS",
    "FOUNDING_VIP_ENTITLEMENT_ID",
    "FOUNDING_VIP_TIER_NAME",
    "MEMBERSHIP_ENTITLEMENT_MAP",
    "MEMBERSHIP_TIER_NAMES",
    "UserService",
    "user_service",
]
