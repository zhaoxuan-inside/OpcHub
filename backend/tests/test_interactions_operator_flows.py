"""Operator-flow tests for the unified interactions (统一互动) domain.

Every business flow is expressed by ``config/scenarios/interactions.yaml`` and
executed through ``orchestration_service.execute_scenario``. Identity always
travels in the pipeline ``context``; targets are created in the generic entity
store so the cross-domain counter write-back can be asserted end to end.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.core.entity import entity_store
from src.domains.interactions.entities import (
    ENTITY_CONTENT_COMMENT,
    ENTITY_INTERACTION_RATING,
    ENTITY_INTERACTION_RECORD,
    ENTITY_INTERACTION_STAT,
)
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _seed_product(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": _uid("prd_int"),
        "title": "互动测试产品",
        "tagline": "用于验证互动算子的测试产品",
        "description": "用于验证点赞/收藏/喜欢/踩与评论计数回写的测试产品。",
        "category": "AI",
        "pricing_model": "FREE",
        "price_cny": 0.0,
        "author_id": "usr_product_author",
        "author_name": "测试创客",
        "status": "PUBLISHED",
        "upvote_count": 0,
        "favorite_count": 0,
        "love_count": 0,
        "comment_count": 0,
    }
    payload.update(overrides)
    return entity_store.create("product.item", payload)


def _seed_perk(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": _uid("perk_int"),
        "name": "互动测试优惠公告",
        "provider": "OpcHub 测试供应商",
        "value_cny": 100.0,
        "category": "TOKEN",
        "summary": "用于验证互动计数回写的测试优惠公告。",
        "quota_remaining": 5,
        "priority": 50,
        "status": "PUBLISHED",
    }
    payload.update(overrides)
    return entity_store.create("perk.item", payload)


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


def _ctx(user_id: str, role: str = "MAKER", **extra: Any) -> dict[str, Any]:
    return {"user_id": user_id, "user_role": role, "nickname": "互动测试创客", **extra}


async def _toggle(user_id: str, product_id: str, kind: str):
    return await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product_id, "kind": kind},
        _ctx(user_id),
    )


@pytest.fixture
def cleanup():
    created: list[tuple[str, dict[str, Any]]] = []

    def track(entity: str, doc: dict[str, Any]) -> dict[str, Any]:
        created.append((entity, doc))
        return doc

    yield track
    for entity, doc in reversed(created):
        spec = entity_store.spec(entity)
        entity_store.adapter(entity).delete(spec.key_of(doc))


# ---------------------------------------------------------------------------
# 1. Toggle: LIKE / FAVORITE / LOVE / DISLIKE and cancel
# ---------------------------------------------------------------------------
async def test_toggle_like_updates_stat_ledger_and_target(cleanup):
    product = cleanup("product.item", _seed_product())
    user_id = _uid("usr_like")

    res = await _toggle(user_id, product["id"], "LIKE")
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]
    assert body["active"] is True
    assert body["count"] == 1
    assert body["like_count"] == 1
    assert body["viewer"]["liked"] is True

    stat = entity_store.get(
        ENTITY_INTERACTION_STAT, {"target_type": "PRODUCT", "target_id": product["id"]}
    )
    assert stat["like_count"] == 1
    record = entity_store.get(
        ENTITY_INTERACTION_RECORD,
        {"user_id": user_id, "target_type": "PRODUCT", "target_id": product["id"], "kind": "LIKE"},
    )
    assert record is not None
    assert record["target_title"] == "互动测试产品"

    # cross-domain counter write-back through calc.interaction.target + entity.patch
    stored = entity_store.get("product.item", {"key": product["id"]})
    assert stored["upvote_count"] == 1


async def test_toggle_favorite_and_love_are_independent(cleanup):
    product = cleanup("product.item", _seed_product())
    user_id = _uid("usr_fav")

    assert (await _toggle(user_id, product["id"], "FAVORITE")).status == "SUCCESS"
    love = await _toggle(user_id, product["id"], "LOVE")
    assert love.status == "SUCCESS", love.error_message
    body = love.final_output["response"]
    assert body["favorite_count"] == 1
    assert body["love_count"] == 1
    assert body["viewer"]["favorited"] is True
    assert body["viewer"]["loved"] is True

    stored = entity_store.get("product.item", {"key": product["id"]})
    assert stored["favorite_count"] == 1
    assert stored["love_count"] == 1


async def test_toggle_dislike_and_cancel(cleanup):
    product = cleanup("product.item", _seed_product())
    user_id = _uid("usr_dislike")

    on = await _toggle(user_id, product["id"], "DISLIKE")
    assert on.status == "SUCCESS", on.error_message
    assert on.final_output["response"]["dislike_count"] == 1
    assert on.final_output["response"]["viewer"]["disliked"] is True

    off = await _toggle(user_id, product["id"], "DISLIKE")
    assert off.status == "SUCCESS", off.error_message
    body = off.final_output["response"]
    assert body["active"] is False
    assert body["count"] == 0
    assert body["dislike_count"] == 0
    assert body["viewer"]["disliked"] is False

    assert (
        entity_store.get(
            ENTITY_INTERACTION_RECORD,
            {"user_id": user_id, "target_type": "PRODUCT", "target_id": product["id"], "kind": "DISLIKE"},
        )
        is None
    )
    stored = entity_store.get("product.item", {"key": product["id"]})
    assert stored["upvote_count"] == 0


async def test_like_cancel_restores_target_counter(cleanup):
    product = cleanup("product.item", _seed_product(upvote_count=7))
    user_id = _uid("usr_cancel")

    first = await _toggle(user_id, product["id"], "LIKE")
    assert first.status == "SUCCESS", first.error_message
    # legacy counter is the initial value of a missing stat row
    assert first.final_output["response"]["like_count"] == 8

    stored = entity_store.get("product.item", {"key": product["id"]})
    assert stored["upvote_count"] == 8

    second = await _toggle(user_id, product["id"], "LIKE")
    assert second.status == "SUCCESS", second.error_message
    assert second.final_output["response"]["active"] is False
    assert second.final_output["response"]["like_count"] == 7
    stored = entity_store.get("product.item", {"key": product["id"]})
    assert stored["upvote_count"] == 7


async def test_perk_counter_write_back(cleanup):
    perk = cleanup("perk.item", _seed_perk())
    user_id = _uid("usr_perk")

    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PERK", "target_id": perk["id"], "kind": "LOVE"},
        _ctx(user_id),
    )
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["response"]["love_count"] == 1

    stored = entity_store.get("perk.item", {"key": perk["id"]})
    assert stored["love_count"] == 1


async def test_forum_thread_write_back_only_mirrors_bookmark_and_love(cleanup):
    thread = cleanup(
        "forum.thread",
        entity_store.create(
            "forum.thread",
            {
                "id": _uid("thr_int"),
                "category_code": "DEV",
                "author_id": "usr_thread_author",
                "title": "互动测试讨论帖",
                "content": "用于验证论坛收藏/喜欢计数回写，不覆盖论坛域赞同与评论账本。",
            },
        ),
    )
    user_id = _uid("usr_thread")
    for kind in ("FAVORITE", "LOVE"):
        res = await _run(
            "OPC_INTERACTION_TOGGLE_PIPELINE",
            {"target_type": "FORUM_THREAD", "target_id": thread["id"], "kind": kind},
            _ctx(user_id),
        )
        assert res.status == "SUCCESS", res.error_message

    stored = entity_store.get("forum.thread", {"key": thread["id"]})
    assert stored["bookmark_count"] == 1
    assert stored["love_count"] == 1
    assert stored["upvote_count"] == 0
    assert stored["comment_count"] == 0


async def test_toggle_unknown_target_fails(cleanup):
    missing = _uid("prd_missing")
    res = await _toggle(_uid("usr_missing"), missing, "LIKE")
    assert res.status == "FAILED"
    assert "不存在" in (res.error_message or "")


async def test_toggle_requires_login(cleanup):
    product = cleanup("product.item", _seed_product())
    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "kind": "LIKE"},
    )
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


async def test_toggle_rejects_unsupported_kind(cleanup):
    product = cleanup("product.item", _seed_product())
    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "kind": "CLAP"},
        _ctx(_uid("usr_bad_kind")),
    )
    assert res.status == "FAILED"
    assert "kind" in (res.error_message or "").lower()


async def test_toggle_rejects_unsupported_target_type():
    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "BLOG", "target_id": "whatever", "kind": "LIKE"},
        _ctx(_uid("usr_bad_target")),
    )
    assert res.status == "FAILED"
    assert "target_type" in (res.error_message or "")


# ---------------------------------------------------------------------------
# 2. Rating
# ---------------------------------------------------------------------------
async def test_rating_overwrites_and_aggregates_across_users(cleanup):
    product = cleanup("product.item", _seed_product())
    alice = _uid("usr_rate_a")
    bob = _uid("usr_rate_b")

    first = await _run(
        "OPC_INTERACTION_RATE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "score": 4},
        _ctx(alice),
    )
    assert first.status == "SUCCESS", first.error_message
    body = first.final_output["response"]
    assert body["rating_avg"] == 4.0
    assert body["rating_count"] == 1
    assert body["viewer"]["rating"] == 4

    updated = await _run(
        "OPC_INTERACTION_RATE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "score": 5},
        _ctx(alice),
    )
    assert updated.status == "SUCCESS", updated.error_message
    body = updated.final_output["response"]
    assert body["rating_avg"] == 5.0
    assert body["rating_count"] == 1  # overwrite, never double count
    assert body["viewer"]["rating"] == 5

    second = await _run(
        "OPC_INTERACTION_RATE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "score": 3},
        _ctx(bob),
    )
    assert second.status == "SUCCESS", second.error_message
    body = second.final_output["response"]
    assert body["rating_count"] == 2
    assert body["rating_avg"] == 4.0

    stat = entity_store.get(
        ENTITY_INTERACTION_STAT, {"target_type": "PRODUCT", "target_id": product["id"]}
    )
    assert stat["rating_sum"] == 8
    assert stat["rating_count"] == 2
    assert (
        entity_store.get(
            ENTITY_INTERACTION_RATING,
            {"user_id": alice, "target_type": "PRODUCT", "target_id": product["id"]},
        )["score"]
        == 5
    )


async def test_rating_rejects_out_of_range(cleanup):
    product = cleanup("product.item", _seed_product())
    res = await _run(
        "OPC_INTERACTION_RATE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "score": 6},
        _ctx(_uid("usr_rate_bad")),
    )
    assert res.status == "FAILED"
    assert "打分" in (res.error_message or "")


async def test_rating_requires_login(cleanup):
    product = cleanup("product.item", _seed_product())
    res = await _run(
        "OPC_INTERACTION_RATE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "score": 3},
    )
    assert res.status == "GUARD_REJECTED"


# ---------------------------------------------------------------------------
# 3. Comments: create / list / delete
# ---------------------------------------------------------------------------
async def test_comment_create_list_delete(cleanup):
    product = cleanup("product.item", _seed_product())
    author = _uid("usr_comment")

    created = await _run(
        "OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "content": "这是一条互动评论"},
        _ctx(author),
    )
    assert created.status == "SUCCESS", created.error_message
    comment = created.final_output["created_comment"]
    assert comment["id"].startswith("cmt_")
    assert comment["author_id"] == author
    assert comment["target_title"] == "互动测试产品"
    assert created.final_output["response"]["id"] == comment["id"]
    assert created.final_output["comment_count"] == 1

    listed = await _run(
        "OPC_INTERACTION_COMMENTS_LIST_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"]},
    )
    assert listed.status == "SUCCESS", listed.error_message
    assert listed.final_output["response"]["total"] == 1
    assert listed.final_output["response"]["items"][0]["id"] == comment["id"]

    state = await _run(
        "OPC_INTERACTION_STATE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"]},
        _ctx(author),
    )
    assert state.status == "SUCCESS", state.error_message
    assert state.final_output["response"]["comment_count"] == 1
    assert state.final_output["response"]["viewer"]["commented"] is True

    deleted = await _run(
        "OPC_INTERACTION_COMMENT_DELETE_PIPELINE",
        {"comment_id": comment["id"]},
        _ctx(author),
    )
    assert deleted.status == "SUCCESS", deleted.error_message
    assert deleted.final_output["response"]["deleted"] is True
    assert deleted.final_output["response"]["comment_count"] == 0

    assert entity_store.get(ENTITY_CONTENT_COMMENT, {"key": comment["id"]}) is None
    stored = entity_store.get("product.item", {"key": product["id"]})
    assert stored["comment_count"] == 0


async def test_comment_delete_denied_for_non_author(cleanup):
    product = cleanup("product.item", _seed_product())
    author = _uid("usr_cmt_owner")
    other = _uid("usr_cmt_other")

    created = await _run(
        "OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "content": "只允许作者删除的评论"},
        _ctx(author),
    )
    assert created.status == "SUCCESS", created.error_message
    comment_id = created.final_output["created_comment"]["id"]

    denied = await _run(
        "OPC_INTERACTION_COMMENT_DELETE_PIPELINE",
        {"comment_id": comment_id},
        _ctx(other),
    )
    assert denied.status == "GUARD_REJECTED"
    assert "权限" in (denied.error_message or "")
    assert entity_store.get(ENTITY_CONTENT_COMMENT, {"key": comment_id}) is not None

    # ADMIN bypasses ownership
    admin = await _run(
        "OPC_INTERACTION_COMMENT_DELETE_PIPELINE",
        {"comment_id": comment_id},
        _ctx(_uid("usr_admin"), role="ADMIN"),
    )
    assert admin.status == "SUCCESS", admin.error_message
    assert entity_store.get(ENTITY_CONTENT_COMMENT, {"key": comment_id}) is None


async def test_comment_create_rejects_blank_content(cleanup):
    product = cleanup("product.item", _seed_product())
    res = await _run(
        "OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "content": "   "},
        _ctx(_uid("usr_blank")),
    )
    assert res.status == "FAILED"
    assert "评论内容" in (res.error_message or "")


async def test_comment_create_unknown_target_fails(cleanup):
    res = await _run(
        "OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
        {"target_type": "PRODUCT", "target_id": _uid("prd_missing"), "content": "目标不存在的评论"},
        _ctx(_uid("usr_cmt_missing")),
    )
    assert res.status == "FAILED"
    assert "不存在" in (res.error_message or "")


# ---------------------------------------------------------------------------
# 4. Batch state / mine
# ---------------------------------------------------------------------------
async def test_batch_state_returns_viewer_flags(cleanup):
    product = cleanup("product.item", _seed_product())
    perk = cleanup("perk.item", _seed_perk())
    user_id = _uid("usr_batch")

    assert (await _toggle(user_id, product["id"], "LIKE")).status == "SUCCESS"
    loved = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PERK", "target_id": perk["id"], "kind": "FAVORITE"},
        _ctx(user_id),
    )
    assert loved.status == "SUCCESS", loved.error_message

    res = await _run(
        "OPC_INTERACTION_BATCH_STATE_PIPELINE",
        {
            "targets": [
                {"target_type": "PRODUCT", "target_id": product["id"]},
                {"target_type": "PERK", "target_id": perk["id"]},
            ]
        },
        _ctx(user_id),
    )
    assert res.status == "SUCCESS", res.error_message
    items = {(item["target_type"], item["target_id"]): item for item in res.final_output["response"]["items"]}
    assert ("PRODUCT", product["id"]) in items
    assert ("PERK", perk["id"]) in items
    assert items[("PRODUCT", product["id"])]["viewer"]["liked"] is True
    assert items[("PRODUCT", product["id"])]["like_count"] == 1
    assert items[("PERK", perk["id"])]["viewer"]["favorited"] is True
    assert items[("PERK", perk["id"])]["favorite_count"] == 1


async def test_mine_returns_ledger_and_comments(cleanup):
    product = cleanup("product.item", _seed_product())
    user_id = _uid("usr_mine")

    assert (await _toggle(user_id, product["id"], "LIKE")).status == "SUCCESS"
    created = await _run(
        "OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"], "content": "我的互动足迹评论"},
        _ctx(user_id),
    )
    assert created.status == "SUCCESS", created.error_message

    res = await _run("OPC_INTERACTION_MINE_PIPELINE", {}, _ctx(user_id))
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]
    kinds = {item["kind"] for item in body["items"]}
    assert "LIKE" in kinds
    assert "COMMENT" in kinds
    assert body["counts"]["like"] == 1
    assert body["counts"]["comment"] == 1
    comment_item = next(item for item in body["items"] if item["kind"] == "COMMENT")
    assert comment_item["title"] == "互动测试产品"


async def test_counts_initial_seeds_from_target(cleanup):
    product = cleanup(
        "product.item",
        _seed_product(upvote_count=11, favorite_count=2, love_count=3, comment_count=4),
    )
    res = await _run(
        "OPC_INTERACTION_COUNTS_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"]},
    )
    assert res.status == "SUCCESS", res.error_message
    body = res.final_output["response"]
    assert body["has_stat"] is False
    assert body["target_exists"] is True
    assert body["like_count"] == 11
    assert body["favorite_count"] == 2
    assert body["love_count"] == 3
    assert body["comment_count"] == 4

    assert (await _toggle(_uid("usr_seed"), product["id"], "LIKE")).status == "SUCCESS"
    after = await _run(
        "OPC_INTERACTION_COUNTS_PIPELINE",
        {"target_type": "PRODUCT", "target_id": product["id"]},
    )
    assert after.final_output["response"]["has_stat"] is True
    assert after.final_output["response"]["like_count"] == 12
