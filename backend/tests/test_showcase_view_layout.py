"""Tests for Product Showcase View (ShowcaseView.vue) Layout and Card Structure.

Verifies:
1. Overall layout consistency: Product Showcase follows the dual-column stream + sidebar layout of Brainstorming (头脑风暴 / ForumView).
2. Content card-centric design: Product showcase content is strictly card-centric (showcase-cards-container, showcase-product-card, app-icon, pricing, highlights, actions).
3. Sidebar parity: Includes Creator Center Card, Today's Hot Product Rank, and Platform Guidelines.
4. Dist compilation validity: Compiled bundle includes the new layout and card components.
"""
from pathlib import Path
import pytest


def test_showcase_view_source_code_layout_and_cards():
    """Verify ShowcaseView.vue source adheres to dual-column layout and card-first architecture."""
    source_file = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "views" / "ShowcaseView.vue"
    assert source_file.is_file(), "ShowcaseView.vue must exist"

    content = source_file.read_text(encoding="utf-8")

    # 1. Overall layout matching ForumView (头脑风暴)
    assert "showcase-feed-layout" in content
    assert "showcase-feed-stream" in content
    assert "showcase-feed-sidebar" in content
    assert "showcase-top-bar" in content
    assert "feed-filter-bar" in content

    # 2. Card-centric content structure (产品橱窗的内容是以卡片为主)
    assert "showcase-cards-container" in content
    assert "showcase-product-card" in content
    assert "card-header-row" in content
    assert "app-icon-wrapper" in content
    assert "card-title-group" in content
    assert "card-body" in content
    assert "product-tagline" in content
    assert "product-desc-snippet" in content
    assert "card-highlights-row" in content
    assert "card-footer-row" in content
    assert "upvote-btn-pill" in content

    # 3. Sidebar matching ForumView cards
    assert "creator-center-card" in content
    assert "hot-ranking-card" in content
    assert "guidelines-card" in content
    assert "创客作品中心" in content
    assert "今日作品打榜" in content
    assert "超级个体橱窗规范" in content


def test_showcase_product_detail_content_is_complete():
    """Verify the inline product detail exposes the full DB-backed product metadata."""
    source_file = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "views" / "ShowcaseView.vue"
    content = source_file.read_text(encoding="utf-8")

    for token in (
        "detail-overview-grid",
        "productStats",
        "应用信息与规格",
        "获取与交付",
        "产品编号",
        "最近更新",
        "发布状态",
        "截图数量",
        "作者 ID",
        "spec-link",
    ):
        assert token in content, f"product detail missing {token}"


def test_showcase_view_compiled_dist():
    """Verify that frontend dist bundle contains product showcase and card structure."""
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "assets"
    assert dist_dir.is_dir(), "Frontend dist assets must exist"

    js_files = list(dist_dir.glob("*.js"))
    assert len(js_files) > 0

    combined_js = "".join(f.read_text(encoding="utf-8") for f in js_files)
    assert "showcase-feed-layout" in combined_js or "创客作品中心" in combined_js
    assert "今日作品打榜" in combined_js
    assert "超级个体橱窗规范" in combined_js
