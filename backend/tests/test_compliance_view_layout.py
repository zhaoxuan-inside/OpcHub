"""Tests for Compliance Center View (ComplianceView.vue) Layout & Data/Config/Code Separation.

Verifies:
1. ComplianceView.vue mirrors the Policy Center (PolicyView.vue) dual-column feed layout:
   category filter bar, scrollable card grid, and right auxiliary sidebar.
2. 数据 / 配置 / 代码 三分离:
   - 数据: backend/data/seeds/compliance.json seeds 全量入 PostgreSQL (domain_snapshots)
   - 配置: frontend/src/config/compliancePage.js 承载展示配置 (分类/图标/配色/排序)
   - 代码: 视图组件仅承担逻辑，不硬编码业务数据
3. 合规页面展示法条(Law) 与 案例(Case)，提供发布入口、热门打榜与免责声明。
4. Dist compilation validity: compiled bundle includes the layout and components.
"""
from pathlib import Path
import json
import pytest

from src.domains.compliance.service import compliance_service


ROOT = Path(__file__).resolve().parent.parent.parent
COMPLIANCE_VIEW = ROOT / "frontend" / "src" / "views" / "ComplianceView.vue"
POLICY_VIEW = ROOT / "frontend" / "src" / "views" / "PolicyView.vue"
COMPLIANCE_CONFIG = ROOT / "frontend" / "src" / "config" / "compliancePage.js"
COMPLIANCE_SEEDS = ROOT / "backend" / "data" / "seeds" / "compliance.json"


def test_compliance_view_dual_column_feed_layout():
    """Verify ComplianceView.vue references the same dual-column feed layout as PolicyView."""
    source = COMPLIANCE_VIEW.read_text(encoding="utf-8")

    # 1. Same wrapper / main-content / feed-layout skeleton as Policy Center
    assert "compliance-view-wrapper" in source
    assert "compliance-main-content" in source
    assert "compliance-feed-layout" in source

    # 2. Main stream: category filter bar + scrollable card container (统一卡片体系)
    assert "compliance-feed-stream" in source
    assert "feed-filter-bar" in source
    assert "category-tab-pill" in source
    assert "opc-cards-scroll" in source
    assert "compliance-cards-container opc-cards-grid" in source
    assert "compliance-card opc-card-shell" in source

    # 3. Right auxiliary sidebar (与政策中心同款)
    assert "compliance-feed-sidebar" in source
    assert "sidebar-card" in source

    # 4. Reuses the same component vocabulary as the Policy Center feed
    for token in ("glass-box", "glass-card", "posts-loading-banner", "empty-state-box", "inline-detail-slot"):
        assert token in source


def test_compliance_view_categories_and_features():
    """Verify 法条/案例/热门 分类、发布入口与免责声明落地。"""
    source = COMPLIANCE_VIEW.read_text(encoding="utf-8")

    # 1. 分类 tab: 全部 / 法条 / 案例 / 热门
    for label in ("全部", "法条", "案例", "热门"):
        assert f"label: '{label}'" in source or f"'{label}'" in source

    # 2. 右上角发布按钮 + 内容区内联创建视图（同论坛"发起新风暴话题"，非弹窗）
    assert "openPublishModal" in source
    assert "submitPublish" in source
    assert "发布法条 / 案例" in source or "发布法条/案例" in source
    assert "compliance.publish" in source
    assert "currentViewMode" in source
    assert "compliance-create-page" in source
    assert "create-page-header" in source
    assert "create-workspace-box" in source
    assert "btn-back-square" in source
    # 弹窗已移除（内容区展开，不再使用 Teleport modal）
    assert "Teleport" not in source
    assert "modal-backdrop" not in source

    # 3. 热门打榜（右栏今日合规打榜 + 排序）
    assert "hotRankItems" in source
    assert "今日合规打榜" in source
    assert "hot_score" in source

    # 4. 免责声明（右下角）
    assert "免责声明" in source

    # 5. 自检评分已移除
    assert "audit-panel" not in source
    assert "auditScore" not in source
    assert "radar-score-card" not in source


def test_compliance_view_data_config_code_separation():
    """Verify data, config, and code are strictly separated across three layers."""
    source = COMPLIANCE_VIEW.read_text(encoding="utf-8")
    config_src = COMPLIANCE_CONFIG.read_text(encoding="utf-8")

    # 1. View source must NOT hardcode compliance business data
    assert "个人信息保护法 · 最小必要与明示授权" not in source
    assert "某知名独立开发者工具" not in source
    assert "law_privacy" not in source

    # 2. View imports display configuration from config layer
    assert "from '@/config/compliancePage'" in source
    for token in ("COMPLIANCE_LAW_ICONS", "COMPLIANCE_LEVEL_COLORS", "COMPLIANCE_LAW_COLORS", "COMPLIANCE_SORT_OPTIONS"):
        assert token in config_src

    # 3. View loads knowledge base via gateway scenarios (backend / DB)
    for scenario in ("compliance.laws", "compliance.cases"):
        assert scenario in source


def test_compliance_seeds_cover_all_entity_kinds():
    """Verify the compliance seed data file contains laws / cases / checkpoints."""
    data = json.loads(COMPLIANCE_SEEDS.read_text(encoding="utf-8"))
    assert len(data["laws"]) >= 6
    assert len(data["cases"]) >= 3
    assert len(data["checkpoints"]) >= 10

    # Law model fields: 编号 / 效力级别 / 发布机关 / 条文 / 发布日期 / 热度
    for law in data["laws"]:
        for key in ("id", "code", "name", "title", "summary", "content", "level", "issuer", "published_at", "penalties", "law_ref", "hot_score"):
            assert key in law, f"law missing {key}"


def test_compliance_service_hydrated_from_seeds():
    """Verify the compliance domain service is seeded from the data file (not hardcoded)."""
    assert len(compliance_service.get_laws()) >= 6
    assert len(compliance_service.get_cases()) >= 3
    assert len(compliance_service.get_checkpoints()) >= 10


def test_compliance_compiled_dist():
    """Verify that frontend dist bundle contains compliance layout components."""
    dist_dir = ROOT / "frontend" / "dist" / "assets"
    assert dist_dir.is_dir(), "Frontend dist assets must exist"

    js_files = list(dist_dir.glob("*.js"))
    assert len(js_files) > 0

    combined_js = "".join(f.read_text(encoding="utf-8") for f in js_files)
    assert "compliance-feed-layout" in combined_js or "compliance-view-wrapper" in combined_js
    assert "compliance-cards-container" in combined_js or "compliance-card" in combined_js
    assert "合规指南中心" in combined_js
