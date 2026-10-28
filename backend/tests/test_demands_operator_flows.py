"""Operator-flow tests for the demands (需求集市) domain.

Every flow asserted here is declared in ``config/scenarios/demands.yaml`` and
executed by the operator kernel through
``orchestration_service.execute_scenario``; identity is carried in ``context``.
The legacy ``demand_service`` module is only used for its data/query shim.
"""
from __future__ import annotations

import pytest

from src.core.entity import entity_store
from src.domains.demands.service import demand_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

PUBLISH = "OPC_DEMAND_PUBLISH_PIPELINE"
BID = "OPC_DEMAND_BID_PIPELINE"
LIST = "OPC_DEMAND_LIST_PIPELINE"
DETAIL = "OPC_DEMAND_DETAIL_PIPELINE"
CLOSE = "OPC_DEMAND_CLOSE_PIPELINE"
DELETE = "OPC_DEMAND_DELETE_PIPELINE"
WITHDRAW = "OPC_DEMAND_BID_WITHDRAW_PIPELINE"

MAKER = {"user_id": "usr_dem_flow_maker", "user_role": "MAKER", "nickname": "算核测试委托方"}
OTHER_MAKER = {"user_id": "usr_dem_flow_bidder", "user_role": "MAKER", "nickname": "算核测试竞标方"}
ADMIN = {"user_id": "usr_dem_flow_admin", "user_role": "ADMIN", "nickname": "平台管理员"}

PUBLISH_PAYLOAD = {
    "title": "算子内核迁移测试：跨境支付网关对接委托",
    "description": "需要对接 Stripe 订阅计费与外汇结算通道，交付可运行的支付网关适配层与合规说明。",
    "budget_cny": 12000.0,
    "category": "DEV",
    "deadline_days": 21,
}

BID_PAYLOAD = {
    "demand_id": "",
    "bid_amount_cny": 11000.0,
    "delivery_days": 14,
    "proposal_text": "已交付三套同类跨境支付接入方案，可在两周内完成网关适配与上线验收。",
}


@pytest.fixture(autouse=True)
def clean_demand_state():
    """Reset the demand/bid entities so every flow starts from a known state."""
    _purge()
    demand_service.invalidate_cache()
    yield
    _purge()
    demand_service.invalidate_cache()


def _purge() -> None:
    for entity in ("demands.item", "demands.bid"):
        adapter = entity_store.adapter(entity)
        for row in list(adapter.all()):
            adapter.delete(str(row["id"]))
    demand_service._mirror.clear()


async def _run(scenario: str, inputs: dict, context: dict | None = None):
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=dict(inputs),
            context=dict(context or {}),
        )
    )


async def _publish(**overrides):
    payload = dict(PUBLISH_PAYLOAD, **overrides)
    res = await _run(PUBLISH, payload, MAKER)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["response"]


async def _bid(demand_id: str, **overrides):
    payload = dict(BID_PAYLOAD, demand_id=demand_id, **overrides)
    return await _run(BID, payload, OTHER_MAKER)


# --------------------------------------------------------------- publish
@pytest.mark.asyncio
async def test_publish_binds_creator_from_context_and_persists():
    res = await _run(
        PUBLISH,
        dict(PUBLISH_PAYLOAD, creator_id="usr_spoofed_creator", creator_name="官方发布"),
        MAKER,
    )

    assert res.status == "SUCCESS", res.error_message
    demand = res.final_output["response"]
    assert demand["creator_id"] == MAKER["user_id"]
    assert demand["creator_name"] == MAKER["nickname"]
    assert demand["is_official"] is False
    assert demand["status"] == "OPEN"
    assert demand["bidders_count"] == 0
    assert demand["title"] == PUBLISH_PAYLOAD["title"]
    assert demand["category"] == "DEV"
    assert demand["deadline_at"]
    assert demand["id"].startswith("dmd_")

    # Legacy shim reads the very same document out of the entity store.
    stored = demand_service.get_demand(demand["id"])
    assert stored is not None
    assert stored.creator_id == MAKER["user_id"]
    assert demand_service._demands[demand["id"]].title == PUBLISH_PAYLOAD["title"]


@pytest.mark.asyncio
async def test_publish_admin_is_stamped_official():
    demand = await _publish(is_official=False)
    assert demand["is_official"] is False

    res = await _run(PUBLISH, dict(PUBLISH_PAYLOAD, title="管理员代发委托"), ADMIN)
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["response"]["is_official"] is True


@pytest.mark.asyncio
async def test_publish_requires_authentication():
    res = await _run(PUBLISH, PUBLISH_PAYLOAD, {})
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


@pytest.mark.asyncio
async def test_publish_rejects_invalid_fields():
    short = await _run(PUBLISH, dict(PUBLISH_PAYLOAD, description="太短"), MAKER)
    assert short.status == "FAILED"
    assert "description" in (short.error_message or "")

    negative = await _run(PUBLISH, dict(PUBLISH_PAYLOAD, budget_cny=-1), MAKER)
    assert negative.status == "FAILED"
    assert "budget_cny" in (negative.error_message or "")


@pytest.mark.asyncio
async def test_publish_blocks_sensitive_content():
    res = await _run(
        PUBLISH,
        dict(PUBLISH_PAYLOAD, description="需要能够提供洗钱与地下钱庄资金通道的合作方。"),
        MAKER,
    )
    assert res.status == "FAILED"
    assert "敏感" in (res.error_message or "")
    assert demand_service.list_demands() == []


# --------------------------------------------------------------- bidding
@pytest.mark.asyncio
async def test_bid_persists_bid_and_increments_counter():
    demand = await _publish()
    res = await _bid(demand["id"], bidder_id="usr_spoofed_bidder")

    assert res.status == "SUCCESS", res.error_message
    bid = res.final_output["response"]
    assert bid["demand_id"] == demand["id"]
    assert bid["bidder_id"] == OTHER_MAKER["user_id"]
    assert bid["bid_amount_cny"] == BID_PAYLOAD["bid_amount_cny"]
    assert bid["delivery_days"] == BID_PAYLOAD["delivery_days"]
    assert bid["status"] == "SUBMITTED"
    assert bid["id"].startswith("bid_")

    refreshed = demand_service.get_demand(demand["id"])
    assert refreshed is not None
    assert refreshed.bidders_count == 1
    assert [item.id for item in demand_service.list_bids(demand["id"])] == [bid["id"]]
    assert len(demand_service._bids[demand["id"]]) == 1


@pytest.mark.asyncio
async def test_bid_rejects_unknown_demand():
    res = await _bid("dmd_does_not_exist")
    assert res.status == "FAILED"
    assert "不存在" in (res.error_message or "")


@pytest.mark.asyncio
async def test_bid_rejects_closed_demand():
    demand = await _publish()
    closed = await _run(CLOSE, {"demand_id": demand["id"]}, MAKER)
    assert closed.status == "SUCCESS", closed.error_message
    assert closed.final_output["response"]["status"] == "CLOSED"

    res = await _bid(demand["id"])
    assert res.status == "FAILED"
    assert "无法继续竞标" in (res.error_message or "")


@pytest.mark.asyncio
async def test_bid_rejects_invalid_proposal_and_anonymous_caller():
    demand = await _publish()

    short = await _bid(demand["id"], proposal_text="太短")
    assert short.status == "FAILED"
    assert "proposal_text" in (short.error_message or "")

    anonymous = await _run(BID, dict(BID_PAYLOAD, demand_id=demand["id"]), {})
    assert anonymous.status == "GUARD_REJECTED"

    sensitive = await _bid(demand["id"], proposal_text="可以配合代开假发票冲抵外包开发成本。")
    assert sensitive.status == "FAILED"
    assert "敏感" in (sensitive.error_message or "")

    assert demand_service.get_demand(demand["id"]).bidders_count == 0


# --------------------------------------------------------------- listing
@pytest.mark.asyncio
async def test_list_returns_flat_feed_without_page_and_filters_by_category():
    first = await _publish(title="列表测试委托甲", category="TAX")
    second = await _publish(title="列表测试委托乙", category="TAX")
    await _publish(title="列表测试委托丙", category="AI")

    res = await _run(LIST, {"category": "TAX", "search": "列表测试委托"})
    assert res.status == "SUCCESS", res.error_message
    items = res.final_output["response"]
    assert isinstance(items, list)
    assert {item["id"] for item in items} == {first["id"], second["id"]}


@pytest.mark.asyncio
async def test_list_returns_paged_envelope_when_page_is_provided():
    for index in range(3):
        await _publish(title=f"分页测试委托{index}")

    res = await _run(LIST, {"search": "分页测试委托", "page": 1, "page_size": 2})
    assert res.status == "SUCCESS", res.error_message
    envelope = res.final_output["response"]
    assert envelope["total"] == 3
    assert envelope["page"] == 1
    assert envelope["page_size"] == 2
    assert envelope["total_pages"] == 2
    assert envelope["has_more"] is True
    assert len(envelope["items"]) == 2

    second_page = await _run(LIST, {"search": "分页测试委托", "page": 2, "page_size": 2})
    tail = second_page.final_output["response"]
    assert len(tail["items"]) == 1
    assert tail["has_more"] is False


@pytest.mark.asyncio
async def test_detail_returns_demand_with_its_bids():
    demand = await _publish(title="详情测试委托")
    bid_res = await _bid(demand["id"])
    assert bid_res.status == "SUCCESS", bid_res.error_message
    bid = bid_res.final_output["response"]

    res = await _run(DETAIL, {"demand_id": demand["id"]})
    assert res.status == "SUCCESS", res.error_message
    detail = res.final_output["response"]
    assert detail["demand"]["id"] == demand["id"]
    assert detail["bid_count"] == 1
    assert [item["id"] for item in detail["bids"]] == [bid["id"]]


# ------------------------------------------------- close / delete / withdraw
@pytest.mark.asyncio
async def test_close_requires_owner():
    demand = await _publish()

    denied = await _run(CLOSE, {"demand_id": demand["id"]}, OTHER_MAKER)
    assert denied.status == "GUARD_REJECTED"
    assert "权限" in (denied.error_message or "")

    allowed = await _run(CLOSE, {"demand_id": demand["id"]}, MAKER)
    assert allowed.status == "SUCCESS", allowed.error_message
    assert allowed.final_output["response"]["status"] == "CLOSED"

    again = await _run(CLOSE, {"demand_id": demand["id"]}, MAKER)
    assert again.status == "FAILED"
    assert "无需重复操作" in (again.error_message or "")


@pytest.mark.asyncio
async def test_delete_removes_demand_and_requires_owner():
    demand = await _publish()

    denied = await _run(DELETE, {"demand_id": demand["id"]}, OTHER_MAKER)
    assert denied.status == "GUARD_REJECTED"
    assert demand_service.get_demand(demand["id"]) is not None

    removed = await _run(DELETE, {"demand_id": demand["id"]}, MAKER)
    assert removed.status == "SUCCESS", removed.error_message
    assert removed.final_output["response"] is True
    assert demand_service.get_demand(demand["id"]) is None


@pytest.mark.asyncio
async def test_withdraw_bid_decrements_counter_and_requires_owner():
    demand = await _publish()
    bid = (await _bid(demand["id"])).final_output["response"]

    denied = await _run(WITHDRAW, {"bid_id": bid["id"]}, MAKER)
    assert denied.status == "GUARD_REJECTED"
    assert demand_service.get_demand(demand["id"]).bidders_count == 1

    withdrawn = await _run(WITHDRAW, {"bid_id": bid["id"]}, OTHER_MAKER)
    assert withdrawn.status == "SUCCESS", withdrawn.error_message
    assert withdrawn.final_output["response"] is True
    assert demand_service.list_bids(demand["id"]) == []
    assert demand_service.get_demand(demand["id"]).bidders_count == 0
