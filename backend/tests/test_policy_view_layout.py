"""Tests for Policy Center View (PolicyView.vue) Layout and Card Structure.

Verifies:
1. Overall layout consistency: Policy Center references the layout of Product Showcase (ShowcaseView.vue)
   with dual-column feed layout (stream + sidebar).
2. Content card-centric design: Policy Center content is card-centric (policy-cards-container,
   policy-card, emblem icon, category badges, highlights, and action buttons).
3. Sidebar parity: Includes Policy Center Card (申报发布), Tax & Subsidy Calculator Card (免税即时测算),
   and Policy Center Guidelines Card.
4. Dist compilation validity: Compiled bundle includes the layout and components.
"""
from pathlib import Path
import pytest


def test_policy_view_source_code_layout_and_cards():
    """Verify PolicyView.vue source references ShowcaseView dual-column layout and card architecture."""
    source_file = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "views" / "PolicyView.vue"
    assert source_file.is_file(), "PolicyView.vue must exist"

    content = source_file.read_text(encoding="utf-8")

    # 1. Overall layout referencing ShowcaseView (产品橱窗)
    assert "policy-feed-layout" in content
    assert "policy-feed-stream" in content
    assert "policy-feed-sidebar" in content
    assert "feed-filter-bar" in content
    assert "category-tabs-scroll" in content

    # 2. Card-centric content structure (卡片流布局)
    assert "policy-cards-container" in content
    assert "policy-card" in content
    assert "card-header-row" in content
    assert "policy-icon-wrapper" in content
    assert "card-title-group" in content
    assert "card-body" in content
    assert "card-highlights-row" in content
    assert "card-footer-row" in content
    assert "btn-ai-summary" in content
    assert "btn-match-eval" in content

    # 3. Sidebar parity
    assert "creator-center-card" in content
    assert "tax-calc-card" in content
    assert "guidelines-card" in content
    assert "政策申报中心" in content
    assert "增值税免税即时测算" in content
    assert "政策中心智库公约" in content

    # 4. Modals
    assert "policy-detail-modal" in content
    assert "policy-publish-modal" in content


def test_policy_view_compiled_dist():
    """Verify that frontend dist bundle contains policy radar layout and components."""
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "assets"
    assert dist_dir.is_dir(), "Frontend dist assets must exist"

    js_files = list(dist_dir.glob("*.js"))
    assert len(js_files) > 0

    combined_js = "".join(f.read_text(encoding="utf-8") for f in js_files)
    assert "policy-feed-layout" in combined_js or "政策申报中心" in combined_js
    assert "增值税免税即时测算" in combined_js
    assert "政策中心智库公约" in combined_js
