"""Tests for the free-form document editor (起草新文书).

The drafting experience is a text editor: the maker writes the body directly
(optionally seeded from a template), saves it to「我的文书」, and can publish it
to the standard catalog through the review queue.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from conftest import dispatch
from src.core.security import create_session_token
from src.domains.sop.models import (
    SOP_DOC_STATUS_PENDING_REVIEW,
    SOP_DOC_STATUS_PUBLISHED,
    SOP_DOC_STATUS_READY,
    SOP_REVIEW_STATUS_APPROVED,
)
from src.domains.sop.service import sop_service

ROOT = Path(__file__).resolve().parent.parent.parent
SOP_DOC_PAGE = ROOT / "frontend" / "src" / "components" / "sop" / "SopDocPage.vue"
SOP_VIEW = ROOT / "frontend" / "src" / "views" / "SopView.vue"

USER_ID = "usr_editor_draft_test"
EDITOR_TOKEN = create_session_token({
    "uid": USER_ID,
    "email": "editor@opchub.cn",
    "nickname": "起草测试员",
    "role": "MAKER",
    "must_change_password": False,
})


@pytest.fixture(autouse=True)
def _cleanup_editor_state():
    yield
    for did in [d.id for d in sop_service._documents.values() if d.user_id == USER_ID]:
        sop_service.delete_document(did)
    for nid in [n.id for n in sop_service._nodes.values() if n.id.startswith("tpl_pub_")]:
        sop_service._nodes.pop(nid, None)
        sop_service._templates.pop(nid, None)
    sop_service._review_queue.clear()


@pytest.fixture
def passing_moderation(monkeypatch):
    """Make the publish-review moderation gate always pass (hermetic tests)."""
    import importlib
    cg_module = importlib.import_module("src.infrastructure.external_gateway.content_moderation_gateway")

    async def _pass(content: str, field_name: str = "content"):
        return {"verdict": "CONFIRMED_SAFE", "passed": True, "external_scan_used": False,
                "external_unavailable": False, "nlp": {}, "external": {}}

    monkeypatch.setattr(cg_module, "prescreen_and_scan", _pass)


def _draft(client, **payload):
    return dispatch(client, "sop.document.draft", {"user_id": USER_ID, **payload}, token=EDITOR_TOKEN)


def test_editor_saves_free_form_draft_without_template():
    """A from-scratch document must save even when no template was chosen."""
    client = TestClient(app)
    body = _draft(
        client,
        title="我的第一份声明",
        content="本人承诺所提交材料真实、合法、有效。\n签署人：张创客",
    ).json()

    assert body["code"] == 200
    doc = body["data"]
    assert doc["user_id"] == USER_ID
    assert doc["document_title"] == "我的第一份声明"
    assert "本人承诺" in doc["rendered_content"]
    assert doc["template_id"] == ""
    assert doc["status"] == SOP_DOC_STATUS_READY

    listed = dispatch(client, "sop.document.list", {"user_id": USER_ID}, token=EDITOR_TOKEN).json()["data"]
    assert any(d["id"] == doc["id"] for d in listed)


def test_editor_saves_draft_seeded_from_template():
    """A template only provides provenance/category; the edited text is stored verbatim."""
    client = TestClient(app)
    body = _draft(
        client,
        title="个体工商户设立登记申请书",
        content="个体工商户设立登记申请书\n\n经营者姓名：张创客\n经营范围：软件开发。",
        template_id="tpl_individual_biz_reg",
    ).json()

    assert body["code"] == 200
    doc = body["data"]
    assert doc["template_id"] == "tpl_individual_biz_reg"
    assert doc["category"] == "ENTITY"
    # The editor body wins: no {placeholder} interpolation happens here.
    assert doc["rendered_content"].startswith("个体工商户设立登记申请书")


def test_editor_rejects_empty_content():
    client = TestClient(app)
    body = _draft(client, title="空文书", content="   ").json()
    assert body["code"] != 200
    assert "正文" in body["message"]


def test_editor_updates_existing_draft():
    client = TestClient(app)
    created = _draft(client, title="初稿", content="第一版正文内容。").json()["data"]

    updated = _draft(
        client,
        doc_id=created["id"],
        title="修订稿",
        content="第二版正文内容，已经修改。",
    ).json()["data"]

    assert updated["id"] == created["id"]
    assert updated["document_title"] == "修订稿"
    assert "第二版" in updated["rendered_content"]
    assert sop_service.get_document(created["id"]).rendered_content == "第二版正文内容，已经修改。"


def test_save_and_publish_then_review_promotes_to_catalog(passing_moderation):
    """保存并发布: draft → PENDING_REVIEW → approved → 标准文书库."""
    client = TestClient(app)
    doc = _draft(
        client,
        title="创客发布测试文书",
        content="这是一份由创客通过文本编辑器起草并发布的合规文书正文。",
    ).json()["data"]

    publish = dispatch(client, "sop.document.publish", {"doc_id": doc["id"]}, token=EDITOR_TOKEN).json()
    assert publish["code"] == 200
    assert publish["data"]["status"] == SOP_DOC_STATUS_PENDING_REVIEW

    result = asyncio.run(sop_service.process_review_queue())
    assert result.approved == 1
    assert sop_service.get_document(doc["id"]).status == SOP_DOC_STATUS_PUBLISHED

    item = sop_service.list_review_queue(status=SOP_REVIEW_STATUS_APPROVED).items[0]
    assert "审核通过" in item.review_note

    catalog = sop_service.list_document_cards(user_id=USER_ID)
    assert any(i.id.startswith("tpl_pub_") for i in catalog.items)


def test_editor_frontend_is_a_text_editor_with_template_panel():
    """The drafting page must be an editor with a right-side template library."""
    source = SOP_DOC_PAGE.read_text(encoding="utf-8")

    # 1. A real editable surface + title input.
    assert "sop-doc-editor-textarea" in source
    assert "sop-doc-title-input" in source
    assert "v-model=\"draftContent\"" in source

    # 2. Templates load into the editor rather than replacing the page.
    assert "applyTemplate" in source
    assert "buildEditableContent" in source

    # 3. Both save-to-private and save-and-publish paths exist.
    assert "sop.document.draft" in source
    assert "保存并发布" in source
    assert "sop.document.publish" in source

    # 4. The workspace exposes the drafting entry and the my-docs empty state.
    view = SOP_VIEW.read_text(encoding="utf-8")
    assert "起草新文书" in view


def test_admin_published_document_gets_official_badge(passing_moderation):
    """官方账号发布的文书经审核进入标准文书库后仍保留官方标签。"""
    from conftest import DEFAULT_ADMIN_TOKEN

    client = TestClient(app)
    title = "官方标准文书发布测试"
    doc = dispatch(client, "sop.document.draft", {
        "title": title,
        "content": "本文件由平台官方账号起草并发布，用于统一文书发布契约验证。",
    }, token=DEFAULT_ADMIN_TOKEN).json()["data"]

    try:
        publish = dispatch(client, "sop.document.publish", {"doc_id": doc["id"]},
                           token=DEFAULT_ADMIN_TOKEN).json()
        assert publish["code"] == 200, publish

        result = asyncio.run(sop_service.process_review_queue())
        assert result.approved == 1

        node = next(n for n in sop_service._nodes.values() if n.name == title)
        assert node.is_official is True
        assert node.author_title == "官方发布"
    finally:
        sop_service.delete_document(doc["id"])

