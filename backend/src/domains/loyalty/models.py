"""Data models for the loyalty domain (晨光积分 / 会员 / 积分兑换).

Three orthogonal ledgers, one membership track:

* ``points``      - spendable community currency (expires, revocable)
* ``growth``      - non-spendable experience that decides V1-V6 levels
* ``reputation``  - behaviour quality score that gates interaction weight

Membership (STANDARD / PRO / BLACK_DIAMOND) is time-based and can be bought or
redeemed with points. It never inflates interaction counters.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Points rules & ledger
# ---------------------------------------------------------------------------


class PointsRule(BaseModel):
    code: str
    name: str
    category: str = "CONTENT"  # TASK / CONTENT / INTERACTION / READ / BONUS
    points: int = 0
    growth: int = 0
    daily_cap: Optional[int] = None
    monthly_cap: Optional[int] = None
    per_target_cap: Optional[int] = None
    once: bool = False
    enabled: bool = True
    description: str = ""


class PointsLedgerEntry(BaseModel):
    id: str
    uid: str
    event_code: str
    title: str
    delta: int
    balance_after: int
    status: str = "SETTLED"  # PENDING / SETTLED / REVOKED / EXPIRED / FROZEN
    ref_type: str = ""
    ref_id: str = ""
    actor_id: str = ""
    idempotency_key: str = ""
    note: str = ""
    expires_at: str = ""
    created_at: str


class PointsAccount(BaseModel):
    uid: str
    balance: int = 0
    frozen: int = 0
    debt: int = 0
    total_earned: int = 0
    total_spent: int = 0
    growth: int = 0
    level: int = 1
    level_name: str = "微光"
    next_level_growth: int = 500
    level_progress: float = 0.0
    reputation: int = 80
    membership_tier: str = "STANDARD"
    membership_tier_name: str = "标准创客"
    membership_expires_at: str = ""
    today_earned: int = 0
    month_earned: int = 0
    updated_at: str = ""


class PointsLedgerResponse(BaseModel):
    items: List[PointsLedgerEntry] = Field(default_factory=list)
    total: int = 0
    balance: int = 0


class PointsRulesResponse(BaseModel):
    items: List[PointsRule] = Field(default_factory=list)
    daily_global_cap: int = 1000
    monthly_global_cap: int = 20000
    expiry_months: int = 24


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


class MembershipPlan(BaseModel):
    code: str
    tier: str  # PRO / BLACK_DIAMOND
    tier_name: str
    period_months: int
    price_cny: float
    points_price: int
    benefits: List[str] = Field(default_factory=list)
    quotas: Dict[str, int] = Field(default_factory=dict)
    recommended: bool = False


class MembershipInfo(BaseModel):
    uid: str = ""
    tier: str = "STANDARD"
    tier_name: str = "标准创客"
    source: str = ""  # CASH / POINTS / GRANT
    status: str = "NONE"  # ACTIVE / EXPIRED / NONE
    plan_code: str = ""
    started_at: str = ""
    expires_at: str = ""
    days_left: int = 0
    auto_renew: bool = False
    benefits: List[str] = Field(default_factory=list)


class MembershipPlansResponse(BaseModel):
    items: List[MembershipPlan] = Field(default_factory=list)
    current_tier: str = "STANDARD"
    current_tier_name: str = "标准创客"


class SubscribeRequest(BaseModel):
    plan_code: str
    pay_method: str = "POINTS"  # POINTS / CASH
    idempotency_key: Optional[str] = None


class AutoRenewRequest(BaseModel):
    enabled: bool = False


# ---------------------------------------------------------------------------
# Rewards & redemption
# ---------------------------------------------------------------------------


class RewardItem(BaseModel):
    code: str
    name: str
    type: str  # MEMBERSHIP / PHYSICAL / DIGITAL
    points_price: int
    stock: int = 0
    per_user_limit: int = 1
    icon: str = "gift"
    description: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class RewardItemsResponse(BaseModel):
    items: List[RewardItem] = Field(default_factory=list)
    balance: int = 0


class RedeemRequest(BaseModel):
    item_code: str
    qty: int = Field(default=1, ge=1, le=10)
    address: Optional[Any] = None
    idempotency_key: Optional[str] = None


class RedemptionOrder(BaseModel):
    id: str
    uid: str
    item_code: str
    item_name: str
    item_type: str
    qty: int
    points_cost: int
    status: str = "COMPLETED"  # PENDING_PAYMENT / PAID / SHIPPED / COMPLETED / CANCELLED
    address: Optional[Any] = None
    tracking_no: str = ""
    note: str = ""
    idempotency_key: str = ""
    created_at: str = ""
    updated_at: str = ""


class RedemptionOrdersResponse(BaseModel):
    items: List[RedemptionOrder] = Field(default_factory=list)
    total: int = 0


class RedeemResponse(BaseModel):
    order: RedemptionOrder
    account: PointsAccount
    membership: Optional[MembershipInfo] = None
    message: str = "兑换成功"


# ---------------------------------------------------------------------------
# Internal award contract (operators <-> service)
# ---------------------------------------------------------------------------


class AwardDecision(BaseModel):
    allowed: bool = False
    reason: str = ""
    uid: str = ""
    actor_id: str = ""
    event_code: str = ""
    rule_code: str = ""
    rule_name: str = ""
    base_points: int = 0
    delta: int = 0
    growth: int = 0
    target_type: str = ""
    target_id: str = ""
    idempotency_key: str = ""
    note: str = ""


class AwardRequest(BaseModel):
    event_code: str
    user_id: str = ""
    actor_id: str = ""
    target_type: str = ""
    target_id: str = ""
    quantity: int = 1
    idempotency_key: Optional[str] = None
    note: str = ""


class RevokeRequest(BaseModel):
    event_code: str = ""
    user_id: str = ""
    actor_id: str = ""
    target_type: str = ""
    target_id: str = ""
    idempotency_key: Optional[str] = None
