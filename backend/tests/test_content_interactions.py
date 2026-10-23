"""Unified content interaction + comments domain tests.

Covers the four public-card interactions (点赞 LIKE / 收藏 FAVORITE / 喜欢 LOVE /
评论 comments), backend persistence via domain snapshots, per-user viewer state,
and the personal interaction centre (content.interactions.mine).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.security import create_session_token
from src.domains.interactions.service import content_interaction_service
from src.domains.products.service import product_service

PRODUCT_ID = "prod-inkflow-001"
USER_ID = "interact_tester"
USER_TOKEN = create_session_token(
    {"uid": USER_ID, "role": "USER", "nickname": "互动测试创客"},
    expires_in_seconds=3600,
)


@pytest.fixture(autouse=True)
def clean_interactions():
    content_interaction_service.clear()
    yield
    content_interaction_service.clear()


def test_toggle_like_persists_and_toggles():
    base = content_interaction_service.get_state(None, "PRODUCT", PRODUCT_ID).like_count
    first = content_interaction_service.toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LIKE")
    assert first.active is True
    assert first.count == base + 1
    assert first.viewer.liked is True

    second = content_interaction_service.toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LIKE")
    assert second.active is False
    assert second.count == base
    assert second.viewer.liked is False


def test_favorite_and_love_are_independent_toggles():
    a = content_interaction_service.toggle(USER_ID, "PRODUCT", PRODUCT_ID, "FAVORITE")
    b = content_interaction_service.toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LOVE")
    assert a.active and b.active
    state = content_interaction_service.get_state(USER_ID, "PRODUCT", PRODUCT_ID)
    assert state.favorite_count == 1
    assert state.love_count == 1
    assert state.viewer.favorited and state.viewer.loved


def test_dislike_toggle_is_independent():
    state = content_interaction_service.toggle(USER_ID, "PRODUCT", PRODUCT_ID, "DISLIKE")
    assert state.active is True
    assert state.dislike_count == 1
    assert state.viewer.disliked is True

    off = content_interaction_service.toggle(USER_ID, "PRODUCT", PRODUCT_ID, "DISLIKE")
    assert off.active is False
    assert off.dislike_count == 0
    assert off.viewer.disliked is False


def test_rate_submits_and_updates():
    first = content_interaction_service.rate(USER_ID, "PRODUCT", PRODUCT_ID, 4)
    assert first.rating_avg == 4.0
    assert first.rating_count == 1
    assert first.viewer.rating == 4

    updated = content_interaction_service.rate(USER_ID, "PRODUCT", PRODUCT_ID, 5)
    assert updated.rating_avg == 5.0
    assert updated.rating_count == 1  # overwrite, not double-count
    assert updated.viewer.rating == 5


def test_rating_aggregates_across_users():
    content_interaction_service.rate(USER_ID, "PRODUCT", PRODUCT_ID, 5)
    content_interaction_service.rate("other_user", "PRODUCT", PRODUCT_ID, 3)
    state = content_interaction_service.get_state(None, "PRODUCT", PRODUCT_ID)
    assert state.rating_count == 2
    assert state.rating_avg == 4.0


def test_rating_rejects_out_of_range():
    with pytest.raises(ValueError):
        content_interaction_service.rate(USER_ID, "PRODUCT", PRODUCT_ID, 6)


def test_batch_state_merges_legacy_product_upvotes():
    product = product_service._products.get(PRODUCT_ID)
    legacy = product.upvote_count
    state = content_interaction_service.get_state(None, "PRODUCT", PRODUCT_ID)
    assert state.like_count == legacy
    assert state.viewer.liked is False


def test_comments_create_list_delete():
    comment = content_interaction_service.create_comment(
        USER_ID, "PRODUCT", PRODUCT_ID, "这是一条评论", author_name="互动测试创客"
    )
    listed = content_interaction_service.list_comments("PRODUCT", PRODUCT_ID)
    assert listed.total == 1
    assert listed.items[0].id == comment.id

    ok = content_interaction_service.delete_comment(USER_ID, comment.id)
    assert ok is True
    assert content_interaction_service.list_comments("PRODUCT", PRODUCT_ID).total == 0


def test_mine_returns_own_interactions():
    content_interaction_service.toggle(USER_ID, "PRODUCT", PRODUCT_ID, "LIKE")
    content_interaction_service.create_comment(
        USER_ID, "PRODUCT", PRODUCT_ID, "评论足迹", author_name="互动测试创客"
    )
    mine = content_interaction_service.mine(USER_ID)
    kinds = {item.kind for item in mine.items}
    assert "LIKE" in kinds
    assert "COMMENT" in kinds
    assert mine.counts["like"] == 1
    assert mine.counts["comment"] == 1


def test_requires_login_for_toggle():
    with pytest.raises(PermissionError):
        content_interaction_service.toggle("", "PRODUCT", PRODUCT_ID, "LIKE")


def test_unknown_target_rejected():
    with pytest.raises(KeyError):
        content_interaction_service.toggle(USER_ID, "PRODUCT", "no_such_product", "LIKE")


# ---------------------------------------------------------------------------
# PERK target type: ecosystem discount announcement cards share the same
# interaction band as policy/product cards (生态特权 优惠公告点赞/收藏/喜欢).
# ---------------------------------------------------------------------------
PERK_ID = "perk_volc_ark_tokens"


@pytest.fixture
def seeded_perk():
    from src.domains.perks.service import perk_service

    perk_service._init_seeds()
    assert perk_service._perks.get(PERK_ID) is not None
    yield perk_service._perks[PERK_ID]


def test_perk_toggle_like_favorite_love(seeded_perk):
    like = content_interaction_service.toggle(USER_ID, "PERK", PERK_ID, "LIKE")
    assert like.active is True
    assert like.count >= 1
    assert like.viewer.liked is True

    fav = content_interaction_service.toggle(USER_ID, "PERK", PERK_ID, "FAVORITE")
    love = content_interaction_service.toggle(USER_ID, "PERK", PERK_ID, "LOVE")
    assert fav.active and love.active

    state = content_interaction_service.get_state(USER_ID, "PERK", PERK_ID)
    assert state.viewer.liked and state.viewer.favorited and state.viewer.loved
    assert state.favorite_count == 1
    assert state.love_count == 1


def test_perk_unknown_target_rejected():
    with pytest.raises(KeyError):
        content_interaction_service.toggle(USER_ID, "PERK", "perk_no_such", "LIKE")


def test_perk_counts_sync_back_to_domain(seeded_perk):
    content_interaction_service.toggle(USER_ID, "PERK", PERK_ID, "LIKE")
    content_interaction_service.toggle(USER_ID, "PERK", PERK_ID, "FAVORITE")
    perk = seeded_perk
    assert perk.like_count >= 1
    assert perk.favorite_count >= 1


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
