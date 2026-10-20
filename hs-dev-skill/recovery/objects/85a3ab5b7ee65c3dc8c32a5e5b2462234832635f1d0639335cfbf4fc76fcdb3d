"""Tests for Forum Domain (Threads, Materialized-path Recursive Comments Tree, Upvotes, Bookmarks).

All business access goes through the unified gateway entrypoint (single-entry architecture).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from conftest import DEFAULT_ADMIN_TOKEN
from src.domains.forum.service import forum_service


@pytest.fixture(autouse=True)
def clean_forum_service():
    """Reset service in-memory store before each test."""
    forum_service.clear()
    yield
    forum_service.clear()


def _client(ac):
    ac.headers["Authorization"] = f"Bearer {DEFAULT_ADMIN_TOKEN}"
    return ac


async def _gw(ac, scenario, payload):
    return await ac.post("/api/welcom/opc_world", json={
        "scenario": scenario, "version": "v1.0.0", "payload": payload,
    })


@pytest.mark.asyncio
async def test_forum_thread_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        _client(ac)
        # 1. Publish discussion thread (via gateway scenario forum.threads.publish)
        thread_payload = {
            "category_code": "DEV",
            "author_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "title": "一人公司如何利用 Claude 3.5 Sonnet 与 AST 构建沙箱？",
            "content": "本文详细解析如何在独立开发场景下，构建轻量级微内核沙箱...",
        }
        res = await _gw(ac, "forum.threads.publish", thread_payload)
        assert res.status_code == 200
        body = res.json()
        assert body["code"] == 200
        data = body["data"]
        assert data["title"] == thread_payload["title"]
        assert data["category_code"] == "DEV"
        assert data["view_count"] == 0
        assert data["upvote_count"] == 0
        assert data["comment_count"] == 0
        assert data["bookmark_count"] == 0
        assert data["status"] == "PUBLISHED"
        thread_id = data["id"]

        # 2. List threads
        list_res = await _gw(ac, "forum.threads.list", {})
        assert list_res.json()["code"] == 200
        threads = list_res.json()["data"]
        assert len(threads) == 1
        assert threads[0]["id"] == thread_id

        # Filter by category
        cat_res = await _gw(ac, "forum.threads.list", {"category_code": "BIZ"})
        assert cat_res.json()["code"] == 200
        assert len(cat_res.json()["data"]) == 0


@pytest.mark.asyncio
async def test_forum_nested_comments_tree_and_materialized_path():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        _client(ac)
        # Create thread
        thread_res = await _gw(ac, "forum.threads.publish", {
            "category_code": "DEV",
            "author_id": "author-uuid-1",
            "title": "AST 沙箱的符号表隔离策略",
            "content": "讨论一下关于 AST 安全扫描的具体实现方案...",
        })
        thread_id = thread_res.json()["data"]["id"]

        # 1. Create top-level answer A (depth 0)
        c1_res = await _gw(ac, "forum.comments.create", {
            "thread_id": thread_id,
            "author_id": "user-a",
            "content": "顶级回答：建议采用 NodeVisitor 拦截危险调用",
        })
        assert c1_res.json()["code"] == 200
        c1 = c1_res.json()["data"]
        assert c1["depth"] == 0
        assert c1["parent_id"] is None
        assert c1["root_id"] == c1["id"]
        assert c1["materialized_path"] == f"/{c1['id']}"

        # 2. Create reply to answer A ("回答的回答", depth 1)
        c2_res = await _gw(ac, "forum.comments.create", {
            "thread_id": thread_id,
            "author_id": "user-b",
            "content": "楼中楼第一层：NodeVisitor 确实比正则解析更安全",
            "parent_id": c1["id"],
        })
        assert c2_res.json()["code"] == 200
        c2 = c2_res.json()["data"]
        assert c2["depth"] == 1
        assert c2["parent_id"] == c1["id"]
        assert c2["root_id"] == c1["id"]
        assert c2["reply_to_user_id"] == "user-a"
        assert c2["materialized_path"] == f"/{c1['id']}/{c2['id']}"

        # 3. Create sub-reply to reply ("对回答的回答的回答", depth 2)
        c3_res = await _gw(ac, "forum.comments.create", {
            "thread_id": thread_id,
            "author_id": "user-c",
            "content": "楼中楼第二层（3级嵌套）：配合只读沙箱隔离内存",
            "parent_id": c2["id"],
        })
        assert c3_res.json()["code"] == 200
        c3 = c3_res.json()["data"]
        assert c3["depth"] == 2
        assert c3["parent_id"] == c2["id"]
        assert c3["root_id"] == c1["id"]
        assert c3["reply_to_user_id"] == "user-b"
        assert c3["materialized_path"] == f"/{c1['id']}/{c2['id']}/{c3['id']}"

        # 4. Create another top-level answer B (depth 0)
        c4_res = await _gw(ac, "forum.comments.create", {
            "thread_id": thread_id,
            "author_id": "user-d",
            "content": "独立回答：我们还可以利用 WebAssembly 沙箱",
        })
        assert c4_res.json()["code"] == 200
        c4 = c4_res.json()["data"]
        assert c4["depth"] == 0
        assert c4["parent_id"] is None
        assert c4["root_id"] == c4["id"]

        # 5. Fetch full thread detail and verify assembled recursive tree
        detail_res = await _gw(ac, "forum.threads.get", {"thread_id": thread_id})
        assert detail_res.json()["code"] == 200
        detail = detail_res.json()["data"]

        # Thread stats
        assert detail["thread"]["comment_count"] == 4
        assert detail["thread"]["view_count"] == 1

        # Tree structure verification
        comments = detail["comments"]
        assert len(comments) == 2  # Two top-level answers: c1 and c4

        # Verify c1 branch
        tree_c1 = comments[0]
        assert tree_c1["id"] == c1["id"]
        assert len(tree_c1["children"]) == 1

        tree_c2 = tree_c1["children"][0]
        assert tree_c2["id"] == c2["id"]
        assert len(tree_c2["children"]) == 1

        tree_c3 = tree_c2["children"][0]
        assert tree_c3["id"] == c3["id"]
        assert len(tree_c3["children"]) == 0

        # Verify c4 branch
        tree_c4 = comments[1]
        assert tree_c4["id"] == c4["id"]
        assert len(tree_c4["children"]) == 0


@pytest.mark.asyncio
async def test_forum_upvote_atomic_toggle_and_deduplication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        _client(ac)
        # Create thread
        thread_res = await _gw(ac, "forum.threads.publish", {
            "category_code": "TAX",
            "author_id": "maker-tax-1",
            "title": "2026 小微个体户季度 30 万增值税免征细则解析",
            "content": "全面拆解如何开具免税发票与规避补税风险...",
        })
        thread_id = thread_res.json()["data"]["id"]

        # 1. User 1 upvotes thread
        up1 = await _gw(ac, "forum.upvote", {
            "user_id": "user-1", "target_type": "THREAD", "target_id": thread_id,
        })
        assert up1.json()["code"] == 200
        assert up1.json()["data"]["is_upvoted"] is True
        assert up1.json()["data"]["upvote_count"] == 1

        # 2. User 1 upvotes thread again (atomic toggle cancels vote)
        up1_cancel = await _gw(ac, "forum.upvote", {
            "user_id": "user-1", "target_type": "THREAD", "target_id": thread_id,
        })
        assert up1_cancel.json()["code"] == 200
        assert up1_cancel.json()["data"]["is_upvoted"] is False
        assert up1_cancel.json()["data"]["upvote_count"] == 0

        # 3. Multi-user concurrent upvote accumulation
        await _gw(ac, "forum.upvote", {"user_id": "user-1", "target_type": "THREAD", "target_id": thread_id})
        up2 = await _gw(ac, "forum.upvote", {"user_id": "user-2", "target_type": "THREAD", "target_id": thread_id})
        assert up2.json()["code"] == 200
        assert up2.json()["data"]["is_upvoted"] is True
        assert up2.json()["data"]["upvote_count"] == 2

        # 4. Upvote a comment
        c_res = await _gw(ac, "forum.comments.create", {
            "thread_id": thread_id,
            "author_id": "expert-1",
            "content": "注意：免征增值税依然需要依法申报，不得直接跳过零申报！",
        })
        comment_id = c_res.json()["data"]["id"]

        up_comment = await _gw(ac, "forum.upvote", {
            "user_id": "user-3", "target_type": "COMMENT", "target_id": comment_id,
        })
        assert up_comment.json()["code"] == 200
        assert up_comment.json()["data"]["is_upvoted"] is True
        assert up_comment.json()["data"]["upvote_count"] == 1


@pytest.mark.asyncio
async def test_forum_bookmark_atomic_toggle_and_folders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        _client(ac)
        # Create thread
        thread_res = await _gw(ac, "forum.threads.publish", {
            "category_code": "AGENTS",
            "author_id": "maker-ai-1",
            "title": "出海 Stripe + Mercury 离岸公司极速注册 SOP",
            "content": "实操步骤与合规门槛...",
        })
        thread_id = thread_res.json()["data"]["id"]

        # 1. Bookmark thread
        bm1 = await _gw(ac, "forum.bookmark", {
            "user_id": "user-maker-9",
            "thread_id": thread_id,
            "folder_name": "出海合规精选",
        })
        assert bm1.json()["code"] == 200
        assert bm1.json()["data"]["is_bookmarked"] is True
        assert bm1.json()["data"]["bookmark_count"] == 1
        assert bm1.json()["data"]["folder_name"] == "出海合规精选"

        # 2. Toggle cancel bookmark
        bm1_cancel = await _gw(ac, "forum.bookmark", {
            "user_id": "user-maker-9",
            "thread_id": thread_id,
        })
        assert bm1_cancel.json()["code"] == 200
        assert bm1_cancel.json()["data"]["is_bookmarked"] is False
        assert bm1_cancel.json()["data"]["bookmark_count"] == 0

        # 3. Two makers bookmarking same thread
        await _gw(ac, "forum.bookmark", {"user_id": "user-a", "thread_id": thread_id})
        bm_b = await _gw(ac, "forum.bookmark", {"user_id": "user-b", "thread_id": thread_id})
        assert bm_b.json()["data"]["bookmark_count"] == 2


@pytest.mark.asyncio
async def test_forum_error_handling():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        _client(ac)
        # 1. Non-existent thread detail => 404
        res = await _gw(ac, "forum.threads.get", {"thread_id": "non-existent-uuid"})
        assert res.json()["code"] == 404

        # 2. Comment on non-existent thread => error propagated from DAG pipeline
        res = await _gw(ac, "forum.comments.create", {
            "thread_id": "non-existent-uuid", "author_id": "user-1", "content": "hello",
        })
        assert res.json()["code"] >= 400

        # 3. Invalid parent comment
        thread_res = await _gw(ac, "forum.threads.publish", {
            "category_code": "DEV", "author_id": "user-1", "title": "Title",
            "content": "这是一个长度足够的测试帖子正文内容",
        })
        tid = thread_res.json()["data"]["id"]
        res = await _gw(ac, "forum.comments.create", {
            "thread_id": tid, "author_id": "user-1", "content": "reply", "parent_id": "non-existent-parent",
        })
        assert res.json()["code"] >= 400

        # 4. Upvote non-existent target => 404
        up_res = await _gw(ac, "forum.upvote", {
            "user_id": "user-1", "target_type": "THREAD", "target_id": "fake-thread-id",
        })
        assert up_res.json()["code"] == 404
