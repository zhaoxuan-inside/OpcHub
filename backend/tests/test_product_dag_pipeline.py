"""Test suite for P03 Product Showcase driven by Microkernel DAG Orchestration & Saga Compensation."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.products.service import product_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


@pytest.fixture(autouse=True)
def clean_product_state():
    """Reset product service state before each test."""
    product_service.clear()
    product_service._seed_default_products()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_product_publish_via_microkernel_dag(client):
    """Verify publishing a product strictly orchestrated by OPC_PRODUCT_PUBLISH_PIPELINE DAG."""
    payload = {
        "scenario": "products.publish",
        "version": "v1.0.0",
        "client_code_version": "v1.0.4",
        "payload": {
            "title": "极速出海自动结汇机器人",
            "tagline": "基于 Stripe 与万里汇 API 的全自动结汇与报税凭证同步系统",
            "description": "专为超级个体和出海一人公司设计的金融自动化流水线，合规透明无需人工干预。",
            "category": "SAAS",
            "pricing_model": "SUBSCRIPTION",
            "price_cny": 129.0,
            "demo_url": "https://remit.opchub.dev",
            "author_id": "usr_maker_2026",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["code"] == 200
    assert data["scenario"] == "products.publish"

    prod = data["data"]
    assert "id" in prod
    assert prod["title"] == "极速出海自动结汇机器人"
    assert prod["category"] == "SAAS"
    assert prod["price_cny"] == 129.0
    assert prod["status"] == "PUBLISHED"

    # Verify repository persistence
    all_prods = product_service.list_products()
    matched = next((p for p in all_prods if p.id == prod["id"]), None)
    assert matched is not None
    assert matched.title == "极速出海自动结汇机器人"


def test_product_publish_moderation_guard_blocks_violation(client):
    """Verify that sensitive keywords are blocked by product.validate_guard."""
    payload = {
        "scenario": "products.publish",
        "version": "v1.0.0",
        "payload": {
            "title": "代开假发票自动化脚本",
            "tagline": "批量生成非法抵扣进项发票",
            "description": "针对小微企业的违规避税方案...",
            "category": "DEV",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 400 or resp.status_code == 422 or resp.status_code == 200
    data = resp.json()
    assert data["code"] != 200 or "violation" in str(data) or "prohibited" in str(data)


@pytest.mark.asyncio
async def test_product_publish_saga_rollback_on_failure():
    """Verify Saga reverse compensation deletes persisted product when downstream fails."""
    exec_req = ScenarioExecuteRequest(
        scenario_code="OPC_PRODUCT_PUBLISH_PIPELINE",
        version="v1.0.0",
        inputs={
            "title": "将要在下游失败测试回滚的商用作品",
            "tagline": "用于验证分布式 Saga 事务补偿回滚算法的作品实体",
            "description": "如果下游度量或事件发布失败，本作品必须从作品库中物理删除。",
            "category": "DEV",
            "price_cny": 50.0,
            "author_id": "usr_saga_tester",
            "simulate_downstream_failure": True,
        },
    )

    res = await orchestration_service.execute_scenario(exec_req)
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0
    # Product must NOT exist in service repository
    all_prods = product_service.list_products()
    assert not any(p.title == "将要在下游失败测试回滚的商用作品" for p in all_prods)


def test_product_upvote_and_listing(client):
    """Verify upvoting products and retrieving sorted showcase via gateway."""
    prods = product_service.list_products()
    target_prod = prods[-1]
    initial_upvotes = target_prod.upvote_count

    # Upvote via gateway
    upvote_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "products.upvote",
            "version": "v1.0.0",
            "payload": {"product_id": target_prod.id},
        },
    )
    assert upvote_resp.status_code == 200
    upvoted_data = upvote_resp.json()["data"]
    assert upvoted_data["upvote_count"] == initial_upvotes + 1

    # List products via gateway
    list_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "products.list",
            "version": "v1.0.0",
            "payload": {},
        },
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()["data"]
    assert isinstance(list_data, list)
    assert len(list_data) >= 1
    # Check descending sort by upvote count
    counts = [p["upvote_count"] for p in list_data]
    assert counts == sorted(counts, reverse=True)
