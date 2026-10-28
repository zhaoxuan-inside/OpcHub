"""Tests for Forum Infinite Scroll Stream Feed, Multi-tier Caching, and Preloading DAG Pipeline."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.domains.forum.service import forum_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


def _populate_feed_threads(count: int = 6) -> None:
    """Create deterministic, test-owned threads (no production seed data)."""
    from src.domains.forum.models import ForumThreadResponse

    for i in range(count):
        tid = f"th_feed_{i + 1}"
        created = f"2026-01-{i + 1:02d}T00:00:00+00:00"
        forum_service._threads[tid] = ForumThreadResponse(
            id=tid,
            category_code="DEV" if i % 2 == 0 else "BIZ",
            author_id=f"usr_feed_{i + 1}",
            title=f"Feed 测试帖子 {i + 1}",
            content=f"用于分页与游标测试的帖子正文 {i + 1}。",
            created_at=created,
            updated_at=created,
        )


@pytest_asyncio.fixture(autouse=True)
async def setup_forum_feed():
    forum_service.clear()
    _populate_feed_threads()
    forum_service.invalidate_feed_cache()
    yield
    forum_service.clear()
    forum_service.invalidate_feed_cache()


@pytest.mark.asyncio
async def test_forum_feed_stream_dag_execution():
    """Verify that OPC_FORUM_FEED_STREAM_PIPELINE executes successfully through the microkernel DAG."""
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
            version="v1.0.0",
            inputs={"category_code": "ALL", "cursor": 0, "limit": 2, "sort_by": "latest"},
        )
    )
    assert res.status == "SUCCESS"
    feed = res.final_output.get("feed_result")
    assert feed is not None
    assert feed["limit"] == 2
    assert len(feed["items"]) == 2
    assert feed["has_more"] is True
    assert feed["next_cursor"] == 2
    assert "prefetch_hint" in feed
    assert feed["prefetch_hint"]["recommended_prefetch_cursor"] == 2


@pytest.mark.asyncio
async def test_forum_feed_cache_hit_and_prewarming():
    """Verify cache read, cache write, and speculative next-batch prewarming."""
    # First request: Cache Miss
    res1 = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
            version="v1.0.0",
            inputs={"category_code": "ALL", "cursor": 0, "limit": 2, "sort_by": "latest"},
        )
    )
    assert res1.status == "SUCCESS"
    assert res1.final_output.get("cache_hit") is False
    assert res1.final_output.get("cache_written") is True
    assert res1.final_output.get("prewarmed_next") is True

    # Second request: Cache Hit
    res2 = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
            version="v1.0.0",
            inputs={"category_code": "ALL", "cursor": 0, "limit": 2, "sort_by": "latest"},
        )
    )
    assert res2.status == "SUCCESS"
    assert res2.final_output.get("cache_hit") is True

    # Next cursor request (cursor=2): Should already be pre-warmed in cache!
    res3 = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
            version="v1.0.0",
            inputs={"category_code": "ALL", "cursor": 2, "limit": 2, "sort_by": "latest"},
        )
    )
    assert res3.status == "SUCCESS"
    assert res3.final_output.get("cache_hit") is True


@pytest.mark.asyncio
async def test_forum_publish_invalidates_feed_cache():
    """Verify that publishing a new thread invalidates the feed cache via forum.cache.invalidate_operator."""
    # 1. Warm up cache
    await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
            version="v1.0.0",
            inputs={"category_code": "DEV", "cursor": 0, "limit": 5, "sort_by": "latest"},
        )
    )

    # 2. Publish thread via DAG (which includes step_invalidate_cache)
    pub_res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_THREAD_PUBLISH",
            version="v1.0.0",
            inputs={
                "category_code": "DEV",
                "title": "测试全新微内核缓存驱逐讨论帖",
                "content": "这里是详细的代码测试探讨与实战复盘内容描述。",
                "author_id": "usr_test_cache",
            },
        )
    )
    assert pub_res.status == "SUCCESS"
    assert pub_res.final_output.get("cache_invalidated") is True

    # 3. Next fetch: Cache should be missed and newly created thread should be at top
    res = await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
            version="v1.0.0",
            inputs={"category_code": "DEV", "cursor": 0, "limit": 5, "sort_by": "latest"},
        )
    )
    assert res.status == "SUCCESS"
    assert res.final_output.get("cache_hit") is False
    items = res.final_output["feed_result"]["items"]
    assert any(t["title"] == "测试全新微内核缓存驱逐讨论帖" for t in items)


@pytest.mark.asyncio
async def test_gateway_route_forum_feed_stream():
    """Verify HTTP gateway route /api/v1/gateway/dispatch for forum.feed.stream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/gateway/dispatch",
            json={
                "scenario": "forum.feed.stream",
                "payload": {
                    "category_code": "ALL",
                    "cursor": 0,
                    "limit": 3,
                    "sort_by": "latest",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        feed = data["data"]
        assert len(feed["items"]) == 3
        assert feed["has_more"] is True
        assert feed["next_cursor"] == 3
        assert "prefetch_hint" in feed
