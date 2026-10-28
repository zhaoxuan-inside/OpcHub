"""Operator-flow tests for the content-moderation domain.

Every business flow is expressed by ``config/scenarios/moderation.yaml`` and
executed through ``orchestration_service.execute_scenario``. Identity always
travels in the pipeline ``context`` (``user_id`` / ``user_role``); data is
created here so the tests stay hermetic.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.core.entity import entity_store
from src.domains.moderation.entities import ENTITY_MODERATION_ITEM
from src.domains.moderation.models import ContentReportRequest, ModerationItemResponse
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

ADMIN = {"user_id": "usr_admin_mod_flow", "user_role": "ADMIN"}
MAKER = {"user_id": "usr_maker_mod_flow", "user_role": "MAKER"}


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


async def _run(
    scenario: str,
    inputs: dict[str, Any],
    context: dict[str, Any] | None = None,
):
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=inputs,
            context=context or {},
        )
    )


def _seed_item(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": _uid("mod_test"),
        "target_type": "FORUM_THREAD",
        "target_id": _uid("thr"),
        "author_id": "usr_target_author",
        "author_name": "被举报作者",
        "snippet_content": "用于验收算子编排流程的测试内容。",
        "violation_type": "USER_REPORT",
        "status": "FLAGGED",
        "report_count": 1,
        "reported_at": "2026-10-20T08:00:00+00:00",
        "reason": "测试举报原因",
        "reporter_id": "usr_reporter_seed",
        "reporters": ["usr_reporter_seed"],
    }
    payload.update(overrides)
    return entity_store.create(ENTITY_MODERATION_ITEM, payload)


@pytest.fixture
def cleanup():
    item_ids: list[str] = []
    yield item_ids
    for item_id in item_ids:
        entity_store.delete(ENTITY_MODERATION_ITEM, {"key": item_id})


# ---------------------------------------------------------------------------
# 1. User report: create + merge de-duplication
# ---------------------------------------------------------------------------
async def test_report_creates_flagged_item(cleanup):
    item_ids = cleanup
    target_id = _uid("thr_report")

    res = await _run(
        "OPC_MODERATION_REPORT_PIPELINE",
        {
            "target_type": "FORUM_THREAD",
            "target_id": target_id,
            "target_title": "疑似失实的创业经历帖",
            "author_id": "usr_target_author",
            "author_name": "被举报作者",
            "reason": "经历明显失实",
        },
        MAKER,
    )
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]
    item_ids.append(body["id"])

    assert body["id"].startswith("mod_")
    assert body["target_type"] == "FORUM_THREAD"
    assert body["target_id"] == target_id
    assert body["status"] == "FLAGGED"
    assert body["report_count"] == 1
    assert body["violation_type"] == "USER_REPORT"
    assert body["author_id"] == "usr_target_author"
    assert body["reporter_id"] == MAKER["user_id"]
    assert body["reporters"] == [MAKER["user_id"]]
    assert res.final_output["created_report"]["id"] == body["id"]
    assert res.final_output["merged"] is False
    assert res.final_output["orchestrated_by"] == "OPC_MODERATION_REPORT_PIPELINE"

    stored = entity_store.get(ENTITY_MODERATION_ITEM, {"key": body["id"]})
    assert stored is not None
    assert stored["reason"] == "经历明显失实"


async def test_duplicate_reports_merge_into_one_item(cleanup):
    item_ids = cleanup
    target_id = _uid("thr_dup")
    payload = {
        "target_type": "FORUM_THREAD",
        "target_id": target_id,
        "target_title": "重复举报测试帖",
        "author_id": "usr_target_author",
        "author_name": "被举报作者",
        "reason": "信息失实",
    }

    first = await _run("OPC_MODERATION_REPORT_PIPELINE", payload, MAKER)
    assert first.status == "SUCCESS", first.error_message
    item_id = first.final_output["response"]["id"]
    item_ids.append(item_id)

    other_reporter = {"user_id": "usr_maker_mod_second", "user_role": "MAKER"}
    second = await _run("OPC_MODERATION_REPORT_PIPELINE", payload, other_reporter)
    assert second.status == "SUCCESS", second.error_message
    merged = second.final_output["response"]

    assert merged["id"] == item_id
    assert merged["report_count"] == 2
    assert merged["reporters"] == [MAKER["user_id"], other_reporter["user_id"]]
    assert merged["reporter_id"] == other_reporter["user_id"]
    assert second.final_output["merged"] is True
    assert second.final_output["report_previous_count"] == 1

    rows, total = entity_store.list(
        ENTITY_MODERATION_ITEM,
        {"filters": {"target_type": "FORUM_THREAD", "target_id": target_id}},
    )
    assert total == 1
    assert rows[0]["report_count"] == 2


async def test_report_rejects_invalid_target():
    res = await _run(
        "OPC_MODERATION_REPORT_PIPELINE",
        {"target_type": "NOT_A_TARGET", "target_id": _uid("x"), "reason": "测试"},
        MAKER,
    )
    assert res.status == "FAILED"
    assert "Unsupported report target_type" in (res.error_message or "")


async def test_report_reopens_moderated_target_as_new_item(cleanup):
    """A previously taken-down target must not be silently un-taken-down by a report."""
    item_ids = cleanup
    target_id = _uid("thr_remoderate")
    moderated = _seed_item(status="TAKEN_DOWN", target_id=target_id)
    item_ids.append(moderated["id"])

    res = await _run(
        "OPC_MODERATION_REPORT_PIPELINE",
        {
            "target_type": "FORUM_THREAD",
            "target_id": target_id,
            "reason": "下架后再次被举报",
        },
        MAKER,
    )
    assert res.status == "SUCCESS", res.error_message
    fresh = res.final_output["response"]
    item_ids.append(fresh["id"])

    assert fresh["id"] != moderated["id"]
    assert fresh["status"] == "FLAGGED"
    assert fresh["report_count"] == 1
    assert entity_store.get(ENTITY_MODERATION_ITEM, {"key": moderated["id"]})["status"] == "TAKEN_DOWN"


async def test_report_requires_authentication():
    res = await _run(
        "OPC_MODERATION_REPORT_PIPELINE",
        {"target_type": "FORUM_THREAD", "target_id": _uid("thr"), "reason": "测试"},
    )
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


# ---------------------------------------------------------------------------
# 2. Take-down (ADMIN only)
# ---------------------------------------------------------------------------
async def test_admin_takedown_moves_item_to_taken_down(cleanup):
    item_ids = cleanup
    item = _seed_item(status="FLAGGED")
    item_ids.append(item["id"])

    res = await _run(
        "OPC_MODERATION_TAKEDOWN_PIPELINE",
        {
            "item_id": item["id"],
            "reason": "泄露内网密钥",
            "ban_author": True,
        },
        ADMIN,
    )
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]

    assert body["item_id"] == item["id"]
    assert body["status"] == "TAKEN_DOWN"
    assert body["prev_status"] == "FLAGGED"
    assert "泄露内网密钥" in body["note"]
    assert "作者已封禁" in body["note"]
    assert body["moderator_id"] == ADMIN["user_id"]
    assert body["orchestrated_by"] == "OPC_MODERATION_TAKEDOWN_PIPELINE"

    stored = entity_store.get(ENTITY_MODERATION_ITEM, {"key": item["id"]})
    assert stored["status"] == "TAKEN_DOWN"
    assert stored["moderator_id"] == ADMIN["user_id"]


async def test_takedown_requires_admin(cleanup):
    item_ids = cleanup
    item = _seed_item(status="FLAGGED")
    item_ids.append(item["id"])

    res = await _run(
        "OPC_MODERATION_TAKEDOWN_PIPELINE",
        {"item_id": item["id"], "reason": "普通用户尝试下架"},
        MAKER,
    )
    assert res.status == "GUARD_REJECTED"
    assert "管理员" in (res.error_message or "")

    stored = entity_store.get(ENTITY_MODERATION_ITEM, {"key": item["id"]})
    assert stored["status"] == "FLAGGED"


async def test_takedown_missing_item_fails(cleanup):
    res = await _run(
        "OPC_MODERATION_TAKEDOWN_PIPELINE",
        {"item_id": "mod_missing_999", "reason": "不存在的内容"},
        ADMIN,
    )
    assert res.status == "FAILED"
    assert "不存在" in (res.error_message or "")


async def test_takedown_already_taken_down_fails(cleanup):
    item_ids = cleanup
    item = _seed_item(status="TAKEN_DOWN")
    item_ids.append(item["id"])

    res = await _run(
        "OPC_MODERATION_TAKEDOWN_PIPELINE",
        {"item_id": item["id"], "reason": "重复下架"},
        ADMIN,
    )
    assert res.status == "FAILED"
    assert "已下架" in (res.error_message or "")


# ---------------------------------------------------------------------------
# 3. Restore (ADMIN only)
# ---------------------------------------------------------------------------
async def test_admin_restore_returns_item_to_normal(cleanup):
    item_ids = cleanup
    item = _seed_item(status="TAKEN_DOWN", moderated_at="2026-10-21T08:00:00+00:00")
    item_ids.append(item["id"])

    res = await _run(
        "OPC_MODERATION_RESTORE_PIPELINE",
        {"item_id": item["id"]},
        ADMIN,
    )
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]

    assert body["item_id"] == item["id"]
    assert body["status"] == "NORMAL"
    assert body["prev_status"] == "TAKEN_DOWN"
    assert "恢复正常展示" in body["note"]
    assert body["orchestrated_by"] == "OPC_MODERATION_RESTORE_PIPELINE"

    stored = entity_store.get(ENTITY_MODERATION_ITEM, {"key": item["id"]})
    assert stored["status"] == "NORMAL"


async def test_restore_requires_admin(cleanup):
    item_ids = cleanup
    item = _seed_item(status="TAKEN_DOWN")
    item_ids.append(item["id"])

    res = await _run(
        "OPC_MODERATION_RESTORE_PIPELINE",
        {"item_id": item["id"]},
        MAKER,
    )
    assert res.status == "GUARD_REJECTED"
    assert "管理员" in (res.error_message or "")

    stored = entity_store.get(ENTITY_MODERATION_ITEM, {"key": item["id"]})
    assert stored["status"] == "TAKEN_DOWN"


async def test_restore_flagged_item_fails(cleanup):
    item_ids = cleanup
    item = _seed_item(status="FLAGGED")
    item_ids.append(item["id"])

    res = await _run(
        "OPC_MODERATION_RESTORE_PIPELINE",
        {"item_id": item["id"]},
        ADMIN,
    )
    assert res.status == "FAILED"
    assert "仅已下架" in (res.error_message or "")


# ---------------------------------------------------------------------------
# 4. Queue listing + detail
# ---------------------------------------------------------------------------
async def test_list_filters_by_status_and_supports_paging(cleanup):
    item_ids = cleanup
    flagged = _seed_item(status="FLAGGED")
    taken = _seed_item(status="TAKEN_DOWN")
    item_ids.extend([flagged["id"], taken["id"]])

    res = await _run("OPC_MODERATION_LIST_PIPELINE", {"status": "FLAGGED"}, ADMIN)
    assert res.status == "SUCCESS", res.error_message
    queue = res.final_output["response"]
    assert isinstance(queue, list)
    ids = [item["id"] for item in queue]
    assert flagged["id"] in ids
    assert taken["id"] not in ids
    assert all(item["status"] == "FLAGGED" for item in queue)

    paged = await _run(
        "OPC_MODERATION_LIST_PIPELINE",
        {"status": "FLAGGED", "page": 1, "page_size": 2},
        ADMIN,
    )
    assert paged.status == "SUCCESS", paged.error_message
    envelope = paged.final_output["response"]
    assert set(envelope) >= {"items", "total", "page", "page_size", "total_pages"}
    assert envelope["page"] == 1
    assert envelope["page_size"] == 2
    assert len(envelope["items"]) <= 2


async def test_list_requires_admin():
    res = await _run("OPC_MODERATION_LIST_PIPELINE", {}, MAKER)
    assert res.status == "GUARD_REJECTED"
    assert "管理员" in (res.error_message or "")


async def test_detail_returns_item_and_missing_fails(cleanup):
    item_ids = cleanup
    item = _seed_item(status="FLAGGED")
    item_ids.append(item["id"])

    res = await _run(
        "OPC_MODERATION_DETAIL_PIPELINE",
        {"item_id": item["id"]},
        ADMIN,
    )
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["response"]["id"] == item["id"]

    missing = await _run(
        "OPC_MODERATION_DETAIL_PIPELINE",
        {"item_id": "mod_missing_888"},
        ADMIN,
    )
    assert missing.status == "FAILED"
    assert "不存在" in (missing.error_message or "")


# ---------------------------------------------------------------------------
# 5. NLP pre-screen: three-state mapping + declarative degradation
# ---------------------------------------------------------------------------
async def test_prescreen_confident_safe_passes_without_enqueue():
    res = await _run(
        "OPC_MODERATION_PRESCREEN_PIPELINE",
        {"content": "软件开发与技术咨询，经营范围包括人工智能算法与知识产权申报备案。"},
        MAKER,
    )
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]
    assert body["verdict"] == "CONFIRMED_SAFE"
    assert body["action"] == "PASS"
    assert body["external_service_required"] is False
    assert body["degraded"] is False
    assert body["enqueued"] is False
    assert body["item"] is None


async def test_prescreen_confident_violation_blocks_and_enqueues(cleanup):
    item_ids = cleanup
    target_id = _uid("thr_prescreen_bad")

    res = await _run(
        "OPC_MODERATION_PRESCREEN_PIPELINE",
        {
            "content": "承接代开发票与洗钱业务，另售私钥与泄露内网接口。",
            "target_type": "FORUM_THREAD",
            "target_id": target_id,
            "author_id": "usr_target_author",
            "author_name": "被举报作者",
        },
        MAKER,
    )
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]
    assert body["verdict"] == "CONFIRMED_VIOLATION"
    assert body["action"] == "BLOCK"
    assert body["degraded"] is False
    assert body["enqueued"] is True
    assert body["item"]["status"] == "FLAGGED"
    assert body["item"]["target_id"] == target_id
    item_ids.append(body["item"]["id"])

    stored = entity_store.get(ENTITY_MODERATION_ITEM, {"key": body["item"]["id"]})
    assert stored["violation_type"] == "ILLEGAL_TRADE"
    assert stored["report_count"] == 0


async def test_prescreen_uncertain_degrades_to_human_review(cleanup):
    item_ids = cleanup
    target_id = _uid("thr_prescreen_uncertain")

    res = await _run(
        "OPC_MODERATION_PRESCREEN_PIPELINE",
        {
            "content": "今天天气不错，周末想去湖边走走，顺便看看新开的店。",
            "target_type": "FORUM_THREAD",
            "target_id": target_id,
        },
        MAKER,
    )
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]
    assert body["verdict"] == "UNCERTAIN"
    assert body["action"] == "DEFER"
    assert body["external_service_required"] is True
    assert body["degraded"] is True
    assert body["degraded_strategy"] == "DECLARATIVE_PRESCREEN_FLAG_FOR_REVIEW"
    assert "外部审核服务不可用" in body["note"]
    assert body["enqueued"] is True
    assert body["item"]["status"] == "FLAGGED"
    item_ids.append(body["item"]["id"])


# ---------------------------------------------------------------------------
# 6. Legacy service import surface (thin shim only)
# ---------------------------------------------------------------------------
async def test_service_shim_reads_operator_written_items(cleanup):
    from src.domains.moderation.service import moderation_service

    item_ids = cleanup
    item = _seed_item(status="FLAGGED")
    item_ids.append(item["id"])

    assert moderation_service.get_item(item["id"]).id == item["id"]
    assert any(row.id == item["id"] for row in moderation_service.list_items("FLAGGED"))

    # Seeding the legacy mapping must stay visible to the operator scenarios.
    legacy_id = _uid("mod_legacy")
    moderation_service._items[legacy_id] = ModerationItemResponse(
        id=legacy_id,
        target_type="FORUM_THREAD",
        target_id=_uid("thr_legacy"),
        author_id="usr_target_author",
        author_name="被举报作者",
        snippet_content="历史 fixture 直接写入的审核项。",
        violation_type="USER_REPORT",
        status="FLAGGED",
        report_count=1,
        reported_at="2026-10-22T08:00:00+00:00",
    )
    item_ids.append(legacy_id)
    assert entity_store.get(ENTITY_MODERATION_ITEM, {"key": legacy_id}) is not None

    # The data-level report shim must persist through the same entity + merge path.
    shim_report = moderation_service.report(
        ContentReportRequest(
            target_type="FORUM_THREAD",
            target_id=_uid("thr_shim"),
            target_title="兼容层举报测试",
            reporter_id="usr_legacy_reporter",
        )
    )
    item_ids.append(shim_report.id)
    assert shim_report.report_count == 1
    assert shim_report.reporter_id == "usr_legacy_reporter"
    assert entity_store.get(ENTITY_MODERATION_ITEM, {"key": shim_report.id}) is not None
