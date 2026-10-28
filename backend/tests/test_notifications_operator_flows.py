"""Operator-kernel v2 flow tests for the message box (消息箱) domain.

Every flow asserted here is declared in ``config/scenarios/notifications.yaml``
and executed by the operator kernel through
``orchestration_service.execute_scenario``; identity travels in ``context``.
The legacy ``notification_service`` is only used for its data/query shim.
"""
from __future__ import annotations

import pytest

from src.core.entity import entity_store
from src.core.scenario import ensure_scenarios_loaded
from src.domains.notifications.service import notification_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

CREATE = "OPC_NOTIFICATION_CREATE_PIPELINE"
LIST = "OPC_NOTIFICATION_LIST_PIPELINE"
UNREAD = "OPC_NOTIFICATION_UNREAD_COUNT_PIPELINE"
MARK_READ = "OPC_NOTIFICATION_MARK_READ_PIPELINE"
MARK_ALL_READ = "OPC_NOTIFICATION_MARK_ALL_READ_PIPELINE"
DELETE = "OPC_NOTIFICATION_DELETE_PIPELINE"

MAKER_A = {"user_id": "usr_notif_flow_a", "user_role": "MAKER", "nickname": "消息箱创客甲"}
MAKER_B = {"user_id": "usr_notif_flow_b", "user_role": "MAKER", "nickname": "消息箱创客乙"}


@pytest.fixture(autouse=True)
def clean_notification_state():
    _purge()
    yield
    _purge()


def _purge() -> None:
    for entity in ("notification.item", "notification.inbox"):
        adapter = entity_store.adapter(entity)
        for row in list(adapter.all()):
            key = str(row.get("id") or row.get("user_id") or "")
            if key:
                adapter.delete(key)


async def _run(scenario: str, inputs: dict, context: dict | None = None):
    ensure_scenarios_loaded()
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=dict(inputs),
            context=dict(context or {}),
        )
    )


async def _create(user_id: str = MAKER_A["user_id"], *, title: str = "平台通知", content: str = "通知内容") -> dict:
    res = await _run(CREATE, {"user_id": user_id, "title": title, "content": content})
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["response"]


async def _list(context: dict | None = MAKER_A, **inputs) -> dict:
    res = await _run(LIST, inputs, context)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output


# ------------------------------------------------------------------ create
async def test_create_persists_notification_item_for_recipient():
    created = await _create(title="审核回执", content="你的内容已通过校验")

    assert created["id"].startswith("msg_")
    assert created["user_id"] == MAKER_A["user_id"]
    assert created["title"] == "审核回执"
    assert created["content"] == "你的内容已通过校验"
    assert created["status"] == "UNREAD"

    stored = entity_store.get("notification.item", {"key": created["id"]})
    assert stored is not None
    assert stored["user_id"] == MAKER_A["user_id"]


async def test_create_requires_recipient():
    res = await _run(CREATE, {"user_id": "", "title": "无收件人", "content": "x"})
    assert res.status == "FAILED"
    assert "接收人" in (res.error_message or "")


# -------------------------------------------------------------------- list
async def test_list_returns_items_total_and_unread_per_user():
    await _create(title="消息甲", content="甲")
    await _create(title="消息乙", content="乙")
    await _create(user_id=MAKER_B["user_id"], title="他人消息", content="乙的")

    inbox_a = await _list(MAKER_A)
    assert inbox_a["total"] == 2
    assert inbox_a["unread"] == 2
    assert {item["title"] for item in inbox_a["items"]} == {"消息甲", "消息乙"}
    assert all(item["user_id"] == MAKER_A["user_id"] for item in inbox_a["items"])

    inbox_b = await _list(MAKER_B)
    assert inbox_b["total"] == 1
    assert inbox_b["items"][0]["title"] == "他人消息"


async def test_list_requires_authentication():
    res = await _run(LIST, {}, {})
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


async def test_list_filters_by_read_status_and_pages():
    created = [await _create(title=f"分页消息{index}") for index in range(3)]

    marked = await _run(MARK_READ, {"ids": [created[0]["id"]]}, MAKER_A)
    assert marked.status == "SUCCESS", marked.error_message

    unread_only = await _list(MAKER_A, status="UNREAD")
    assert unread_only["total"] == 2
    assert created[0]["id"] not in [item["id"] for item in unread_only["items"]]

    read_only = await _list(MAKER_A, status="READ")
    assert read_only["total"] == 1
    assert read_only["items"][0]["id"] == created[0]["id"]
    assert read_only["items"][0]["status"] == "READ"

    paged = await _list(MAKER_A, limit=1, offset=1)
    assert paged["total"] == 3
    assert paged["unread"] == 2
    assert len(paged["items"]) == 1


# ---------------------------------------------------------------- unread
async def test_unread_count_tracks_read_state():
    first = await _create(title="未读一")
    await _create(title="未读二")

    res = await _run(UNREAD, {}, MAKER_A)
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["unread"] == 2

    await _run(MARK_READ, {"ids": [first["id"]]}, MAKER_A)
    refreshed = await _run(UNREAD, {}, MAKER_A)
    assert refreshed.final_output["unread"] == 1

    # Another user's unread counter is unaffected.
    other = await _run(UNREAD, {}, MAKER_B)
    assert other.final_output["unread"] == 0


# --------------------------------------------------------------- mark read
async def test_mark_read_marks_selected_ids_and_is_idempotent():
    first = await _create(title="待读一")
    second = await _create(title="待读二")

    res = await _run(MARK_READ, {"ids": [first["id"], second["id"]]}, MAKER_A)
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["updated"] == 2
    assert res.final_output["unread"] == 0

    again = await _run(MARK_READ, {"ids": [first["id"], second["id"]]}, MAKER_A)
    assert again.status == "SUCCESS", again.error_message
    assert again.final_output["updated"] == 0
    assert again.final_output["unread"] == 0

    listed = await _list(MAKER_A)
    assert {item["status"] for item in listed["items"]} == {"READ"}


async def test_mark_read_without_ids_is_a_noop():
    await _create(title="未指定消息")

    res = await _run(MARK_READ, {"ids": []}, MAKER_A)
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["updated"] == 0
    assert res.final_output["unread"] == 1
    assert "未指定" in res.final_output["message"]


async def test_mark_read_cannot_touch_another_users_message():
    victim = await _create(title="他人未读")

    denied = await _run(MARK_READ, {"ids": [victim["id"]]}, MAKER_B)
    assert denied.status == "SUCCESS", denied.error_message
    assert denied.final_output["updated"] == 0

    owner_view = await _run(UNREAD, {}, MAKER_A)
    assert owner_view.final_output["unread"] == 1


async def test_mark_all_read_only_clears_the_callers_inbox():
    await _create(title="全部已读一")
    await _create(title="全部已读二")
    await _create(user_id=MAKER_B["user_id"], title="乙的未读")

    res = await _run(MARK_ALL_READ, {}, MAKER_A)
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["updated"] == 2
    assert res.final_output["unread"] == 0

    assert (await _run(UNREAD, {}, MAKER_A)).final_output["unread"] == 0
    assert (await _run(UNREAD, {}, MAKER_B)).final_output["unread"] == 1


# ----------------------------------------------------------------- delete
async def test_delete_removes_own_message_and_recomputes_unread():
    created = await _create(title="待删除消息")

    res = await _run(DELETE, {"id": created["id"]}, MAKER_A)
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["updated"] == 1
    assert res.final_output["unread"] == 0
    assert res.final_output["message"] == "消息已删除"

    assert entity_store.get("notification.item", {"key": created["id"]}) is None
    assert (await _list(MAKER_A))["total"] == 0


async def test_delete_rejects_another_users_message():
    created = await _create(title="不可删除消息")

    res = await _run(DELETE, {"id": created["id"]}, MAKER_B)
    assert res.status == "GUARD_REJECTED"
    assert "无权" in (res.error_message or "")

    assert entity_store.get("notification.item", {"key": created["id"]}) is not None
    assert (await _list(MAKER_A))["total"] == 1


async def test_delete_unknown_message_fails_cleanly():
    res = await _run(DELETE, {"id": "msg_does_not_exist"}, MAKER_A)
    assert res.status == "FAILED"
    assert "消息不存在" in (res.error_message or "")


# ------------------------------------------------------- legacy shim bridge
async def test_notify_emit_writes_the_notification_item_entity():
    from src.core.operators.side_effects import emit

    result = emit(
        {},
        {
            "recipient_id": MAKER_A["user_id"],
            "title": "系统通知",
            "body": "通用 notify.emit 写入的消息",
        },
        {},
    )
    assert result["emitted"] is True

    listed = await _list(MAKER_A)
    assert listed["total"] == 1
    item = listed["items"][0]
    assert item["kind"] == "SYSTEM"
    assert item["content"] == "通用 notify.emit 写入的消息"
    assert item["status"] == "UNREAD"


async def test_legacy_shim_create_is_visible_to_operator_pipelines():
    doc = notification_service.create(
        user_id=MAKER_A["user_id"],
        title="审核服务写入",
        content="审核回执内容",
        verdict="PASSED",
    )

    assert doc.id.startswith("msg_")
    assert notification_service.unread_count(MAKER_A["user_id"]) == 1

    listed = await _list(MAKER_A)
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == doc.id
    assert listed["items"][0]["verdict"] == "PASSED"


async def test_moderation_receipt_shim_writes_through_entity_store():
    receipt = notification_service.record_moderation_result(
        user_id=MAKER_A["user_id"],
        scene="政策中心",
        title="被拦截的政策",
        verdict="BLOCKED",
        hit_words=["洗钱"],
        target_type="policy",
        target_id="pol_1",
    )

    assert receipt is not None
    assert receipt.level == "WARNING"
    assert "未通过" in receipt.title
    assert receipt.target_type == "POLICY"
    assert receipt.hit_words == ["洗钱"]

    listed = await _list(MAKER_A)
    assert listed["items"][0]["verdict"] == "BLOCKED"
