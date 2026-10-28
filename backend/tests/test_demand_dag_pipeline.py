"""Gateway-level regression tests for the demand marketplace (需求集市).

Business flows are declared in ``config/scenarios/demands.yaml`` and executed by
the operator kernel; the gateway route still funnels through the legacy
scenario adapter, so these tests assert the end-to-end ``/api/welcom/opc_world``
contract (identity binding, response shape, content gate). Kernel-level flow
coverage lives in ``tests/test_demands_operator_flows.py``.
"""
import pytest
from fastapi.testclient import TestClient

from src.core.security import create_session_token
from src.domains.demands.service import demand_service
from src.main import app
from conftest import dispatch, gw_data

MAKER_TOKEN = create_session_token({
    "uid": "usr_dem_gw_maker",
    "email": "dem_gw_maker@opchub.cn",
    "nickname": "网关测试委托方",
    "role": "MAKER",
    "must_change_password": False,
})

DEMAND_PAYLOAD = {
    "title": "海外独立站 Shopify 支付插件定制开发",
    "description": "需要资深独立开发者对接 Stripe 与 PayPal 订阅计费网关，要求通过 PCI-DSS 基础合规检查。",
    "budget_cny": 15000.0,
    "category": "DEV",
    "deadline_days": 10,
}


@pytest.fixture(autouse=True)
def clean_demand_state():
    demand_service.clear()
    yield
    demand_service.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _publish(client, payload=None):
    return dispatch(client, "demands.publish", payload or DEMAND_PAYLOAD, token=MAKER_TOKEN)


def test_demand_publish_via_gateway_binds_gateway_identity(client):
    body = _publish(client).json()
    assert body["code"] == 200, body
    demand = body["data"]
    assert demand["title"] == DEMAND_PAYLOAD["title"]
    assert demand["budget_cny"] == 15000.0
    assert demand["creator_id"] == "usr_dem_gw_maker"
    assert demand["is_official"] is False
    assert demand["status"] == "OPEN"

    stored = demand_service.get_demand(demand["id"])
    assert stored is not None
    assert stored.creator_id == "usr_dem_gw_maker"


def test_demand_publish_blocks_sensitive_content_via_gateway(client):
    payload = dict(
        DEMAND_PAYLOAD,
        description="需要能够提供洗钱与地下钱庄资金通道的合作方。",
    )
    body = _publish(client, payload).json()
    assert body["code"] == 400
    assert "敏感" in str(body)


def test_demand_bid_via_gateway_binds_bidder_and_counts(client):
    demand = gw_data(client, "demands.publish", DEMAND_PAYLOAD)

    bid = dispatch(
        client,
        "demands.bid",
        {
            "demand_id": demand["id"],
            "bid_amount_cny": 14000.0,
            "delivery_days": 6,
            "proposal_text": "已交付过同类独立站系统，拥有成熟方案与生产级代码，6 天内高质量交付并协助上线。",
        },
        token=MAKER_TOKEN,
    ).json()["data"]

    assert bid["demand_id"] == demand["id"]
    assert bid["bidder_id"] == "usr_dem_gw_maker"
    assert bid["bid_amount_cny"] == 14000.0
    assert demand_service.get_demand(demand["id"]).bidders_count == 1


def test_demand_list_supports_flat_feed_and_paged_envelope(client):
    gw_data(client, "demands.publish", DEMAND_PAYLOAD)

    flat = gw_data(client, "demands.list", {})
    assert isinstance(flat, list)
    assert any(item["title"] == DEMAND_PAYLOAD["title"] for item in flat)

    paged = gw_data(client, "demands.list", {"page": 1, "page_size": 5})
    assert paged["page"] == 1
    assert paged["page_size"] == 5
    assert paged["total"] >= 1
    assert len(paged["items"]) >= 1
