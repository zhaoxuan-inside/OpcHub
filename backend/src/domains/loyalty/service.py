"""Compatibility shim for the loyalty (晨光积分 / 会员 / 兑换) domain.

All business flows live in ``config/scenarios/loyalty.yaml`` and execute on the
operator kernel. Pure calculations (settlement, revocation, redemption,
membership transitions, level mapping) live in
``src.domains.loyalty.functions``; documents live in the generic entity store
(``src.domains.loyalty.entities``).

This module therefore only keeps the legacy **data / query** surface that other
modules still import:

* ``hydrate_*`` / ``clear`` – startup hydration and test isolation;
* ``get_account`` / ``list_ledger`` / ``list_rules`` / ``list_plans`` /
  ``get_membership`` / ``list_items`` / ``list_orders`` – read projections over
  the entity store, assembled with the very same pure functions the scenarios use.

Three methods remain *legacy gateway bridges* because
``core/gateway/adapters.py`` still calls them directly: ``set_auto_renew``,
``admin_adjust`` and ``resolve_target_author/title``. They contain no business
rules; they only compose the domain pure functions with generic store reads /
writes, and can be deleted once ``config/gateway_routes.yaml`` is regenerated
from ``config/routes/loyalty.yaml``.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator, MutableMapping
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.entity import entity_store
from src.domains.loyalty import entities as _entities
from src.domains.loyalty.models import (
    MembershipInfo,
    MembershipPlan,
    PointsAccount,
    PointsLedgerEntry,
    PointsLedgerResponse,
    PointsRule,
    PointsRulesResponse,
    RedemptionOrder,
    RedemptionOrdersResponse,
    RewardItem,
)
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.loyalty")

ACCOUNTS_DOMAIN = "loyalty.accounts"
LEDGER_DOMAIN = "loyalty.ledger"
MEMBERSHIPS_DOMAIN = "loyalty.memberships"
ORDERS_DOMAIN = "loyalty.orders"
ITEMS_DOMAIN = "loyalty.items"
LEGACY_ITEMS_DOMAIN = "loyalty.reward_items"

ENTITY_ACCOUNT = _entities.ENTITY_ACCOUNT
ENTITY_LEDGER = _entities.ENTITY_LEDGER
ENTITY_MEMBERSHIP = _entities.ENTITY_MEMBERSHIP
ENTITY_ORDER = _entities.ENTITY_ORDER
ENTITY_ITEM = _entities.ENTITY_ITEM


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _functions():
    """Lazily import the pure operators (avoids a core<->domain import cycle)."""
    from src.domains.loyalty import functions

    return functions


def _pretty(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


class _EntityMap(MutableMapping[str, Any]):
    """Mutable mapping view over one entity family (legacy ``_accounts`` / ``_ledger``...)."""

    def __init__(self, entity: str, key_field: str):
        self._entity = entity
        self._key_field = key_field

    def _spec(self):
        return entity_store.spec(self._entity)

    def _row(self, key: Any) -> Optional[Dict[str, Any]]:
        return entity_store.get(self._entity, {"key": str(key)})

    def __getitem__(self, key: str) -> Any:
        row = self._row(key)
        if row is None:
            raise KeyError(key)
        return row

    def __setitem__(self, key: str, value: Any) -> None:
        doc = _pretty(value)
        doc[self._key_field] = doc.get(self._key_field) or str(key)
        if self._row(str(key)) is None:
            entity_store.create(self._entity, doc)
        else:
            entity_store.update(self._entity, doc, partial=True)

    def __delitem__(self, key: str) -> None:
        if not entity_store.delete(self._entity, {"key": str(key)}):
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        for row in entity_store.adapter(self._entity).all():
            if row.get(self._key_field):
                yield str(row[self._key_field])

    def __len__(self) -> int:
        return len(entity_store.adapter(self._entity).all())

    def clear(self) -> None:
        spec = self._spec()
        adapter = entity_store.adapter(self._entity)
        for row in list(adapter.all()):
            adapter.delete(spec.key_of(row))


class _AccountHandle(dict):
    """Legacy ``_ensure_account`` handle: attribute-like mutation writes through."""

    def __init__(self, uid: str, row: Dict[str, Any]):
        super().__init__(row)
        self._uid = str(uid)

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        if self._uid:
            payload = {**dict(self), "uid": self._uid}
            if entity_store.get(ENTITY_ACCOUNT, {"key": self._uid}) is None:
                entity_store.create(ENTITY_ACCOUNT, payload)
            else:
                entity_store.update(ENTITY_ACCOUNT, payload, partial=False)

    def update(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        super().update(*args, **kwargs)
        if self._uid:
            payload = {**dict(self), "uid": self._uid}
            if entity_store.get(ENTITY_ACCOUNT, {"key": self._uid}) is None:
                entity_store.create(ENTITY_ACCOUNT, payload)
            else:
                entity_store.update(ENTITY_ACCOUNT, payload, partial=False)


def _account_defaults(uid: str) -> Dict[str, Any]:
    return {
        "uid": str(uid),
        "balance": 0,
        "frozen": 0,
        "debt": 0,
        "total_earned": 0,
        "total_spent": 0,
        "growth": 0,
        "reputation": 80,
        "updated_at": utc_now_iso(),
    }


class LoyaltyService:
    """Legacy read / data surface over the generic loyalty entity store."""

    def __init__(self) -> None:
        # Retained only so old test fixtures can call ``.clear()``; idempotency and
        # cap accounting are derived from the append-only ledger entity family.
        self._idempotency: Dict[str, str] = {}
        self._order_keys: Dict[str, str] = {}
        self._daily: Dict[Any, int] = {}
        self._daily_total: Dict[Any, int] = {}
        self._monthly_total: Dict[Any, int] = {}
        self._target_daily: Dict[Any, int] = {}
        self._pair_daily: Dict[Any, int] = {}

    # ------------------------------------------------------------------
    # Legacy collection views
    # ------------------------------------------------------------------
    @property
    def _accounts(self) -> MutableMapping[str, Any]:
        return _EntityMap(ENTITY_ACCOUNT, "uid")

    @property
    def _ledger(self) -> MutableMapping[str, Any]:
        return _EntityMap(ENTITY_LEDGER, "id")

    @property
    def _memberships(self) -> MutableMapping[str, Any]:
        return _EntityMap(ENTITY_MEMBERSHIP, "uid")

    @property
    def _orders(self) -> MutableMapping[str, Any]:
        return _EntityMap(ENTITY_ORDER, "id")

    # ------------------------------------------------------------------
    # Catalogue / runtime preparation (data only)
    # ------------------------------------------------------------------
    def ensure_catalog(self) -> int:
        """Seed the static reward catalogue into ``loyalty.item`` (idempotent)."""
        created = 0
        for item in _functions().REWARD_ITEMS:
            if entity_store.get(ENTITY_ITEM, {"key": item["code"]}) is None:
                entity_store.create(ENTITY_ITEM, dict(item))
                created += 1
        return created

    def sync_legacy_memberships(self) -> int:
        """Project legacy founding-VIP / entitlement grants into membership entities.

        The loyalty membership record stays authoritative once it exists; this
        only mirrors grants that were issued by other flows (e.g. the founding
        maker black diamond gift) so scenario nodes can see them without a
        cross-domain import.
        """
        created = 0
        try:
            from src.domains.user.service import user_service
        except Exception:  # pragma: no cover - user domain always present
            return 0
        for uid in list(user_service._users_by_uid.keys()):
            if entity_store.get(ENTITY_MEMBERSHIP, {"key": str(uid)}) is not None:
                continue
            legacy = self._legacy_membership(uid)
            if not legacy:
                continue
            doc = {
                "uid": str(uid),
                "tier": legacy.tier,
                "tier_name": legacy.tier_name,
                "source": "GRANT",
                "status": "ACTIVE",
                "plan_code": "",
                "started_at": "",
                "expires_at": legacy.expires_at,
                "days_left": legacy.days_left,
                "auto_renew": False,
                "benefits": list(legacy.benefits),
            }
            entity_store.create(ENTITY_MEMBERSHIP, doc)
            created += 1
        return created

    def prepare_runtime(self) -> None:
        self.ensure_catalog()
        self.sync_legacy_memberships()

    def clear(self) -> None:
        """Reset every loyalty entity family (test isolation)."""
        for entity in (ENTITY_ACCOUNT, ENTITY_LEDGER, ENTITY_MEMBERSHIP, ENTITY_ORDER, ENTITY_ITEM):
            spec = entity_store.spec(entity)
            adapter = entity_store.adapter(entity)
            for row in list(adapter.all()):
                adapter.delete(spec.key_of(row))
        self._idempotency.clear()
        self._order_keys.clear()
        self._daily.clear()
        self._daily_total.clear()
        self._monthly_total.clear()
        self._target_daily.clear()
        self._pair_daily.clear()
        self.ensure_catalog()

    # ------------------------------------------------------------------
    # Hydration (legacy domain_persistence contract)
    # ------------------------------------------------------------------
    def hydrate_accounts(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_ACCOUNT).hydrate(rows)

    def hydrate_ledger(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_LEDGER).hydrate(rows)

    def hydrate_memberships(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_MEMBERSHIP).hydrate(rows)

    def hydrate_orders(self, rows: List[Dict[str, Any]]) -> int:
        return entity_store.adapter(ENTITY_ORDER).hydrate(rows)

    def hydrate_items(self, rows: List[Dict[str, Any]]) -> int:
        count = entity_store.adapter(ENTITY_ITEM).hydrate(rows)
        self.ensure_catalog()
        return count

    # ------------------------------------------------------------------
    # Account / ledger reads
    # ------------------------------------------------------------------
    def _ledger_rows(self, uid: str = "") -> List[Dict[str, Any]]:
        rows = entity_store.adapter(ENTITY_LEDGER).all()
        if uid:
            return [row for row in rows if str(row.get("uid")) == str(uid)]
        return list(rows)

    def get_account(self, uid: str) -> PointsAccount:
        uid = str(uid or "")
        account = entity_store.get(ENTITY_ACCOUNT, {"key": uid})
        membership = entity_store.get(ENTITY_MEMBERSHIP, {"key": uid})
        doc = _functions().build_account(uid, account, membership, self._ledger_rows(uid))
        return PointsAccount(**doc)

    def list_ledger(
        self,
        uid: str,
        limit: int = 50,
        offset: int = 0,
        event_code: str = "",
    ) -> PointsLedgerResponse:
        payload = _functions().ledger_page(
            self._ledger_rows(str(uid)),
            str(uid),
            limit=limit,
            offset=offset,
            event_code=event_code,
            balance=int((entity_store.get(ENTITY_ACCOUNT, {"key": str(uid)}) or {}).get("balance") or 0),
        )
        return PointsLedgerResponse(
            items=[PointsLedgerEntry(**row) for row in payload["items"]],
            total=payload["total"],
            balance=payload["balance"],
        )

    def list_rules(self) -> PointsRulesResponse:
        return PointsRulesResponse(**_functions().rules_payload())

    def get_rule(self, event_code: str) -> Optional[PointsRule]:
        rule = _functions().RULES_BY_CODE.get(str(event_code or "").upper())
        return PointsRule(**rule) if rule else None

    def has_award(self, uid: str, event_prefix: str = "") -> bool:
        for entry in self._ledger_rows(str(uid)):
            if str(entry.get("status") or "").upper() == "REVOKED":
                continue
            if int(entry.get("delta") or 0) <= 0:
                continue
            if not event_prefix or str(entry.get("event_code") or "").startswith(event_prefix):
                return True
        return False

    def _ensure_account(self, uid: str) -> Dict[str, Any]:
        uid = str(uid or "")
        row = entity_store.get(ENTITY_ACCOUNT, {"key": uid})
        if row is None:
            row = _account_defaults(uid)
            if uid:
                entity_store.create(ENTITY_ACCOUNT, row)
        return _AccountHandle(uid, row)

    # ------------------------------------------------------------------
    # Membership reads
    # ------------------------------------------------------------------
    def get_membership(self, uid: str) -> MembershipInfo:
        uid = str(uid or "")
        row = entity_store.get(ENTITY_MEMBERSHIP, {"key": uid})
        if row:
            view = _functions().membership_view(row)
            if view["status"] == "ACTIVE":
                self._project_profile(uid, view["tier"], view["expires_at"])
                return MembershipInfo(**view)
            legacy = self._legacy_membership(uid)
            if legacy:
                self._project_profile(uid, legacy.tier, legacy.expires_at)
                return legacy
            self._project_profile(uid, "STANDARD", "")
            return MembershipInfo(**view)
        legacy = self._legacy_membership(uid)
        if legacy:
            self._project_profile(uid, legacy.tier, legacy.expires_at)
            return legacy
        return MembershipInfo(uid=uid)

    def _legacy_membership(self, uid: str) -> Optional[MembershipInfo]:
        """Expose founding-VIP / independently activated entitlements as membership."""
        try:
            from src.domains.user.service import user_service

            record = user_service._users_by_uid.get(str(uid))
            if not record:
                return None
            if str(record.get("membership_tier") or "").upper() in ("PRO", "BLACK_DIAMOND"):
                return None
            active = record.get("active_entitlements") or set()
            expiries = record.get("entitlement_expiries") or {}
            tier = ""
            entitlement = ""
            if "ent_black_diamond_priority" in active:
                tier = "BLACK_DIAMOND"
                entitlement = "ent_black_diamond_priority"
            elif "ent_ai_tax_assistant" in active:
                tier = "PRO"
                entitlement = "ent_ai_tax_assistant"
            if not tier:
                return None
            import math

            raw_expiry = str(expiries.get(entitlement) or "")
            expires = _functions()._parse_dt(raw_expiry) if raw_expiry else None
            now = datetime.now(timezone.utc)
            if expires and expires <= now:
                return None
            days_left = max(0, math.ceil((expires - now).total_seconds() / 86400)) if expires else 0
            return MembershipInfo(
                uid=str(uid),
                tier=tier,
                tier_name=_functions().TIER_NAMES.get(tier, tier),
                source="GRANT",
                status="ACTIVE",
                expires_at=expires.isoformat() if expires else "",
                days_left=days_left,
                benefits=_functions().membership_benefits(tier),
            )
        except Exception:
            return None

    def _project_profile(self, uid: str, tier: str, expires_at: str) -> None:
        """Mirror a membership window into the legacy profile fields (compatibility)."""
        try:
            from src.domains.user.service import user_service

            record = user_service._users_by_uid.get(str(uid))
            if not record:
                return
            tier = str(tier or "STANDARD").upper()
            if tier not in _functions().MEMBERSHIP_ENTITLEMENTS:
                tier = "STANDARD"
            owned = {"ent_ai_tax_assistant", "ent_black_diamond_priority"}
            active = record.setdefault("active_entitlements", set())
            expiries = record.setdefault("entitlement_expiries", {})
            for ent_id in owned:
                active.discard(ent_id)
                expiries.pop(ent_id, None)
            for ent_id in _functions().MEMBERSHIP_ENTITLEMENTS.get(tier, ()):
                active.add(ent_id)
                expiries[ent_id] = expires_at or utc_now_iso()
            record["tier_name"] = _functions().TIER_NAMES.get(tier, "标准创客")
            record["membership_tier"] = tier
            record["membership_expires_at"] = expires_at or ""
            # ``_users_by_uid`` is a live view over ``user.account`` entities: a
            # read returns a projected copy, so the mutated record must be written
            # back through the mapping.
            user_service._users_by_uid[str(uid)] = record
        except Exception as exc:  # pragma: no cover - profile index may be absent
            logger.debug("Membership profile projection skipped for %s: %s", uid, exc)

    def set_auto_renew(self, uid: str, enabled: bool) -> MembershipInfo:
        uid = str(uid or "")
        row = entity_store.get(ENTITY_MEMBERSHIP, {"key": uid})
        if row is None:
            raise ValueError("当前没有可续费的会员")
        entity_store.update(ENTITY_MEMBERSHIP, {"uid": uid, "auto_renew": bool(enabled)}, partial=True)
        return self.get_membership(uid)

    def list_plans(self, current_tier: str = "STANDARD") -> List[MembershipPlan]:
        return [MembershipPlan(**plan) for plan in _functions().plans_payload()["items"]]

    def get_plan(self, plan_code: str) -> Optional[MembershipPlan]:
        plan = _functions().PLANS_BY_CODE.get(str(plan_code or ""))
        return MembershipPlan(**plan) if plan else None

    # ------------------------------------------------------------------
    # Rewards / orders reads
    # ------------------------------------------------------------------
    def list_items(self, uid: str = "") -> List[RewardItem]:
        if not entity_store.adapter(ENTITY_ITEM).all():
            self.ensure_catalog()
        payload = _functions().rewards_payload(entity_store.adapter(ENTITY_ITEM).all())
        return [RewardItem(**item) for item in payload["items"]]

    def list_orders(self, uid: str) -> RedemptionOrdersResponse:
        rows = [row for row in entity_store.adapter(ENTITY_ORDER).all() if str(row.get("uid")) == str(uid)]
        payload = _functions().orders_payload(rows, str(uid))
        return RedemptionOrdersResponse(
            items=[RedemptionOrder(**row) for row in payload["items"]],
            total=payload["total"],
        )

    # ------------------------------------------------------------------
    # Legacy gateway bridges (deleted once gateway_routes.yaml is regenerated)
    # ------------------------------------------------------------------
    def resolve_target_author(self, target_type: str, target_id: str) -> str:
        try:
            from src.domains.interactions.service import content_interaction_service

            return content_interaction_service.resolve_target_author(target_type, target_id)
        except Exception:
            return ""

    def resolve_target_title(self, target_type: str, target_id: str) -> str:
        try:
            from src.domains.interactions.service import content_interaction_service

            return content_interaction_service.resolve_target_title(target_type, target_id)
        except Exception:
            return ""

    def admin_adjust(self, uid: str, delta: int, reason: str = "", operator_id: str = "") -> Dict[str, Any]:
        """Admin-only audited adjustment: pure settlement + entity writes."""
        uid = str(uid or "")
        delta = int(delta or 0)
        if not uid:
            raise ValueError("uid is required")
        if delta == 0:
            raise ValueError("delta cannot be zero")
        account = entity_store.get(ENTITY_ACCOUNT, {"key": uid})
        ledger = entity_store.adapter(ENTITY_LEDGER).all()
        result = _functions().settle(
            {"admin_mode": True},
            {
                "admin_mode": True,
                "user_id": uid,
                "actor_id": str(operator_id or ""),
                "admin_delta": delta,
                "note": str(reason or ""),
                "account": account,
                "ledger": ledger,
            },
            {},
        )
        if not result.get("allowed"):
            raise ValueError(result.get("reason") or "积分调整失败")
        entry = entity_store.create(ENTITY_LEDGER, result["ledger"])
        if entity_store.get(ENTITY_ACCOUNT, {"key": uid}) is None:
            entity_store.create(ENTITY_ACCOUNT, result["account"])
        else:
            entity_store.update(ENTITY_ACCOUNT, result["account"], partial=False)
        view = _functions().build_account(uid, result["account"], None, ledger)
        return {
            "adjusted": True,
            "delta": int(result.get("delta") or 0),
            "ledger_id": entry.get("id"),
            "account": view,
        }


loyalty_service = LoyaltyService()

# Hydration bindings (legacy ``domain_persistence`` contract; the generic entity
# store also hydrates the same families at startup, which is idempotent).
domain_persistence.register(ACCOUNTS_DOMAIN, loyalty_service.hydrate_accounts)
domain_persistence.register(LEDGER_DOMAIN, loyalty_service.hydrate_ledger)
domain_persistence.register(MEMBERSHIPS_DOMAIN, loyalty_service.hydrate_memberships)
domain_persistence.register(ORDERS_DOMAIN, loyalty_service.hydrate_orders)
domain_persistence.register(ITEMS_DOMAIN, loyalty_service.hydrate_items)
domain_persistence.register(LEGACY_ITEMS_DOMAIN, loyalty_service.hydrate_items)
