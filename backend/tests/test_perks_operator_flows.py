"""Operator-flow tests for the perks (生态特权) domain.

Every business flow is expressed by ``config/scenarios/perks.yaml`` and executed
through ``orchestration_service.execute_scenario``. Identity always travels in
the pipeline ``context``; data is created here so the tests stay hermetic.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.core.entity import entity_store
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service
from src.domains.perks.entities import ENTITY_PERK, ENTITY_PERK_CLAIM


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _seed_perk(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": _uid("perk_test"),
        "name": "算子迁移测试优惠",
        "provider": "OpcHub 测试供应商",
        "value_cny": 100.0,
        "category": "TOKEN",
        "summary": "用于验收算子编排流程的测试优惠公告。",
        "quota_remaining": 5,
        "priority": 60,
        "status": "PUBLISHED",
        "effective_start": "2026-01-01",
        "effective_end": "2099-12-31",
        "highlights": ["测试卖点"],
        "author_id": "usr_perk_author",
        "author_name": "测试发布者",
        "is_official": False,
    }
    payload.update(overrides)
    return entity_store.create(ENTITY_PERK, payload)


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


@pytest.fixture
def cleanup():
    perks: list[str] = []
    claims: list[tuple[str, str]] = []
    yield perks, claims
    for perk_id in perks:
        entity_store.delete(ENTITY_PERK, {"key": perk_id})
    for user_id, perk_id in claims:
        entity_store.delete(ENTITY_PERK_CLAIM, {"user_id": user_id, "perk_id": perk_id})


async def test_publish_perk_creates_entity(cleanup):
    perk_ids, _claims = cleanup
    res = await _run(
        "OPC_PERK_PUBLISH_PIPELINE",
        {
            "name": "火山方舟 Token 畅用券（测试）",
            "provider": "火山引擎方舟",
            "value_cny": 500.0,
            "category": "TOKEN",
            "summary": "新入驻创客可领取的 Token 抵扣券测试数据。",
            "quota_remaining": 20,
            "priority": 88,
            "effective_start": "2026-11-01",
            "effective_end": "2027-01-31",
            "redeem_url": "https://example.com/redeem",
            "highlights": ["测试卖点一", "测试卖点二"],
        },
        {"user_id": "usr_flow_publisher", "user_role": "MAKER"},
    )
    assert res.status == "SUCCESS", res.error_message
    created = res.final_output["response"]
    perk_ids.append(created["id"])

    assert created["id"].startswith("perk_")
    assert created["name"] == "火山方舟 Token 畅用券（测试）"
    assert created["category"] == "TOKEN"
    assert created["quota_remaining"] == 20
    assert created["priority"] == 88
    assert created["author_id"] == "usr_flow_publisher"
    assert created["is_official"] is False
    assert created["status"] == "PUBLISHED"
    assert res.final_output["created_perk"]["id"] == created["id"]

    stored = entity_store.get(ENTITY_PERK, {"key": created["id"]})
    assert stored is not None
    assert stored["highlights"] == ["测试卖点一", "测试卖点二"]


async def test_publish_rejects_invalid_payload():
    res = await _run(
        "OPC_PERK_PUBLISH_PIPELINE",
        {
            "name": "短",
            "provider": "供应商",
            "value_cny": 10,
            "summary": "太短",
        },
        {"user_id": "usr_flow_publisher", "user_role": "MAKER"},
    )
    assert res.status == "FAILED"
    message = res.error_message or ""
    assert "name" in message or "summary" in message


async def test_publish_requires_authentication():
    res = await _run(
        "OPC_PERK_PUBLISH_PIPELINE",
        {
            "name": "未登录发布测试",
            "provider": "测试供应商",
            "value_cny": 10,
            "summary": "未登录发布应当被门禁拦截。",
        },
    )
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


async def test_public_list_filters_expired_offline_and_sorts(cleanup):
    perk_ids, _claims = cleanup
    visible_high = _seed_perk(priority=90, name="高优先级测试优惠")
    visible_low = _seed_perk(priority=10, name="低优先级测试优惠")
    expired = _seed_perk(priority=99, name="已过期测试优惠", effective_end="2020-01-01")
    offline = _seed_perk(priority=99, name="已下线测试优惠", status="OFFLINE")
    perk_ids.extend([visible_high["id"], visible_low["id"], expired["id"], offline["id"]])

    res = await _run("OPC_PERK_LIST_PIPELINE", {"category": "ALL"})
    assert res.status == "SUCCESS", res.error_message
    board = res.final_output["response"]
    assert isinstance(board, list)
    ids = [item["id"] for item in board]

    assert visible_high["id"] in ids
    assert visible_low["id"] in ids
    assert expired["id"] not in ids
    assert offline["id"] not in ids
    assert ids.index(visible_high["id"]) < ids.index(visible_low["id"])
    assert all(item["status"] == "PUBLISHED" for item in board)


async def test_public_list_category_filter(cleanup):
    perk_ids, _claims = cleanup
    token = _seed_perk(category="TOKEN", name="Token 测试优惠")
    server = _seed_perk(category="SERVER", name="服务器测试优惠")
    perk_ids.extend([token["id"], server["id"]])

    res = await _run("OPC_PERK_LIST_PIPELINE", {"category": "SERVER"})
    assert res.status == "SUCCESS", res.error_message
    board = res.final_output["response"]
    ids = [item["id"] for item in board]
    assert server["id"] in ids
    assert token["id"] not in ids
    assert all(item["category"] == "SERVER" for item in board)


async def test_claim_decrements_quota_and_creates_claim(cleanup):
    perk_ids, claims = cleanup
    perk = _seed_perk(quota_remaining=2)
    perk_ids.append(perk["id"])
    user_id = _uid("usr_claim")
    claims.append((user_id, perk["id"]))

    res = await _run(
        "OPC_PERK_CLAIM_PIPELINE",
        {"perk_id": perk["id"]},
        {"user_id": user_id, "user_role": "MAKER"},
    )
    assert res.status == "SUCCESS", res.error_message
    claim = res.final_output["response"]

    assert claim["voucher_code"].startswith("OPC-")
    assert claim["status"] == "ACTIVATED"
    assert claim["user_id"] == user_id
    assert claim["perk_id"] == perk["id"]
    assert claim["claim_id"].startswith("clm_")
    assert "测试供应商" in claim["instructions"]
    assert res.final_output["created_claim"]["voucher_code"] == claim["voucher_code"]

    updated = entity_store.get(ENTITY_PERK, {"key": perk["id"]})
    assert updated["quota_remaining"] == 1
    assert updated["claim_count"] == 1

    stored_claim = entity_store.get(
        ENTITY_PERK_CLAIM, {"user_id": user_id, "perk_id": perk["id"]}
    )
    assert stored_claim is not None
    assert stored_claim["voucher_code"] == claim["voucher_code"]


async def test_duplicate_claim_fails_and_does_not_double_deduct(cleanup):
    perk_ids, claims = cleanup
    perk = _seed_perk(quota_remaining=3)
    perk_ids.append(perk["id"])
    user_id = _uid("usr_dup")
    claims.append((user_id, perk["id"]))

    first = await _run(
        "OPC_PERK_CLAIM_PIPELINE",
        {"perk_id": perk["id"]},
        {"user_id": user_id, "user_role": "MAKER"},
    )
    assert first.status == "SUCCESS", first.error_message

    second = await _run(
        "OPC_PERK_CLAIM_PIPELINE",
        {"perk_id": perk["id"]},
        {"user_id": user_id, "user_role": "MAKER"},
    )
    assert second.status == "FAILED"
    assert "重复" in (second.error_message or "")

    updated = entity_store.get(ENTITY_PERK, {"key": perk["id"]})
    assert updated["quota_remaining"] == 2
    assert updated["claim_count"] == 1


async def test_claim_rejects_exhausted_quota(cleanup):
    perk_ids, _claims = cleanup
    perk = _seed_perk(quota_remaining=0)
    perk_ids.append(perk["id"])

    res = await _run(
        "OPC_PERK_CLAIM_PIPELINE",
        {"perk_id": perk["id"]},
        {"user_id": _uid("usr_soldout"), "user_role": "MAKER"},
    )
    assert res.status == "FAILED"
    assert "领完" in (res.error_message or "")
    updated = entity_store.get(ENTITY_PERK, {"key": perk["id"]})
    assert updated["quota_remaining"] == 0


async def test_claim_requires_identity(cleanup):
    perk_ids, _claims = cleanup
    perk = _seed_perk(quota_remaining=1)
    perk_ids.append(perk["id"])

    res = await _run("OPC_PERK_CLAIM_PIPELINE", {"perk_id": perk["id"]})
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


async def test_revoke_claim_restores_quota(cleanup):
    perk_ids, claims = cleanup
    perk = _seed_perk(quota_remaining=2)
    perk_ids.append(perk["id"])
    user_id = _uid("usr_revoke")
    claims.append((user_id, perk["id"]))

    claimed = await _run(
        "OPC_PERK_CLAIM_PIPELINE",
        {"perk_id": perk["id"]},
        {"user_id": user_id, "user_role": "MAKER"},
    )
    assert claimed.status == "SUCCESS", claimed.error_message

    revoked = await _run(
        "OPC_PERK_REVOKE_CLAIM_PIPELINE",
        {"perk_id": perk["id"]},
        {"user_id": user_id, "user_role": "MAKER"},
    )
    assert revoked.status == "SUCCESS", revoked.error_message
    assert revoked.final_output["response"]["revoked"] is True

    assert (
        entity_store.get(ENTITY_PERK_CLAIM, {"user_id": user_id, "perk_id": perk["id"]})
        is None
    )
    restored = entity_store.get(ENTITY_PERK, {"key": perk["id"]})
    assert restored["quota_remaining"] == 2
    assert restored["claim_count"] == 0


async def test_detail_and_delete(cleanup):
    _perk_ids, _claims = cleanup
    perk = _seed_perk(author_id="usr_owner_delete", name="待删除测试优惠")

    detail = await _run("OPC_PERK_DETAIL_PIPELINE", {"perk_id": perk["id"]})
    assert detail.status == "SUCCESS", detail.error_message
    assert detail.final_output["response"]["id"] == perk["id"]

    deleted = await _run(
        "OPC_PERK_DELETE_PIPELINE",
        {"perk_id": perk["id"]},
        {"user_id": "usr_owner_delete", "user_role": "MAKER"},
    )
    assert deleted.status == "SUCCESS", deleted.error_message
    assert deleted.final_output["response"]["deleted"] is True
    assert entity_store.get(ENTITY_PERK, {"key": perk["id"]}) is None
