"""Operator-flow tests for the loyalty (晨光积分 / 会员 / 兑换) domain.

Every business flow is executed through ``config/scenarios/loyalty.yaml``. Identity
always travels in the pipeline ``context``; points / membership / orders are
asserted on the generic entity store.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.core.entity import entity_store
from src.core.scenario import ensure_scenarios_loaded
from src.domains.loyalty.entities import (
    ENTITY_ACCOUNT,
    ENTITY_ITEM,
    ENTITY_LEDGER,
    ENTITY_MEMBERSHIP,
    ENTITY_ORDER,
)
from src.domains.loyalty.service import loyalty_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

AWARD = "OPC_LOYALTY_AWARD_PIPELINE"
REVOKE = "OPC_LOYALTY_REVOKE_PIPELINE"
REDEEM = "OPC_LOYALTY_REDEEM_PIPELINE"
SUBSCRIBE = "OPC_LOYALTY_SUBSCRIBE_PIPELINE"
AUTO_RENEW = "OPC_LOYALTY_AUTO_RENEW_PIPELINE"
ACCOUNT = "OPC_LOYALTY_ACCOUNT_PIPELINE"
LEDGER = "OPC_LOYALTY_LEDGER_PIPELINE"
RULES = "OPC_LOYALTY_RULES_PIPELINE"
PLANS = "OPC_LOYALTY_MEMBERSHIP_PLANS_PIPELINE"
MEMBERSHIP_ME = "OPC_LOYALTY_MEMBERSHIP_ME_PIPELINE"
REWARDS = "OPC_LOYALTY_REWARDS_ITEMS_PIPELINE"
ORDERS = "OPC_LOYALTY_REWARDS_ORDERS_PIPELINE"
CONTENT_READ = "OPC_LOYALTY_CONTENT_READ_PIPELINE"
ADMIN_GRANT = "OPC_LOYALTY_ADMIN_GRANT_PIPELINE"


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _ctx(user_id: str, role: str = "MAKER") -> dict[str, Any]:
    return {"user_id": user_id, "user_role": role, "nickname": "积分测试创客"}


async def _run(scenario: str, inputs: dict[str, Any], context: dict[str, Any] | None = None):
    ensure_scenarios_loaded()
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=inputs,
            context=context or {},
        )
    )


async def _award(
    event_code: str,
    user_id: str,
    *,
    actor_id: str = "",
    target_type: str = "",
    target_id: str = "",
    key: str | None = None,
    context: dict[str, Any] | None = None,
):
    return await _run(
        AWARD,
        {
            "event_code": event_code,
            "user_id": user_id,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            "idempotency_key": key,
        },
        context or _ctx(actor_id or user_id),
    )


def _balance(uid: str) -> int:
    row = entity_store.get(ENTITY_ACCOUNT, {"key": uid}) or {}
    return int(row.get("balance") or 0)


def _set_balance(uid: str, balance: int) -> None:
    row = entity_store.get(ENTITY_ACCOUNT, {"key": uid})
    payload = {
        "uid": uid,
        "balance": balance,
        "frozen": 0,
        "debt": 0,
        "total_earned": 0,
        "total_spent": 0,
        "growth": 0,
        "reputation": 80,
    }
    if row is None:
        entity_store.create(ENTITY_ACCOUNT, payload)
    else:
        entity_store.update(ENTITY_ACCOUNT, {**row, **payload}, partial=False)


def _items() -> dict[str, dict[str, Any]]:
    return {row["code"]: row for row in entity_store.adapter(ENTITY_ITEM).all()}


@pytest.fixture(autouse=True)
def clean_loyalty():
    ensure_scenarios_loaded()
    loyalty_service.clear()
    yield
    loyalty_service.clear()


# ---------------------------------------------------------------------------
# 1. Award: first publish / idempotency / daily caps / levels
# ---------------------------------------------------------------------------
async def test_award_first_publish_and_idempotency():
    uid = _uid("usr_award")
    first_publish = await _award(
        "FIRST_PUBLISH",
        uid,
        target_type="POLICY",
        target_id="pol_first",
        key=f"once:FIRST_PUBLISH:{uid}",
    )
    assert first_publish.status == "SUCCESS", first_publish.error_message
    assert first_publish.final_output["loyalty_awarded"] is True
    assert first_publish.final_output["delta"] == 300
    assert first_publish.final_output["balance"] == 300

    duplicate = await _award(
        "FIRST_PUBLISH",
        uid,
        target_type="POLICY",
        target_id="pol_first",
        key=f"once:FIRST_PUBLISH:{uid}",
    )
    assert duplicate.status == "SUCCESS"
    assert duplicate.final_output["loyalty_awarded"] is False
    assert duplicate.final_output["loyalty_reason"] == "duplicate"
    assert _balance(uid) == 300

    publish = await _award(
        "PUBLISH_POLICY",
        uid,
        target_type="POLICY",
        target_id="pol_first",
        key="publish:POLICY:pol_first",
    )
    assert publish.final_output["loyalty_awarded"] is True
    assert publish.final_output["delta"] == 100
    assert _balance(uid) == 400

    ledger = entity_store.adapter(ENTITY_LEDGER).all()
    assert len([row for row in ledger if row["uid"] == uid and row["delta"] > 0]) == 2


async def test_award_daily_global_cap_and_level():
    uid = _uid("usr_cap")
    first = await _award(
        "QUALITY_BONUS", uid, target_type="POLICY", target_id="pol_q1", key="q1"
    )
    second = await _award(
        "QUALITY_BONUS", uid, target_type="POLICY", target_id="pol_q2", key="q2"
    )
    third = await _award(
        "QUALITY_BONUS", uid, target_type="POLICY", target_id="pol_q3", key="q3"
    )
    assert first.final_output["loyalty_awarded"] is True
    assert second.final_output["loyalty_awarded"] is True
    assert third.final_output["loyalty_awarded"] is False
    assert third.final_output["loyalty_reason"] == "daily_cap_reached"
    assert _balance(uid) == 1000

    account = await _run(ACCOUNT, {}, _ctx(uid))
    assert account.status == "SUCCESS"
    body = account.final_output["response"]
    assert body["balance"] == 1000
    assert body["level"] == 2
    assert body["level_name"] == "破晓"
    assert body["today_earned"] == 1000


async def test_award_reputation_block_and_self_interaction():
    uid = _uid("usr_self")
    self_award = await _award(
        "RECEIVE_LIKE",
        uid,
        actor_id=uid,
        target_type="PRODUCT",
        target_id="prd_self",
        key="self-like",
    )
    assert self_award.final_output["loyalty_awarded"] is False
    assert self_award.final_output["loyalty_reason"] == "self_interaction"
    assert _balance(uid) == 0


# ---------------------------------------------------------------------------
# 2. Revoke: reverse settlement + idempotent tombstone
# ---------------------------------------------------------------------------
async def test_revoke_reverses_balance_and_is_idempotent():
    uid = _uid("usr_revoke")
    key = "publish:POLICY:pol_revoke"
    awarded = await _award(
        "PUBLISH_POLICY",
        uid,
        target_type="POLICY",
        target_id="pol_revoke",
        key=key,
    )
    assert awarded.final_output["loyalty_awarded"] is True
    assert _balance(uid) == 100

    revoked = await _run(
        REVOKE,
        {"event_code": "PUBLISH_POLICY", "target_type": "POLICY", "target_id": "pol_revoke", "idempotency_key": key},
        _ctx(uid),
    )
    assert revoked.status == "SUCCESS", revoked.error_message
    assert revoked.final_output["loyalty_revoked"] is True
    assert revoked.final_output["delta"] == -100
    assert _balance(uid) == 0

    original = next(row for row in entity_store.adapter(ENTITY_LEDGER).all() if row["idempotency_key"] == key)
    assert original["status"] == "REVOKED"
    reversal = next(
        row
        for row in entity_store.adapter(ENTITY_LEDGER).all()
        if row["idempotency_key"] == f"revoke:{original['id']}"
    )
    assert reversal["delta"] == -100

    again = await _run(
        REVOKE,
        {"event_code": "PUBLISH_POLICY", "target_type": "POLICY", "target_id": "pol_revoke", "idempotency_key": key},
        _ctx(uid),
    )
    assert again.final_output["loyalty_revoked"] is False
    assert again.final_output["reason"] == "already_revoked"
    assert _balance(uid) == 0


# ---------------------------------------------------------------------------
# 3. Redemption: eligibility failures, stock, orders and idempotency
# ---------------------------------------------------------------------------
async def test_redeem_physical_requires_address_then_succeeds():
    uid = _uid("usr_redeem_physical")
    _set_balance(uid, 5000)
    stock_before = _items()["physical_sticker_pack"]["stock"]

    missing = await _run(
        REDEEM,
        {"item_code": "physical_sticker_pack", "qty": 1, "idempotency_key": "phys:1"},
        _ctx(uid),
    )
    assert missing.status == "SUCCESS"
    assert missing.final_output["loyalty_redeemed"] is False
    assert missing.final_output["loyalty_reason"] == "address_required"
    assert _balance(uid) == 5000

    ok = await _run(
        REDEEM,
        {
            "item_code": "physical_sticker_pack",
            "qty": 1,
            "address": {"name": "张三", "phone": "13800000000", "detail": "杭州市西湖区"},
            "idempotency_key": "phys:1",
        },
        _ctx(uid),
    )
    assert ok.status == "SUCCESS", ok.error_message
    assert ok.final_output["loyalty_redeemed"] is True
    assert ok.final_output["order"]["status"] == "PAID"
    assert ok.final_output["account"]["balance"] == 3500
    assert _balance(uid) == 3500
    assert _items()["physical_sticker_pack"]["stock"] == stock_before - 1

    orders = await _run(ORDERS, {}, _ctx(uid))
    assert orders.final_output["total"] == 1


async def test_redeem_insufficient_points_and_duplicate_order():
    uid = _uid("usr_redeem_dup")
    _set_balance(uid, 500)

    poor = await _run(
        REDEEM,
        {"item_code": "digital_rename_card", "qty": 1, "idempotency_key": "rename:poor"},
        _ctx(uid),
    )
    assert poor.final_output["loyalty_redeemed"] is False
    assert poor.final_output["loyalty_reason"] == "insufficient_points"

    _set_balance(uid, 5000)
    first = await _run(
        REDEEM,
        {"item_code": "digital_rename_card", "qty": 1, "idempotency_key": "rename:once"},
        _ctx(uid),
    )
    assert first.final_output["loyalty_redeemed"] is True
    assert first.final_output["account"]["balance"] == 4000
    order_id = first.final_output["order"]["id"]

    duplicate = await _run(
        REDEEM,
        {"item_code": "digital_rename_card", "qty": 1, "idempotency_key": "rename:once"},
        _ctx(uid),
    )
    assert duplicate.final_output["loyalty_redeemed"] is True
    assert duplicate.final_output["duplicate"] is True
    assert duplicate.final_output["order"]["id"] == order_id
    assert _balance(uid) == 4000
    assert len(entity_store.adapter(ENTITY_ORDER).all()) == 1


async def test_redeem_membership_activates_and_extends():
    uid = _uid("usr_redeem_member")
    _set_balance(uid, 30000)
    result = await _run(
        REDEEM,
        {"item_code": "membership_pro_yearly", "qty": 1, "idempotency_key": "member:1"},
        _ctx(uid),
    )
    assert result.status == "SUCCESS", result.error_message
    assert result.final_output["loyalty_redeemed"] is True
    assert result.final_output["order"]["status"] == "COMPLETED"
    assert result.final_output["account"]["balance"] == 6000
    assert result.final_output["membership"]["tier"] == "PRO"
    assert result.final_output["membership"]["status"] == "ACTIVE"

    me = await _run(MEMBERSHIP_ME, {}, _ctx(uid))
    assert me.final_output["response"]["tier"] == "PRO"
    assert me.final_output["response"]["source"] == "POINTS"
    assert me.final_output["response"]["days_left"] > 300

    other = await _run(
        REDEEM,
        {"item_code": "membership_pro_monthly", "qty": 1, "idempotency_key": "member:2"},
        _ctx(uid),
    )
    assert other.final_output["loyalty_redeemed"] is True
    extended = await _run(MEMBERSHIP_ME, {}, _ctx(uid))
    assert extended.final_output["response"]["days_left"] > me.final_output["response"]["days_left"]


# ---------------------------------------------------------------------------
# 4. Membership subscription / auto-renew / higher tier guard
# ---------------------------------------------------------------------------
async def test_subscribe_with_points_and_auto_renew():
    uid = _uid("usr_subscribe")
    _set_balance(uid, 5000)

    subscribed = await _run(
        SUBSCRIBE,
        {"plan_code": "pro_monthly", "pay_method": "POINTS", "idempotency_key": "sub:1"},
        _ctx(uid),
    )
    assert subscribed.status == "SUCCESS", subscribed.error_message
    assert subscribed.final_output["loyalty_subscribed"] is True
    assert subscribed.final_output["order"]["status"] == "COMPLETED"
    assert subscribed.final_output["membership"]["tier"] == "PRO"
    assert subscribed.final_output["account"]["balance"] == 2600
    assert _balance(uid) == 2600

    enabled = await _run(AUTO_RENEW, {"enabled": True}, _ctx(uid))
    assert enabled.status == "SUCCESS", enabled.error_message
    assert enabled.final_output["response"]["auto_renew"] is True

    me = await _run(MEMBERSHIP_ME, {}, _ctx(uid))
    assert me.final_output["response"]["auto_renew"] is True


async def test_subscribe_cash_creates_pending_order_without_activation():
    uid = _uid("usr_cash")
    pending = await _run(
        SUBSCRIBE,
        {"plan_code": "black_monthly", "pay_method": "CASH", "idempotency_key": "cash:1"},
        _ctx(uid),
    )
    assert pending.status == "SUCCESS", pending.error_message
    assert pending.final_output["loyalty_subscribed"] is True
    assert pending.final_output["payment_required"] is True
    assert pending.final_output["order"]["status"] == "PENDING_PAYMENT"
    assert pending.final_output["payment_amount_cny"] == 89.0
    assert entity_store.get(ENTITY_MEMBERSHIP, {"key": uid}) is None

    me = await _run(MEMBERSHIP_ME, {}, _ctx(uid))
    assert me.final_output["response"]["tier"] == "STANDARD"
    assert me.final_output["response"]["status"] == "NONE"


async def test_higher_tier_cannot_be_downgraded():
    uid = _uid("usr_higher")
    _set_balance(uid, 50000)
    black = await _run(
        SUBSCRIBE,
        {"plan_code": "black_monthly", "pay_method": "POINTS", "idempotency_key": "black:1"},
        _ctx(uid),
    )
    assert black.final_output["loyalty_subscribed"] is True
    balance = _balance(uid)

    lower = await _run(
        SUBSCRIBE,
        {"plan_code": "pro_yearly", "pay_method": "POINTS", "idempotency_key": "pro:lower"},
        _ctx(uid),
    )
    assert lower.final_output["loyalty_subscribed"] is False
    assert lower.final_output["loyalty_reason"] == "higher_tier_active"
    assert _balance(uid) == balance


async def test_auto_renew_requires_membership_and_auth():
    uid = _uid("usr_no_member")
    missing = await _run(AUTO_RENEW, {"enabled": True}, _ctx(uid))
    assert missing.status != "SUCCESS"
    assert "当前没有可续费的会员" in (missing.error_message or "")

    unauthenticated = await _run(AUTO_RENEW, {"enabled": True}, {})
    assert unauthenticated.status != "SUCCESS"


# ---------------------------------------------------------------------------
# 5. Queries: account / ledger / rules / plans / rewards / orders
# ---------------------------------------------------------------------------
async def test_account_ledger_and_rules_queries():
    uid = _uid("usr_query")
    await _award("PUBLISH_POLICY", uid, target_type="POLICY", target_id="pol_q", key="query:1")
    await _award("RECEIVE_READ", uid, actor_id="usr_reader", target_type="POLICY", target_id="pol_q", key="query:2")

    account = await _run(ACCOUNT, {}, _ctx(uid))
    body = account.final_output["response"]
    assert body["balance"] == 101
    assert body["growth"] == 20
    assert body["level"] == 1
    assert body["today_earned"] == 101

    ledger = await _run(LEDGER, {"limit": 10, "offset": 0}, _ctx(uid))
    payload = ledger.final_output["response"]
    assert payload["total"] == 2
    assert payload["balance"] == 101
    assert [row["event_code"] for row in payload["items"]] == ["RECEIVE_READ", "PUBLISH_POLICY"]

    filtered = await _run(LEDGER, {"event_code": "PUBLISH_POLICY"}, _ctx(uid))
    assert filtered.final_output["response"]["total"] == 1

    rules = await _run(RULES, {}, {})
    codes = {row["code"] for row in rules.final_output["items"]}
    assert {"PUBLISH_POLICY", "RECEIVE_READ", "RECEIVE_DISLIKE"} <= codes
    read_rule = next(row for row in rules.final_output["items"] if row["code"] == "RECEIVE_READ")
    assert read_rule["points"] == 1
    dislike_rule = next(row for row in rules.final_output["items"] if row["code"] == "RECEIVE_DISLIKE")
    assert dislike_rule["points"] == 0

    plans = await _run(PLANS, {}, {})
    assert {row["tier"] for row in plans.final_output["items"]} == {"PRO", "BLACK_DIAMOND"}
    assert any(row["points_price"] == 24000 for row in plans.final_output["items"])

    rewards = await _run(REWARDS, {}, _ctx(uid))
    codes = {row["code"] for row in rewards.final_output["items"]}
    assert {"membership_pro_yearly", "physical_sticker_pack", "digital_rename_card"} <= codes
    assert rewards.final_output["balance"] == 101

    orders = await _run(ORDERS, {}, _ctx(uid))
    assert orders.final_output["total"] == 0


async def test_content_read_falls_back_to_target_author_and_dedupes():
    from src.domains.policies.entities import ENTITY_POLICY

    author = _uid("usr_read_author")
    reader = _uid("usr_read_reader")
    policy = entity_store.create(
        ENTITY_POLICY,
        {
            "title": "阅读积分测试政策",
            "policy_level": "省市级",
            "category": "TAX",
            "subsidy_amount_max": 10000.0,
            "summary": "用于验证阅读积分归属与每日去重的测试政策。",
            "eligible_conditions": ["注册创客"],
            "legal_basis": "测试依据",
            "author_id": author,
            "author_name": "积分作者",
        },
    )
    payload = {"target_type": "POLICY", "target_id": policy["id"]}

    first = await _run(CONTENT_READ, payload, _ctx(reader))
    assert first.status == "SUCCESS", first.error_message
    assert first.final_output["awarded"] is True
    assert first.final_output["delta"] == 1
    assert _balance(author) == 1

    second = await _run(CONTENT_READ, payload, _ctx(reader))
    assert second.final_output["awarded"] is False
    assert second.final_output["reason"] == "duplicate"
    assert _balance(author) == 1


# ---------------------------------------------------------------------------
# 6. Admin adjustment: audited, uncapped, permission gated
# ---------------------------------------------------------------------------
async def test_admin_grant_and_deduction_bypass_caps():
    uid = _uid("usr_admin_target")
    admin_ctx = _ctx("usr_admin_ops", role="ADMIN")

    granted = await _run(ADMIN_GRANT, {"uid": uid, "delta": 50000, "reason": "运营补发测试"}, admin_ctx)
    assert granted.status == "SUCCESS", granted.error_message
    assert granted.final_output["response"]["adjusted"] is True
    assert granted.final_output["response"]["balance"] == 50000
    assert _balance(uid) == 50000

    deducted = await _run(ADMIN_GRANT, {"uid": uid, "delta": -20000, "reason": "运营扣回测试"}, admin_ctx)
    assert deducted.status == "SUCCESS", deducted.error_message
    assert deducted.final_output["response"]["balance"] == 30000

    entries = [row for row in entity_store.adapter(ENTITY_LEDGER).all() if row["uid"] == uid]
    assert len(entries) == 2
    assert {row["event_code"] for row in entries} == {"ADMIN_ADJUST"}

    forbidden = await _run(ADMIN_GRANT, {"uid": uid, "delta": 100}, _ctx("usr_maker"))
    assert forbidden.status != "SUCCESS"
    assert "权限" in (forbidden.error_message or "")


async def test_account_query_requires_login():
    anonymous = await _run(ACCOUNT, {}, {})
    assert anonymous.status != "SUCCESS"
    assert "登录" in (anonymous.error_message or "")


# ---------------------------------------------------------------------------
# 7. Scenario asset / route wiring
# ---------------------------------------------------------------------------
def test_loyalty_routes_map_to_known_pipelines():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[1] / "config"
    routes = yaml.safe_load((root / "routes" / "loyalty.yaml").read_text(encoding="utf-8"))["routes"]
    scenarios = yaml.safe_load((root / "scenarios" / "loyalty.yaml").read_text(encoding="utf-8"))["scenarios"]
    known = {asset["scenario"] for asset in scenarios}

    assert len(routes) == 12
    assert {route["gateway"] for route in routes} == {
        "loyalty.account",
        "loyalty.ledger",
        "loyalty.rules",
        "loyalty.membership.plans",
        "loyalty.membership.me",
        "loyalty.membership.subscribe",
        "loyalty.membership.auto-renew",
        "loyalty.rewards.items",
        "loyalty.rewards.redeem",
        "loyalty.rewards.orders",
        "loyalty.content.read",
        "loyalty.admin.grant",
    }
    assert all(route["pipeline"] in known for route in routes)
    assert {"OPC_LOYALTY_AWARD_PIPELINE", "OPC_LOYALTY_REVOKE_PIPELINE", "OPC_LOYALTY_REDEEM_PIPELINE", "OPC_LOYALTY_SUBSCRIBE_PIPELINE"} <= known
