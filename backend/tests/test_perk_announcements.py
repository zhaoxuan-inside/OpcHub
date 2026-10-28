"""Tests for the 生态特权 优惠公告 (discount announcement board) feature.

Verifies:
1. Test-only announcement fixtures cover every category (production ships no seeds).
2. ``perks.list`` returns PUBLISHED announcements sorted by display priority (featured first).
3. Category filtering (TOKEN / SERVER / SAAS / FINANCE / AI / INFRA) works.
4. The board is an announcement feed, NOT a membership/pricing tier system
   (no tier / membership-price fields; cards carry announcement metadata instead).
5. Publishing with announcement fields (effective dates, redeem_url, highlights)
   round-trips through the gateway and appears on the board.
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.perks.service import perk_service
from src.domains.perks.models import PerkCreate
from tests.catalog_fixtures import seed_perks
from tests.conftest import gw_data

EXPECTED_CATEGORIES = {"TOKEN", "SERVER", "SAAS", "AI", "FINANCE", "INFRA"}


@pytest.fixture(autouse=True)
def ensure_announcement_seeds():
    """Guard against other test modules clearing the shared perk singleton."""
    if not perk_service._perks:
        seed_perks(perk_service)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_perk_seeds_loaded_across_categories():
    """Baseline announcement seeds cover every board category."""
    assert len(perk_service._perks) >= 10
    categories = {p.category for p in perk_service._perks.values()}
    assert EXPECTED_CATEGORIES.issubset(categories)


def test_perks_list_returns_published_sorted_by_priority(client):
    """Board list exposes only PUBLISHED announcements, featured first."""
    perks = gw_data(client, "perks.list", {})
    assert isinstance(perks, list)
    assert len(perks) >= 10

    priorities = [p["priority"] for p in perks]
    assert priorities == sorted(priorities, reverse=True)
    assert all(p["status"] == "PUBLISHED" for p in perks)

    # Featured offers (priority >= 90) surface at the top
    featured = [p for p in perks if p["priority"] >= 90]
    assert featured, "Featured announcements should exist"
    assert perks[0]["priority"] >= 90


def test_perks_list_category_filter(client):
    """Category filtering returns only announcements of that type."""
    token_perks = gw_data(client, "perks.list", {"category": "TOKEN"})
    assert token_perks
    assert all(p["category"] == "TOKEN" for p in token_perks)

    server_perks = gw_data(client, "perks.list", {"category": "SERVER"})
    assert server_perks
    assert all(p["category"] == "SERVER" for p in server_perks)

    saas_perks = gw_data(client, "perks.list", {"category": "SAAS"})
    assert saas_perks
    assert all(p["category"] == "SAAS" for p in saas_perks)


def test_perks_list_is_announcement_board_not_membership(client):
    """Board cards carry announcement metadata and no membership tier / pricing."""
    perks = gw_data(client, "perks.list", {})
    assert isinstance(perks, list) and len(perks) > 0

    announcement_fields = {"name", "provider", "value_cny", "category", "summary",
                           "effective_start", "effective_end", "redeem_url", "priority"}
    membership_fields = {"tier", "membership_price", "annual_price", "lifetime_price"}

    for p in perks:
        assert announcement_fields.issubset(set(p.keys()))
        # No membership pricing / tier machinery leaks into the board payload
        assert membership_fields.isdisjoint(set(p.keys())), f"membership field found in {p}"


def test_publish_announcement_with_full_fields(client):
    """Publishing an announcement with dates / redeem_url / highlights round-trips."""
    created = gw_data(client, "perks.publish", {
        "name": "测试站-某海外服务器黑五特惠",
        "provider": "某云服务商",
        "value_cny": 888.0,
        "category": "SERVER",
        "summary": "黑五期间新用户年付立减 888 元，限量 50 台。",
        "quota_remaining": 50,
        "effective_start": "2026-11-20",
        "effective_end": "2026-11-30",
        "redeem_url": "https://example.com/deal",
        "priority": 60,
        "status": "PUBLISHED",
        "highlights": ["限量 50 台", "年付立减 ¥888"],
    })
    assert created["id"].startswith("perk_")
    assert created["effective_start"] == "2026-11-20"
    assert created["redeem_url"] == "https://example.com/deal"
    assert created["highlights"] == ["限量 50 台", "年付立减 ¥888"]

    # Appears on the board
    board = gw_data(client, "perks.list", {"category": "SERVER"})
    assert any(p["id"] == created["id"] for p in board)


def test_offline_announcement_hidden_from_public_board(client):
    """OFFLINE announcements stay off the public board but remain in admin listing."""
    perk = perk_service.create_perk(PerkCreate(
        name="测试站-内部下线优惠",
        provider="测试供应商",
        value_cny=100.0,
        category="SAAS",
        summary="该公告已下线，不应出现在公开公告板。",
        status="OFFLINE",
    ))
    board_ids = {p.id for p in perk_service.list_perks({})}
    assert perk.id not in board_ids
    assert perk.id in {p.id for p in perk_service.list_all()}
