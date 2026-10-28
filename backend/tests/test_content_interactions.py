"""Unified content interaction + comments domain tests.

Covers the four public-card interactions (点赞 LIKE / 收藏 FAVORITE / 喜欢 LOVE /
评论 comments), backend persistence via the generic entity store, per-user viewer
state, and the personal interaction centre (content.interactions.mine).

Operator-kernel v2: every mutation is executed through the declarative scenarios
in ``config/scenarios/interactions.yaml`` (``OPC_INTERACTION_*`` /
``OPC_CONTENT_COMMENT_PUBLISH_PIPELINE``). The legacy ``service.toggle`` /
``rate`` / ``create_comment`` / ``delete_comment`` write methods were removed.
Read projections still come from ``content_interaction_service``.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.security import create_session_token
from src.domains.interactions.service import content_interaction_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service
from src.domains.products.service import product_service

PRODUCT_ID = "prod-inkflow-001"
USER_ID = "interact_tester"
USER_TOKEN = create_session_token(
    {"uid": USER_ID, "role": "USER", "nickname": "互动测试创客"},
    expires_in_seconds=3600,
)


def _ctx(user_id: str = USER_ID, role: str = "MAKER", **extra) -> dict:
    return {"user_id": user_id, "user_role": role, "nickname": "互动测试创客", **extra}


async def _run(scenario: str, inputs: dict, context: dict | None = None):
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=inputs,
            context=context or {},
        )
    )


async def _toggle(user_id: str, target_type: str, target_id: str, kind: str):
    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": target_type, "target_id": target_id, "kind": kind},
        _ctx(user_id),
    )
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["response"]


async def _rate(user_id: str, target_type: str, target_id: str, score: int):
    res = await _run(
        "OPC_INTERACTION_RATE_PIPELINE",
        {"target_type": target_type, "target_id": target_id, "score": score},
        _ctx(user_id),
    )
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["response"]


async def _create_comment(
    user_id: str, target_type: str, target_id: str, content: str, author_name: str = "互动测试创客"
):
    res = await _run(
        "OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
        {"target_type": target_type, "target_id": target_id, "content": content},
        _ctx(user_id, nickname=author_name),
    )
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["created_comment"]


@pytest.fixture(autouse=True)
def clean_interactions():
    content_interaction_service.clear()
    yield
    content_interaction_service.clear()


async def test_toggle_like_persists_and_toggles():
    base = content_interaction_service.get_state(None, "PRODUCT", PRODUCT_ID).like_count
    first = await _toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LIKE")
    assert first["active"] is True
    assert first["count"] == base + 1
    assert first["viewer"]["liked"] is True

    second = await _toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LIKE")
    assert second["active"] is False
    assert second["count"] == base
    assert second["viewer"]["liked"] is False


async def test_favorite_and_love_are_independent_toggles():
    a = await _toggle(USER_ID, "PRODUCT", PRODUCT_ID, "FAVORITE")
    b = await _toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LOVE")
    assert a["active"] and b["active"]
    state = content_interaction_service.get_state(USER_ID, "PRODUCT", PRODUCT_ID)
    assert state.favorite_count == 1
    assert state.love_count == 1
    assert state.viewer.favorited and state.viewer.loved


async def test_dislike_toggle_is_independent():
    state = await _toggle(USER_ID, "PRODUCT", PRODUCT_ID, "DISLIKE")
    assert state["active"] is True
    assert state["dislike_count"] == 1
    assert state["viewer"]["disliked"] is True

    off = await _toggle(USER_ID, "PRODUCT", PRODUCT_ID, "DISLIKE")
    assert off["active"] is False
    assert off["dislike_count"] == 0
    assert off["viewer"]["disliked"] is False


async def test_rate_submits_and_updates():
    first = await _rate(USER_ID, "PRODUCT", PRODUCT_ID, 4)
    assert first["rating_avg"] == 4.0
    assert first["rating_count"] == 1
    assert first["viewer"]["rating"] == 4

    updated = await _rate(USER_ID, "PRODUCT", PRODUCT_ID, 5)
    assert updated["rating_avg"] == 5.0
    assert updated["rating_count"] == 1  # overwrite, not double-count
    assert updated["viewer"]["rating"] == 5


async def test_rating_aggregates_across_users():
    await _rate(USER_ID, "PRODUCT", PRODUCT_ID, 5)
    await _rate("other_user", "PRODUCT", PRODUCT_ID, 3)
    state = content_interaction_service.get_state(None, "PRODUCT", PRODUCT_ID)
    assert state.rating_count == 2
    assert state.rating_avg == 4.0


async def test_rating_rejects_out_of_range():
    res = await _run(
        "OPC_INTERACTION_RATE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": PRODUCT_ID, "score": 6},
        _ctx(USER_ID),
    )
    assert res.status == "FAILED"
    assert "打分" in (res.error_message or "")


async def test_batch_state_merges_legacy_product_upvotes():
    product = product_service._products.get(PRODUCT_ID)
    legacy = product.upvote_count
    state = content_interaction_service.get_state(None, "PRODUCT", PRODUCT_ID)
    assert state.like_count == legacy
    assert state.viewer.liked is False


async def test_comments_create_list_delete():
    comment = await _create_comment(USER_ID, "PRODUCT", PRODUCT_ID, "这是一条评论")
    listed = content_interaction_service.list_comments("PRODUCT", PRODUCT_ID)
    assert listed.total == 1
    assert listed.items[0].id == comment["id"]

    deleted = await _run(
        "OPC_INTERACTION_COMMENT_DELETE_PIPELINE",
        {"comment_id": comment["id"]},
        _ctx(USER_ID),
    )
    assert deleted.status == "SUCCESS", deleted.error_message
    assert deleted.final_output["response"]["deleted"] is True
    assert content_interaction_service.list_comments("PRODUCT", PRODUCT_ID).total == 0


async def test_mine_returns_own_interactions():
    await _toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LIKE")
    await _create_comment(USER_ID, "PRODUCT", PRODUCT_ID, "评论足迹")
    mine = content_interaction_service.mine(USER_ID)
    kinds = {item.kind for item in mine.items}
    assert "LIKE" in kinds
    assert "COMMENT" in kinds
    assert mine.counts["like"] == 1
    assert mine.counts["comment"] == 1


async def test_requires_login_for_toggle():
    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": PRODUCT_ID, "kind": "LIKE"},
    )
    assert res.status == "GUARD_REJECTED"


async def test_unknown_target_rejected():
    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PRODUCT", "target_id": "no_such_product", "kind": "LIKE"},
        _ctx(USER_ID),
    )
    assert res.status == "FAILED"
    assert "不存在" in (res.error_message or "")


# ---------------------------------------------------------------------------
# PERK target type: ecosystem discount announcement cards share the same
# interaction band as policy/product cards (生态特权 优惠公告点赞/收藏/喜欢).
# ---------------------------------------------------------------------------
PERK_ID = "perk_volc_ark_tokens"


@pytest.fixture
def seeded_perk():
    from src.domains.perks.service import perk_service
    from tests.catalog_fixtures import seed_perks

    if not perk_service._perks:
        seed_perks(perk_service)
    assert perk_service._perks.get(PERK_ID) is not None
    yield perk_service._perks[PERK_ID]


async def test_perk_toggle_like_favorite_love(seeded_perk):
    like = await _toggle(USER_ID, "PERK", PERK_ID, "LIKE")
    assert like["active"] is True
    assert like["count"] >= 1
    assert like["viewer"]["liked"] is True

    fav = await _toggle(USER_ID, "PERK", PERK_ID, "FAVORITE")
    love = await _toggle(USER_ID, "PERK", PERK_ID, "LOVE")
    assert fav["active"] and love["active"]

    state = content_interaction_service.get_state(USER_ID, "PERK", PERK_ID)
    assert state.viewer.liked and state.viewer.favorited and state.viewer.loved
    assert state.favorite_count == 1
    assert state.love_count == 1


async def test_perk_unknown_target_rejected():
    res = await _run(
        "OPC_INTERACTION_TOGGLE_PIPELINE",
        {"target_type": "PERK", "target_id": "perk_no_such", "kind": "LIKE"},
        _ctx(USER_ID),
    )
    assert res.status == "FAILED"
    assert "不存在" in (res.error_message or "")


async def test_perk_counts_sync_back_to_domain(seeded_perk):
    await _toggle(USER_ID, "PERK", PERK_ID, "LIKE")
    await _toggle(USER_ID, "PERK", PERK_ID, "FAVORITE")
    # entity store is authoritative after the operator-kernel v2 migration, so the
    # counter write-back is asserted by re-reading the perk document.
    from src.core.entity import entity_store

    perk = entity_store.get("perk.item", {"key": PERK_ID})
    assert perk["like_count"] >= 1
    assert perk["favorite_count"] >= 1


def test_rbac_allows_user_but_blocks_guest_via_gateway():
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    base = {"version": "v1.0.0", "context": {}}
    client.headers.pop("Authorization", None)  # conftest injects ADMIN by default

    guest = client.post(
        "/api/welcom/opc_world",
        json={
            **base,
            "scenario": "content.interaction.toggle",
            "payload": {"target_type": "PRODUCT", "target_id": PRODUCT_ID, "kind": "LIKE"},
        },
    )
    assert guest.status_code == 200
    assert guest.json()["code"] == 401

    logged_in = client.post(
        "/api/welcom/opc_world",
        json={
            **base,
            "context": {"token": USER_TOKEN},
            "scenario": "content.interaction.toggle",
            "payload": {"target_type": "PRODUCT", "target_id": PRODUCT_ID, "kind": "LIKE"},
        },
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["code"] == 200
