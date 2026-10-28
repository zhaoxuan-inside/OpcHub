"""Loyalty (晨光积分 / 会员 / 兑换) end-to-end tests.

Covers:
* DAG operator registration and orchestration
* publish / read / like awards, duplicate idempotency, cancel rollback
* dislike never deducts points
* points redemption of membership and physical rewards
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conftest import dispatch
from src.core.microkernel.registry import registry
from src.core.security import create_session_token
from src.domains.interactions.service import content_interaction_service
from src.domains.loyalty.pipelines import ensure_loyalty_pipelines
from src.domains.loyalty.service import loyalty_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service
from src.domains.policies.models import PolicyCreate
from src.domains.policies.service import policy_service
from src.domains.products.models import ProductCreate
from src.domains.products.service import product_service
from src.domains.user.service import user_service
from src.main import app

AUTHOR_ID = "usr_loyalty_author"
READER_ID = "usr_loyalty_reader"
AUTHOR_TOKEN = create_session_token({"uid": AUTHOR_ID, "role": "MAKER", "nickname": "积分作者"}, expires_in_seconds=3600)
READER_TOKEN = create_session_token({"uid": READER_ID, "role": "MAKER", "nickname": "积分读者"}, expires_in_seconds=3600)


def _seed_user(uid: str, nickname: str) -> None:
    record = {
        "uid": uid,
        "email": f"{uid}@example.com",
        "nickname": nickname,
        "role": "MAKER",
        "tier_name": "标准创客",
        "active_entitlements": set(),
        "entitlement_expiries": {},
        "membership_tier": "STANDARD",
    }
    user_service._users_by_uid[uid] = record
    user_service._users_by_email[record["email"]] = record


@pytest.fixture(autouse=True)
def clean_loyalty_state():
    ensure_loyalty_pipelines()
    loyalty_service._accounts.clear()
    loyalty_service._ledger.clear()
    loyalty_service._memberships.clear()
    loyalty_service._orders.clear()
    loyalty_service._idempotency.clear()
    loyalty_service._order_keys.clear()
    loyalty_service._daily.clear()
    loyalty_service._daily_total.clear()
    loyalty_service._monthly_total.clear()
    loyalty_service._target_daily.clear()
    loyalty_service._pair_daily.clear()
    content_interaction_service.clear()
    _seed_user(AUTHOR_ID, "积分作者")
    _seed_user(READER_ID, "积分读者")
    yield


@pytest.fixture
def client():
    return TestClient(app)


async def _run_scenario(scenario: str, inputs: dict, context: dict | None = None):
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
    uid: str,
    *,
    actor_id: str = "",
    target_type: str = "",
    target_id: str = "",
    key: str | None = None,
):
    """Compose the loyalty award scenario (operator-kernel v2 has no service hook)."""
    return await _run_scenario(
        "OPC_LOYALTY_AWARD_PIPELINE",
        {
            "event_code": event_code,
            "user_id": uid,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            "idempotency_key": key,
        },
        {"user_id": actor_id or uid, "user_role": "MAKER"},
    )


async def _revoke(
    event_code: str,
    uid: str,
    *,
    actor_id: str = "",
    target_type: str = "",
    target_id: str = "",
    key: str | None = None,
):
    return await _run_scenario(
        "OPC_LOYALTY_REVOKE_PIPELINE",
        {
            "event_code": event_code,
            "user_id": uid,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            "idempotency_key": key,
        },
        {"user_id": actor_id or uid, "user_role": "MAKER"},
    )


def test_loyalty_operators_are_registered():
    handlers = registry.list_handlers()
    for name in (
        "calc.loyalty.event",
        "calc.loyalty.resolve",
        "calc.loyalty.settle",
        "calc.loyalty.revoke",
        "calc.loyalty.redeem",
        "calc.loyalty.membership",
        "assemble.loyalty.award_result",
        "assemble.loyalty.revoke_result",
        "assemble.loyalty.redemption_result",
        "assemble.loyalty.subscription_result",
    ):
        assert name in handlers


def test_rules_are_public(client):
    resp = dispatch(client, "loyalty.rules")
    body = resp.json()
    assert body.get("code") == 200
    codes = {item["code"] for item in body["data"]["items"]}
    assert "PUBLISH_POLICY" in codes
    assert "RECEIVE_READ" in codes
    read_rule = next(item for item in body["data"]["items"] if item["code"] == "RECEIVE_READ")
    assert read_rule["points"] == 1
    dislike_rule = next(item for item in body["data"]["items"] if item["code"] == "RECEIVE_DISLIKE")
    assert dislike_rule["points"] == 0


@pytest.mark.asyncio
async def test_publish_policy_awards_points(client):
    resp = dispatch(
        client,
        "policies.publish",
        {
            "title": "创客发布政策积分测试",
            "policy_level": "省市级",
            "category": "TAX",
            "subsidy_amount_max": 10000.0,
            "summary": "用于验证发布政策后作者获得基础积分的测试政策摘要。",
            "eligible_conditions": ["注册创客"],
            "legal_basis": "测试依据",
        },
        token=AUTHOR_TOKEN,
    ).json()
    assert resp.get("code") == 200, resp
    policy_id = resp["data"]["id"]

    # 发布场景不再隐式跨域发积分；由上层组合显式调用积分发放场景。
    first = await _award(
        "FIRST_PUBLISH", AUTHOR_ID, target_type="POLICY", target_id=policy_id,
        key=f"once:FIRST_PUBLISH:{AUTHOR_ID}",
    )
    assert first.status == "SUCCESS", first.error_message
    assert first.final_output["loyalty_awarded"] is True
    publish = await _award(
        "PUBLISH_POLICY", AUTHOR_ID, target_type="POLICY", target_id=policy_id,
        key=f"publish:POLICY:{policy_id}",
    )
    assert publish.status == "SUCCESS", publish.error_message
    assert publish.final_output["loyalty_awarded"] is True
    # 发布政策 100 + 首次发布一次性奖励 300
    assert loyalty_service.get_account(AUTHOR_ID).balance == 400


def test_read_reward_is_deduplicated_per_day(client):
    policy = policy_service.create_policy(
        PolicyCreate(
            title="阅读积分测试政策",
            summary="用于验证阅读积分只计一次的政策摘要内容。",
            legal_basis="测试依据",
            author_id=AUTHOR_ID,
            author_name="积分作者",
        )
    )
    payload = {"target_type": "POLICY", "target_id": policy.id}
    first = dispatch(client, "loyalty.content.read", payload, token=READER_TOKEN).json()
    assert first.get("code") == 200
    assert first["data"]["awarded"] is True
    assert first["data"]["delta"] == 1

    second = dispatch(client, "loyalty.content.read", payload, token=READER_TOKEN).json()
    assert second.get("code") == 200
    assert second["data"]["awarded"] is False

    account = loyalty_service.get_account(AUTHOR_ID)
    assert account.balance == 1


def _seed_product() -> str:
    product = product_service.create_product(
        ProductCreate(
            title="积分互动测试产品",
            tagline="用于验证点赞与踩的积分联动",
            description="这是一条用于验证互动积分联动与撤销回滚的测试产品描述。",
            author_id=AUTHOR_ID,
            author_name="积分作者",
        )
    )
    return product.id


@pytest.mark.asyncio
async def test_like_awards_author_and_cancel_revokes(client):
    from src.core.entity import entity_store

    product = entity_store.create(
        "product.item",
        {
            "title": "积分互动测试产品",
            "tagline": "用于验证点赞与踩的积分联动",
            "description": "这是一条用于验证互动积分联动与撤销回滚的测试产品描述。",
            "author_id": AUTHOR_ID,
            "author_name": "积分作者",
        },
    )
    product_id = product["id"]
    payload = {"target_type": "PRODUCT", "target_id": product_id, "kind": "LIKE"}
    key = f"like:{READER_ID}:{product_id}"

    first = dispatch(client, "content.interaction.toggle", payload, token=READER_TOKEN).json()
    assert first.get("code") == 200
    assert first["data"]["active"] is True
    awarded = await _award(
        "RECEIVE_LIKE", AUTHOR_ID, actor_id=READER_ID,
        target_type="PRODUCT", target_id=product_id, key=key,
    )
    assert awarded.status == "SUCCESS", awarded.error_message
    assert awarded.final_output["loyalty_awarded"] is True
    assert loyalty_service.get_account(AUTHOR_ID).balance == 5

    second = dispatch(client, "content.interaction.toggle", payload, token=READER_TOKEN).json()
    assert second.get("code") == 200
    assert second["data"]["active"] is False
    revoked = await _revoke(
        "RECEIVE_LIKE", AUTHOR_ID, actor_id=READER_ID,
        target_type="PRODUCT", target_id=product_id, key=key,
    )
    assert revoked.status == "SUCCESS", revoked.error_message
    assert revoked.final_output["loyalty_revoked"] is True
    assert loyalty_service.get_account(AUTHOR_ID).balance == 0


@pytest.mark.asyncio
async def test_cancel_then_relike_does_not_recredit(client):
    product = product_service.create_product(
        ProductCreate(
            title="积分互动测试产品",
            tagline="用于验证点赞与踩的积分联动",
            description="这是一条用于验证互动积分联动与撤销回滚的测试产品描述。",
            author_id=AUTHOR_ID,
            author_name="积分作者",
        )
    )
    product_id = product.id
    payload = {"target_type": "PRODUCT", "target_id": product_id, "kind": "LIKE"}
    key = f"like:{READER_ID}:{product_id}"

    assert dispatch(client, "content.interaction.toggle", payload, token=READER_TOKEN).json()["code"] == 200
    assert (await _award("RECEIVE_LIKE", AUTHOR_ID, actor_id=READER_ID,
                         target_type="PRODUCT", target_id=product_id, key=key)).final_output["loyalty_awarded"] is True
    assert loyalty_service.get_account(AUTHOR_ID).balance == 5

    assert dispatch(client, "content.interaction.toggle", payload, token=READER_TOKEN).json()["code"] == 200
    assert (await _revoke("RECEIVE_LIKE", AUTHOR_ID, actor_id=READER_ID,
                          target_type="PRODUCT", target_id=product_id, key=key)).final_output["loyalty_revoked"] is True
    assert loyalty_service.get_account(AUTHOR_ID).balance == 0

    assert dispatch(client, "content.interaction.toggle", payload, token=READER_TOKEN).json()["code"] == 200
    relike = await _award("RECEIVE_LIKE", AUTHOR_ID, actor_id=READER_ID,
                          target_type="PRODUCT", target_id=product_id, key=key)
    # Tombstone: cancel + re-like must not re-credit the same pair.
    assert relike.final_output["loyalty_awarded"] is False
    assert relike.final_output["loyalty_reason"] == "duplicate"
    assert loyalty_service.get_account(AUTHOR_ID).balance == 0


@pytest.mark.asyncio
async def test_dislike_never_deducts_points(client):
    product = product_service.create_product(
        ProductCreate(
            title="积分互动测试产品",
            tagline="用于验证点赞与踩的积分联动",
            description="这是一条用于验证互动积分联动与撤销回滚的测试产品描述。",
            author_id=AUTHOR_ID,
            author_name="积分作者",
        )
    )
    product_id = product.id
    payload = {"target_type": "PRODUCT", "target_id": product_id, "kind": "DISLIKE"}
    before = loyalty_service.get_account(AUTHOR_ID).balance
    resp = dispatch(client, "content.interaction.toggle", payload, token=READER_TOKEN).json()
    assert resp.get("code") == 200
    awarded = await _award(
        "RECEIVE_DISLIKE", AUTHOR_ID, actor_id=READER_ID,
        target_type="PRODUCT", target_id=product_id, key=f"dislike:{READER_ID}:{product_id}",
    )
    assert awarded.final_output["loyalty_awarded"] is False
    after = loyalty_service.get_account(AUTHOR_ID).balance
    assert after == before


def test_redeem_membership_with_points(client):
    account = loyalty_service._ensure_account(AUTHOR_ID)
    account["balance"] = 30000

    resp = dispatch(
        client,
        "loyalty.rewards.redeem",
        {"item_code": "membership_pro_yearly", "qty": 1, "idempotency_key": "redeem:pro:test"},
        token=AUTHOR_TOKEN,
    ).json()
    assert resp.get("code") == 200, resp
    assert resp["data"]["order"]["status"] == "COMPLETED"
    assert loyalty_service.get_account(AUTHOR_ID).balance == 6000

    membership = loyalty_service.get_membership(AUTHOR_ID)
    assert membership.tier == "PRO"
    assert membership.status == "ACTIVE"
    assert user_service._users_by_uid[AUTHOR_ID]["tier_name"] == "PRO 创客"
    assert "ent_ai_tax_assistant" in user_service._users_by_uid[AUTHOR_ID]["active_entitlements"]


def test_physical_reward_requires_address(client):
    account = loyalty_service._ensure_account(AUTHOR_ID)
    account["balance"] = 5000

    resp = dispatch(
        client,
        "loyalty.rewards.redeem",
        {"item_code": "physical_sticker_pack", "qty": 1},
        token=AUTHOR_TOKEN,
    ).json()
    # v2 兑换场景用业务结果标记拒绝，而不是抛错：地址缺失 → loyalty_redeemed=False
    assert resp.get("code") == 200
    assert resp["data"]["loyalty_redeemed"] is False
    assert resp["data"]["loyalty_reason"] == "address_required"
    assert loyalty_service.get_account(AUTHOR_ID).balance == 5000

    ok = dispatch(
        client,
        "loyalty.rewards.redeem",
        {
            "item_code": "physical_sticker_pack",
            "qty": 1,
            "address": {"name": "张三", "phone": "13800000000", "detail": "杭州市西湖区"},
        },
        token=AUTHOR_TOKEN,
    ).json()
    assert ok.get("code") == 200, ok
    assert ok["data"]["order"]["status"] == "PAID"
    assert loyalty_service.get_account(AUTHOR_ID).balance == 3500


def test_admin_grant_is_audited_and_uncapped(client):
    resp = dispatch(
        client,
        "loyalty.admin.grant",
        {"uid": AUTHOR_ID, "delta": 50000, "reason": "运营补发测试"},
    ).json()
    assert resp.get("code") == 200, resp
    assert loyalty_service.get_account(AUTHOR_ID).balance == 50000
    entries = loyalty_service.list_ledger(AUTHOR_ID, limit=10).items
    assert any(entry.event_code == "ADMIN_ADJUST" for entry in entries)


def test_founding_vip_is_exposed_as_membership(client):
    record = user_service._users_by_uid[AUTHOR_ID]
    record["tier_name"] = "黑钻创客 VIP"
    record["active_entitlements"] = {"ent_black_diamond_priority"}
    record["entitlement_expiries"] = {"ent_black_diamond_priority": "2099-01-01 00:00:00"}
    # v2：会员记录是权威数据源，创始会员的旧用户记录由同步算子投影一次。
    loyalty_service.sync_legacy_memberships()
    me = dispatch(client, "loyalty.membership.me", token=AUTHOR_TOKEN).json()
    assert me.get("code") == 200, me
    assert me["data"]["tier"] == "BLACK_DIAMOND"
    assert me["data"]["source"] == "GRANT"
    assert me["data"]["status"] == "ACTIVE"


def test_lower_tier_redeem_is_rejected_for_higher_grant(client):
    record = user_service._users_by_uid[AUTHOR_ID]
    record["tier_name"] = "黑钻创客 VIP"
    record["active_entitlements"] = {"ent_black_diamond_priority"}
    record["entitlement_expiries"] = {"ent_black_diamond_priority": "2099-01-01 00:00:00"}
    loyalty_service.sync_legacy_memberships()
    loyalty_service._ensure_account(AUTHOR_ID)["balance"] = 30000

    resp = dispatch(
        client,
        "loyalty.rewards.redeem",
        {"item_code": "membership_pro_yearly", "qty": 1},
        token=AUTHOR_TOKEN,
    ).json()
    assert resp.get("code") == 200
    assert resp["data"]["loyalty_redeemed"] is False
    assert resp["data"]["loyalty_reason"] == "higher_tier_active"
    # 余额未被扣减
    assert loyalty_service.get_account(AUTHOR_ID).balance == 30000


def test_membership_plans_and_account_surface(client):
    plans = dispatch(client, "loyalty.membership.plans").json()
    assert plans.get("code") == 200
    assert {item["tier"] for item in plans["data"]["items"]} == {"PRO", "BLACK_DIAMOND"}
    assert any(item["points_price"] == 24000 for item in plans["data"]["items"])

    account = dispatch(client, "loyalty.account", token=AUTHOR_TOKEN).json()
    assert account.get("code") == 200
    assert account["data"]["membership_tier"] == "STANDARD"
    assert account["data"]["level_name"] == "微光"
