"""Tests verifying that user-published content across all 7 modules includes disclaimers on display pages.

Modules covered:
1. 头脑风暴 (Forum / Brainstorming)
2. 产品橱窗 (Product Showcase)
3. 政策中心 (Policy Center)
4. 需求集市 (Demands Marketplace)
5. 流程文书 (SOP Documents & Flows)
6. 生态特权 (Ecosystem Perks)
7. 合规指南 (Compliance Guidelines)

Verification points:
- All 7 modules support user publishing (用户自主发布/起草/提报入库).
- All 7 modules' display/reading pages (展示页面) include the disclaimer (免责声明).
- ContentDisclaimer component contains domain-specific disclaimers.
- Compiled frontend assets include the disclaimers.
"""
from pathlib import Path
import pytest

FRONTEND_SRC = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"


def test_content_disclaimer_component_exists_and_covers_all_7_domains():
    """Verify ContentDisclaimer.vue exists and covers all 7 modules with tailored disclaimer copy."""
    disclaimer_file = FRONTEND_SRC / "components" / "ContentDisclaimer.vue"
    assert disclaimer_file.is_file(), "ContentDisclaimer.vue must exist"

    content = disclaimer_file.read_text(encoding="utf-8")
    assert "免责声明" in content
    assert "用户自主发布" in content

    # All 7 domain keys present in disclaimer map
    assert "forum:" in content
    assert "showcase:" in content
    assert "policy:" in content
    assert "demand:" in content
    assert "sop:" in content
    assert "perk:" in content
    assert "compliance:" in content

    # Domain specific disclaimer copy keywords
    assert "头脑风暴免责声明" in content
    assert "产品橱窗免责声明" in content
    assert "政策中心免责声明" in content
    assert "需求集市免责声明" in content
    assert "流程文书免责声明" in content
    assert "生态特权免责声明" in content
    assert "合规指南免责声明" in content


def test_all_7_modules_display_pages_contain_disclaimers():
    """Verify that every display / reader / detail page across all 7 modules contains disclaimers."""
    # 1. 头脑风暴 (Forum)
    forum_detail = (FRONTEND_SRC / "components" / "ForumDetailView.vue").read_text(encoding="utf-8")
    forum_view = (FRONTEND_SRC / "views" / "ForumView.vue").read_text(encoding="utf-8")
    assert "<ContentDisclaimer" in forum_detail
    assert 'type="forum"' in forum_detail
    assert "<ContentDisclaimer" in forum_view

    # 2. 产品橱窗 (Showcase)
    showcase_view = (FRONTEND_SRC / "views" / "ShowcaseView.vue").read_text(encoding="utf-8")
    assert "<ContentDisclaimer" in showcase_view
    assert 'type="showcase"' in showcase_view

    # 3. 政策中心 (Policy)
    policy_view = (FRONTEND_SRC / "views" / "PolicyView.vue").read_text(encoding="utf-8")
    assert "<ContentDisclaimer" in policy_view
    assert 'type="policy"' in policy_view

    # 4. 需求集市 (Demands)
    demands_view = (FRONTEND_SRC / "views" / "DemandsView.vue").read_text(encoding="utf-8")
    assert "<ContentDisclaimer" in demands_view
    assert 'type="demand"' in demands_view

    # 5. 流程文书 (SOP)
    sop_doc_page = (FRONTEND_SRC / "components" / "sop" / "SopDocPage.vue").read_text(encoding="utf-8")
    sop_flow_page = (FRONTEND_SRC / "components" / "sop" / "SopFlowPage.vue").read_text(encoding="utf-8")
    sop_mydoc_page = (FRONTEND_SRC / "components" / "sop" / "SopMyDocPage.vue").read_text(encoding="utf-8")
    sop_view = (FRONTEND_SRC / "views" / "SopView.vue").read_text(encoding="utf-8")
    assert "<ContentDisclaimer" in sop_doc_page
    assert "<ContentDisclaimer" in sop_flow_page
    assert "<ContentDisclaimer" in sop_mydoc_page
    assert "免责声明" in sop_view

    # 6. 生态特权 (Perks)
    perks_view = (FRONTEND_SRC / "views" / "PerksView.vue").read_text(encoding="utf-8")
    assert "<ContentDisclaimer" in perks_view
    assert 'type="perk"' in perks_view
    assert "免责声明" in perks_view

    # 7. 合规指南 (Compliance)
    compliance_view = (FRONTEND_SRC / "views" / "ComplianceView.vue").read_text(encoding="utf-8")
    assert "<ContentDisclaimer" in compliance_view
    assert 'type="compliance"' in compliance_view
    assert "免责声明" in compliance_view


def test_all_7_modules_support_user_publishing():
    """Verify that all 7 modules have user publishing interfaces (forms / builder / editor)."""
    # 1. 头脑风暴
    forum_create = FRONTEND_SRC / "components" / "ForumCreateView.vue"
    assert forum_create.is_file()

    # 2. 产品橱窗, 3. 政策中心, 4. 需求集市, 6. 生态特权, 7. 合规指南
    publish_forms_config = FRONTEND_SRC / "config" / "publishForms.js"
    assert publish_forms_config.is_file()
    cfg_text = publish_forms_config.read_text(encoding="utf-8")
    assert "PRODUCT_FIELDS" in cfg_text
    assert "POLICY_FIELDS" in cfg_text
    assert "DEMAND_FIELDS" in cfg_text
    assert "PERK_FIELDS" in cfg_text
    assert "COMPLIANCE_FIELDS" in cfg_text

    # 5. 流程文书
    sop_view = (FRONTEND_SRC / "views" / "SopView.vue").read_text(encoding="utf-8")
    assert "flowbuilder" in sop_view or "起草新文书" in sop_view


def test_compiled_dist_includes_disclaimer_copy():
    """Verify that the compiled frontend bundle contains the disclaimer text."""
    dist_dir = FRONTEND_SRC.parent / "dist" / "assets"
    if not dist_dir.is_dir():
        pytest.skip("Frontend dist assets not built yet")

    js_files = list(dist_dir.glob("*.js"))
    assert len(js_files) > 0, "Built js files must exist"

    combined_js = "".join(f.read_text(encoding="utf-8") for f in js_files)
    assert "免责声明" in combined_js
    assert "用户自主发布" in combined_js
