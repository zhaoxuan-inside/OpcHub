"""Tests for Administrator Content Moderation and Take-down APIs."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_list_moderation_items():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/admin/moderation/items")
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 4
        ids = [it["id"] for it in items]
        assert "mod-101" in ids
        assert "mod-102" in ids


@pytest.mark.asyncio
async def test_filter_moderation_items_by_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/admin/moderation/items?status=FLAGGED")
        assert res.status_code == 200
        items = res.json()
        for it in items:
            assert it["status"] == "FLAGGED"


@pytest.mark.asyncio
async def test_takedown_violating_content():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "item_id": "mod-101",
            "reason": "泄露内网敏感代码与API密钥",
            "moderator_id": "admin_sys_01",
            "ban_author": True
        }
        res = await ac.post("/api/v1/admin/moderation/takedown", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["item_id"] == "mod-101"
        assert data["status"] == "TAKEN_DOWN"
        assert "泄露内网敏感代码" in data["note"]
        assert "作者已封禁" in data["note"]

        # Verify list reflects TAKEN_DOWN
        res_list = await ac.get("/api/v1/admin/moderation/items")
        items = res_list.json()
        target = next(it for it in items if it["id"] == "mod-101")
        assert target["status"] == "TAKEN_DOWN"
        assert target["moderator_id"] == "admin_sys_01"


@pytest.mark.asyncio
async def test_restore_content():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "item_id": "mod-102",
            "moderator_id": "admin_sys_01"
        }
        res = await ac.post("/api/v1/admin/moderation/restore", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["item_id"] == "mod-102"
        assert data["status"] == "NORMAL"


@pytest.mark.asyncio
async def test_moderation_item_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/admin/moderation/takedown", json={
            "item_id": "mod-nonexistent-999",
            "reason": "测试"
        })
        assert res.status_code == 404
