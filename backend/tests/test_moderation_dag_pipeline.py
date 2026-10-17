"""Tests for P09 Content Moderation microkernel DAG pipeline and Saga compensation."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.domains.moderation.service import moderation_service
from src.domains.moderation.models import ModerationItemResponse


@pytest.fixture(autouse=True)
def reset_moderation_state():
    """Reset moderation items to a known baseline before each test."""
    moderation_service._items["mod-101"] = ModerationItemResponse(
        id="mod-101",
        target_type="FORUM_THREAD",
        target_id="th_viol_01",
        author_id="usr_leak_0821",
        author_name="匿名外包工作室",
        snippet_content="出售未经脱敏的某大厂内网 API 鉴权私钥及爬虫套件...",
        violation_type="ILLEGAL_TRADE",
        status="FLAGGED",
        reported_at="2026-10-17T07:12:00Z",
        reason="涉嫌商业机密泄露与非法倒卖 API 鉴权私钥"
    )
    moderation_service._items["mod-102"] = ModerationItemResponse(
        id="mod-102",
        target_type="FORUM_COMMENT",
        target_id="cm_viol_02",
        author_id="usr_tax_fake_33",
        author_name="财税黑中介",
        snippet_content="保证月入十万！加 V 信 138XXXX 一对一包过工商免征偷逃税...",
        violation_type="SCAM",
        status="TAKEN_DOWN",
        reported_at="2026-10-17T06:45:00Z",
        moderated_at="2026-10-17T07:00:00Z",
        reason="虚假违规宣传与涉税违法黑产引流",
        moderator_id="admin_001"
    )


@pytest.mark.asyncio
async def test_moderation_takedown_pipeline_success():
    """Verify OPC_MODERATION_TAKEDOWN_PIPELINE successfully takes down violating content."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "moderation.takedown",
            "version": "v1.0.4",
            "payload": {
                "item_id": "mod-101",
                "reason": "泄露内网高密API密钥与代码资产",
                "moderator_id": "admin_audit_01",
                "ban_author": True
            },
            "context": {
                "trace_id": "tr_mod_takedown_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        res_data = data["data"]
        assert res_data["status"] == "TAKEN_DOWN"
        assert res_data["orchestrated_by"] == "OPC_MODERATION_TAKEDOWN_PIPELINE"
        assert "泄露内网高密API密钥" in res_data["note"]
        assert "作者已封禁" in res_data["note"]

        # Check domain state
        item = moderation_service.get_item("mod-101")
        assert item is not None
        assert item.status == "TAKEN_DOWN"


@pytest.mark.asyncio
async def test_moderation_takedown_saga_rollback_on_failure():
    """Verify Saga reverse compensation restores original status when downstream fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "moderation.takedown",
            "version": "v1.0.4",
            "payload": {
                "item_id": "mod-101",
                "reason": "测试下游故障触发Saga补偿",
                "moderator_id": "admin_audit_01",
                "simulate_downstream_failure": True
            },
            "context": {
                "trace_id": "tr_mod_takedown_saga"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        # Pipeline must fail and trigger compensation
        assert data["code"] != 200 or "Simulated downstream telemetry failure" in str(data)

        # Domain item must be rolled back to FLAGGED
        item = moderation_service.get_item("mod-101")
        assert item.status == "FLAGGED"


@pytest.mark.asyncio
async def test_moderation_restore_pipeline_success():
    """Verify OPC_MODERATION_RESTORE_PIPELINE successfully restores taken down content."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "moderation.restore",
            "version": "v1.0.4",
            "payload": {
                "item_id": "mod-102",
                "moderator_id": "admin_restore_01"
            },
            "context": {
                "trace_id": "tr_mod_restore_001"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == 200
        res_data = data["data"]
        assert res_data["status"] == "NORMAL"
        assert res_data["orchestrated_by"] == "OPC_MODERATION_RESTORE_PIPELINE"
        assert "言论恢复正常展示" in res_data["note"]

        # Check domain state
        item = moderation_service.get_item("mod-102")
        assert item is not None
        assert item.status == "NORMAL"


@pytest.mark.asyncio
async def test_moderation_restore_saga_rollback_on_failure():
    """Verify Saga reverse compensation re-marks status as TAKEN_DOWN if restore downstream fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req_body = {
            "scenario": "moderation.restore",
            "version": "v1.0.4",
            "payload": {
                "item_id": "mod-102",
                "moderator_id": "admin_restore_01",
                "simulate_downstream_failure": True
            },
            "context": {
                "trace_id": "tr_mod_restore_saga"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "Simulated downstream telemetry failure" in str(data)

        # Domain item must be rolled back to TAKEN_DOWN
        item = moderation_service.get_item("mod-102")
        assert item.status == "TAKEN_DOWN"


@pytest.mark.asyncio
async def test_moderation_guard_validation_failure():
    """Verify Guard blocks requests with non-existent item or empty reason."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Non-existent item
        req_body = {
            "scenario": "moderation.takedown",
            "version": "v1.0.4",
            "payload": {
                "item_id": "mod-nonexistent-888",
                "reason": "合规下架"
            }
        }
        res = await ac.post("/api/welcom/opc_world", json=req_body)
        data = res.json()
        assert data["code"] != 200 or "not found" in str(data)

        # Empty reason
        req_body2 = {
            "scenario": "moderation.takedown",
            "version": "v1.0.4",
            "payload": {
                "item_id": "mod-101",
                "reason": ""
            }
        }
        res2 = await ac.post("/api/welcom/opc_world", json=req_body2)
        data2 = res2.json()
        assert data2["code"] != 200 or "cannot be empty" in str(data2)
