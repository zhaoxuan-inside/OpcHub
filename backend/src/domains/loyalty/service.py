"""Loyalty service: 晨光积分账本、会员订阅与积分兑换。

Design contract
---------------
* The service is the single writer for points balances. Business domains never
  mutate balances directly; they emit award / revoke intents which are executed
  by the loyalty DAG operators (``loyalty.*``).
* The ledger is append-only. Every mutation carries an idempotency key so the
  same interaction / publish event can never be credited twice.
* Points are revocable (unlike / content takedown), growth is monotonic, and
  reputation gates interaction weight.
* Membership is time-based and synced into the legacy ``tier_name`` /
  ``active_entitlements`` fields so existing profile APIs keep working.
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.domains.loyalty.models import (
    AwardDecision,
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
ITEMS_DOMAIN = "loyalty.reward_items"

DAILY_GLOBAL_CAP = 1000
MONTHLY_GLOBAL_CAP = 20000
POINTS_EXPIRY_MONTHS = 24
PAIR_DAILY_LIMIT = 3

TIER_NAMES = {
    "STANDARD": "标准创客",
    "PRO": "PRO 创客",
    "BLACK_DIAMOND": "黑钻创客 VIP",
}

TIER_MULTIPLIERS = {
    "STANDARD": 1.0,
    "PRO": 1.2,
    "BLACK_DIAMOND": 1.5,
}

# (threshold, level, name, multiplier)
LEVELS: List[Tuple[int, int, str, float]] = [
    (0, 1, "微光", 1.0),
    (500, 2, "破晓", 1.05),
    (2000, 3, "晨光", 1.10),
    (6000, 4, "炽阳", 1.15),
    (15000, 5, "长明", 1.20),
    (40000, 6, "恒星", 1.30),
]

# 会员权益映射到现有 entitlement 目录，保证旧接口兼容
MEMBERSHIP_ENTITLEMENTS = {
    "PRO": {"ent_ai_tax_assistant"},
    "BLACK_DIAMOND": {"ent_ai_tax_assistant", "ent_black_diamond_priority"},
}

CATEGORY_ORDER = {"TASK": 0, "CONTENT": 1, "INTERACTION": 2, "READ": 3, "BONUS": 4}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _add_months(moment: datetime, months: int) -> datetime:
    """Calendar-month addition without dateutil."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                           31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return moment.replace(year=year, month=month, day=day)


def _seed_paths(filename: str) -> List[Path]:
    root = Path(__file__).resolve().parents[4]
    return [
        Path("backend/data/seeds") / filename,
        Path("data/seeds") / filename,
        Path(__file__).resolve().parents[3] / "data" / "seeds" / filename,
        root / "data" / "seeds" / filename,
    ]


def _load_seed_list(filename: str) -> List[Dict[str, Any]]:
    for path in _seed_paths(filename):
        if not path.is_file():
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                return list(payload.values())
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load loyalty seed %s: %s", path, exc)
    return []


class LoyaltyService:
    """Points, growth, reputation, membership and redemption store."""

    def __init__(self) -> None:
        self._rules: Dict[str, PointsRule] = {}
        self._plans: Dict[str, MembershipPlan] = {}
        self._items: Dict[str, RewardItem] = {}

        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._ledger: Dict[str, Dict[str, Any]] = {}
        self._memberships: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}

        self._idempotency: Dict[str, str] = {}
        self._order_keys: Dict[str, str] = {}

        # cap counters
        self._daily: Dict[Tuple[str, str, str], int] = {}
        self._daily_total: Dict[Tuple[str, str], int] = {}
        self._monthly_total: Dict[Tuple[str, str], int] = {}
        self._target_daily: Dict[Tuple[str, str, str, str], int] = {}
        self._pair_daily: Dict[Tuple[str, str, str], int] = {}

        self._load_seeds()

    # ------------------------------------------------------------------
    # Seeding & hydration
    # ------------------------------------------------------------------
    def _load_seeds(self) -> None:
        for raw in _load_seed_list("loyalty_rules.json"):
            try:
                rule = PointsRule(**raw)
            except Exception:
                continue
            self._rules[rule.code] = rule
        for raw in _load_seed_list("membership_plans.json"):
            try:
                plan = MembershipPlan(**raw)
            except Exception:
                continue
            self._plans[plan.code] = plan
        for raw in _load_seed_list("reward_items.json"):
            try:
                item = RewardItem(**raw)
            except Exception:
                continue
            self._items[item.code] = item

    def hydrate_accounts(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            uid = str(row.get("uid") or "")
            if not uid:
                continue
            self._accounts[uid] = {
                "uid": uid,
                "balance": int(row.get("balance", 0) or 0),
                "frozen": int(row.get("frozen", 0) or 0),
                "debt": int(row.get("debt", 0) or 0),
                "total_earned": int(row.get("total_earned", 0) or 0),
                "total_spent": int(row.get("total_spent", 0) or 0),
                "growth": int(row.get("growth", 0) or 0),
                "reputation": int(row.get("reputation", 80) or 80),
                "updated_at": row.get("updated_at") or utc_now_iso(),
            }
        return len(rows)

    def hydrate_ledger(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            try:
                entry = PointsLedgerEntry(**row)
            except Exception:
                continue
            self._ledger[entry.id] = entry.model_dump()
            if entry.idempotency_key:
                self._idempotency[entry.idempotency_key] = entry.id
        self._recount()
        return len(rows)

    def hydrate_memberships(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            uid = str(row.get("uid") or "")
            if uid:
                self._memberships[uid] = dict(row)
        return len(rows)

    def hydrate_orders(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            order_id = str(row.get("id") or "")
            if order_id:
                self._orders[order_id] = dict(row)
        return len(rows)

    def hydrate_items(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            try:
                item = RewardItem(**row)
            except Exception:
                continue
            seed = self._items.get(item.code)
            # Membership / digital goods are intentionally unlimited; never let a
            # stale persisted stock turn them into "sold out".
            if seed and seed.type in ("MEMBERSHIP", "DIGITAL"):
                item.stock = -1
            self._items[item.code] = item
        return len(rows)

    def _recount(self) -> None:
        """Rebuild cap counters and growth from the append-only ledger."""
        self._daily.clear()
        self._daily_total.clear()
        self._monthly_total.clear()
        self._target_daily.clear()
        self._pair_daily.clear()
        for uid, account in self._accounts.items():
            account["growth"] = 0
        for entry in self._ledger.values():
            delta = int(entry.get("delta", 0) or 0)
            if delta == 0 or entry.get("status") == "REVOKED":
                continue
            uid = str(entry.get("uid") or "")
            if not uid:
                continue
            created = str(entry.get("created_at") or "")
            day = created[:10]
            month = created[:7]
            event = str(entry.get("event_code") or "")
            account = self._ensure_account(uid)
            if event == "ADMIN_ADJUST":
                continue
            if delta > 0:
                rule = self._rules.get(event)
                if rule:
                    account["growth"] += int(rule.growth)
                self._daily[(uid, event, day)] = self._daily.get((uid, event, day), 0) + delta
                self._daily_total[(uid, day)] = self._daily_total.get((uid, day), 0) + delta
                self._monthly_total[(uid, month)] = self._monthly_total.get((uid, month), 0) + delta
                target_id = str(entry.get("ref_id") or "")
                if target_id:
                    key = (uid, event, target_id, day)
                    self._target_daily[key] = self._target_daily.get(key, 0) + delta
                actor = str(entry.get("actor_id") or "")
                if actor and event.startswith("RECEIVE_"):
                    pair = (actor, uid, day)
                    self._pair_daily[pair] = self._pair_daily.get(pair, 0) + 1

    # ------------------------------------------------------------------
    # Read models
    # ------------------------------------------------------------------
    def has_award(self, uid: str, event_prefix: str = "") -> bool:
        """True when the user already owns a settled award matching the prefix."""
        for entry in self._ledger.values():
            if str(entry.get("uid")) != str(uid):
                continue
            if entry.get("status") == "REVOKED":
                continue
            if int(entry.get("delta", 0) or 0) <= 0:
                continue
            if not event_prefix or str(entry.get("event_code") or "").startswith(event_prefix):
                return True
        return False

    def list_rules(self) -> PointsRulesResponse:
        items = [rule for rule in self._rules.values() if rule.enabled]
        items.sort(key=lambda r: (CATEGORY_ORDER.get(r.category, 9), r.code))
        return PointsRulesResponse(
            items=items,
            daily_global_cap=DAILY_GLOBAL_CAP,
            monthly_global_cap=MONTHLY_GLOBAL_CAP,
            expiry_months=POINTS_EXPIRY_MONTHS,
        )

    def get_rule(self, event_code: str) -> Optional[PointsRule]:
        return self._rules.get(str(event_code or "").upper())

    def list_plans(self, current_tier: str = "STANDARD") -> List[MembershipPlan]:
        tier_order = {"PRO": 1, "BLACK_DIAMOND": 2}
        plans = sorted(self._plans.values(), key=lambda p: (tier_order.get(p.tier, 9), p.period_months))
        return plans

    def get_plan(self, plan_code: str) -> Optional[MembershipPlan]:
        return self._plans.get(str(plan_code or ""))

    def get_account(self, uid: str) -> PointsAccount:
        account = self._ensure_account(uid)
        membership = self.get_membership(uid)
        level, level_name, next_growth, progress = self._level_info(int(account.get("growth", 0) or 0))
        today = utc_now().date().isoformat()
        month = utc_now().strftime("%Y-%m")
        return PointsAccount(
            uid=uid,
            balance=int(account.get("balance", 0) or 0),
            frozen=int(account.get("frozen", 0) or 0),
            debt=int(account.get("debt", 0) or 0),
            total_earned=int(account.get("total_earned", 0) or 0),
            total_spent=int(account.get("total_spent", 0) or 0),
            growth=int(account.get("growth", 0) or 0),
            level=level,
            level_name=level_name,
            next_level_growth=next_growth,
            level_progress=progress,
            reputation=int(account.get("reputation", 80) or 80),
            membership_tier=membership.tier,
            membership_tier_name=membership.tier_name,
            membership_expires_at=membership.expires_at,
            today_earned=int(self._daily_total.get((uid, today), 0) or 0),
            month_earned=int(self._monthly_total.get((uid, month), 0) or 0),
            updated_at=str(account.get("updated_at") or utc_now_iso()),
        )

    def list_ledger(self, uid: str, limit: int = 50, offset: int = 0, event_code: str = "") -> PointsLedgerResponse:
        entries = [e for e in self._ledger.values() if str(e.get("uid")) == str(uid)]
        if event_code:
            entries = [e for e in entries if str(e.get("event_code")) == event_code.upper()]
        entries.sort(key=lambda e: str(e.get("created_at") or ""), reverse=True)
        total = len(entries)
        page = entries[offset: offset + max(1, min(limit, 200))]
        return PointsLedgerResponse(
            items=[PointsLedgerEntry(**e) for e in page],
            total=total,
            balance=int(self._ensure_account(uid).get("balance", 0) or 0),
        )

    def list_items(self, uid: str = "") -> List[RewardItem]:
        items = [item for item in self._items.values() if item.active]
        items.sort(key=lambda i: ({"MEMBERSHIP": 0, "DIGITAL": 1, "PHYSICAL": 2}.get(i.type, 9), i.points_price))
        return items

    def list_orders(self, uid: str) -> RedemptionOrdersResponse:
        orders = [o for o in self._orders.values() if str(o.get("uid")) == str(uid)]
        orders.sort(key=lambda o: str(o.get("created_at") or ""), reverse=True)
        return RedemptionOrdersResponse(
            items=[RedemptionOrder(**o) for o in orders],
            total=len(orders),
        )

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------
    def get_membership(self, uid: str) -> MembershipInfo:
        membership = self._memberships.get(str(uid))
        if not membership:
            legacy = self._legacy_membership(uid)
            return legacy or MembershipInfo(uid=str(uid))
        expires = _parse_iso(str(membership.get("expires_at") or ""))
        now = utc_now()
        if expires and expires <= now:
            if membership.get("status") == "ACTIVE":
                membership["status"] = "EXPIRED"
                membership["updated_at"] = utc_now_iso()
                domain_persistence.write_raw(MEMBERSHIPS_DOMAIN, str(uid), membership)
            legacy = self._legacy_membership(uid)
            if legacy:
                return legacy
            return MembershipInfo(
                uid=str(uid),
                tier="STANDARD",
                tier_name=TIER_NAMES["STANDARD"],
                source=str(membership.get("source") or ""),
                status="EXPIRED",
                plan_code=str(membership.get("plan_code") or ""),
                started_at=str(membership.get("started_at") or ""),
                expires_at=str(membership.get("expires_at") or ""),
                days_left=0,
                auto_renew=bool(membership.get("auto_renew", False)),
            )
        days_left = max(0, math.ceil((expires - now).total_seconds() / 86400)) if expires else 0
        tier = str(membership.get("tier") or "STANDARD")
        return MembershipInfo(
            uid=str(uid),
            tier=tier,
            tier_name=TIER_NAMES.get(tier, tier),
            source=str(membership.get("source") or ""),
            status=str(membership.get("status") or "ACTIVE"),
            plan_code=str(membership.get("plan_code") or ""),
            started_at=str(membership.get("started_at") or ""),
            expires_at=str(membership.get("expires_at") or ""),
            days_left=days_left,
            auto_renew=bool(membership.get("auto_renew", False)),
            benefits=self._membership_benefits(tier),
        )

    def _legacy_membership(self, uid: str) -> Optional[MembershipInfo]:
        """Expose founding-VIP / independently activated entitlements as membership.

        The loyalty membership record is authoritative once it exists; this
        fallback only covers legacy grants that were never written by the
        loyalty domain (e.g. the founding-maker black diamond gift).
        """
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
            raw_expiry = str(expiries.get(entitlement) or "")
            expires = _parse_iso(raw_expiry) if raw_expiry else None
            now = utc_now()
            if expires and expires <= now:
                return None
            days_left = max(0, math.ceil((expires - now).total_seconds() / 86400)) if expires else 0
            return MembershipInfo(
                uid=str(uid),
                tier=tier,
                tier_name=TIER_NAMES.get(tier, tier),
                source="GRANT",
                status="ACTIVE",
                expires_at=expires.isoformat() if expires else "",
                days_left=days_left,
                benefits=self._membership_benefits(tier),
            )
        except Exception:
            return None

    def set_auto_renew(self, uid: str, enabled: bool) -> MembershipInfo:
        membership = self._memberships.get(str(uid))
        if not membership:
            raise ValueError("当前没有可续费的会员")
        membership["auto_renew"] = bool(enabled)
        membership["updated_at"] = utc_now_iso()
        domain_persistence.write_raw(MEMBERSHIPS_DOMAIN, str(uid), membership)
        return self.get_membership(uid)

    async def _apply_membership(self, uid: str, tier: str, months: int, source: str, plan_code: str = "") -> MembershipInfo:
        tier = str(tier or "PRO").upper()
        if tier not in ("PRO", "BLACK_DIAMOND"):
            raise ValueError(f"不支持的会员档位: {tier}")
        months = max(1, int(months or 1))
        now = utc_now()
        current = self._memberships.get(str(uid))
        current_expiry = _parse_iso(str((current or {}).get("expires_at") or ""))
        same_active_tier = bool(
            current
            and current.get("status") == "ACTIVE"
            and current.get("tier") == tier
            and current_expiry
            and current_expiry > now
        )
        legacy = self._legacy_membership(uid)
        tier_rank = {"PRO": 1, "BLACK_DIAMOND": 2}
        if legacy and tier_rank.get(legacy.tier, 0) > tier_rank.get(tier, 0):
            raise ValueError("当前已有更高档会员权益，无需降级兑换")
        base_candidates = [now]
        if same_active_tier and current_expiry:
            base_candidates.append(current_expiry)
        if legacy and legacy.tier == tier and legacy.expires_at:
            legacy_expiry = _parse_iso(legacy.expires_at)
            if legacy_expiry:
                base_candidates.append(legacy_expiry)
        base = max(base_candidates)
        started_at = str((current or {}).get("started_at") or now.isoformat())
        expires = _add_months(base, months)
        membership = {
            "uid": str(uid),
            "tier": tier,
            "source": source,
            "status": "ACTIVE",
            "plan_code": plan_code,
            "started_at": started_at,
            "expires_at": expires.isoformat(),
            "auto_renew": bool((current or {}).get("auto_renew", False)),
            "updated_at": now.isoformat(),
        }
        self._memberships[str(uid)] = membership
        domain_persistence.write_raw(MEMBERSHIPS_DOMAIN, str(uid), membership)
        await self._sync_user_membership(uid, tier, expires)
        return self.get_membership(uid)

    async def _sync_user_membership(self, uid: str, tier: str, expires: datetime) -> None:
        try:
            from src.domains.user.service import user_service

            await user_service.sync_membership(uid, tier, expires.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as exc:  # pragma: no cover - user index may be absent in unit tests
            logger.warning("Failed to sync membership to user profile %s: %s", uid, exc)

    def _membership_benefits(self, tier: str) -> List[str]:
        candidates = [p for p in self._plans.values() if p.tier == tier]
        if not candidates:
            return []
        candidates.sort(key=lambda p: p.period_months, reverse=True)
        return list(candidates[0].benefits)

    # ------------------------------------------------------------------
    # Award / revoke
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

    def check_award(
        self,
        event_code: str,
        uid: str,
        actor_id: str = "",
        target_type: str = "",
        target_id: str = "",
        quantity: int = 1,
        idempotency_key: Optional[str] = None,
        note: str = "",
    ) -> AwardDecision:
        event = str(event_code or "").upper()
        uid = str(uid or "")
        actor_id = str(actor_id or "")
        rule = self._rules.get(event)
        decision = AwardDecision(
            uid=uid,
            actor_id=actor_id,
            event_code=event,
            target_type=str(target_type or "").upper(),
            target_id=str(target_id or ""),
            note=note,
        )
        if not rule or not rule.enabled:
            decision.reason = "rule_disabled"
            return decision
        if rule.points <= 0:
            decision.reason = "rule_zero_points"
            return decision
        if not uid:
            decision.reason = "missing_user"
            return decision
        if self._is_official(uid):
            decision.reason = "official_account"
            return decision
        if event.startswith("RECEIVE_") and actor_id and actor_id == uid:
            decision.reason = "self_interaction"
            return decision

        key = str(idempotency_key or self._default_idempotency(event, uid, actor_id, target_type, target_id, rule))
        if key in self._idempotency:
            decision.reason = "duplicate"
            return decision

        quantity = max(1, int(quantity or 1))
        base = int(rule.points) * quantity
        delta = self._scale_points(uid, base)
        if delta <= 0:
            decision.reason = "reputation_blocked"
            return decision

        now = utc_now()
        day = now.date().isoformat()
        month = now.strftime("%Y-%m")

        if rule.daily_cap is not None and rule.daily_cap > 0:
            used = int(self._daily.get((uid, event, day), 0) or 0)
            delta = min(delta, max(0, rule.daily_cap - used))
        if rule.monthly_cap is not None and rule.monthly_cap > 0:
            used = int(self._monthly_total.get((uid, month), 0) or 0)
            delta = min(delta, max(0, rule.monthly_cap - used))
        if rule.per_target_cap is not None and rule.per_target_cap > 0 and target_id:
            used = int(self._target_daily.get((uid, event, str(target_id), day), 0) or 0)
            delta = min(delta, max(0, rule.per_target_cap - used))

        used_today = int(self._daily_total.get((uid, day), 0) or 0)
        delta = min(delta, max(0, DAILY_GLOBAL_CAP - used_today))
        used_month = int(self._monthly_total.get((uid, month), 0) or 0)
        delta = min(delta, max(0, MONTHLY_GLOBAL_CAP - used_month))

        if event.startswith("RECEIVE_") and actor_id:
            pair_key = (actor_id, uid, day)
            if int(self._pair_daily.get(pair_key, 0) or 0) >= PAIR_DAILY_LIMIT:
                decision.reason = "pair_daily_cap"
                return decision

        if delta <= 0:
            decision.reason = "daily_cap_reached"
            return decision

        decision.allowed = True
        decision.rule_code = rule.code
        decision.rule_name = rule.name
        decision.base_points = base
        decision.delta = int(delta)
        decision.growth = int(rule.growth)
        decision.idempotency_key = key
        return decision

    def apply_award(self, decision: AwardDecision) -> Dict[str, Any]:
        if not decision.allowed or decision.delta <= 0:
            return {"awarded": False, "reason": decision.reason or "not_allowed", "delta": 0}
        if decision.idempotency_key and decision.idempotency_key in self._idempotency:
            return {"awarded": False, "reason": "duplicate", "delta": 0}

        account = self._ensure_account(decision.uid)
        entry = self._append_ledger(
            uid=decision.uid,
            event_code=decision.event_code,
            title=decision.rule_name or decision.event_code,
            delta=decision.delta,
            actor_id=decision.actor_id,
            ref_type=decision.target_type,
            ref_id=decision.target_id,
            idempotency_key=decision.idempotency_key,
            note=decision.note or self.resolve_target_title(decision.target_type, decision.target_id),
            count_as_earn=True,
            count_as_spend=False,
        )
        account["growth"] = int(account.get("growth", 0) or 0) + max(0, int(decision.growth))
        account["updated_at"] = utc_now_iso()
        self._persist_account(decision.uid)

        now = utc_now()
        day = now.date().isoformat()
        month = now.strftime("%Y-%m")
        self._daily[(decision.uid, decision.event_code, day)] = (
            int(self._daily.get((decision.uid, decision.event_code, day), 0) or 0) + decision.delta
        )
        self._daily_total[(decision.uid, day)] = int(self._daily_total.get((decision.uid, day), 0) or 0) + decision.delta
        self._monthly_total[(decision.uid, month)] = (
            int(self._monthly_total.get((decision.uid, month), 0) or 0) + decision.delta
        )
        if decision.target_id:
            key = (decision.uid, decision.event_code, str(decision.target_id), day)
            self._target_daily[key] = int(self._target_daily.get(key, 0) or 0) + decision.delta
        if decision.event_code.startswith("RECEIVE_") and decision.actor_id:
            pair = (decision.actor_id, decision.uid, day)
            self._pair_daily[pair] = int(self._pair_daily.get(pair, 0) or 0) + 1

        level, level_name, _, _ = self._level_info(int(account.get("growth", 0) or 0))
        return {
            "awarded": True,
            "delta": decision.delta,
            "balance": int(account.get("balance", 0) or 0),
            "growth": int(account.get("growth", 0) or 0),
            "level": level,
            "level_name": level_name,
            "ledger_id": entry.id,
        }

    def revoke(
        self,
        event_code: str = "",
        uid: str = "",
        actor_id: str = "",
        target_type: str = "",
        target_id: str = "",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        event = str(event_code or "").upper()
        uid = str(uid or "")
        actor_id = str(actor_id or "")
        target_type = str(target_type or "").upper()
        target_id = str(target_id or "")

        key = str(idempotency_key or "")
        if not key:
            rule = self._rules.get(event)
            key = self._default_idempotency(event, uid, actor_id, target_type, target_id, rule)

        entry_id = self._idempotency.get(key)
        if not entry_id:
            return {"revoked": False, "reason": "not_found", "delta": 0}
        entry = self._ledger.get(entry_id)
        if not entry or entry.get("status") == "REVOKED":
            return {"revoked": False, "reason": "already_revoked", "delta": 0}

        # The reversal must target the original earner, not the caller.
        uid = uid or str(entry.get("uid") or "")
        actor_id = actor_id or str(entry.get("actor_id") or "")
        target_type = target_type or str(entry.get("ref_type") or "")
        target_id = target_id or str(entry.get("ref_id") or "")

        delta = int(entry.get("delta", 0) or 0)
        if delta == 0:
            return {"revoked": False, "reason": "zero_delta", "delta": 0}

        entry["status"] = "REVOKED"
        entry["updated_at"] = utc_now_iso()
        self._ledger[entry_id] = entry
        domain_persistence.write_raw(LEDGER_DOMAIN, entry_id, entry)
        # Keep the idempotency key as a tombstone: cancel + re-like must not
        # re-credit the same actor/target pair.

        account = self._ensure_account(uid)
        account["balance"] = int(account.get("balance", 0) or 0) - delta
        account["total_earned"] = max(0, int(account.get("total_earned", 0) or 0) - max(0, delta))
        account["debt"] = abs(int(account["balance"])) if int(account["balance"]) < 0 else 0
        account["updated_at"] = utc_now_iso()
        self._persist_account(uid)

        reversal = self._append_ledger(
            uid=uid,
            event_code=f"{event}_REVOKE",
            title=f"撤销 · {entry.get('title') or event}",
            delta=-delta,
            actor_id=actor_id or str(entry.get("actor_id") or ""),
            ref_type=target_type or str(entry.get("ref_type") or ""),
            ref_id=target_id or str(entry.get("ref_id") or ""),
            idempotency_key=f"revoke:{entry_id}",
            note="互动取消或内容下架回滚",
            count_as_earn=False,
            count_as_spend=False,
            apply_balance=False,
        )

        now = utc_now()
        day = now.date().isoformat()
        month = now.strftime("%Y-%m")
        self._daily[(uid, event, day)] = max(0, int(self._daily.get((uid, event, day), 0) or 0) - delta)
        self._daily_total[(uid, day)] = max(0, int(self._daily_total.get((uid, day), 0) or 0) - delta)
        self._monthly_total[(uid, month)] = max(0, int(self._monthly_total.get((uid, month), 0) or 0) - delta)
        if target_id:
            tkey = (uid, event, target_id, day)
            self._target_daily[tkey] = max(0, int(self._target_daily.get(tkey, 0) or 0) - delta)
        if event.startswith("RECEIVE_") and actor_id:
            pair = (actor_id, uid, day)
            self._pair_daily[pair] = max(0, int(self._pair_daily.get(pair, 0) or 0) - 1)

        return {
            "revoked": True,
            "delta": -delta,
            "balance": int(account.get("balance", 0) or 0),
            "ledger_id": reversal.id,
        }

    def revoke_target(self, target_type: str, target_id: str) -> int:
        """Revoke every award attached to a removed / violated content target."""
        count = 0
        for entry in list(self._ledger.values()):
            if str(entry.get("ref_type") or "").upper() != str(target_type or "").upper():
                continue
            if str(entry.get("ref_id") or "") != str(target_id or ""):
                continue
            if entry.get("status") == "REVOKED" or int(entry.get("delta", 0) or 0) <= 0:
                continue
            result = self.revoke(uid=str(entry.get("uid")), idempotency_key=str(entry.get("idempotency_key") or ""))
            if result.get("revoked"):
                count += 1
        return count

    def revoke_ledger(self, ledger_id: str) -> bool:
        entry = self._ledger.get(str(ledger_id))
        if not entry:
            return False
        result = self.revoke(uid=str(entry.get("uid")), idempotency_key=str(entry.get("idempotency_key") or ""))
        return bool(result.get("revoked"))

    def admin_adjust(self, uid: str, delta: int, reason: str = "", operator_id: str = "") -> Dict[str, Any]:
        """Operational adjustment (admin only): no caps, fully audited."""
        uid = str(uid or "")
        delta = int(delta or 0)
        if not uid:
            raise ValueError("uid is required")
        if delta == 0:
            raise ValueError("delta cannot be zero")
        entry = self._append_ledger(
            uid=uid,
            event_code="ADMIN_ADJUST",
            title="运营积分调整",
            delta=delta,
            actor_id=str(operator_id or ""),
            ref_type="ADMIN",
            ref_id=str(operator_id or ""),
            idempotency_key=f"admin:{uuid.uuid4().hex}",
            note=str(reason or ""),
            count_as_earn=delta > 0,
            count_as_spend=delta < 0,
        )
        account = self.get_account(uid)
        return {"adjusted": True, "delta": delta, "ledger_id": entry.id, "account": account.model_dump()}

    # ------------------------------------------------------------------
    # Redemption & subscription
    # ------------------------------------------------------------------
    def check_redeem(self, uid: str, item_code: str, qty: int = 1, address: Any = None) -> Dict[str, Any]:
        uid = str(uid or "")
        item = self._items.get(str(item_code or ""))
        if not uid:
            return {"allowed": False, "reason": "missing_user"}
        if not item or not item.active:
            return {"allowed": False, "reason": "item_unavailable"}
        qty = max(1, min(int(qty or 1), 10))
        if item.stock >= 0 and item.stock < qty:
            return {"allowed": False, "reason": "out_of_stock"}
        if item.type == "PHYSICAL" and not address:
            return {"allowed": False, "reason": "address_required"}
        if item.type == "MEMBERSHIP":
            target_tier = str((item.meta or {}).get("tier") or "PRO").upper()
            legacy = self._legacy_membership(uid)
            tier_rank = {"PRO": 1, "BLACK_DIAMOND": 2}
            if legacy and tier_rank.get(legacy.tier, 0) > tier_rank.get(target_tier, 0):
                return {"allowed": False, "reason": "higher_tier_active"}
        used = sum(
            1
            for order in self._orders.values()
            if str(order.get("uid")) == uid
            and str(order.get("item_code")) == item.code
            and order.get("status") != "CANCELLED"
        )
        if item.per_user_limit > 0 and used + qty > item.per_user_limit:
            return {"allowed": False, "reason": "per_user_limit"}
        cost = int(item.points_price) * qty
        account = self._ensure_account(uid)
        if int(account.get("balance", 0) or 0) < cost:
            return {"allowed": False, "reason": "insufficient_points"}
        if int(account.get("debt", 0) or 0) > 0:
            return {"allowed": False, "reason": "debt_pending"}
        return {"allowed": True, "item": item, "qty": qty, "cost": cost}

    async def redeem(
        self,
        uid: str,
        item_code: str,
        qty: int = 1,
        address: Any = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        uid = str(uid or "")
        if idempotency_key and idempotency_key in self._order_keys:
            existing = self._orders.get(self._order_keys[idempotency_key])
            if existing:
                return {
                    "order": RedemptionOrder(**existing),
                    "account": self.get_account(uid),
                    "membership": self.get_membership(uid),
                    "message": "该兑换已处理",
                }

        decision = self.check_redeem(uid, item_code, qty, address)
        if not decision.get("allowed"):
            raise ValueError(self._redeem_reason_text(str(decision.get("reason"))))
        item: RewardItem = decision["item"]
        qty = int(decision["qty"])
        cost = int(decision["cost"])

        order = RedemptionOrder(
            id=f"ord_{uuid.uuid4().hex[:12]}",
            uid=uid,
            item_code=item.code,
            item_name=item.name,
            item_type=item.type,
            qty=qty,
            points_cost=cost,
            status="COMPLETED" if item.type in ("MEMBERSHIP", "DIGITAL") else "PAID",
            address=address if item.type == "PHYSICAL" else None,
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
        )

        self._append_ledger(
            uid=uid,
            event_code="REDEEM_ITEM",
            title=f"兑换 · {item.name}",
            delta=-cost,
            actor_id=uid,
            ref_type=item.type,
            ref_id=order.id,
            idempotency_key=f"redeem:{order.id}",
            note=f"×{qty}",
            count_as_earn=False,
            count_as_spend=True,
        )

        if item.stock >= 0:
            item.stock = max(0, item.stock - qty)
            domain_persistence.write_raw(ITEMS_DOMAIN, item.code, item.model_dump())

        membership = None
        if item.type == "MEMBERSHIP":
            meta = item.meta or {}
            membership = await self._apply_membership(
                uid,
                str(meta.get("tier") or "PRO"),
                int(meta.get("months") or 1) * qty,
                "POINTS",
                item.code,
            )
        elif item.type == "PHYSICAL":
            order.note = "实物兑换已受理，等待发货"

        self._orders[order.id] = order.model_dump()
        domain_persistence.write_raw(ORDERS_DOMAIN, order.id, order.model_dump())
        if idempotency_key:
            self._order_keys[idempotency_key] = order.id

        return {
            "order": order,
            "account": self.get_account(uid),
            "membership": membership,
            "message": "兑换成功" if item.type != "PHYSICAL" else "兑换成功，实物将尽快发出",
        }

    async def subscribe(self, uid: str, plan_code: str, pay_method: str = "POINTS", idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        uid = str(uid or "")
        plan = self._plans.get(str(plan_code or ""))
        if not plan:
            raise ValueError("会员套餐不存在")
        if not uid:
            raise ValueError("请先登录创客账号")
        method = str(pay_method or "POINTS").upper()

        if idempotency_key and idempotency_key in self._order_keys:
            existing = self._orders.get(self._order_keys[idempotency_key])
            if existing:
                return {
                    "order": RedemptionOrder(**existing),
                    "account": self.get_account(uid),
                    "membership": self.get_membership(uid),
                    "message": "该订单已处理",
                }

        order = RedemptionOrder(
            id=f"ord_{uuid.uuid4().hex[:12]}",
            uid=uid,
            item_code=plan.code,
            item_name=plan.tier_name + ("年卡" if plan.period_months >= 12 else "月卡"),
            item_type="MEMBERSHIP",
            qty=1,
            points_cost=plan.points_price if method == "POINTS" else 0,
            status="PENDING_PAYMENT",
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
        )

        if method == "CASH":
            order.note = f"应付 ¥{plan.price_cny:.2f}，请通过收银台完成支付"
            self._orders[order.id] = order.model_dump()
            domain_persistence.write_raw(ORDERS_DOMAIN, order.id, order.model_dump())
            if idempotency_key:
                self._order_keys[idempotency_key] = order.id
            return {
                "order": order,
                "account": self.get_account(uid),
                "membership": self.get_membership(uid),
                "message": "订单已创建，请完成现金支付后激活会员",
                "payment_required": True,
                "payment_amount_cny": plan.price_cny,
            }

        account = self._ensure_account(uid)
        if int(account.get("balance", 0) or 0) < plan.points_price:
            raise ValueError("晨光积分不足，无法兑换该会员套餐")

        self._append_ledger(
            uid=uid,
            event_code="SUBSCRIBE_MEMBERSHIP",
            title=f"兑换会员 · {plan.tier_name}",
            delta=-plan.points_price,
            actor_id=uid,
            ref_type="MEMBERSHIP",
            ref_id=order.id,
            idempotency_key=f"subscribe:{order.id}",
            note=plan.code,
            count_as_earn=False,
            count_as_spend=True,
        )
        membership = await self._apply_membership(uid, plan.tier, plan.period_months, "POINTS", plan.code)
        order.status = "COMPLETED"
        order.note = f"积分兑换，有效期至 {membership.expires_at[:10]}"
        self._orders[order.id] = order.model_dump()
        domain_persistence.write_raw(ORDERS_DOMAIN, order.id, order.model_dump())
        if idempotency_key:
            self._order_keys[idempotency_key] = order.id

        return {
            "order": order,
            "account": self.get_account(uid),
            "membership": membership,
            "message": "会员已开通",
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _ensure_account(self, uid: str) -> Dict[str, Any]:
        uid = str(uid or "")
        account = self._accounts.get(uid)
        if account is None:
            account = {
                "uid": uid,
                "balance": 0,
                "frozen": 0,
                "debt": 0,
                "total_earned": 0,
                "total_spent": 0,
                "growth": 0,
                "reputation": 80,
                "updated_at": utc_now_iso(),
            }
            self._accounts[uid] = account
            self._persist_account(uid)
        return account

    def _persist_account(self, uid: str) -> None:
        account = self._accounts.get(str(uid))
        if account is not None:
            domain_persistence.write_raw(ACCOUNTS_DOMAIN, str(uid), account)

    def _append_ledger(
        self,
        uid: str,
        event_code: str,
        title: str,
        delta: int,
        actor_id: str = "",
        ref_type: str = "",
        ref_id: str = "",
        idempotency_key: str = "",
        note: str = "",
        count_as_earn: bool = False,
        count_as_spend: bool = False,
        apply_balance: bool = True,
    ) -> PointsLedgerEntry:
        account = self._ensure_account(uid)
        if apply_balance:
            account["balance"] = int(account.get("balance", 0) or 0) + int(delta)
            account["debt"] = abs(int(account["balance"])) if int(account["balance"]) < 0 else 0
        if count_as_earn and delta > 0:
            account["total_earned"] = int(account.get("total_earned", 0) or 0) + int(delta)
        if count_as_spend and delta < 0:
            account["total_spent"] = int(account.get("total_spent", 0) or 0) + abs(int(delta))
        account["updated_at"] = utc_now_iso()

        entry = PointsLedgerEntry(
            id=f"pl_{uuid.uuid4().hex[:14]}",
            uid=uid,
            event_code=event_code,
            title=title,
            delta=int(delta),
            balance_after=int(account.get("balance", 0) or 0),
            status="SETTLED",
            ref_type=ref_type,
            ref_id=ref_id,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            note=note,
            expires_at=_add_months(utc_now(), POINTS_EXPIRY_MONTHS).isoformat() if delta > 0 else "",
            created_at=utc_now_iso(),
        )
        self._ledger[entry.id] = entry.model_dump()
        if idempotency_key:
            self._idempotency[idempotency_key] = entry.id
        self._persist_account(uid)
        domain_persistence.write_raw(LEDGER_DOMAIN, entry.id, entry.model_dump())
        return entry

    def _scale_points(self, uid: str, base: int) -> int:
        if base <= 0:
            return 0
        account = self._ensure_account(uid)
        growth = int(account.get("growth", 0) or 0)
        reputation = int(account.get("reputation", 80) or 80)
        level_mult = 1.0
        for threshold, _, _, multiplier in LEVELS:
            if growth >= threshold:
                level_mult = multiplier
        rep_mult = 1.0 if reputation >= 80 else (0.5 if reputation >= 60 else 0.0)
        if rep_mult <= 0:
            return 0
        member_mult = self._membership_multiplier(uid)
        total = min(2.0, level_mult * rep_mult * member_mult)
        return max(1, int(round(base * total)))

    def _membership_multiplier(self, uid: str) -> float:
        membership = self.get_membership(uid)
        if membership.status != "ACTIVE":
            return 1.0
        return TIER_MULTIPLIERS.get(membership.tier, 1.0)

    def _default_idempotency(
        self,
        event: str,
        uid: str,
        actor_id: str,
        target_type: str,
        target_id: str,
        rule: Optional[PointsRule],
    ) -> str:
        day = utc_now().date().isoformat()
        if rule and rule.once:
            return f"once:{event}:{uid}"
        if event == "RECEIVE_READ":
            return f"read:{actor_id}:{target_type}:{target_id}:{day}"
        if event.startswith("RECEIVE_") and target_id:
            return f"interaction:{event}:{actor_id}:{target_type}:{target_id}"
        if event.startswith("PUBLISH_") and target_id:
            return f"publish:{target_type}:{target_id}"
        return f"{event}:{uid}:{actor_id}:{target_type}:{target_id}:{day}"

    def _is_official(self, uid: str) -> bool:
        try:
            from src.domains.user.service import user_service

            record = user_service._users_by_uid.get(str(uid))
            return bool(record and str(record.get("role", "")).upper() == "ADMIN")
        except Exception:
            return False

    @staticmethod
    def _level_info(growth: int) -> Tuple[int, str, int, float]:
        current = LEVELS[0]
        next_threshold = LEVELS[1][0] if len(LEVELS) > 1 else LEVELS[0][0]
        for index, row in enumerate(LEVELS):
            if growth >= row[0]:
                current = row
                next_threshold = LEVELS[index + 1][0] if index + 1 < len(LEVELS) else row[0]
        threshold, level, name, _ = current
        if next_threshold <= threshold:
            progress = 100.0
        else:
            progress = round(min(100.0, max(0.0, (growth - threshold) / (next_threshold - threshold) * 100)), 1)
        return level, name, next_threshold, progress

    @staticmethod
    def _redeem_reason_text(reason: str) -> str:
        return {
            "missing_user": "请先登录创客账号",
            "item_unavailable": "该兑换商品已下架",
            "out_of_stock": "该商品库存不足",
            "address_required": "实物兑换需要填写收货地址",
            "per_user_limit": "已达到该商品的兑换上限",
            "insufficient_points": "晨光积分不足",
            "debt_pending": "存在待补扣积分，暂时无法兑换",
            "higher_tier_active": "当前已有更高档会员权益，无需降级兑换",
        }.get(reason, "兑换条件不满足")


loyalty_service = LoyaltyService()

domain_persistence.register(ACCOUNTS_DOMAIN, loyalty_service.hydrate_accounts)
domain_persistence.register(LEDGER_DOMAIN, loyalty_service.hydrate_ledger)
domain_persistence.register(MEMBERSHIPS_DOMAIN, loyalty_service.hydrate_memberships)
domain_persistence.register(ORDERS_DOMAIN, loyalty_service.hydrate_orders)
domain_persistence.register(ITEMS_DOMAIN, loyalty_service.hydrate_items)
