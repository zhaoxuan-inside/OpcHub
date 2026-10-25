"""创建发布入口统一为内容区全页面（不再使用发布弹窗）.

覆盖：政策中心 / 产品橱窗 / 需求集市 / 生态特权 的发布表单改为
CreatePageLayout 全页面；头脑风暴与流程文书确认沿用既有全页面创建工作区。
"""
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"

FULL_PAGE_VIEWS = {
    "PolicyView.vue": "policy-main-content",
    "ShowcaseView.vue": "showcase-main-content",
    "DemandsView.vue": "demands-main-content",
    "PerksView.vue": "perks-main-content",
}


@pytest.mark.parametrize("filename,list_class", FULL_PAGE_VIEWS.items())
def test_publish_uses_full_page_layout(filename, list_class):
    source = (SRC / "views" / filename).read_text(encoding="utf-8")

    assert "CreatePageLayout" in source
    assert 'v-if="showPublishPage"' in source
    assert f'v-else class="{list_class}"' in source
    assert "<PublishForm" in source
    assert "from '@/config/publishForms'" in source
    # The old modal surface must be gone from the publish entry.
    assert 'v-if="showPublishPage" class="modal-backdrop"' not in source
    assert "publish-form" in source


def test_forum_create_is_full_page():
    view = (SRC / "views" / "ForumView.vue").read_text(encoding="utf-8")
    create_view = (SRC / "components" / "ForumCreateView.vue").read_text(encoding="utf-8")

    assert "currentViewMode === 'create'" in view
    assert "<ForumCreateView" in view
    assert "<CreatePageLayout" in create_view
    assert 'plain-body' in create_view
    assert "create-workspace-box" in create_view


def test_create_page_header_keeps_only_essentials():
    """顶部玻璃卡片只保留返回、标题和发布动作，不展示冗余描述。"""
    layout = (SRC / "components" / "CreatePageLayout.vue").read_text(encoding="utf-8")

    assert "create-page-title" in layout
    assert "create-back-btn" in layout
    assert 'name="actions"' in layout
    # No breadcrumb / subtitle / descriptive paragraph in the header.
    assert "create-page-crumb" not in layout
    assert "subtitle" not in layout
    assert "create-page-sub" not in layout
    # Width follows the global navbar/main container instead of a narrower modal width.
    assert "max-width: 1180px" not in layout
    assert "max-width: 100%" in layout


def test_shared_publish_form_drives_the_simple_boards():
    """政策/产品/需求/特权共用一个 schema 驱动的表单组件。"""
    form = (SRC / "components" / "PublishForm.vue").read_text(encoding="utf-8")
    schema = (SRC / "config" / "publishForms.js").read_text(encoding="utf-8")

    assert "publish-section" in form
    assert "publish-grid" in form
    assert "visibleFields" in form
    assert "POLICY_FIELDS" in schema
    assert "PRODUCT_FIELDS" in schema
    assert "DEMAND_FIELDS" in schema
    assert "PERK_FIELDS" in schema


def test_forum_and_sop_headers_are_trimmed():
    forum = (SRC / "components" / "ForumCreateView.vue").read_text(encoding="utf-8")
    sop = (SRC / "views" / "SopView.vue").read_text(encoding="utf-8")

    # Forum: no breadcrumb and no estimated-reading description.
    assert '<div class="breadcrumb-row">' not in forum
    assert "约需阅读" not in forum
    # Word count lives under the editor, not in the sticky header.
    assert '<div class="meta-stats-text">' not in forum
    assert 'class="editor-word-count"' in forum
    # SOP flow builder: no descriptive subtitle under the title.
    assert '<p class="sop-flow-builder-sub">' not in sop


def test_sop_create_is_full_page():
    view = (SRC / "views" / "SopView.vue").read_text(encoding="utf-8")
    doc_page = (SRC / "components" / "sop" / "SopDocPage.vue").read_text(encoding="utf-8")

    # 流程创建复用共享全页面壳；文书起草使用全页面编辑器。
    assert "<CreatePageLayout" in view
    assert "currentViewMode === 'flowbuilder'" in view
    assert "SopDocPage" in view
    assert "sop-doc-editor" in doc_page  # 编辑器容器类（草稿重开编辑演进后由 RichEditor 承载正文）
    # 文书编辑器顶部也只保留标题与必要元信息。
    assert "sop-doc-title" in doc_page
    assert "sop-doc-breadcrumb" not in doc_page
    assert "基于模板" not in doc_page
