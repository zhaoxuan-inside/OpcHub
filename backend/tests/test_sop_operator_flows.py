"""Operator-kernel v2 flow tests for the SOP domain (合规文书 / 流程模板 / 审核队列).

Every business flow is executed through the declarative scenario assets in
``config/scenarios/sop.yaml``; the legacy service is used only to prove it still
exposes the data/query surface other modules import.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import yaml

from src.core.entity import entity_store
from src.core.microkernel.registry import registry
from src.core.scenario import ensure_scenarios_loaded
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service
from src.domains.sop.entities import ENTITY_SOP_DOCUMENT, ENTITY_SOP_REVIEW_ITEM
from src.domains.sop.service import sop_service

MAKER_CONTEXT = {"user_id": "usr_sop_flow_maker", "user_role": "MAKER", "nickname": "文书创客"}
OTHER_MAKER_CONTEXT = {"user_id": "usr_sop_flow_other", "user_role": "MAKER", "nickname": "路人创客"}
ADMIN_CONTEXT = {"user_id": "usr_sop_flow_admin", "user_role": "ADMIN", "nickname": "平台运营"}
REVIEW_CONTEXT = {"user_id": "review_engine", "user_role": "SYSTEM", "nickname": "审核引擎"}

TEMPLATE_PIPELINE = "OPC_SOP_TEMPLATE_LIST_PIPELINE"
TEMPLATE_PUBLISH_PIPELINE = "OPC_SOP_TEMPLATE_PUBLISH_PIPELINE"
CATALOG_PIPELINE = "OPC_SOP_DOCUMENT_CATALOG_PIPELINE"
GRAPH_PIPELINE = "OPC_SOP_GRAPH_PIPELINE"
NODE_PIPELINE = "OPC_SOP_NODE_CONTEXT_PIPELINE"
FLOW_TEMPLATE_LIST_PIPELINE = "OPC_SOP_FLOW_TEMPLATE_LIST_PIPELINE"
FLOW_TEMPLATE_DETAIL_PIPELINE = "OPC_SOP_FLOW_TEMPLATE_DETAIL_PIPELINE"
FLOW_LIST_PIPELINE = "OPC_SOP_FLOW_LIST_PIPELINE"
MY_FLOW_CARDS_PIPELINE = "OPC_SOP_MY_FLOW_CARDS_PIPELINE"
FLOW_DETAIL_PIPELINE = "OPC_SOP_FLOW_DETAIL_PIPELINE"
FLOW_CREATE_PIPELINE = "OPC_SOP_FLOW_CREATE_PIPELINE"
FLOW_UPDATE_PIPELINE = "OPC_SOP_FLOW_UPDATE_PIPELINE"
FLOW_DELETE_PIPELINE = "OPC_SOP_FLOW_DELETE_PIPELINE"
RENDER_PIPELINE = "OPC_SOP_DOCUMENT_RENDER_PIPELINE"
DRAFT_PIPELINE = "OPC_SOP_DOCUMENT_DRAFT_PIPELINE"
DOCUMENT_MINE_PIPELINE = "OPC_SOP_DOCUMENT_MINE_PIPELINE"
DOCUMENT_DETAIL_PIPELINE = "OPC_SOP_DOCUMENT_DETAIL_PIPELINE"
DOCUMENT_DELETE_PIPELINE = "OPC_SOP_DOCUMENT_DELETE_PIPELINE"
DOCUMENT_PUBLISH_PIPELINE = "OPC_SOP_DOCUMENT_PUBLISH_PIPELINE"
FLOW_PUBLISH_PIPELINE = "OPC_SOP_FLOW_PUBLISH_PIPELINE"
REVIEW_QUEUE_PIPELINE = "OPC_SOP_REVIEW_QUEUE_PIPELINE"
REVIEW_PROCESS_PIPELINE = "OPC_SOP_REVIEW_PROCESS_PIPELINE"
REVIEW_WITHDRAW_PIPELINE = "OPC_SOP_REVIEW_WITHDRAW_PIPELINE"

TEMPLATE_ID = "tpl_oneperson_company_reg"
FORM_DATA = {
    "company_name": "杭州算子内核科技有限公司",
    "capital": "100 万元",
    "owner_name": "张创客",
    "address": "杭州市滨江区江陵路 100 号",
    "biz_scope": "软件开发；人工智能应用软件研发",
    "apply_date": "2026-10-28",
}
LONG_CONTENT = (
    "本人承诺所提交的全部材料真实、合法、有效，并愿意承担由此产生的法律责任。"
    "本文件用于验证算子内核 v2 的文书起草、发布审核与标准目录发布全链路。"
)


async def _run(scenario: str, inputs: dict, context: dict | None = None):
    ensure_scenarios_loaded()
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=inputs,
            context=dict(context or {}),
        )
    )


async def _draft(title: str, content: str = LONG_CONTENT) -> dict:
    """Create a private draft through the scenario asset."""
    res = await _run(DRAFT_PIPELINE, {"title": title, "content": content}, MAKER_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["response"]


async def _publish_document(doc_id: str, context: dict | None = None) -> dict:
    res = await _run(DOCUMENT_PUBLISH_PIPELINE, {"doc_id": doc_id}, context or MAKER_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["review_submission"]


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    for doc_id in [
        doc.get("id")
        for doc in entity_store.adapter(ENTITY_SOP_DOCUMENT).all()
        if str(doc.get("user_id", "")).startswith("usr_sop_flow")
    ]:
        entity_store.delete(ENTITY_SOP_DOCUMENT, {"key": doc_id})
    for flow_id in [
        flow.id for flow in sop_service._flows.values()
        if flow.owner_id.startswith("usr_sop_flow")
    ]:
        sop_service.delete_flow(flow_id)
    for item_id in [
        item.get("id")
        for item in entity_store.adapter(ENTITY_SOP_REVIEW_ITEM).all()
        if str(item.get("author_id", "")).startswith("usr_sop_flow")
    ]:
        entity_store.delete(ENTITY_SOP_REVIEW_ITEM, {"key": item_id})
    for node_id in [
        node_id for node_id in sop_service._nodes
        if node_id.startswith("tpl_pub_") or node_id.startswith("tpl_flow_")
    ]:
        sop_service._nodes.pop(node_id, None)
        sop_service._templates.pop(node_id, None)
    for flow_id in [
        flow_id for flow_id in sop_service._flow_templates if flow_id.startswith("flowpub_")
    ]:
        sop_service._flow_templates.pop(flow_id, None)


# ---------------------------------------------------------------------------
# 1. 文档生成 / 起草 / 快照
# ---------------------------------------------------------------------------
async def test_render_document_interpolates_template_and_persists():
    res = await _run(RENDER_PIPELINE, {"template_id": TEMPLATE_ID, "form_data": FORM_DATA}, MAKER_CONTEXT)
    assert res.status == "SUCCESS", res.error_message

    document = res.final_output["response"]
    assert document["template_id"] == TEMPLATE_ID
    assert document["user_id"] == MAKER_CONTEXT["user_id"]
    assert FORM_DATA["company_name"] in document["document_title"]
    assert FORM_DATA["owner_name"] in document["rendered_content"]
    assert document["form_data"]["verify_serial"].startswith("VER-")
    assert document["status"] == "READY"
    assert document["compliance_passed"] is True

    # The legacy shim must read the same entity the scenario wrote to.
    stored = sop_service.get_document(document["id"])
    assert stored.form_data["biz_scope"] == FORM_DATA["biz_scope"]

    detail = await _run(DOCUMENT_DETAIL_PIPELINE, {"doc_id": document["id"]})
    assert detail.status == "SUCCESS", detail.error_message
    assert detail.final_output["response"]["id"] == document["id"]

    mine = await _run(DOCUMENT_MINE_PIPELINE, {}, MAKER_CONTEXT)
    assert mine.status == "SUCCESS", mine.error_message
    assert document["id"] in [item["id"] for item in mine.final_output["response"]]


async def test_render_document_requires_existing_template():
    res = await _run(
        RENDER_PIPELINE,
        {"template_id": "tpl_not_a_real_template", "form_data": {}},
        MAKER_CONTEXT,
    )
    assert res.status != "SUCCESS"
    assert "模板" in (res.error_message or "")


async def test_render_operator_enforces_required_fields():
    """The pure operator validates required fields; the legacy render asset is lenient."""
    handler = registry.get("calc.sop.render_document")
    template = sop_service.get_template(TEMPLATE_ID)
    with pytest.raises(ValueError) as exc:
        await handler(
            {"params": {}, "args": {"template_id": TEMPLATE_ID, "template": template.model_dump(), "form_data": {}}}
        , {"user_id": MAKER_CONTEXT["user_id"]})
    assert "必填" in str(exc.value)

    lenient = await handler(
        {"params": {"enforce_required": False}, "args": {"template_id": TEMPLATE_ID, "template": template.model_dump(), "form_data": {}}},
        {"user_id": MAKER_CONTEXT["user_id"]},
    )
    assert lenient["missing_fields"]
    assert lenient["document"]["status"] == "READY"


async def test_draft_save_update_and_snapshot_rollback():
    created = await _draft("草稿：一人公司设立声明", "第一版正文内容，用于验证草稿保存。")
    assert created["document_title"] == "草稿：一人公司设立声明"
    assert created["user_id"] == MAKER_CONTEXT["user_id"]
    assert created["status"] == "READY"

    # Update the same draft in place.
    res = await _run(
        DRAFT_PIPELINE,
        {"doc_id": created["id"], "title": "草稿：修订版", "content": LONG_CONTENT},
        MAKER_CONTEXT,
    )
    assert res.status == "SUCCESS", res.error_message
    updated = res.final_output["response"]
    assert updated["id"] == created["id"]
    assert updated["document_title"] == "草稿：修订版"

    # Snapshot / restore is the Saga rollback surface for the draft flow.
    snapshot = sop_service.snapshot_draft(created["id"])
    assert snapshot["document_title"] == "草稿：修订版"
    entity_store.update(ENTITY_SOP_DOCUMENT, {"id": created["id"], "document_title": "被破坏的标题"})
    assert sop_service.restore_draft_snapshot(created["id"], snapshot) is True
    assert sop_service.get_document(created["id"]).document_title == "草稿：修订版"


async def test_draft_rejects_empty_content_and_foreign_document():
    empty = await _run(DRAFT_PIPELINE, {"title": "空文书", "content": "   "}, MAKER_CONTEXT)
    assert empty.status != "SUCCESS"
    assert "正文" in (empty.error_message or "")

    foreign = await _draft("他人草稿")
    stolen = await _run(
        DRAFT_PIPELINE,
        {"doc_id": foreign["id"], "title": "劫持", "content": LONG_CONTENT},
        OTHER_MAKER_CONTEXT,
    )
    assert stolen.status != "SUCCESS"
    assert "本人" in (stolen.error_message or "")


# ---------------------------------------------------------------------------
# 2. 提交审核 / 审核处理 / 撤回
# ---------------------------------------------------------------------------
async def test_submit_document_moves_to_pending_review_and_queues_item():
    doc = await _draft("待审核文书")
    submission = await _publish_document(doc["id"])

    assert submission["status"] == "PENDING_REVIEW"
    assert submission["target_type"] == "DOCUMENT"
    assert submission["target_id"] == doc["id"]
    assert "发布成功" in submission["message"]
    assert sop_service.get_document(doc["id"]).status == "PENDING_REVIEW"

    queue = await _run(REVIEW_QUEUE_PIPELINE, {}, ADMIN_CONTEXT)
    assert queue.status == "SUCCESS", queue.error_message
    queue_data = queue.final_output["response"]
    assert queue_data["pending"] >= 1
    assert doc["id"] in [item["target_id"] for item in queue_data["items"]]

    # A second submission of the same document is rejected by the state guard.
    duplicate = await _run(DOCUMENT_PUBLISH_PIPELINE, {"doc_id": doc["id"]}, MAKER_CONTEXT)
    assert duplicate.status != "SUCCESS"
    assert "审核" in (duplicate.error_message or "")


async def test_review_approve_publishes_document_to_standard_catalog():
    doc = await _draft("待发布标准文书")
    item = (await _publish_document(doc["id"]))["item_id"]

    res = await _run(REVIEW_PROCESS_PIPELINE, {"item_id": item}, REVIEW_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    decision = res.final_output["review_decision"]
    assert decision["status"] == "APPROVED"
    assert decision["published_id"].startswith("tpl_pub_")
    assert res.final_output["approved"] == 1

    assert sop_service.get_document(doc["id"]).status == "PUBLISHED"
    assert decision["published_id"] in sop_service._nodes
    catalog = await _run(CATALOG_PIPELINE, {}, MAKER_CONTEXT)
    assert decision["published_id"] in [card["id"] for card in catalog.final_output["response"]["items"]]

    queue = sop_service.list_review_queue()
    assert queue.approved >= 1
    assert any("审核通过" in (reviewed.review_note or "") for reviewed in queue.items)

    # Re-processing the same item is an illegal transition.
    again = await _run(REVIEW_PROCESS_PIPELINE, {"item_id": item}, REVIEW_CONTEXT)
    assert again.status != "SUCCESS"


async def test_review_rejects_flow_with_missing_node():
    created = await _run(
        FLOW_CREATE_PIPELINE,
        {
            "name": f"失效节点流程 {uuid.uuid4().hex[:6]}",
            "description": "引用了不存在的流程节点",
            "node_refs": [{"node_id": "tpl_does_not_exist"}],
        },
        MAKER_CONTEXT,
    )
    assert created.status == "SUCCESS", created.error_message
    flow = created.final_output["response"]

    published = await _run(FLOW_PUBLISH_PIPELINE, {"flow_id": flow["id"]}, MAKER_CONTEXT)
    assert published.status == "SUCCESS", published.error_message
    item = published.final_output["review_submission"]["item_id"]

    res = await _run(REVIEW_PROCESS_PIPELINE, {"item_id": item}, REVIEW_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    decision = res.final_output["review_decision"]
    assert decision["status"] == "REJECTED"
    assert "失效节点" in decision["review_note"]
    assert sop_service.get_flow(flow["id"]).status == "REJECTED"


async def test_review_rejects_sensitive_content():
    doc = await _draft("可疑资金通道说明", "本文件介绍如何通过境外账户完成洗钱操作，并规避监管。")
    item = (await _publish_document(doc["id"]))["item_id"]

    res = await _run(REVIEW_PROCESS_PIPELINE, {"item_id": item}, REVIEW_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    decision = res.final_output["review_decision"]
    assert decision["status"] == "REJECTED"
    assert "敏感词" in decision["review_note"]
    assert sop_service.get_document(doc["id"]).status == "REJECTED"


async def test_review_withdraw_returns_document_to_editable_state():
    doc = await _draft("待撤回文书")
    item = (await _publish_document(doc["id"]))["item_id"]

    res = await _run(REVIEW_WITHDRAW_PIPELINE, {"item_id": item}, MAKER_CONTEXT)
    assert res.status == "SUCCESS", res.error_message
    decision = res.final_output["review_decision"]
    assert decision["status"] == "WITHDRAWN"
    assert sop_service.get_document(doc["id"]).status == "READY"

    # A withdrawn submission cannot be processed again.
    processed = await _run(REVIEW_PROCESS_PIPELINE, {"item_id": item}, REVIEW_CONTEXT)
    assert processed.status != "SUCCESS"


async def test_review_consumer_executes_the_process_pipeline():
    doc = await _draft("后台消费者验证文书")
    await _publish_document(doc["id"])

    result = await sop_service.process_review_queue()
    assert result.processed >= 1
    assert result.approved >= 1
    assert doc["id"] in result.published_documents
    assert sop_service.get_document(doc["id"]).status == "PUBLISHED"
    assert sop_service.review_consumer_status()["pipeline"] == REVIEW_PROCESS_PIPELINE


# ---------------------------------------------------------------------------
# 3. 流程 CRUD / 目录
# ---------------------------------------------------------------------------
async def test_flow_crud_round_trip():
    created = await _run(
        FLOW_CREATE_PIPELINE,
        {
            "name": "一人公司设立全流程",
            "description": "从主体登记到对公账户开户。",
            "node_refs": [
                {"node_id": TEMPLATE_ID},
                {"node_id": "tpl_bank_account_opening"},
            ],
        },
        MAKER_CONTEXT,
    )
    assert created.status == "SUCCESS", created.error_message
    flow = created.final_output["response"]
    assert flow["owner_id"] == MAKER_CONTEXT["user_id"]
    assert flow["status"] == "ACTIVE"

    detail = await _run(FLOW_DETAIL_PIPELINE, {"flow_id": flow["id"]})
    assert detail.status == "SUCCESS", detail.error_message
    assert [item["node_id"] for item in detail.final_output["response"]["items"]] == [
        TEMPLATE_ID,
        "tpl_bank_account_opening",
    ]

    listed = await _run(FLOW_LIST_PIPELINE, {}, MAKER_CONTEXT)
    assert listed.status == "SUCCESS", listed.error_message
    assert flow["id"] in [item["id"] for item in listed.final_output["response"]]

    cards = await _run(MY_FLOW_CARDS_PIPELINE, {}, MAKER_CONTEXT)
    assert cards.status == "SUCCESS", cards.error_message
    card = next(item for item in cards.final_output["response"] if item["id"] == flow["id"])
    assert card["step_count"] == 2

    updated = await _run(
        FLOW_UPDATE_PIPELINE,
        {"flow_id": flow["id"], "name": "一人公司设立全流程（修订）", "node_refs": [{"node_id": TEMPLATE_ID}]},
        MAKER_CONTEXT,
    )
    assert updated.status == "SUCCESS", updated.error_message
    assert updated.final_output["response"]["name"] == "一人公司设立全流程（修订）"

    deleted = await _run(FLOW_DELETE_PIPELINE, {"flow_id": flow["id"]}, MAKER_CONTEXT)
    assert deleted.status == "SUCCESS", deleted.error_message
    assert deleted.final_output["deleted"] is True
    with pytest.raises(KeyError):
        sop_service.get_flow(flow["id"])


async def test_flow_update_rejects_other_owners():
    created = await _run(
        FLOW_CREATE_PIPELINE,
        {"name": "他人流程", "description": "用于越权校验的流程"},
        MAKER_CONTEXT,
    )
    flow = created.final_output["response"]

    res = await _run(
        FLOW_UPDATE_PIPELINE,
        {"flow_id": flow["id"], "name": "越权修改"},
        OTHER_MAKER_CONTEXT,
    )
    assert res.status != "SUCCESS"
    assert "权限" in (res.error_message or "")


async def test_template_publish_joins_template_catalog_and_graph():
    code = f"SMOKE_{uuid.uuid4().hex[:6].upper()}"
    res = await _run(
        TEMPLATE_PUBLISH_PIPELINE,
        {
            "stage": 2,
            "code": code,
            "name": "跨境结算账户开立指引",
            "category": "FINANCE",
            "description": "面向跨境创客的结算账户开立与材料清单指引。",
            "template_content": "开户主体：{company_name}\n经办人：{owner_name}",
            "required_fields": [{"key": "company_name", "label": "主体名称"}],
        },
        ADMIN_CONTEXT,
    )
    assert res.status == "SUCCESS", res.error_message
    template = res.final_output["response"]
    assert template["id"].startswith("tpl_")
    assert template["code"] == code

    catalog = await _run(TEMPLATE_PIPELINE, {}, MAKER_CONTEXT)
    assert catalog.status == "SUCCESS", catalog.error_message
    assert template["id"] in [item["id"] for item in catalog.final_output["response"]["templates"]]
    assert catalog.final_output["response"]["stages"]

    graph = await _run(GRAPH_PIPELINE, {})
    assert graph.status == "SUCCESS", graph.error_message
    assert template["id"] in [node["id"] for node in graph.final_output["response"]["nodes"]]


# ---------------------------------------------------------------------------
# 4. 目录 / 图谱读取
# ---------------------------------------------------------------------------
async def test_flow_template_catalog_and_detail():
    catalog = await _run(FLOW_TEMPLATE_LIST_PIPELINE, {}, MAKER_CONTEXT)
    assert catalog.status == "SUCCESS", catalog.error_message
    items = catalog.final_output["response"]["items"]
    assert items, "conftest must seed representative flow templates"
    assert all("step_count" in item for item in items)

    detail = await _run(FLOW_TEMPLATE_DETAIL_PIPELINE, {"flow_id": items[0]["id"]})
    assert detail.status == "SUCCESS", detail.error_message
    assert detail.final_output["response"]["template"]["id"] == items[0]["id"]
    assert detail.final_output["response"]["steps"]

    missing = await _run(FLOW_TEMPLATE_DETAIL_PIPELINE, {"flow_id": "flow_not_real"})
    assert missing.status != "SUCCESS"


async def test_node_context_lists_children_and_prerequisites():
    graph = await _run(GRAPH_PIPELINE, {})
    nodes = graph.final_output["response"]["nodes"]
    subgraph = next(node for node in nodes if node["kind"] == "subgraph")

    res = await _run(NODE_PIPELINE, {"node_id": subgraph["id"]})
    assert res.status == "SUCCESS", res.error_message
    context = res.final_output["response"]
    assert context["node"]["id"] == subgraph["id"]
    assert len(context["children"]) == len(subgraph["children"])

    unknown = await _run(NODE_PIPELINE, {"node_id": "tpl_not_a_real_node"})
    assert unknown.status != "SUCCESS"


# ---------------------------------------------------------------------------
# 5. 关键失败：未登录 / 越权 / 非法状态
# ---------------------------------------------------------------------------
async def test_authenticated_identity_is_required_for_writes():
    res = await _run(DRAFT_PIPELINE, {"title": "匿名草稿", "content": LONG_CONTENT}, {})
    assert res.status == "GUARD_REJECTED"
    assert "登录" in (res.error_message or "")


async def test_publishing_someone_elses_document_is_rejected():
    doc = await _draft("本人私有文书")
    res = await _run(DOCUMENT_PUBLISH_PIPELINE, {"doc_id": doc["id"]}, OTHER_MAKER_CONTEXT)
    assert res.status != "SUCCESS"
    assert "权限" in (res.error_message or "")


async def test_deleting_a_missing_document_reports_not_found():
    res = await _run(DOCUMENT_DELETE_PIPELINE, {"doc_id": f"doc_{uuid.uuid4().hex[:12]}"}, MAKER_CONTEXT)
    assert res.status != "SUCCESS"
    assert "不存在" in (res.error_message or "")


async def test_malformed_review_transition_is_rejected():
    handler = registry.get("calc.sop.review_transition")
    with pytest.raises(ValueError) as exc:
        await handler(
            {"params": {}, "args": {"current": "APPROVED", "action": "APPROVE", "target_type": "DOCUMENT"}},
            {},
        )
    assert "不允许" in str(exc.value)


# ---------------------------------------------------------------------------
# 6. Route asset
# ---------------------------------------------------------------------------
def test_route_asset_maps_every_sop_gateway():
    route_file = Path(__file__).resolve().parents[1] / "config" / "routes" / "sop.yaml"
    payload = yaml.safe_load(route_file.read_text(encoding="utf-8"))
    mapping = {entry["gateway"]: entry["pipeline"] for entry in payload["routes"]}
    assert mapping == {
        "sop.templates": TEMPLATE_PIPELINE,
        "sop.template.publish": TEMPLATE_PUBLISH_PIPELINE,
        "sop.documents": CATALOG_PIPELINE,
        "sop.graph": GRAPH_PIPELINE,
        "sop.node": NODE_PIPELINE,
        "sop.flow.templates": FLOW_TEMPLATE_LIST_PIPELINE,
        "sop.flow.template.detail": FLOW_TEMPLATE_DETAIL_PIPELINE,
        "sop.flow.list": FLOW_LIST_PIPELINE,
        "sop.myflow.cards": MY_FLOW_CARDS_PIPELINE,
        "sop.flow.get": FLOW_DETAIL_PIPELINE,
        "sop.flow.create": FLOW_CREATE_PIPELINE,
        "sop.flow.update": FLOW_UPDATE_PIPELINE,
        "sop.flow.delete": FLOW_DELETE_PIPELINE,
        "sop.flow.publish": FLOW_PUBLISH_PIPELINE,
        "sop.document.render": RENDER_PIPELINE,
        "sop.document.draft": DRAFT_PIPELINE,
        "sop.document.get": DOCUMENT_DETAIL_PIPELINE,
        "sop.document.list": DOCUMENT_MINE_PIPELINE,
        "sop.document.delete": DOCUMENT_DELETE_PIPELINE,
        "sop.document.publish": DOCUMENT_PUBLISH_PIPELINE,
        "sop.review.queue": REVIEW_QUEUE_PIPELINE,
        "sop.review.process": REVIEW_PROCESS_PIPELINE,
        "sop.review.withdraw": REVIEW_WITHDRAW_PIPELINE,
    }
