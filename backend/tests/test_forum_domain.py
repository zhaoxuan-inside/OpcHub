"""Tests for Forum Domain (Threads, Materialized-path Recursive Comments Tree, Upvotes, Bookmarks)."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.domains.forum.service import forum_service


@pytest.fixture(autouse=True)
def clean_forum_service():
    """Reset service in-memory store before each test."""
    forum_service.clear()
    yield
    forum_service.clear()


@pytest.mark.asyncio
async def test_forum_thread_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Publish discussion thread
        thread_payload = {
            "category_code": "DEV",
            "author_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "title": "一人公司如何利用 Claude 3.5 Sonnet 与 AST 构建沙箱？",
            "content": "本文详细解析如何在独立开发场景下，构建轻量级微内核沙箱...",
        }
        res = await ac.post("/api/v1/forum/threads", json=thread_payload)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == thread_payload["title"]
        assert data["category_code"] == "DEV"
        assert data["view_count"] == 0
        assert data["upvote_count"] == 0
        assert data["comment_count"] == 0
        assert data["bookmark_count"] == 0
        assert data["status"] == "PUBLISHED"
        thread_id = data["id"]

        # 2. List threads
        list_res = await ac.get("/api/v1/forum/threads")
        assert list_res.status_code == 200
        threads = list_res.json()
        assert len(threads) == 1
        assert threads[0]["id"] == thread_id

        # Filter by category
        cat_res = await ac.get("/api/v1/forum/threads?category_code=BIZ")
        assert cat_res.status_code == 200
        assert len(cat_res.json()) == 0


@pytest.mark.asyncio
async def test_forum_nested_comments_tree_and_materialized_path():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create thread
        thread_res = await ac.post("/api/v1/forum/threads", json={
            "category_code": "DEV",
            "author_id": "author-uuid-1",
            "title": "AST 沙箱的符号表隔离策略",
            "content": "讨论一下关于 AST 安全扫描的具体实现方案...",
        })
        thread_id = thread_res.json()["id"]

        # 1. Create top-level answer A (depth 0)
        c1_res = await ac.post(f"/api/v1/forum/threads/{thread_id}/comments", json={
            "author_id": "user-a",
            "content": "顶级回答：建议采用 NodeVisitor 拦截危险调用",
        })
        assert c1_res.status_code == 201
        c1 = c1_res.json()
        assert c1["depth"] == 0
        assert c1["parent_id"] is None
        assert c1["root_id"] == c1["id"]
        assert c1["materialized_path"] == f"/{c1['id']}"

        # 2. Create reply to answer A ("回答的回答", depth 1)
        c2_res = await ac.post(f"/api/v1/forum/threads/{thread_id}/comments", json={
            "author_id": "user-b",
            "content": "楼中楼第一层：NodeVisitor 确实比正则解析更安全",
            "parent_id": c1["id"],
        })
        assert c2_res.status_code == 201
        c2 = c2_res.json()
        assert c2["depth"] == 1
        assert c2["parent_id"] == c1["id"]
        assert c2["root_id"] == c1["id"]
        assert c2["reply_to_user_id"] == "user-a"
        assert c2["materialized_path"] == f"/{c1['id']}/{c2['id']}"

        # 3. Create sub-reply to reply ("对回答的回答的回答", depth 2)
        c3_res = await ac.post(f"/api/v1/forum/threads/{thread_id}/comments", json={
            "author_id": "user-c",
            "content": "楼中楼第二层（3级嵌套）：配合只读沙箱隔离内存",
            "parent_id": c2["id"],
        })
        assert c3_res.status_code == 201
        c3 = c3_res.json()
        assert c3["depth"] == 2
        assert c3["parent_id"] == c2["id"]
        assert c3["root_id"] == c1["id"]
        assert c3["reply_to_user_id"] == "user-b"
        assert c3["materialized_path"] == f"/{c1['id']}/{c2['id']}/{c3['id']}"

        # 4. Create another top-level answer B (depth 0)
        c4_res = await ac.post(f"/api/v1/forum/threads/{thread_id}/comments", json={
            "author_id": "user-d",
            "content": "独立回答：我们还可以利用 WebAssembly 沙箱",
        })
        assert c4_res.status_code == 201
        c4 = c4_res.json()
        assert c4["depth"] == 0
        assert c4["parent_id"] is None
        assert c4["root_id"] == c4["id"]

        # 5. Fetch full thread detail and verify assembled recursive tree
        detail_res = await ac.get(f"/api/v1/forum/threads/{thread_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()

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
        # Create thread
        thread_res = await ac.post("/api/v1/forum/threads", json={
            "category_code": "TAX",
            "author_id": "maker-tax-1",
            "title": "2026 小微个体户季度 30 万增值税免征细则解析",
            "content": "全面拆解如何开具免税发票与规避补税风险...",
        })
        thread_id = thread_res.json()["id"]

        # 1. User 1 upvotes thread
        up1 = await ac.post("/api/v1/forum/upvote", json={
            "user_id": "user-1",
            "target_type": "THREAD",
            "target_id": thread_id,
        })
        assert up1.status_code == 200
        assert up1.json()["is_upvoted"] is True
        assert up1.json()["upvote_count"] == 1

        # 2. User 1 upvotes thread again (atomic toggle cancels vote)
        up1_cancel = await ac.post("/api/v1/forum/upvote", json={
            "user_id": "user-1",
            "target_type": "THREAD",
            "target_id": thread_id,
        })
        assert up1_cancel.status_code == 200
        assert up1_cancel.json()["is_upvoted"] is False
        assert up1_cancel.json()["upvote_count"] == 0

        # 3. Multi-user concurrent upvote accumulation
        await ac.post("/api/v1/forum/upvote", json={
            "user_id": "user-1",
            "target_type": "THREAD",
            "target_id": thread_id,
        })
        up2 = await ac.post("/api/v1/forum/upvote", json={
            "user_id": "user-2",
            "target_type": "THREAD",
            "target_id": thread_id,
        })
        assert up2.status_code == 200
        assert up2.json()["is_upvoted"] is True
        assert up2.json()["upvote_count"] == 2

        # 4. Upvote a comment
        c_res = await ac.post(f"/api/v1/forum/threads/{thread_id}/comments", json={
            "author_id": "expert-1",
            "content": "注意：免征增值税依然需要依法申报，不得直接跳过零申报！",
        })
        comment_id = c_res.json()["id"]

        up_comment = await ac.post("/api/v1/forum/upvote", json={
            "user_id": "user-3",
            "target_type": "COMMENT",
            "target_id": comment_id,
        })
        assert up_comment.status_code == 200
        assert up_comment.json()["is_upvoted"] is True
        assert up_comment.json()["upvote_count"] == 1


@pytest.mark.asyncio
async def test_forum_bookmark_atomic_toggle_and_folders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create thread
        thread_res = await ac.post("/api/v1/forum/threads", json={
            "category_code": "AGENTS",
            "author_id": "maker-ai-1",
            "title": "出海 Stripe + Mercury 离岸公司极速注册 SOP",
            "content": "实操步骤与合规门槛...",
        })
        thread_id = thread_res.json()["id"]

        # 1. Bookmark thread
        bm1 = await ac.post("/api/v1/forum/bookmark", json={
            "user_id": "user-maker-9",
            "thread_id": thread_id,
            "folder_name": "出海合规精选",
        })
        assert bm1.status_code == 200
        assert bm1.json()["is_bookmarked"] is True
        assert bm1.json()["bookmark_count"] == 1
        assert bm1.json()["folder_name"] == "出海合规精选"

        # 2. Toggle cancel bookmark
        bm1_cancel = await ac.post("/api/v1/forum/bookmark", json={
            "user_id": "user-maker-9",
            "thread_id": thread_id,
        })
        assert bm1_cancel.status_code == 200
        assert bm1_cancel.json()["is_bookmarked"] is False
        assert bm1_cancel.json()["bookmark_count"] == 0

        # 3. Two makers bookmarking same thread
        await ac.post("/api/v1/forum/bookmark", json={
            "user_id": "user-a",
            "thread_id": thread_id,
        })
        bm_b = await ac.post("/api/v1/forum/bookmark", json={
            "user_id": "user-b",
            "thread_id": thread_id,
        })
        assert bm_b.json()["bookmark_count"] == 2


@pytest.mark.asyncio
async def test_forum_error_handling():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Non-existent thread detail
        res = await ac.get("/api/v1/forum/threads/non-existent-uuid")
        assert res.status_code == 404

        # 2. Comment on non-existent thread
        res = await ac.post("/api/v1/forum/threads/non-existent-uuid/comments", json={
            "author_id": "user-1",
            "content": "hello",
        })
        assert res.status_code == 404

        # 3. Invalid parent comment
        thread_res = await ac.post("/api/v1/forum/threads", json={
            "category_code": "DEV",
            "author_id": "user-1",
            "title": "Title",
            "content": "Content",
        })
        tid = thread_res.json()["id"]
        res = await ac.post(f"/api/v1/forum/threads/{tid}/comments", json={
            "author_id": "user-1",
            "content": "reply",
            "parent_id": "non-existent-parent",
        })
        assert res.status_code == 404

        # 4. Upvote non-existent target
        up_res = await ac.post("/api/v1/forum/upvote", json={
            "user_id": "user-1",
            "target_type": "THREAD",
            "target_id": "fake-thread-id",
        })
        assert up_res.status_code == 404
