"""Tests for Administrator Content Moderation and Take-down capabilities.

All business access goes through the unified gateway entrypoint (single-entry architecture).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from conftest import DEFAULT_ADMIN_TOKEN
from src.domains.moderation.service import moderation_service
from src.domains.moderation.models import ModerationItemResponse


async def _gw(ac, scenario, payload):
    ac.headers["Authorization"] = f"Bearer {DEFAULT_ADMIN_TOKEN}"
    return await ac.post("/api/welcom/opc_world", json={
        "scenario": scenario, "version": "v1.0.0", "payload": payload,
    })


@pytest.fixture(autouse=True)
def seed_moderation_items():
    """Seed test-only moderation items so take-down/restore APIs have real targets."""
    from src.domains.moderation.service import utc_now_iso
    moderation_service._items.clear()
    moderation_service._items["mod-101"] = ModerationItemResponse(
        id="mod-101",
        target_type="FORUM_THREAD",
        target_id="th_viol_01",
        author_id="usr_leak_test",
        author_name="测试违规用户",
        snippet_content="测试违规内容：出售未经脱敏的企业数据。",
        violation_type="ILLEGAL_TRADE",
        status="FLAGGED",
        reported_at=utc_now_iso(),
        reason="测试原因：商业机密泄露",
    )
    moderation_service._items["mod-102"] = ModerationItemResponse(
        id="mod-102",
        target_type="FORUM_COMMENT",
        target_id="cm_viol_02",
        author_id="usr_tax_fake_test",
        author_name="测试财税黑中介",
        snippet_content="测试违规内容：买发票冲抵进项。",
        violation_type="SCAM",
        status="TAKEN_DOWN",
        reported_at=utc_now_iso(),
        moderated_at=utc_now_iso(),
        reason="测试原因：虚假宣传",
        moderator_id="admin_test",
    )
    yield
    moderation_service._items.clear()


@pytest.mark.asyncio
async def test_list_moderation_items():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await _gw(ac, "moderation.items.list", {})
        assert res.json()["code"] == 200
        items = res.json()["data"]
        assert len(items) >= 2
        ids = [it["id"] for it in items]
        assert "mod-101" in ids
        assert "mod-102" in ids


@pytest.mark.asyncio
async def test_filter_moderation_items_by_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await _gw(ac, "moderation.items.list", {"status": "FLAGGED"})
        assert res.json()["code"] == 200
        items = res.json()["data"]
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
        res = await _gw(ac, "moderation.takedown", payload)
        assert res.json()["code"] == 200
        data = res.json()["data"]
        assert data.get("item_id") == "mod-101"
        assert data["status"] == "TAKEN_DOWN"
        assert "泄露内网敏感代码" in data["note"]
        assert "作者已封禁" in data["note"]

        # Verify list reflects TAKEN_DOWN
        res_list = await _gw(ac, "moderation.items.list", {})
        items = res_list.json()["data"]
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
        res = await _gw(ac, "moderation.restore", payload)
        assert res.json()["code"] == 200
        data = res.json()["data"]
        assert data.get("item_id") == "mod-102"
        assert data["status"] == "NORMAL"


@pytest.mark.asyncio
async def test_moderation_item_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await _gw(ac, "moderation.takedown", {
            "item_id": "mod-nonexistent-999",
            "reason": "测试"
        })
        assert res.json()["code"] != 200
