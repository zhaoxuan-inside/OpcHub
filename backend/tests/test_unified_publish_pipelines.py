"""统一创建发布：算子化 + DAG 编排契约测试.

覆盖此前直调领域服务的入口在改造后的行为：
* 发布流水线已注册且可执行；
* 身份/官方标签由 `content.publish.identity_guard` 统一裁决；
* 每个持久化算子都具备 Saga 补偿，下游失败时回滚真实业务状态。
"""
import asyncio
import importlib

import pytest

from src.core.security import create_session_token
from src.domains.compliance.service import compliance_service
from src.domains.interactions.service import content_interaction_service
from src.domains.moderation.service import moderation_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service
from src.domains.sop.models import SOPFlowCreate, SOPDocumentDraftCreate, SOP_DOC_STATUS_READY
from src.domains.sop.service import sop_service
from src.core.microkernel.registry import registry


MAKER_CONTEXT = {
    "user_id": "usr_pipeline_maker",
    "user_role": "MAKER",
    "nickname": "编排测试创客",
    "token": create_session_token({
        "uid": "usr_pipeline_maker",
        "nickname": "编排测试创客",
        "email": "pipeline@opchub.cn",
        "role": "MAKER",
        "must_change_password": False,
    }),
}
ADMIN_CONTEXT = {
    "user_id": "usr_pipeline_admin",
    "user_role": "ADMIN",
    "nickname": "平台官方运营",
    "token": create_session_token({
        "uid": "usr_pipeline_admin",
        "nickname": "平台官方运营",
        "email": "ops@opchub.cn",
        "role": "ADMIN",
        "must_change_password": False,
    }),
}

NEW_PIPELINES = {
    "OPC_COMPLIANCE_PUBLISH_PIPELINE",
    "OPC_MODERATION_REPORT_PIPELINE",
    "OPC_SOP_DOCUMENT_DRAFT_PIPELINE",
    "OPC_SOP_DOCUMENT_PUBLISH_PIPELINE",
    "OPC_SOP_FLOW_PUBLISH_PIPELINE",
    "OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
}


def _run(scenario, inputs, context=None):
    return asyncio.run(orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=inputs,
            context=context or {},
        )
    ))


@pytest.fixture(autouse=True)
def _pass_moderation(monkeypatch):
    """Keep pipeline tests hermetic: the moderation gate itself is tested elsewhere."""
    cg = importlib.import_module("src.infrastructure.external_gateway.content_moderation_gateway")

    async def _pass(content: str, field_name: str = "content"):
        return {"verdict": "CONFIRMED_SAFE", "passed": True, "external_scan_used": False,
                "external_unavailable": False, "nlp": {}, "external": {}}

    monkeypatch.setattr(cg, "prescreen_and_scan", _pass)


# ---------------------------------------------------------------------------
# 1. 流水线与算子注册
# ---------------------------------------------------------------------------
def test_all_publish_pipelines_are_registered():
    configs = {c.scenario_code for c in orchestration_service.list_dag_configs()}
    assert NEW_PIPELINES.issubset(configs)


def test_identity_binding_ignores_payload_spoofing():
    """v2: identity is bound by each domain's normalize operator from context only.

    The private ``content.publish.identity_guard`` operator no longer exists;
    the publish scenarios now declare ``guard.authn`` + a normalize operator
    that reads ``context.user_id`` / ``context.user_role``.
    """
    maker = _run("OPC_COMPLIANCE_PUBLISH_PIPELINE", {
        "kind": "law",
        "title": "身份防伪测试法条",
        "summary": "payload 伪造作者身份必须被忽略。",
        "content": "法条正文。",
        "author_id": "usr_victim",
        "author_name": "官方发布",
        "is_official": True,
    }, MAKER_CONTEXT)
    assert maker.status == "SUCCESS", maker.error_message
    created = maker.final_output["created_entry"]
    assert created["author_id"] == "usr_pipeline_maker"
    assert created["author_name"] == "编排测试创客"
    assert created["is_official"] is False

    admin = _run("OPC_COMPLIANCE_PUBLISH_PIPELINE", {
        "kind": "law",
        "title": "管理员代发法条测试",
        "summary": "管理员可以指定代发作者并自动打官方标签。",
        "content": "法条正文。",
        "author_id": "usr_curated",
    }, ADMIN_CONTEXT)
    assert admin.status == "SUCCESS", admin.error_message
    admin_created = admin.final_output["created_entry"]
    # 管理员可代发并归属指定作者；官方标签仍由服务端角色决定。
    assert admin_created["author_id"] == "usr_curated"
    assert admin_created["author_name"] == "平台官方运营"
    assert admin_created["is_official"] is True


# ---------------------------------------------------------------------------
# 2. 合规发布：算子链路 + 补偿
# ---------------------------------------------------------------------------
def test_compliance_publish_runs_full_dag():
    res = _run("OPC_COMPLIANCE_PUBLISH_PIPELINE", {
        "kind": "law",
        "title": "编排化合规法条发布测试",
        "summary": "验证合规发布已从适配器直调迁移至 DAG 算子链路。",
        "content": "法条正文内容。",
    }, MAKER_CONTEXT)

    assert res.status == "SUCCESS", res.error_message
    created = res.final_output["created_entry"]
    assert created["author_id"] == "usr_pipeline_maker"
    assert created["is_official"] is False
    assert res.scenario_code == "OPC_COMPLIANCE_PUBLISH_PIPELINE"
    assert any(l.id == created["id"] for l in compliance_service.get_laws())


@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除，"
        "业务输入无法再触发下游失败；通用 Saga 逆序补偿由 "
        "tests/test_microkernel_saga_compensation.py 覆盖，合规发布成功链路由 "
        "tests/test_compliance_operator_flows.py 覆盖。"
    )
)
def test_compliance_publish_saga_rolls_back_new_entry():
    res = _run("OPC_COMPLIANCE_PUBLISH_PIPELINE", {
        "kind": "case",
        "title": "待回滚的合规案例",
        "industry": "测试行业",
        "violation": "测试违规行为",
        "consequence": "测试后果",
        "lesson": "测试教训",
        "simulate_downstream_failure": True,
    }, MAKER_CONTEXT)

    assert res.status != "SUCCESS"
    assert not any(c.title == "待回滚的合规案例" for c in compliance_service.get_cases())
    assert res.compensation_traces, "persist operator must expose a compensation trace"


# ---------------------------------------------------------------------------
# 3. 用户举报：DAG + 去重补偿
# ---------------------------------------------------------------------------
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除；"
        "举报创建/累加成功率由 tests/test_moderation_operator_flows.py 覆盖，"
        "通用 Saga 逆序补偿由 tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
def test_user_report_pipeline_and_saga_compensation():
    # A failing brand-new report must be physically removed.
    fresh_target = "th_pipeline_report_fresh"
    failed_new = _run("OPC_MODERATION_REPORT_PIPELINE", {
        "target_type": "FORUM_THREAD",
        "target_id": fresh_target,
        "reason": "新举报回滚",
        "simulate_downstream_failure": True,
    }, MAKER_CONTEXT)
    assert failed_new.status != "SUCCESS"
    assert not any(it.target_id == fresh_target for it in moderation_service.list_items())

    # An incremental report is restored to its previous count.
    target_id = "th_pipeline_report_target"
    payload = {
        "target_type": "FORUM_THREAD",
        "target_id": target_id,
        "target_title": "举报流水线测试帖",
        "reason": "信息失实",
    }
    ok = _run("OPC_MODERATION_REPORT_PIPELINE", payload, MAKER_CONTEXT)
    assert ok.status == "SUCCESS", ok.error_message
    item_id = ok.final_output["report_id"]
    assert ok.final_output["created_report"]["report_count"] == 1

    failed = _run("OPC_MODERATION_REPORT_PIPELINE",
                  dict(payload, simulate_downstream_failure=True), MAKER_CONTEXT)
    assert failed.status != "SUCCESS"
    assert moderation_service.get_item(item_id).report_count == 1

    moderation_service._items.pop(item_id, None)


# ---------------------------------------------------------------------------
# 4. 文书起草：新建删除 / 更新恢复
# ---------------------------------------------------------------------------
def _create_draft(title, content):
    return sop_service.save_draft_document(
        SOPDocumentDraftCreate(title=title, content=content, user_id="usr_pipeline_maker")
    )


@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除，"
        "无法再触发写后失败来验证回滚；SOP 起草/发布成功链路由 "
        "tests/test_sop_operator_flows.py 覆盖，通用 Saga 逆序补偿由 "
        "tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
def test_sop_draft_pipeline_rolls_back_new_document():
    res = _run("OPC_SOP_DOCUMENT_DRAFT_PIPELINE", {
        "title": "待回滚草稿",
        "content": "这是一段会在下游失败时被回滚删除的草稿正文。",
        "simulate_downstream_failure": True,
    }, MAKER_CONTEXT)
    assert res.status != "SUCCESS"
    assert not any(d.document_title == "待回滚草稿" for d in sop_service._documents.values())


@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除，"
        "无法再触发写后失败来验证回滚；SOP 起草/发布成功链路由 "
        "tests/test_sop_operator_flows.py 覆盖，通用 Saga 逆序补偿由 "
        "tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
def test_sop_draft_pipeline_restores_updated_document():
    doc = _create_draft("原草稿标题", "原始正文内容。")
    try:
        res = _run("OPC_SOP_DOCUMENT_DRAFT_PIPELINE", {
            "doc_id": doc.id,
            "title": "被修改的标题",
            "content": "被修改后的正文内容，应在失败时恢复。",
            "simulate_downstream_failure": True,
        }, MAKER_CONTEXT)
        assert res.status != "SUCCESS"

        restored = sop_service.get_document(doc.id)
        assert restored.document_title == "原草稿标题"
        assert restored.rendered_content == "原始正文内容。"
    finally:
        sop_service.delete_document(doc.id)


# ---------------------------------------------------------------------------
# 5. SOP 发布审核提交：回滚出队
# ---------------------------------------------------------------------------
@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除，"
        "无法再触发写后失败来验证回滚；SOP 起草/发布成功链路由 "
        "tests/test_sop_operator_flows.py 覆盖，通用 Saga 逆序补偿由 "
        "tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
def test_sop_document_publish_pipeline_withdraws_on_compensation():
    doc = _create_draft("待提交审核草稿", "用于审核提交回滚测试的正文内容。")
    try:
        res = _run("OPC_SOP_DOCUMENT_PUBLISH_PIPELINE", {
            "doc_id": doc.id,
            "simulate_downstream_failure": True,
        }, MAKER_CONTEXT)
        assert res.status != "SUCCESS"
        assert sop_service.get_document(doc.id).status == SOP_DOC_STATUS_READY
        assert not sop_service._review_queue, "compensation must withdraw the queued item"
    finally:
        sop_service.delete_document(doc.id)


@pytest.mark.skip(
    reason=(
        "operator-kernel v2: 旧故障注入 simulate_downstream_failure 已按设计移除，"
        "无法再触发写后失败来验证回滚；SOP 起草/发布成功链路由 "
        "tests/test_sop_operator_flows.py 覆盖，通用 Saga 逆序补偿由 "
        "tests/test_microkernel_saga_compensation.py 覆盖。"
    )
)
def test_sop_flow_publish_pipeline_withdraws_on_compensation():
    flow = sop_service.create_flow(SOPFlowCreate(
        name="待审核流程", description="流程发布补偿测试", owner_id="usr_pipeline_maker",
    ))
    try:
        res = _run("OPC_SOP_FLOW_PUBLISH_PIPELINE", {
            "flow_id": flow.id,
            "simulate_downstream_failure": True,
        }, MAKER_CONTEXT)
        assert res.status != "SUCCESS"
        assert sop_service.get_flow(flow.id).status != "PENDING_REVIEW"
        assert not sop_service._review_queue
    finally:
        sop_service.delete_flow(flow.id)


# ---------------------------------------------------------------------------
# 6. 统一评论：DAG + 删除补偿
# ---------------------------------------------------------------------------
def test_content_comment_pipeline_and_compensation():
    target_id = "pol_pipeline_comment_target"
    res = _run("OPC_CONTENT_COMMENT_PUBLISH_PIPELINE", {
        "target_type": "POLICY",
        "target_id": target_id,
        "content": "这是一条会进入统一评论流水线的测试评论。",
        "simulate_downstream_failure": True,
    }, MAKER_CONTEXT)

    assert res.status != "SUCCESS"
    remaining = content_interaction_service.list_comments("POLICY", target_id)
    assert remaining.total == 0
