"""Tests for NLP Semantic Similarity Search in Forum and Products."""
import pytest
from src.core.gateway import register_default_scenario_routes
from src.core.gateway.router import scenario_router, DispatchRequest


@pytest.fixture(autouse=True)
def setup_routes():
    register_default_scenario_routes()


@pytest.mark.asyncio
async def test_forum_semantic_search():
    """Verify semantic similarity and keyword NLP search on forum threads."""
    req = DispatchRequest(
        scenario="forum.search.semantic",
        payload={"query": "长三角 算力 补贴 申请", "top_k": 5}
    )
    res = await scenario_router.dispatch(req)
    assert res.code == 200
    assert "items" in res.data
    items = res.data["items"]
    assert len(items) > 0
    # Top match should be the math/computing subsidy thread
    top = items[0]
    assert "算力补贴" in top["title"] or "12 万元" in top["title"]
    assert "semantic_score" in top
    assert top["semantic_score"] > 0


@pytest.mark.asyncio
async def test_product_semantic_search():
    """Verify semantic similarity and keyword NLP search on showcase products."""
    req = DispatchRequest(
        scenario="products.search.semantic",
        payload={"query": "AI写作 与 编辑器", "top_k": 5}
    )
    res = await scenario_router.dispatch(req)
    assert res.code == 200
    assert "items" in res.data
    items = res.data["items"]
    assert len(items) > 0
    top = items[0]
    assert "InkFlow" in top["title"] or "写作" in top.get("category", "") or "写作" in top["title"]
    assert "semantic_score" in top
    assert top["semantic_score"] > 0


@pytest.mark.asyncio
async def test_empty_query_returns_empty():
    """Verify empty query returns clean empty results without error."""
    req = DispatchRequest(scenario="forum.search.semantic", payload={"query": "   "})
    res = await scenario_router.dispatch(req)
    assert res.code == 200
    assert res.data["total"] == 0
    assert res.data["items"] == []
