"""Tests for the publish-review pipeline of private documents & flows.

A maker publishes a private document / flow by submitting it for review:
the item enters PENDING_REVIEW (待审核) and is added to the backend review
queue. A consumer audits legality / compliance / sensitive words; approved
items are promoted into the standard document catalog (标准文书库) and the
flow guide (流程向导).
"""
import asyncio
import pytest
from fastapi.testclient import TestClient

from src.main import app
from conftest import dispatch
from src.domains.sop.models import (
    SOPDocumentCreate,
    SOPFlowCreate,
    SOPFlowNodeRef,
    SOP_DOC_STATUS_READY,
    SOP_DOC_STATUS_PENDING_REVIEW,
    SOP_DOC_STATUS_PUBLISHED,
    SOP_DOC_STATUS_REJECTED,
    SOP_FLOW_STATUS_ACTIVE,
    SOP_FLOW_STATUS_PENDING_REVIEW,
    SOP_FLOW_STATUS_PUBLISHED,
    SOP_FLOW_STATUS_REJECTED,
    SOP_REVIEW_STATUS_PENDING,
    SOP_REVIEW_STATUS_APPROVED,
    SOP_REVIEW_STATUS_REJECTED,
    SOP_REVIEW_TARGET_DOCUMENT,
    SOP_REVIEW_TARGET_FLOW,
)
from src.domains.sop.service import sop_service


@pytest.fixture(autouse=True)
def _cleanup_sop_review_state():
    yield
    # Remove published artifacts and queued items created during the tests.
    for nid in [n.id for n in sop_service._nodes.values() if n.id.startswith("tpl_pub_")]:
        sop_service._nodes.pop(nid, None)
        sop_service._templates.pop(nid, None)
    for fid in [f.id for f in sop_service._flow_templates.values() if f.id.startswith("flowpub_")]:
        sop_service._flow_templates.pop(fid, None)
    for did in [d.id for d in sop_service._documents.values() if d.user_id.startswith("usr_review")]:
        sop_service.delete_document(did)
    for fid in [f.id for f in sop_service._flows.values() if f.owner_id.startswith("usr_review")]:
        sop_service.delete_flow(fid)
    sop_service._review_queue.clear()


@pytest.fixture
def passing_moderation(monkeypatch):
    """Make the content-moderation gate always pass (hermetic tests)."""
    import importlib
    cg_module = importlib.import_module("src.infrastructure.external_gateway.content_moderation_gateway")
    async def _pass(content: str, field_name: str = "content"):
        return {"verdict": "CONFIRMED_SAFE", "passed": True, "external_scan_used": False,
                "external_unavailable": False, "nlp": {}, "external": {}}
    monkeypatch.setattr(cg_module, "prescreen_and_scan", _pass)


@pytest.fixture
def blocking_moderation(monkeypatch):
    """Make the content-moderation gate always reject (hermetic tests)."""
    import importlib
    cg_module = importlib.import_module("src.infrastructure.external_gateway.content_moderation_gateway")
    async def _block(content: str, field_name: str = "content"):
        raise ValueError("Content moderation violation: found prohibited keywords")
    monkeypatch.setattr(cg_module, "prescreen_and_scan", _block)


def _make_doc(user_id="usr_review_doc", company="杭州极速微光科技有限公司"):
    return sop_service.render_and_save_document(SOPDocumentCreate(
        template_id="tpl_oneperson_company_reg",
        user_id=user_id,
        form_data={"company_name": company, "founder_name": "张创客"},
    ))


def _make_flow(user_id="usr_review_flow", name="一人公司设立全流程"):
    return sop_service.create_flow(SOPFlowCreate(
        name=name,
        description="从主体登记到对公账户的完整办理路径",
        owner_id=user_id,
        node_refs=[
            SOPFlowNodeRef(node_id="tpl_oneperson_company_reg"),
            SOPFlowNodeRef(node_id="tpl_bank_account_opening"),
        ],
    ))


def _process():
    """Run the async review-queue consumer from a synchronous test."""
    return asyncio.run(sop_service.process_review_queue())


# ---------------------------------------------------------------------------
# Submission: 我的文书 / 我的流程 → 待审核 + review queue
# ---------------------------------------------------------------------------

def test_publish_document_enters_pending_review_and_queue():
    doc = _make_doc()
    assert doc.status == SOP_DOC_STATUS_READY

    resp = sop_service.submit_document_for_review(doc.id, "usr_review_doc")
    assert resp.status == SOP_DOC_STATUS_PENDING_REVIEW
    assert resp.target_type == SOP_REVIEW_TARGET_DOCUMENT
    assert "发布成功" in resp.message

    # The source document is now 待审核.
    assert sop_service.get_document(doc.id).status == SOP_DOC_STATUS_PENDING_REVIEW

    # A review item sits in the backend queue.
    queue = sop_service.list_review_queue()
    assert queue.pending == 1
    item = queue.items[0]
    assert item.target_id == doc.id
    assert item.status == SOP_REVIEW_STATUS_PENDING
    assert item.author_id == "usr_review_doc"


def test_publish_flow_enters_pending_review_and_queue():
    flow = _make_flow()
    assert flow.status == SOP_FLOW_STATUS_ACTIVE

    resp = sop_service.submit_flow_for_review(flow.id, "usr_review_flow")
    assert resp.status == SOP_FLOW_STATUS_PENDING_REVIEW
    assert resp.target_type == SOP_REVIEW_TARGET_FLOW
    assert "发布成功" in resp.message

    assert sop_service.get_flow(flow.id).status == SOP_FLOW_STATUS_PENDING_REVIEW
    queue = sop_service.list_review_queue()
    assert queue.pending == 1
    assert queue.items[0].target_id == flow.id


def test_publish_document_requires_owner():
    doc = _make_doc(user_id="usr_review_owner")
    with pytest.raises(ValueError):
        sop_service.submit_document_for_review(doc.id, "usr_someone_else")


def test_duplicate_publish_is_blocked():
    doc = _make_doc()
    sop_service.submit_document_for_review(doc.id, "usr_review_doc")
    with pytest.raises(ValueError):
        sop_service.submit_document_for_review(doc.id, "usr_review_doc")


def test_empty_document_cannot_be_published():
    doc = _make_doc()
    doc.rendered_content = ""
    with pytest.raises(ValueError):
        sop_service.submit_document_for_review(doc.id, "usr_review_doc")


# ---------------------------------------------------------------------------
# Queue consumption: 合法性 / 合规性 / 敏感词 → 发布到标准文书 & 流程向导
# ---------------------------------------------------------------------------

def test_process_queue_publishes_document_to_standard_catalog(passing_moderation):
    doc = _make_doc()
    sop_service.submit_document_for_review(doc.id, "usr_review_doc")

    result = _process()
    assert result.processed == 1
    assert result.approved == 1
    assert result.rejected == 0
    assert doc.id in result.published_documents

    # Source document is marked PUBLISHED.
    assert sop_service.get_document(doc.id).status == SOP_DOC_STATUS_PUBLISHED

    # The document now appears in the 标准文书库 with maker provenance.
    catalog = sop_service.list_document_cards(user_id="usr_review_doc")
    published = next(i for i in catalog.items if i.id.startswith("tpl_pub_"))
    assert published.publisher_org == "创客发布"
    assert published.author_name == "创客"
    assert published.is_official is False
    assert published.published_at

    # Review item is APPROVED with a note.
    item = sop_service.list_review_queue(status=SOP_REVIEW_STATUS_APPROVED).items[0]
    assert "审核通过" in item.review_note
    assert item.reviewed_at


def test_process_queue_publishes_flow_to_flow_guide(passing_moderation):
    flow = _make_flow()
    sop_service.submit_flow_for_review(flow.id, "usr_review_flow")

    result = _process()
    assert result.processed == 1
    assert result.approved == 1
    assert flow.id in result.published_flows

    assert sop_service.get_flow(flow.id).status == SOP_FLOW_STATUS_PUBLISHED

    # The flow now appears in the 流程向导 catalog.
    catalog = sop_service.list_flow_template_cards(user_id="usr_review_flow")
    published = next(i for i in catalog.items if i.id.startswith("flowpub_"))
    assert published.name == "一人公司设立全流程"
    assert published.step_count == 2
    assert published.publisher_org == "创客发布"
    assert published.is_official is False

    item = sop_service.list_review_queue(status=SOP_REVIEW_STATUS_APPROVED).items[0]
    assert "审核通过" in item.review_note


def test_process_queue_rejects_sensitive_document(blocking_moderation):
    doc = _make_doc()
    sop_service.submit_document_for_review(doc.id, "usr_review_doc")

    result = _process()
    assert result.processed == 1
    assert result.rejected == 1
    assert result.approved == 0

    # Source document is marked REJECTED and is NOT in the standard catalog.
    assert sop_service.get_document(doc.id).status == SOP_DOC_STATUS_REJECTED
    catalog = sop_service.list_document_cards(user_id="usr_review_doc")
    assert not any(i.id.startswith("tpl_pub_") for i in catalog.items)

    item = sop_service.list_review_queue(status=SOP_REVIEW_STATUS_REJECTED).items[0]
    assert "审核未通过" in item.review_note
    assert "敏感词" in item.review_note or "prohibited" in item.review_note


def test_process_queue_rejects_flow_with_missing_node(passing_moderation):
    flow = sop_service.create_flow(SOPFlowCreate(
        name="失效节点流程",
        description="引用了不存在的节点",
        owner_id="usr_review_flow",
        node_refs=[SOPFlowNodeRef(node_id="tpl_does_not_exist")],
    ))
    sop_service.submit_flow_for_review(flow.id, "usr_review_flow")

    result = _process()
    assert result.rejected == 1
    assert sop_service.get_flow(flow.id).status == SOP_FLOW_STATUS_REJECTED
    item = sop_service.list_review_queue(status=SOP_REVIEW_STATUS_REJECTED).items[0]
    assert "失效节点" in item.review_note


def test_queue_status_breakdown(passing_moderation):
    good_doc = _make_doc(user_id="usr_review_doc")
    bad_flow = _make_flow(user_id="usr_review_flow", name="待拒绝流程")
    sop_service.submit_document_for_review(good_doc.id, "usr_review_doc")
    sop_service.submit_flow_for_review(bad_flow.id, "usr_review_flow")

    # Force the flow's content through the pass gate too, then process all.
    result = _process()
    assert result.processed == 2
    assert result.approved == 2

    queue = sop_service.list_review_queue()
    assert queue.total == 2
    assert queue.pending == 0
    assert queue.approved == 2
    assert queue.rejected == 0


# ---------------------------------------------------------------------------
# Gateway scenarios (single-entry architecture)
# ---------------------------------------------------------------------------

def test_gateway_publish_document_and_consume_queue(passing_moderation):
    client = TestClient(app)
    doc = _make_doc(user_id="usr_admin_builtin")

    # Publish → success envelope + PENDING_REVIEW state.
    resp = dispatch(client, "sop.document.publish", {"doc_id": doc.id})
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["status"] == SOP_DOC_STATUS_PENDING_REVIEW
    assert "发布成功" in body["data"]["message"]

    # The queued submission is visible to the audit endpoint.
    queue = dispatch(client, "sop.review.queue", {}).json()["data"]
    assert queue["pending"] == 1
    assert queue["items"][0]["target_id"] == doc.id

    # Consume the queue and confirm promotion into the standard catalog.
    process = dispatch(client, "sop.review.process", {}).json()["data"]
    assert process["approved"] == 1
    assert process["rejected"] == 0

    catalog = dispatch(client, "sop.documents", {}).json()["data"]["items"]
    assert any(item["id"].startswith("tpl_pub_") for item in catalog)


def test_gateway_publish_flow_and_owner_enforcement():
    client = TestClient(app)
    # A maker's own flow (the gateway injects the session identity) publishes fine.
    own_flow = _make_flow(user_id="usr_admin_builtin", name="网关发布流程")
    resp = dispatch(client, "sop.flow.publish", {"flow_id": own_flow.id})
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["status"] == SOP_FLOW_STATUS_PENDING_REVIEW

    # Publishing someone else's flow is blocked by the owner check.
    others_flow = _make_flow(user_id="usr_review_other", name="他人流程")
    blocked = dispatch(client, "sop.flow.publish", {"flow_id": others_flow.id}).json()
    assert blocked["code"] == 400
    assert "本人创建" in blocked["message"]


@pytest.mark.asyncio
async def test_background_review_consumer_starts_and_stops():
    assert sop_service.review_consumer_status()["running"] is False
    sop_service.start_review_consumer(interval=1.0)
    assert sop_service.review_consumer_status()["running"] is True
    sop_service.stop_review_consumer()
    assert sop_service.review_consumer_status()["running"] is False
