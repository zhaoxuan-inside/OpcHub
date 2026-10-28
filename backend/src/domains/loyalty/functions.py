"""Single-responsibility pure function operators for the loyalty domain.

晨光积分 / 会员 / 积分兑换 are expressed as declarative scenarios
(``config/scenarios/loyalty.yaml``). This module only contains deterministic
calculations and assemblers:

* ``calc.loyalty.*``      - points settlement, revocation, redemption,
                            membership transitions, level mapping, query normalisation
* ``assemble.loyalty.*``  - response shapes for account / ledger / rules / plans /
                            membership / rewards / orders

Rules, membership plans and the reward catalogue are configuration constants
(the legacy JSON seed files are data assets only). There is **no I/O**, no
operator invocation, no orchestration and no cross-domain import here.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.core.operators.sdk import operator

# ---------------------------------------------------------------------------
# Configuration assets (rules / plans / rewards)
# ---------------------------------------------------------------------------

ACCOUNT_ENTITY = "loyalty.account"
LEDGER_ENTITY = "loyalty.ledger"
MEMBERSHIP_ENTITY = "loyalty.membership"
ORDER_ENTITY = "loyalty.order"
ITEM_ENTITY = "loyalty.item"

DAILY_GLOBAL_CAP = 1000
MONTHLY_GLOBAL_CAP = 20000
POINTS_EXPIRY_MONTHS = 24
PAIR_DAILY_LIMIT = 3

CATEGORY_ORDER = {"TASK": 0, "CONTENT": 1, "INTERACTION": 2, "READ": 3, "BONUS": 4}
TIER_ORDER = {"PRO": 1, "BLACK_DIAMOND": 2}
ITEM_TYPE_ORDER = {"MEMBERSHIP": 0, "DIGITAL": 1, "PHYSICAL": 2}

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

#: (threshold, level, name, multiplier)
LEVELS: list[tuple[int, int, str, float]] = [
    (0, 1, "微光", 1.0),
    (500, 2, "破晓", 1.05),
    (2000, 3, "晨光", 1.10),
    (6000, 4, "炽阳", 1.15),
    (15000, 5, "长明", 1.20),
    (40000, 6, "恒星", 1.30),
]

MEMBERSHIP_ENTITLEMENTS = {
    "PRO": ("ent_ai_tax_assistant",),
    "BLACK_DIAMOND": ("ent_ai_tax_assistant", "ent_black_diamond_priority"),
}

KIND_TO_EVENT = {
    "LIKE": "RECEIVE_LIKE",
    "FAVORITE": "RECEIVE_FAVORITE",
    "LOVE": "RECEIVE_LOVE",
    "DISLIKE": "RECEIVE_DISLIKE",
}

#: target type -> owning entity used to resolve the award recipient
TARGET_ENTITIES = {
    "PRODUCT": "product.item",
    "POLICY": "policy.item",
    "DEMAND": "demands.item",
    "FORUM_THREAD": "forum.thread",
    "SOP_DOCUMENT": None,
    "SOP_FLOW": None,
    "PERK": "perk.item",
}

POINTS_RULES: tuple[dict[str, Any], ...] = (
    {"code": "PROFILE_COMPLETE", "name": "完善创客资料", "category": "TASK", "points": 200, "growth": 50, "once": True},
    {"code": "VERIFY_EMAIL", "name": "完成邮箱验证", "category": "TASK", "points": 100, "growth": 20, "once": True},
    {"code": "VERIFY_IDENTITY", "name": "完成实名 / 企业认证", "category": "TASK", "points": 500, "growth": 200, "once": True},
    {"code": "FIRST_PUBLISH", "name": "首次发布内容", "category": "TASK", "points": 300, "growth": 50, "once": True},
    {"code": "PUBLISH_POLICY", "name": "发布政策", "category": "CONTENT", "points": 100, "growth": 20, "daily_cap": 500},
    {"code": "PUBLISH_SOP", "name": "发布文书 / 模板", "category": "CONTENT", "points": 120, "growth": 25, "daily_cap": 500},
    {"code": "PUBLISH_FORUM", "name": "发布头脑风暴主题", "category": "CONTENT", "points": 50, "growth": 10, "daily_cap": 500},
    {"code": "PUBLISH_ANSWER", "name": "发表深度回答", "category": "CONTENT", "points": 40, "growth": 8, "daily_cap": 400},
    {"code": "PUBLISH_PRODUCT", "name": "发布产品橱窗", "category": "CONTENT", "points": 60, "growth": 12, "daily_cap": 500},
    {"code": "PUBLISH_DEMAND", "name": "发布需求", "category": "CONTENT", "points": 60, "growth": 12, "daily_cap": 500},
    {"code": "PUBLISH_PERK", "name": "发布生态优惠", "category": "CONTENT", "points": 60, "growth": 12, "daily_cap": 500},
    {"code": "PUBLISH_COMPLIANCE", "name": "发布合规法条 / 案例", "category": "CONTENT", "points": 100, "growth": 20, "daily_cap": 500},
    {"code": "COMMENT_CREATED", "name": "发表有效评论", "category": "INTERACTION", "points": 5, "growth": 1, "daily_cap": 50, "per_target_cap": 15},
    {"code": "RECEIVE_LIKE", "name": "内容被点赞", "category": "INTERACTION", "points": 5, "growth": 2, "daily_cap": 300, "per_target_cap": 300},
    {"code": "RECEIVE_FAVORITE", "name": "内容被收藏", "category": "INTERACTION", "points": 10, "growth": 5, "daily_cap": 400, "per_target_cap": 500},
    {"code": "RECEIVE_LOVE", "name": "内容被喜欢", "category": "INTERACTION", "points": 3, "growth": 1, "daily_cap": 150, "per_target_cap": 150},
    {"code": "RECEIVE_COMMENT", "name": "内容被评论", "category": "INTERACTION", "points": 8, "growth": 3, "daily_cap": 300, "per_target_cap": 400},
    {"code": "RECEIVE_READ", "name": "内容被阅读", "category": "READ", "points": 1, "growth": 0, "daily_cap": 50, "per_target_cap": 200},
    {"code": "RECEIVE_DISLIKE", "name": "内容被踩", "category": "INTERACTION", "points": 0, "growth": 0, "daily_cap": 0, "per_target_cap": 0},
    {"code": "QUALITY_BONUS", "name": "优质内容奖励", "category": "BONUS", "points": 500, "growth": 300, "daily_cap": 3000},
    {"code": "DAILY_STREAK_7", "name": "连续活跃 7 天", "category": "BONUS", "points": 100, "growth": 20},
    {"code": "DAILY_STREAK_30", "name": "连续活跃 30 天", "category": "BONUS", "points": 500, "growth": 100},
    {"code": "INVITE_SUCCESS", "name": "邀请好友", "category": "BONUS", "points": 1000, "growth": 50, "daily_cap": 5000},
)

RULES_BY_CODE: dict[str, dict[str, Any]] = {rule["code"]: dict(rule) for rule in POINTS_RULES}
for _rule in RULES_BY_CODE.values():
    _rule.setdefault("description", "")
    _rule.setdefault("enabled", True)

MEMBERSHIP_PLANS: tuple[dict[str, Any], ...] = (
    {
        "code": "pro_monthly",
        "tier": "PRO",
        "tier_name": "PRO 创客",
        "period_months": 1,
        "price_cny": 19.9,
        "points_price": 2400,
        "recommended": False,
        "benefits": [
            "政策资格匹配无限次",
            "AI 文书生成 100 篇 / 月",
            "全量模板库",
            "PDF / Word 导出",
            "需求投标 20 个 / 月",
            "积分获取 1.2x",
            "积分兑换 95 折",
            "优先工单 24h",
        ],
        "quotas": {"policy_match": -1, "ai_document": 100, "demand_bid": 20},
    },
    {
        "code": "pro_yearly",
        "tier": "PRO",
        "tier_name": "PRO 创客",
        "period_months": 12,
        "price_cny": 199.0,
        "points_price": 24000,
        "recommended": True,
        "benefits": [
            "政策资格匹配无限次",
            "AI 文书生成 100 篇 / 月",
            "全量模板库",
            "PDF / Word 导出",
            "需求投标 20 个 / 月",
            "积分获取 1.2x",
            "积分兑换 95 折",
            "优先工单 24h",
            "年付相当于 10 个月",
        ],
        "quotas": {"policy_match": -1, "ai_document": 100, "demand_bid": 20},
    },
    {
        "code": "black_monthly",
        "tier": "BLACK_DIAMOND",
        "tier_name": "黑钻创客 VIP",
        "period_months": 1,
        "price_cny": 89.0,
        "points_price": 10800,
        "recommended": False,
        "benefits": [
            "PRO 全部权益",
            "AI 文书生成 300 篇 / 月 + 优先队列",
            "模板库全量 + 1 次定制",
            "PDF / Word / Excel 批量导出",
            "需求投标无限 + 顶格优先派单",
            "内容分发权重 1.5x",
            "积分获取 1.5x",
            "积分兑换 9 折",
            "1v1 客服 4h",
        ],
        "quotas": {"policy_match": -1, "ai_document": 300, "demand_bid": -1},
    },
    {
        "code": "black_yearly",
        "tier": "BLACK_DIAMOND",
        "tier_name": "黑钻创客 VIP",
        "period_months": 12,
        "price_cny": 899.0,
        "points_price": 108000,
        "recommended": False,
        "benefits": [
            "PRO 全部权益",
            "AI 文书生成 300 篇 / 月 + 优先队列",
            "模板库全量 + 1 次定制",
            "PDF / Word / Excel 批量导出",
            "需求投标无限 + 顶格优先派单",
            "内容分发权重 1.5x",
            "积分获取 1.5x",
            "积分兑换 9 折",
            "1v1 客服 4h",
            "年度实体礼",
        ],
        "quotas": {"policy_match": -1, "ai_document": 300, "demand_bid": -1},
    },
)

PLANS_BY_CODE: dict[str, dict[str, Any]] = {plan["code"]: dict(plan) for plan in MEMBERSHIP_PLANS}

REWARD_ITEMS: tuple[dict[str, Any], ...] = (
    {"code": "membership_pro_monthly", "name": "PRO 创客月卡", "type": "MEMBERSHIP", "points_price": 2400, "stock": -1, "per_user_limit": 24, "icon": "spark", "description": "解锁 PRO 创客全部功能额度 1 个月，可叠加续期。", "meta": {"tier": "PRO", "months": 1}},
    {"code": "membership_pro_yearly", "name": "PRO 创客年卡", "type": "MEMBERSHIP", "points_price": 24000, "stock": -1, "per_user_limit": 12, "icon": "spark", "description": "解锁 PRO 创客全部功能额度 12 个月，可叠加续期。", "meta": {"tier": "PRO", "months": 12}},
    {"code": "membership_black_monthly", "name": "黑钻创客月卡", "type": "MEMBERSHIP", "points_price": 10800, "stock": -1, "per_user_limit": 24, "icon": "gem", "description": "解锁黑钻创客全部权益 1 个月，含顶格优先派单与 1v1 客服。", "meta": {"tier": "BLACK_DIAMOND", "months": 1}},
    {"code": "membership_black_yearly", "name": "黑钻创客年卡", "type": "MEMBERSHIP", "points_price": 108000, "stock": -1, "per_user_limit": 12, "icon": "gem", "description": "解锁黑钻创客全部权益 12 个月，含年度实体礼。", "meta": {"tier": "BLACK_DIAMOND", "months": 12}},
    {"code": "physical_sticker_pack", "name": "晨昏线外 贴纸包", "type": "PHYSICAL", "points_price": 1500, "stock": 500, "per_user_limit": 3, "icon": "gift", "description": "一套 12 枚哑光贴纸，适合贴在笔记本与电脑外壳。", "meta": {"shipping": True}},
    {"code": "physical_badge", "name": "亚克力创客徽章", "type": "PHYSICAL", "points_price": 3000, "stock": 300, "per_user_limit": 3, "icon": "gift", "description": "磨砂亚克力材质，附磁吸背扣。", "meta": {"shipping": True}},
    {"code": "physical_lanyard", "name": "创客工牌 + 挂绳", "type": "PHYSICAL", "points_price": 4500, "stock": 200, "per_user_limit": 2, "icon": "gift", "description": "可写名字的工牌卡套与织带挂绳，线下活动必备。", "meta": {"shipping": True}},
    {"code": "physical_tote", "name": "晨昏线外 帆布袋", "type": "PHYSICAL", "points_price": 6000, "stock": 150, "per_user_limit": 2, "icon": "gift", "description": "12 盎司加厚帆布，单色丝印，通勤容量。", "meta": {"shipping": True}},
    {"code": "physical_yearbook", "name": "年度创客年鉴", "type": "PHYSICAL", "points_price": 12000, "stock": 80, "per_user_limit": 1, "icon": "book", "description": "年度精选政策、文书与创客故事合集，限量编号。", "meta": {"shipping": True}},
    {"code": "physical_desk_toy", "name": "桌面晨昏线摆件", "type": "PHYSICAL", "points_price": 15000, "stock": 60, "per_user_limit": 1, "icon": "gift", "description": "黄铜与胡桃木组合的桌面摆件，刻有创客编号。", "meta": {"shipping": True}},
    {"code": "physical_collab", "name": "联名限量款", "type": "PHYSICAL", "points_price": 30000, "stock": 20, "per_user_limit": 1, "icon": "gem", "description": "与生态伙伴联名的年度限量单品，兑完即止。", "meta": {"shipping": True}},
    {"code": "digital_exposure_24h", "name": "内容置顶 24 小时", "type": "DIGITAL", "points_price": 3000, "stock": -1, "per_user_limit": 4, "icon": "bolt", "description": "为一条已发布内容增加 24 小时置顶曝光，每人每周限 1 次。", "meta": {"effect": "EXPOSURE_24H"}},
    {"code": "digital_quality_apply", "name": "优质内容申请", "type": "DIGITAL", "points_price": 5000, "stock": -1, "per_user_limit": 4, "icon": "star", "description": "提交一条内容申请加精，审核不通过全额退还积分。", "meta": {"effect": "QUALITY_REVIEW"}},
    {"code": "digital_ai_pack", "name": "AI 文书加量包 50 篇", "type": "DIGITAL", "points_price": 2000, "stock": -1, "per_user_limit": 12, "icon": "spark", "description": "在当前会员额度之外增加 50 篇 AI 文书生成次数。", "meta": {"effect": "AI_PACK_50"}},
    {"code": "digital_template_unlock", "name": "单模板解锁券", "type": "DIGITAL", "points_price": 800, "stock": -1, "per_user_limit": 20, "icon": "file", "description": "解锁任意一个付费模板的永久使用权。", "meta": {"effect": "TEMPLATE_UNLOCK"}},
    {"code": "digital_rename_card", "name": "改名卡", "type": "DIGITAL", "points_price": 1000, "stock": -1, "per_user_limit": 4, "icon": "pen", "description": "修改一次创客昵称，90 天内限用 1 次。", "meta": {"effect": "RENAME"}},
)

ITEMS_BY_CODE: dict[str, dict[str, Any]] = {
    item["code"]: {**item, "active": bool(item.get("active", True))} for item in REWARD_ITEMS
}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pretty(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _now(value: Any = None) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = _text(value)
        parsed = None
        if text:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                parsed = None
    if parsed is None:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_dt(value: Any) -> Optional[datetime]:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _add_months(moment: datetime, months: int) -> datetime:
    month_index = moment.month - 1 + int(months)
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(moment.day, days[month - 1])
    return moment.replace(year=year, month=month, day=day)


def _rule(event: str) -> Optional[dict[str, Any]]:
    return RULES_BY_CODE.get(_text(event).upper())


def _default_idempotency(
    event: str,
    uid: str,
    actor_id: str,
    target_type: str,
    target_id: str,
    rule: Optional[dict[str, Any]],
    day: str,
) -> str:
    event = _text(event).upper()
    if rule and rule.get("once"):
        return f"once:{event}:{uid}"
    if event == "RECEIVE_READ":
        return f"read:{actor_id}:{target_type}:{target_id}:{day}"
    if event.startswith("RECEIVE_") and target_id:
        return f"interaction:{event}:{actor_id}:{target_type}:{target_id}"
    if event.startswith("PUBLISH_") and target_id:
        return f"publish:{target_type}:{target_id}"
    return f"{event}:{uid}:{actor_id}:{target_type}:{target_id}:{day}"


def level_info(growth: int) -> dict[str, Any]:
    """Map growth points to the V1-V6 maker level."""
    growth = max(0, _int(growth))
    current = LEVELS[0]
    next_threshold = LEVELS[1][0] if len(LEVELS) > 1 else LEVELS[0][0]
    for index, row in enumerate(LEVELS):
        if growth >= row[0]:
            current = row
            next_threshold = LEVELS[index + 1][0] if index + 1 < len(LEVELS) else row[0]
    threshold, level, name, multiplier = current
    if next_threshold <= threshold:
        progress = 100.0
    else:
        progress = round(min(100.0, max(0.0, (growth - threshold) / (next_threshold - threshold) * 100)), 1)
    return {
        "level": level,
        "level_name": name,
        "next_level_growth": next_threshold,
        "level_progress": progress,
        "level_multiplier": multiplier,
    }


def membership_benefits(tier: str) -> list[str]:
    candidates = [plan for plan in MEMBERSHIP_PLANS if plan["tier"] == tier]
    if not candidates:
        return []
    candidates.sort(key=lambda plan: plan["period_months"], reverse=True)
    return list(candidates[0]["benefits"])


def membership_multiplier(membership: Any, now: Any = None) -> float:
    doc = _pretty(membership)
    if not doc:
        return 1.0
    expires = _parse_dt(doc.get("expires_at"))
    if _text(doc.get("status") or "ACTIVE").upper() != "ACTIVE":
        return 1.0
    if expires is not None and expires <= _now(now):
        return 1.0
    return TIER_MULTIPLIERS.get(_text(doc.get("tier")).upper(), 1.0)


def membership_view(membership: Any, now: Any = None) -> dict[str, Any]:
    """Project a stored membership document into the public ``MembershipInfo`` shape."""
    doc = _pretty(membership)
    reference = _now(now)
    if not doc:
        return {
            "uid": "",
            "tier": "STANDARD",
            "tier_name": TIER_NAMES["STANDARD"],
            "source": "",
            "status": "NONE",
            "plan_code": "",
            "started_at": "",
            "expires_at": "",
            "days_left": 0,
            "auto_renew": False,
            "benefits": [],
        }
    expires = _parse_dt(doc.get("expires_at"))
    status = _text(doc.get("status") or "ACTIVE").upper()
    if expires is not None and expires <= reference and status == "ACTIVE":
        status = "EXPIRED"
    if status == "EXPIRED":
        return {
            "uid": _text(doc.get("uid")),
            "tier": "STANDARD",
            "tier_name": TIER_NAMES["STANDARD"],
            "source": _text(doc.get("source")),
            "status": "EXPIRED",
            "plan_code": _text(doc.get("plan_code")),
            "started_at": _text(doc.get("started_at")),
            "expires_at": _text(doc.get("expires_at")),
            "days_left": 0,
            "auto_renew": bool(doc.get("auto_renew", False)),
            "benefits": [],
        }
    tier = _text(doc.get("tier") or "STANDARD").upper()
    days_left = 0
    if expires is not None:
        days_left = max(0, math.ceil((expires - reference).total_seconds() / 86400))
    return {
        "uid": _text(doc.get("uid")),
        "tier": tier,
        "tier_name": TIER_NAMES.get(tier, tier),
        "source": _text(doc.get("source")),
        "status": status,
        "plan_code": _text(doc.get("plan_code")),
        "started_at": _text(doc.get("started_at")),
        "expires_at": _text(doc.get("expires_at")),
        "days_left": days_left,
        "auto_renew": bool(doc.get("auto_renew", False)),
        "benefits": membership_benefits(tier),
    }


def normalise_account(uid: str, account: Any) -> dict[str, Any]:
    doc = _pretty(account)
    return {
        "uid": _text(uid) or _text(doc.get("uid")),
        "balance": _int(doc.get("balance")),
        "frozen": _int(doc.get("frozen")),
        "debt": _int(doc.get("debt")),
        "total_earned": _int(doc.get("total_earned")),
        "total_spent": _int(doc.get("total_spent")),
        "growth": _int(doc.get("growth")),
        "reputation": _int(doc.get("reputation"), 80) or 80,
        "updated_at": _text(doc.get("updated_at")),
    }


def _aggregate(
    ledger: Iterable[Any],
    uid: str,
    event: str,
    day: str,
    month: str,
    target_id: str,
    actor_id: str,
) -> dict[str, int]:
    daily = daily_total = monthly_total = target_daily = pair_daily = 0
    for raw in ledger or []:
        entry = _pretty(raw)
        delta = _int(entry.get("delta"))
        if delta <= 0 or _text(entry.get("status")).upper() == "REVOKED":
            continue
        if _text(entry.get("uid")) != uid:
            continue
        if _text(entry.get("event_code")).upper() == "ADMIN_ADJUST":
            continue
        created = _text(entry.get("created_at"))
        entry_day = created[:10]
        entry_month = created[:7]
        entry_event = _text(entry.get("event_code")).upper()
        if entry_day == day:
            daily_total += delta
        if entry_month == month:
            monthly_total += delta
        if entry_event == event and entry_day == day:
            daily += delta
        if event and entry_event == event and entry_day == day and target_id and _text(entry.get("ref_id")) == target_id:
            target_daily += delta
        if (
            entry_event.startswith("RECEIVE_")
            and entry_day == day
            and actor_id
            and _text(entry.get("actor_id")) == actor_id
        ):
            pair_daily += 1
    return {
        "daily": daily,
        "daily_total": daily_total,
        "monthly_total": monthly_total,
        "target_daily": target_daily,
        "pair_daily": pair_daily,
    }


def _scaled_points(base: int, growth: int, reputation: int, membership: Any, now: Any) -> int:
    if base <= 0:
        return 0
    reputation = _int(reputation, 80) or 80
    if reputation < 60:
        return 0
    level_mult = float(level_info(growth)["level_multiplier"])
    rep_mult = 1.0 if reputation >= 80 else 0.5
    member_mult = membership_multiplier(membership, now)
    total = min(2.0, level_mult * rep_mult * member_mult)
    return max(1, int(round(base * total)))


def build_account(
    uid: str,
    account: Any,
    membership: Any = None,
    ledger: Iterable[Any] = (),
    now: Any = None,
) -> dict[str, Any]:
    """Assemble the public ``PointsAccount`` projection."""
    reference = _now(now)
    base = normalise_account(uid, account)
    view = membership_view(membership, reference)
    info = level_info(base["growth"])
    day = reference.date().isoformat()
    month = reference.strftime("%Y-%m")
    today_earned = month_earned = 0
    for raw in ledger or []:
        entry = _pretty(raw)
        delta = _int(entry.get("delta"))
        if delta <= 0 or _text(entry.get("status")).upper() == "REVOKED":
            continue
        if _text(entry.get("uid")) != base["uid"]:
            continue
        if _text(entry.get("event_code")).upper() == "ADMIN_ADJUST":
            continue
        created = _text(entry.get("created_at"))
        if created[:10] == day:
            today_earned += delta
        if created[:7] == month:
            month_earned += delta
    return {
        "uid": base["uid"],
        "balance": base["balance"],
        "frozen": base["frozen"],
        "debt": base["debt"],
        "total_earned": base["total_earned"],
        "total_spent": base["total_spent"],
        "growth": base["growth"],
        "level": info["level"],
        "level_name": info["level_name"],
        "next_level_growth": info["next_level_growth"],
        "level_progress": info["level_progress"],
        "reputation": base["reputation"],
        "membership_tier": view["tier"],
        "membership_tier_name": view["tier_name"],
        "membership_expires_at": view["expires_at"],
        "today_earned": today_earned,
        "month_earned": month_earned,
        "updated_at": base["updated_at"],
    }


def rules_payload() -> dict[str, Any]:
    items = [dict(rule) for rule in POINTS_RULES if rule.get("enabled", True)]
    items.sort(key=lambda rule: (CATEGORY_ORDER.get(rule.get("category"), 9), rule["code"]))
    return {
        "items": items,
        "daily_global_cap": DAILY_GLOBAL_CAP,
        "monthly_global_cap": MONTHLY_GLOBAL_CAP,
        "expiry_months": POINTS_EXPIRY_MONTHS,
    }


def plans_payload(membership: Any = None) -> dict[str, Any]:
    view = membership_view(membership)
    items = sorted(MEMBERSHIP_PLANS, key=lambda plan: (TIER_ORDER.get(plan["tier"], 9), plan["period_months"]))
    return {
        "items": [dict(plan) for plan in items],
        "current_tier": view["tier"],
        "current_tier_name": view["tier_name"],
    }


def rewards_payload(items: Iterable[Any], balance: int = 0) -> dict[str, Any]:
    rows = [_pretty(row) for row in items or []]
    active = [row for row in rows if row.get("active", True)]
    active.sort(key=lambda row: (ITEM_TYPE_ORDER.get(_text(row.get("type")).upper(), 9), _int(row.get("points_price"))))
    return {"items": active, "balance": _int(balance)}


def ledger_page(
    items: Iterable[Any],
    uid: str,
    limit: int = 50,
    offset: int = 0,
    event_code: str = "",
    balance: int = 0,
) -> dict[str, Any]:
    rows = [_pretty(row) for row in items or []]
    rows = [row for row in rows if _text(row.get("uid")) == _text(uid)]
    if event_code:
        rows = [row for row in rows if _text(row.get("event_code")).upper() == _text(event_code).upper()]
    rows.sort(key=lambda row: _text(row.get("created_at")), reverse=True)
    total = len(rows)
    start = max(0, _int(offset))
    size = max(1, min(_int(limit, 50) or 50, 200))
    return {"items": rows[start: start + size], "total": total, "balance": _int(balance)}


def orders_payload(items: Iterable[Any], uid: str) -> dict[str, Any]:
    rows = [_pretty(row) for row in items or []]
    rows = [row for row in rows if _text(row.get("uid")) == _text(uid)]
    rows.sort(key=lambda row: _text(row.get("created_at")), reverse=True)
    return {"items": rows, "total": len(rows)}


# ---------------------------------------------------------------------------
# Award / revoke / admin calculations
# ---------------------------------------------------------------------------
@operator(
    "calc.loyalty.event",
    category="CALC",
    description="Normalise one points event (code / kind / target / rule / owner entity)",
)
def event(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    event_code = _text(args.get("event_code")).upper()
    if not event_code:
        event_code = KIND_TO_EVENT.get(_text(args.get("kind")).upper(), "")
    target_type = _text(args.get("target_type")).upper()
    target_id = _text(args.get("target_id"))
    rule = _rule(event_code)
    return {
        "event_code": event_code,
        "kind": _text(args.get("kind")).upper(),
        "target_type": target_type,
        "target_id": target_id,
        "target_entity": TARGET_ENTITIES.get(target_type),
        "user_id": _text(args.get("user_id")),
        "actor_id": _text(args.get("actor_id")) or _text(context.get("user_id")),
        "quantity": max(1, _int(args.get("quantity"), 1) or 1),
        "rule_code": _text((rule or {}).get("code")),
        "rule_found": rule is not None,
    }


@operator(
    "calc.loyalty.resolve",
    category="CALC",
    description="Resolve the award recipient, target title and idempotency key",
)
def resolve(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    event_code = _text(args.get("event_code")).upper()
    rule = _rule(event_code)
    target = _pretty(args.get("target"))
    target_type = _text(args.get("target_type")).upper()
    target_id = _text(args.get("target_id"))
    explicit_uid = _text(args.get("user_id"))
    target_author = ""
    for field_name in ("author_id", "creator_id", "owner_id", "user_id"):
        if _text(target.get(field_name)):
            target_author = _text(target.get(field_name))
            break
    uid = explicit_uid or target_author
    actor_id = _text(args.get("actor_id")) or _text(context.get("user_id"))
    now = _now(args.get("now"))
    day = now.date().isoformat()
    key = _text(args.get("idempotency_key"))
    if not key:
        key = _default_idempotency(event_code, uid, actor_id, target_type, target_id, rule, day)
    title = ""
    for field_name in ("title", "name", "document_title"):
        if _text(target.get(field_name)):
            title = _text(target.get(field_name))
            break
    return {
        "event_code": event_code,
        "user_id": uid,
        "target_author": target_author,
        "actor_id": actor_id,
        "target_type": target_type,
        "target_id": target_id,
        "target_title": title,
        "quantity": max(1, _int(args.get("quantity"), 1) or 1),
        "idempotency_key": key,
        "now": now.isoformat(),
    }


@operator(
    "calc.loyalty.settle",
    category="CALC",
    description="Settle one points award (caps / idempotency / level growth) or an uncapped admin delta",
)
def settle(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    admin_mode = bool(args.get("admin_mode") or params.get("admin_mode"))
    event_code = _text(args.get("event_code")).upper() or ("ADMIN_ADJUST" if admin_mode else "")
    uid = _text(args.get("user_id"))
    actor_id = _text(args.get("actor_id"))
    target_type = _text(args.get("target_type")).upper()
    target_id = _text(args.get("target_id"))
    title_hint = _text(args.get("target_title"))
    note = _text(args.get("note"))
    quantity = max(1, _int(args.get("quantity"), 1) or 1)
    now = _now(args.get("now"))
    day = now.date().isoformat()
    month = now.strftime("%Y-%m")
    rule = _rule(event_code)
    account = normalise_account(uid, args.get("account"))
    ledger = list(args.get("ledger") or [])

    def _reject(reason: str, delta: int = 0) -> dict[str, Any]:
        info = level_info(account["growth"])
        return {
            "allowed": False,
            "reason": reason,
            "loyalty_awarded": False,
            "loyalty_reason": reason,
            "awarded": False,
            "uid": uid,
            "user_id": uid,
            "actor_id": actor_id,
            "event_code": event_code,
            "rule_code": _text((rule or {}).get("code")),
            "rule_name": _text((rule or {}).get("name")),
            "base_points": 0,
            "delta": delta,
            "growth": 0,
            "target_type": target_type,
            "target_id": target_id,
            "idempotency_key": _text(args.get("idempotency_key")),
            "account": account,
            "ledger": None,
            "balance": account["balance"],
            "level": info["level"],
            "level_name": info["level_name"],
            "next_level_growth": info["next_level_growth"],
            "level_progress": info["level_progress"],
        }

    if not uid:
        return _reject("missing_user")

    admin_delta = _int(args.get("admin_delta") if args.get("admin_delta") is not None else args.get("delta"))
    key = _text(args.get("idempotency_key"))
    if not key:
        if admin_mode:
            key = f"admin:{uid}:{actor_id}:{admin_delta}:{now.isoformat()}"
        else:
            key = _default_idempotency(event_code, uid, actor_id, target_type, target_id, rule, day)

    if not admin_mode:
        if rule is None or not rule.get("enabled", True):
            return _reject("rule_disabled")
        if _int(rule.get("points")) <= 0:
            return _reject("rule_zero_points")
        if event_code.startswith("RECEIVE_") and actor_id and actor_id == uid:
            return _reject("self_interaction")

    if any(_text(_pretty(entry).get("idempotency_key")) == key for entry in ledger):
        return _reject("duplicate")

    if admin_mode:
        delta = admin_delta
        if delta == 0:
            return _reject("invalid_delta")
        growth = 0
        base_points = abs(delta)
    else:
        base = _int(rule.get("points")) * quantity
        delta = _scaled_points(base, account["growth"], account["reputation"], args.get("membership"), now)
        growth = max(0, _int(rule.get("growth")))
        base_points = base
        if delta <= 0:
            return _reject("reputation_blocked")

        usage = _aggregate(ledger, uid, event_code, day, month, target_id, actor_id)
        daily_cap = _int(rule.get("daily_cap"), 0)
        if daily_cap > 0:
            delta = min(delta, max(0, daily_cap - usage["daily"]))
        monthly_cap = _int(rule.get("monthly_cap"), 0)
        if monthly_cap > 0:
            delta = min(delta, max(0, monthly_cap - usage["monthly_total"]))
        per_target_cap = _int(rule.get("per_target_cap"), 0)
        if per_target_cap > 0 and target_id:
            delta = min(delta, max(0, per_target_cap - usage["target_daily"]))
        delta = min(delta, max(0, DAILY_GLOBAL_CAP - usage["daily_total"]))
        delta = min(delta, max(0, MONTHLY_GLOBAL_CAP - usage["monthly_total"]))
        if event_code.startswith("RECEIVE_") and actor_id and usage["pair_daily"] >= PAIR_DAILY_LIMIT:
            return _reject("pair_daily_cap")
        if delta <= 0:
            return _reject("daily_cap_reached")

    balance = account["balance"] + delta
    total_earned = account["total_earned"]
    total_spent = account["total_spent"]
    if delta > 0:
        total_earned += delta
    else:
        total_spent += abs(delta)
    new_account = {
        **account,
        "uid": uid,
        "balance": balance,
        "debt": abs(balance) if balance < 0 else 0,
        "total_earned": total_earned,
        "total_spent": total_spent,
        "growth": account["growth"] + growth,
        "updated_at": now.isoformat(),
    }
    info = level_info(new_account["growth"])
    ledger_title = "运营积分调整" if admin_mode else _text((rule or {}).get("name")) or event_code
    entry = {
        "uid": uid,
        "event_code": "ADMIN_ADJUST" if admin_mode else event_code,
        "title": ledger_title,
        "delta": delta,
        "balance_after": balance,
        "status": "SETTLED",
        "ref_type": "ADMIN" if admin_mode else target_type,
        "ref_id": actor_id if admin_mode else target_id,
        "actor_id": actor_id,
        "idempotency_key": key,
        "note": note or ("" if admin_mode else title_hint),
        "expires_at": _add_months(now, POINTS_EXPIRY_MONTHS).isoformat() if delta > 0 else "",
        "created_at": now.isoformat(),
    }
    return {
        "allowed": True,
        "reason": "",
        "loyalty_awarded": True,
        "loyalty_reason": "",
        "awarded": True,
        "adjusted": admin_mode,
        "uid": uid,
        "user_id": uid,
        "actor_id": actor_id,
        "event_code": entry["event_code"],
        "rule_code": _text((rule or {}).get("code")),
        "rule_name": ledger_title,
        "base_points": base_points,
        "delta": delta,
        "growth": growth,
        "target_type": target_type,
        "target_id": target_id,
        "idempotency_key": key,
        "account": new_account,
        "ledger": entry,
        "balance": balance,
        "growth_total": new_account["growth"],
        "level": info["level"],
        "level_name": info["level_name"],
        "next_level_growth": info["next_level_growth"],
        "level_progress": info["level_progress"],
    }


@operator(
    "calc.loyalty.revoke",
    category="CALC",
    description="Plan the reversal of one previously settled award (idempotent tombstone)",
)
def revoke(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    event_code = _text(args.get("event_code")).upper()
    uid = _text(args.get("user_id"))
    actor_id = _text(args.get("actor_id"))
    target_type = _text(args.get("target_type")).upper()
    target_id = _text(args.get("target_id"))
    now = _now(args.get("now"))
    day = now.date().isoformat()
    ledger = [_pretty(row) for row in (args.get("ledger") or [])]
    key = _text(args.get("idempotency_key"))
    if not key and event_code:
        key = _default_idempotency(
            event_code, uid, actor_id, target_type, target_id, _rule(event_code), day
        )

    original: Optional[dict[str, Any]] = None
    for entry in ledger:
        if _int(entry.get("delta")) <= 0:
            continue
        if key and _text(entry.get("idempotency_key")) == key:
            original = entry
            break
    if original is None:
        return {"revoked": False, "loyalty_revoked": False, "reason": "not_found", "delta": 0, "ledger": None}
    if _text(original.get("status")).upper() == "REVOKED":
        return {
            "revoked": False,
            "loyalty_revoked": False,
            "reason": "already_revoked",
            "delta": 0,
            "uid": _text(original.get("uid")),
            "original_id": _text(original.get("id")),
            "ledger": None,
        }

    uid = _text(original.get("uid")) or uid
    actor_id = actor_id or _text(original.get("actor_id"))
    target_type = target_type or _text(original.get("ref_type"))
    target_id = target_id or _text(original.get("ref_id"))
    accounts = [_pretty(row) for row in (args.get("accounts") or [])]
    account = normalise_account(uid, next((row for row in accounts if _text(row.get("uid")) == uid), None))
    delta = _int(original.get("delta"))
    if delta == 0:
        return {"revoked": False, "loyalty_revoked": False, "reason": "zero_delta", "delta": 0, "ledger": None}

    balance = account["balance"] - delta
    new_account = {
        **account,
        "uid": uid,
        "balance": balance,
        "debt": abs(balance) if balance < 0 else 0,
        "total_earned": max(0, account["total_earned"] - max(0, delta)),
        "updated_at": now.isoformat(),
    }
    reversal_event = f"{event_code or _text(original.get('event_code'))}_REVOKE"
    reversal = {
        "uid": uid,
        "event_code": reversal_event,
        "title": f"撤销 · {_text(original.get('title')) or reversal_event}",
        "delta": -delta,
        "balance_after": balance,
        "status": "SETTLED",
        "ref_type": target_type,
        "ref_id": target_id,
        "actor_id": actor_id,
        "idempotency_key": f"revoke:{_text(original.get('id'))}",
        "note": "互动取消或内容下架回滚",
        "expires_at": "",
        "created_at": now.isoformat(),
    }
    return {
        "revoked": True,
        "loyalty_revoked": True,
        "reason": "",
        "delta": -delta,
        "uid": uid,
        "user_id": uid,
        "actor_id": actor_id,
        "target_type": target_type,
        "target_id": target_id,
        "original_id": _text(original.get("id")),
        "original_patch": {"id": _text(original.get("id")), "status": "REVOKED", "updated_at": now.isoformat()},
        "account": new_account,
        "ledger": reversal,
        "balance": balance,
    }


# ---------------------------------------------------------------------------
# Redemption calculations
# ---------------------------------------------------------------------------
@operator(
    "calc.loyalty.redeem",
    category="CALC",
    description="Check redemption eligibility and plan the debit, stock patch and order document",
)
def redeem(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(args.get("uid")) or _text(context.get("user_id"))
    item = _pretty(args.get("item"))
    qty = max(1, min(_int(args.get("qty"), 1) or 1, 10))
    address = args.get("address")
    account = normalise_account(uid, args.get("account"))
    now = _now(args.get("now"))
    orders = [_pretty(row) for row in (args.get("orders") or [])]
    membership = _pretty(args.get("membership"))
    key = _text(args.get("idempotency_key"))

    def _reject(reason: str) -> dict[str, Any]:
        return {
            "allowed": False,
            "reason": reason,
            "loyalty_redeemed": False,
            "loyalty_reason": reason,
            "duplicate": False,
            "qty": qty,
            "cost": 0,
            "item": item or None,
            "item_type": _text(item.get("type")).upper(),
            "membership_required": _text(item.get("type")).upper() == "MEMBERSHIP",
            "order": None,
            "existing_order": None,
            "account": account,
            "ledger": None,
            "stock_patch": None,
            "balance": account["balance"],
        }

    if not uid:
        return _reject("missing_user")
    if not item or not bool(item.get("active", True)):
        return _reject("item_unavailable")

    if key:
        for order in orders:
            if _text(order.get("idempotency_key")) == key and _text(order.get("status")).upper() != "CANCELLED":
                return {
                    "allowed": True,
                    "reason": "",
                    "duplicate": True,
                    "loyalty_redeemed": True,
                    "loyalty_reason": "",
                    "qty": _int(order.get("qty"), 1),
                    "cost": _int(order.get("points_cost")),
                    "item": item,
                    "item_type": _text(item.get("type")).upper(),
                    "membership_required": _text(item.get("type")).upper() == "MEMBERSHIP",
                    "order": None,
                    "existing_order": order,
                    "account": account,
                    "ledger": None,
                    "stock_patch": None,
                    "balance": account["balance"],
                }

    item_type = _text(item.get("type")).upper()
    stock = _int(item.get("stock"), 0)
    if stock >= 0 and stock < qty:
        return _reject("out_of_stock")
    if item_type == "PHYSICAL" and not address:
        return _reject("address_required")
    if item_type == "MEMBERSHIP":
        meta = _pretty(item.get("meta"))
        target_tier = _text(meta.get("tier") or "PRO").upper()
        view = membership_view(membership, now)
        if view["status"] == "ACTIVE" and TIER_ORDER.get(view["tier"], 0) > TIER_ORDER.get(target_tier, 0):
            return _reject("higher_tier_active")
    used = sum(
        1
        for order in orders
        if _text(order.get("uid")) == uid
        and _text(order.get("item_code")) == _text(item.get("code"))
        and _text(order.get("status")).upper() != "CANCELLED"
    )
    limit = _int(item.get("per_user_limit"), 0)
    if limit > 0 and used + qty > limit:
        return _reject("per_user_limit")
    cost = _int(item.get("points_price")) * qty
    if account["balance"] < cost:
        return _reject("insufficient_points")
    if account["debt"] > 0:
        return _reject("debt_pending")

    balance = account["balance"] - cost
    new_account = {
        **account,
        "uid": uid,
        "balance": balance,
        "debt": abs(balance) if balance < 0 else 0,
        "total_spent": account["total_spent"] + cost,
        "updated_at": now.isoformat(),
    }
    status = "COMPLETED" if item_type in ("MEMBERSHIP", "DIGITAL") else "PAID"
    order = {
        "uid": uid,
        "item_code": _text(item.get("code")),
        "item_name": _text(item.get("name")),
        "item_type": item_type,
        "qty": qty,
        "points_cost": cost,
        "status": status,
        "address": address if item_type == "PHYSICAL" else None,
        "tracking_no": "",
        "note": "实物兑换已受理，等待发货" if item_type == "PHYSICAL" else "",
        "idempotency_key": key,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    ledger = {
        "uid": uid,
        "event_code": "REDEEM_ITEM",
        "title": f"兑换 · {_text(item.get('name'))}",
        "delta": -cost,
        "balance_after": balance,
        "status": "SETTLED",
        "ref_type": item_type,
        "ref_id": "",
        "actor_id": uid,
        "idempotency_key": f"redeem:{key or now.isoformat()}",
        "note": f"×{qty}",
        "expires_at": "",
        "created_at": now.isoformat(),
    }
    stock_patch = None
    if stock >= 0:
        stock_patch = {"code": _text(item.get("code")), "stock": max(0, stock - qty)}
    return {
        "allowed": True,
        "reason": "",
        "duplicate": False,
        "loyalty_redeemed": True,
        "loyalty_reason": "",
        "qty": qty,
        "cost": cost,
        "item": item,
        "item_type": item_type,
        "membership_required": item_type == "MEMBERSHIP",
        "order": order,
        "existing_order": None,
        "account": new_account,
        "ledger": ledger,
        "stock_patch": stock_patch,
        "balance": balance,
        "message": "兑换成功，实物将尽快发出" if item_type == "PHYSICAL" else "兑换成功",
    }


# ---------------------------------------------------------------------------
# Membership calculations
# ---------------------------------------------------------------------------
@operator(
    "calc.loyalty.membership",
    category="CALC",
    description="Plan a membership purchase / redemption / renewal / expiry / auto-renew toggle",
)
def membership(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    action = _text(args.get("action") or params.get("action") or "SUBSCRIBE").upper()
    uid = _text(args.get("uid")) or _text(context.get("user_id"))
    now = _now(args.get("now"))
    current = _pretty(args.get("membership"))
    current_view = membership_view(current, now)
    orders = [_pretty(row) for row in (args.get("orders") or [])]
    account = normalise_account(uid, args.get("account"))
    key = _text(args.get("idempotency_key"))

    if action == "EXPIRE":
        if not current:
            return {"allowed": False, "reason": "not_found", "membership": None}
        if current_view["status"] != "EXPIRED":
            return {"allowed": False, "reason": "not_expired", "membership": current}
        expired = {**current, "status": "EXPIRED", "updated_at": now.isoformat()}
        return {"allowed": True, "reason": "", "membership": expired, "view": membership_view(expired, now)}

    if action == "AUTO_RENEW":
        if not current:
            return {"allowed": False, "reason": "no_membership", "membership": None}
        updated = {
            **current,
            "auto_renew": bool(args.get("enabled", False)),
            "updated_at": now.isoformat(),
        }
        return {"allowed": True, "reason": "", "membership": updated, "view": membership_view(updated, now)}

    if action == "REDEEM":
        meta = _pretty(args.get("meta")) or _pretty(args.get("item"))
        meta = _pretty(meta.get("meta")) or meta
        target_tier = _text(meta.get("tier") or args.get("tier") or "PRO").upper()
        months = max(1, _int(meta.get("months") or args.get("months"), 1) or 1) * max(1, _int(args.get("qty"), 1) or 1)
        source = "POINTS"
        plan_code = _text(args.get("item_code") or args.get("plan_code"))
        price_cny = 0.0
        points_cost = _int(meta.get("points_price"))
    else:
        plan = _pretty(args.get("plan")) or dict(PLANS_BY_CODE.get(_text(args.get("plan_code")), {}))
        if not plan:
            return {"allowed": False, "reason": "plan_not_found", "membership": None}
        target_tier = _text(plan.get("tier") or "PRO").upper()
        months = max(1, _int(plan.get("period_months"), 1) or 1)
        plan_code = _text(plan.get("code"))
        source = "CASH" if _text(args.get("pay_method")).upper() == "CASH" else "POINTS"
        price_cny = float(plan.get("price_cny") or 0.0)
        points_cost = _int(plan.get("points_price"))
        meta = {}

    if target_tier not in ("PRO", "BLACK_DIAMOND"):
        return {"allowed": False, "reason": f"unsupported_tier:{target_tier}", "membership": None}
    if current_view["status"] == "ACTIVE" and TIER_ORDER.get(current_view["tier"], 0) > TIER_ORDER.get(target_tier, 0):
        return {"allowed": False, "reason": "higher_tier_active", "membership": current or None}

    if action not in ("REDEEM", "EXPIRE", "AUTO_RENEW") and source == "POINTS":
        if key:
            for order in orders:
                if _text(order.get("idempotency_key")) == key and _text(order.get("status")).upper() != "CANCELLED":
                    return {
                        "allowed": True,
                        "reason": "",
                        "duplicate": True,
                        "membership": current or None,
                        "view": current_view,
                        "order": None,
                        "existing_order": order,
                        "account": account,
                        "ledger": None,
                        "points_cost": _int(order.get("points_cost")),
                    }
        if account["balance"] < points_cost:
            return {
                "allowed": False,
                "reason": "insufficient_points",
                "membership": None,
                "account": account,
                "points_cost": points_cost,
            }
    elif key:
        for order in orders:
            if _text(order.get("idempotency_key")) == key and _text(order.get("status")).upper() != "CANCELLED":
                return {
                    "allowed": True,
                    "reason": "",
                    "duplicate": True,
                    "membership": current or None,
                    "view": current_view,
                    "order": None,
                    "existing_order": order,
                    "account": account,
                    "ledger": None,
                    "points_cost": _int(order.get("points_cost")),
                }

    base = now
    if current_view["status"] == "ACTIVE" and current_view["tier"] == target_tier:
        expires = _parse_dt(current_view["expires_at"])
        if expires and expires > base:
            base = expires
    expires_at = _add_months(base, months)
    started_at = _text(current.get("started_at")) or now.isoformat()
    record = {
        "uid": uid,
        "tier": target_tier,
        "source": source if action != "REDEEM" else "POINTS",
        "status": "ACTIVE",
        "plan_code": plan_code,
        "started_at": started_at,
        "expires_at": expires_at.isoformat(),
        "auto_renew": bool(current.get("auto_renew", False)),
        "updated_at": now.isoformat(),
        "benefits": membership_benefits(target_tier),
    }
    order = {
        "uid": uid,
        "item_code": plan_code,
        "item_name": TIER_NAMES.get(target_tier, target_tier) + ("年卡" if months >= 12 else "月卡"),
        "item_type": "MEMBERSHIP",
        "qty": 1,
        "points_cost": points_cost if source == "POINTS" else 0,
        "status": "PENDING_PAYMENT" if source == "CASH" else "COMPLETED",
        "address": None,
        "tracking_no": "",
        "note": (
            f"应付 ¥{price_cny:.2f}，请通过收银台完成支付"
            if source == "CASH"
            else f"积分兑换，有效期至 {expires_at.date().isoformat()}"
        ),
        "idempotency_key": key,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    new_account = account
    ledger = None
    if action != "REDEEM" and source == "POINTS":
        balance = account["balance"] - points_cost
        new_account = {
            **account,
            "uid": uid,
            "balance": balance,
            "debt": abs(balance) if balance < 0 else 0,
            "total_spent": account["total_spent"] + points_cost,
            "updated_at": now.isoformat(),
        }
        ledger = {
            "uid": uid,
            "event_code": "SUBSCRIBE_MEMBERSHIP",
            "title": f"兑换会员 · {TIER_NAMES.get(target_tier, target_tier)}",
            "delta": -points_cost,
            "balance_after": balance,
            "status": "SETTLED",
            "ref_type": "MEMBERSHIP",
            "ref_id": "",
            "actor_id": uid,
            "idempotency_key": f"subscribe:{key or now.isoformat()}",
            "note": plan_code,
            "expires_at": "",
            "created_at": now.isoformat(),
        }
    return {
        "allowed": True,
        "reason": "",
        "duplicate": False,
        "membership": record,
        "view": membership_view(record, now),
        "order": order,
        "existing_order": None,
        "account": new_account,
        "ledger": ledger,
        "points_cost": points_cost if source == "POINTS" else 0,
        "payment_required": source == "CASH",
        "payment_amount_cny": price_cny,
        "tier": target_tier,
        "months": months,
        "source": source,
    }


# ---------------------------------------------------------------------------
# Query normalisers
# ---------------------------------------------------------------------------
@operator(
    "calc.loyalty.query",
    category="CALC",
    description="Normalise loyalty paging / event filters",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "limit": max(1, min(_int(args.get("limit"), 50) or 50, 200)),
        "offset": max(0, _int(args.get("offset"))),
        "event_code": _text(args.get("event_code")).upper(),
        "uid": _text(args.get("uid")) or _text(context.get("user_id")),
    }


@operator(
    "calc.loyalty.level",
    category="CALC",
    description="Map growth points to the V1-V6 maker level",
)
def level(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return level_info(_int(args.get("growth")))


# ---------------------------------------------------------------------------
# Assemblers
# ---------------------------------------------------------------------------
@operator("assemble.loyalty.account", category="ASSEMBLE", description="Assemble the points account projection")
def assemble_account(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    doc = build_account(
        _text(args.get("uid")) or _text(context.get("user_id")),
        args.get("account"),
        args.get("membership"),
        args.get("ledger") or [],
        args.get("now"),
    )
    for key in ("level", "level_name", "next_level_growth", "level_progress"):
        if args.get(key) is not None:
            doc[key] = args[key]
    return {"account": doc, "response": doc}


@operator("assemble.loyalty.ledger", category="ASSEMBLE", description="Assemble a paged points ledger")
def assemble_ledger(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = ledger_page(
        args.get("items") or [],
        _text(args.get("uid")) or _text(context.get("user_id")),
        limit=_int(args.get("limit"), 50) or 50,
        offset=_int(args.get("offset")),
        event_code=_text(args.get("event_code")),
        balance=_int(args.get("balance")),
    )
    return {**payload, "response": payload}


@operator("assemble.loyalty.rules", category="ASSEMBLE", description="Assemble the enabled points rule table")
def assemble_rules(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = rules_payload()
    return {**payload, "response": payload}


@operator("assemble.loyalty.plans", category="ASSEMBLE", description="Assemble the membership plan catalogue")
def assemble_plans(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = plans_payload(args.get("membership"))
    return {**payload, "response": payload}


@operator("assemble.loyalty.membership", category="ASSEMBLE", description="Assemble the public membership view")
def assemble_membership(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = membership_view(args.get("membership"), args.get("now"))
    if not payload.get("uid"):
        payload["uid"] = _text(args.get("uid")) or _text(context.get("user_id"))
    return {"membership": payload, "response": payload}


@operator("assemble.loyalty.rewards", category="ASSEMBLE", description="Assemble the rewards catalogue with the caller balance")
def assemble_rewards(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = rewards_payload(args.get("items") or [], _int(args.get("balance")))
    return {**payload, "response": payload}


@operator("assemble.loyalty.orders", category="ASSEMBLE", description="Assemble one maker's redemption orders")
def assemble_orders(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = orders_payload(args.get("items") or [], _text(args.get("uid")) or _text(context.get("user_id")))
    return {**payload, "response": payload}


@operator("assemble.loyalty.award_result", category="ASSEMBLE", description="Shape the final output of one points award")
def assemble_award(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(args.get("uid")) or _text(args.get("user_id"))
    account = build_account(uid, args.get("account"), args.get("membership"), args.get("ledger") or [], args.get("now"))
    awarded = bool(args.get("allowed"))
    delta = _int(args.get("delta"))
    response = {
        "awarded": awarded,
        "loyalty_awarded": awarded,
        "reason": _text(args.get("reason")),
        "loyalty_reason": _text(args.get("reason")),
        "delta": delta if awarded else 0,
        "balance": account["balance"],
        "growth": account["growth"],
        "level": account["level"],
        "level_name": account["level_name"],
        "ledger_id": _text(args.get("ledger_id")),
        "account": account,
    }
    return {**response, "account": account, "response": response}


@operator("assemble.loyalty.revoke_result", category="ASSEMBLE", description="Shape the final output of one points revocation")
def assemble_revoke(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    revoked = bool(args.get("revoked"))
    uid = _text(args.get("uid"))
    account_doc = args.get("account")
    account = (
        build_account(uid, account_doc, None, [], args.get("now"))
        if isinstance(account_doc, dict) and account_doc
        else None
    )
    response = {
        "revoked": revoked,
        "loyalty_revoked": revoked,
        "reason": _text(args.get("reason")),
        "delta": _int(args.get("delta")) if revoked else 0,
        "balance": _int(args.get("balance")),
        "ledger_id": _text(args.get("ledger_id")),
        "account": account,
    }
    return {**response, "response": response}


@operator("assemble.loyalty.redemption_result", category="ASSEMBLE", description="Shape the final output of one points redemption")
def assemble_redemption(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(args.get("uid"))
    order = _pretty(args.get("order")) or None
    membership_doc = args.get("membership") if args.get("membership_required") else None
    account = build_account(
        uid,
        args.get("account"),
        membership_doc,
        args.get("ledger") or [],
        args.get("now"),
    )
    redeemed = bool(args.get("redeemed"))
    duplicate = bool(args.get("duplicate"))
    message = _text(args.get("message")) or ("该兑换已处理" if duplicate else ("兑换成功" if redeemed else ""))
    response = {
        "order": order,
        "account": account,
        "membership": membership_view(membership_doc, args.get("now")) if membership_doc else None,
        "message": message,
        "loyalty_redeemed": redeemed,
        "loyalty_reason": _text(args.get("reason")),
        "duplicate": duplicate,
    }
    return {**response, "response": response}


@operator("assemble.loyalty.subscription_result", category="ASSEMBLE", description="Shape the final output of one membership subscription")
def assemble_subscription(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(args.get("uid"))
    membership_doc = args.get("membership")
    account = build_account(uid, args.get("account"), membership_doc, args.get("ledger") or [], args.get("now"))
    subscribed = bool(args.get("subscribed"))
    duplicate = bool(args.get("duplicate"))
    payment_required = bool(args.get("payment_required"))
    response = {
        "order": _pretty(args.get("order")) or None,
        "account": account,
        "membership": membership_view(membership_doc, args.get("now")),
        "message": _text(args.get("message"))
        or ("该订单已处理" if duplicate else ("订单已创建，请完成现金支付后激活会员" if payment_required else "会员已开通")),
        "loyalty_subscribed": subscribed,
        "loyalty_reason": _text(args.get("reason")),
        "payment_required": payment_required,
        "payment_amount_cny": float(args.get("payment_amount_cny") or 0.0),
        "duplicate": duplicate,
    }
    return {**response, "response": response}


@operator("assemble.loyalty.auto_renew_result", category="ASSEMBLE", description="Shape the final output of an auto-renew toggle")
def assemble_auto_renew(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = membership_view(args.get("membership"), args.get("now"))
    if not payload.get("uid"):
        payload["uid"] = _text(args.get("uid"))
    return {"membership": payload, "auto_renew": payload.get("auto_renew", False), "response": payload}


@operator("assemble.loyalty.read_result", category="ASSEMBLE", description="Shape the final output of one content read reward")
def assemble_read(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    awarded = bool(args.get("allowed"))
    response = {
        "read_tracked": bool(args.get("tracked")),
        "awarded": awarded,
        "delta": _int(args.get("delta")) if awarded else 0,
        "reason": _text(args.get("reason")),
        "balance": _int(args.get("balance")),
    }
    return {**response, "response": response}


@operator("assemble.loyalty.admin_result", category="ASSEMBLE", description="Shape the final output of one admin points adjustment")
def assemble_admin(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    uid = _text(args.get("uid"))
    account = build_account(uid, args.get("account"), None, [], args.get("now"))
    response = {
        "adjusted": bool(args.get("allowed")),
        "delta": _int(args.get("delta")),
        "ledger_id": _text(args.get("ledger_id")),
        "balance": account["balance"],
        "account": account,
    }
    return {**response, "response": response}
