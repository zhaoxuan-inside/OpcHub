"""消息箱：发布内容敏感词校验结果通知.

验证：
* 发布通过 / 被拦截都会给发布者落一条持久消息；
* 消息箱按用户隔离，支持未读计数、标记已读、全部已读与删除；
* 未登录用户无法读取他人消息。
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from src.core.security import create_session_token
from src.domains.notifications.service import notification_service
from src.domains.sop.models import SOPDocumentDraftCreate
from src.domains.sop.service import sop_service
from src.main import app
from conftest import dispatch


def _token(uid: str, nickname: str) -> str:
    return create_session_token({
        "uid": uid,
        "email": f"{uid}@opchub.cn",
        "nickname": nickname,
        "role": "MAKER",
        "must_change_password": False,
    })


MAKER_A = _token("usr_inbox_a", "消息箱创客甲")
MAKER_B = _token("usr_inbox_b", "消息箱创客乙")

POLICY_OK = {
    "title": "园区创客住房补贴申领指引（消息箱测试）",
    "policy_level": "园区级",
    "category": "RENT",
    "subsidy_amount_max": 12000.0,
    "summary": "面向园区创客的住房补贴申领流程、材料清单与常见退回原因说明。",
    "eligible_conditions": ["园区注册且正常经营"],
    "legal_basis": "《园区人才安居实施办法》",
}

POLICY_BLOCKED = dict(
    POLICY_OK,
    title="代开发票与洗钱通道对接",
    summary="提供代开发票与洗钱通道对接服务，保证月入十万。",
)


@pytest.fixture(autouse=True)
def _clean_notifications():
    notification_service.clear()
    yield
    notification_service.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _publish(client, payload, token=MAKER_A):
    return dispatch(client, "policies.publish", payload, token=token)


def _inbox(client, token=MAKER_A, status=None):
    payload = {"status": status} if status else {}
    return dispatch(client, "notifications.list", payload, token=token).json()


def _unread(client, token=MAKER_A):
    return dispatch(client, "notifications.unread_count", {}, token=token).json()


# ---------------------------------------------------------------------------
# 1. 校验通过与拦截都会生成消息
# ---------------------------------------------------------------------------
def test_publish_pass_records_moderation_receipt(client):
    assert _publish(client, POLICY_OK).json()["code"] == 200

    body = _inbox(client)
    assert body["code"] == 200, body
    data = body["data"]
    assert data["total"] == 1
    assert data["unread"] == 1

    item = data["items"][0]
    assert item["kind"] == "PUBLISH_MODERATION"
    assert item["user_id"] == "usr_inbox_a"
    assert item["scene"] == "政策中心"
    assert item["verdict"] in ("PASSED", "PASSED_DEGRADED")
    assert "敏感词校验" in item["title"]
    assert item["status"] == "UNREAD"


def test_publish_blocked_records_hit_words_and_reason(client):
    assert _publish(client, POLICY_BLOCKED).json()["code"] == 400

    data = _inbox(client)["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["verdict"] == "BLOCKED"
    assert "洗钱" in item["hit_words"] or "代开发票" in item["hit_words"]
    assert "未通过" in item["title"]
    assert "发布已被阻止" in item["content"]


def test_unread_count_and_mark_read(client):
    _publish(client, POLICY_OK)
    _publish(client, dict(POLICY_OK, title="第二条政策消息测试"))

    assert _unread(client)["data"]["unread"] == 2

    listed = _inbox(client)["data"]["items"]
    first_id = listed[0]["id"]
    marked = dispatch(client, "notifications.mark_read", {"ids": [first_id]}, token=MAKER_A).json()
    assert marked["code"] == 200
    assert marked["data"]["updated"] == 1
    assert marked["data"]["unread"] == 1

    # UNREAD filter only returns the remaining message.
    unread_items = _inbox(client, status="UNREAD")["data"]
    assert unread_items["total"] == 1
    assert unread_items["items"][0]["id"] != first_id

    all_read = dispatch(client, "notifications.mark_all_read", {}, token=MAKER_A).json()
    assert all_read["code"] == 200
    assert all_read["data"]["unread"] == 0


def test_delete_message(client):
    _publish(client, POLICY_OK)
    item_id = _inbox(client)["data"]["items"][0]["id"]

    deleted = dispatch(client, "notifications.delete", {"id": item_id}, token=MAKER_A).json()
    assert deleted["code"] == 200
    assert deleted["data"]["updated"] == 1
    assert _inbox(client)["data"]["total"] == 0


# ---------------------------------------------------------------------------
# 2. 用户隔离与鉴权
# ---------------------------------------------------------------------------
def test_inbox_is_isolated_per_user(client):
    _publish(client, POLICY_OK, token=MAKER_A)

    other = _inbox(client, token=MAKER_B)["data"]
    assert other["total"] == 0
    assert _unread(client, token=MAKER_B)["data"]["unread"] == 0

    victim_id = _inbox(client, token=MAKER_A)["data"]["items"][0]["id"]
    denied = dispatch(client, "notifications.mark_read", {"ids": [victim_id]}, token=MAKER_B).json()
    assert denied["code"] == 200
    assert denied["data"]["updated"] == 0

    # Still unread for its owner.
    assert _unread(client, token=MAKER_A)["data"]["unread"] == 1


def test_inbox_requires_login(client):
    client.headers.pop("Authorization", None)
    resp = dispatch(client, "notifications.list", {})
    assert resp.json()["code"] in (401, 403)


def test_frontend_inbox_entry_is_wired():
    """导航消息箱入口、未读角标与消息列表均已接线。"""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    navbar = (root / "components" / "Navbar.vue").read_text(encoding="utf-8")
    app = (root / "App.vue").read_text(encoding="utf-8")
    inbox = (root / "components" / "NotificationInbox.vue").read_text(encoding="utf-8")

    assert "open-inbox" in navbar
    assert "nav-inbox-badge" in navbar
    assert "NotificationInbox" in app
    assert "notifications.unread_count" in app
    assert "notifications.list" in inbox
    assert "notifications.mark_all_read" in inbox



# ---------------------------------------------------------------------------
# 3. SOP 审核链路也会写消息
# ---------------------------------------------------------------------------
def test_sop_review_block_records_notification(client):
    sop_service._review_queue.clear()
    doc = sop_service.save_draft_document(SOPDocumentDraftCreate(
        title="审核消息测试文书",
        content="本文件用于测试审核阶段敏感词拦截，并提供洗钱通道的操作说明。",
        user_id="usr_inbox_a",
    ))
    try:
        sop_service.submit_document_for_review(doc.id, "usr_inbox_a")
        result = asyncio.run(sop_service.process_review_queue())
        assert result.rejected == 1

        data = _inbox(client)["data"]
        assert data["total"] == 1
        item = data["items"][0]
        assert item["scene"] == "流程文书审核"
        assert item["verdict"] == "BLOCKED"
        assert "洗钱" in item["hit_words"]
        assert item["target_type"] == "DOCUMENT"
        assert item["target_id"] == doc.id
    finally:
        sop_service._review_queue.clear()
        sop_service.delete_document(doc.id)

