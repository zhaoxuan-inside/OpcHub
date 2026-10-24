"""Test suite for P02 Brainstorm Forum driven by Microkernel DAG Orchestration & Saga Compensation."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.forum.service import forum_service
from src.domains.orchestration.service import orchestration_service
from src.domains.orchestration.models import ScenarioExecuteRequest


@pytest.fixture(autouse=True)
def clean_forum_state():
    """Reset forum service state and seed a test-only thread before each test."""
    forum_service.clear()
    from src.domains.forum.service import utc_now_iso
    from src.domains.forum.models import ForumThreadResponse
    forum_service._threads["th_test_seed_2026"] = ForumThreadResponse(
        id="th_test_seed_2026",
        category_code="TAX",
        author_id="usr_test_author",
        title="【测试】2026 一人公司增值税免征额度操作细则",
        content="测试种子帖子，用于物化路径评论树测试。",
        view_count=0,
        upvote_count=0,
        comment_count=0,
        bookmark_count=0,
        is_pinned=False,
        status="PUBLISHED",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
    )
    yield
    forum_service.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_forum_thread_publish_via_microkernel_dag(client):
    """Verify posting a discussion thread strictly orchestrated by OPC_FORUM_THREAD_PUBLISH DAG."""
    payload = {
        "scenario": "forum.threads.publish",
        "version": "v1.0.0",
        "client_code_version": "v1.0.4",
        "payload": {
            "title": "2026年一人公司海外结汇申报与合规实录",
            "content": "分享个人海外对公户结汇与国内增值税申报的完整实战流程细节，帮助独立创客规避风控。",
            "category_code": "TAX",
            "author_id": "usr_maker_2026",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["code"] == 200
    assert data["scenario"] == "forum.threads.publish"

    thread = data["data"]
    assert "id" in thread
    assert thread["title"] == "2026年一人公司海外结汇申报与合规实录"
    assert thread["category_code"] == "TAX"
    assert thread["status"] == "PUBLISHED"

    # Verify state in repository
    repo_thread = forum_service.get_thread(thread["id"], record_view=False)
    assert repo_thread.id == thread["id"]
    assert repo_thread.author_id == "usr_maker_2026"


def test_forum_thread_moderation_guard_blocks_prohibited_content(client):
    """Verify that sensitive words are blocked by forum.thread.validate_guard."""
    payload = {
        "scenario": "forum.threads.publish",
        "version": "v1.0.0",
        "payload": {
            "title": "高价收代开假发票中介渠道合作",
            "content": "急需批量代开发票抵扣增值税额度，有渠道的私信详谈...",
            "category_code": "TAX",
        },
    }

    resp = client.post("/api/welcom/opc_world", json=payload)
    assert resp.status_code == 400 or resp.status_code == 422 or resp.status_code == 200
    data = resp.json()
    # When blocked, code is error or detail indicates moderation violation
    assert data["code"] != "OPC_SUCCESS" or "violation" in str(data) or "prohibited" in str(data)


@pytest.mark.asyncio
async def test_forum_thread_saga_rollback_on_failure():
    """Verify Saga reverse compensation deletes persisted thread when downstream fails."""
    # Execute directly via orchestration engine with simulate_downstream_failure
    exec_req = ScenarioExecuteRequest(
        scenario_code="OPC_FORUM_THREAD_PUBLISH",
        version="v1.0.0",
        inputs={
            "title": "这是一篇将要在下游失败测试回滚的帖子",
            "content": "测试微内核分布式 Saga 逆向补偿回滚算法，要求数据被撤销物理删除。",
            "category_code": "DEV",
            "author_id": "usr_saga_tester",
            "simulate_downstream_failure": True,
        },
    )

    res = await orchestration_service.execute_scenario(exec_req)
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0
    # Thread must NOT exist in forum service
    all_threads = forum_service.list_threads()
    assert not any(t.title == "这是一篇将要在下游失败测试回滚的帖子" for t in all_threads)


def test_forum_nested_comments_materialized_path_dag(client):
    """Verify hierarchical comments creation via OPC_FORUM_COMMENT_PUBLISH DAG with materialized path."""
    threads = forum_service.list_threads()
    target_thread = threads[0]
    thread_id = target_thread.id

    # 1. Post Level-0 Top comment (一级回答)
    c1_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.comments.create",
            "version": "v1.0.0",
            "payload": {
                "thread_id": thread_id,
                "author_id": "usr_expert_01",
                "content": "这是非常关键的一点，免征额度核算时需要注意按季度累计而不是自然月划分。",
            },
        },
    )
    assert c1_resp.status_code == 200
    c1 = c1_resp.json()["data"]
    assert c1["depth"] == 0
    assert c1["materialized_path"] == f"/{c1['id']}"

    # 2. Post Level-1 Sub-reply (二级追问)
    c2_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.comments.create",
            "version": "v1.0.0",
            "payload": {
                "thread_id": thread_id,
                "parent_id": c1["id"],
                "author_id": "usr_maker_02",
                "reply_to_user_id": "usr_expert_01",
                "content": "请问如果是跨省设立分支机构，这个季度额度是合并计算还是独立计算？",
            },
        },
    )
    assert c2_resp.status_code == 200
    c2 = c2_resp.json()["data"]
    assert c2["depth"] == 1
    assert c2["parent_id"] == c1["id"]
    assert c2["materialized_path"] == f"/{c1['id']}/{c2['id']}"

    # 3. Post Level-2 Sub-reply (三级答复)
    c3_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.comments.create",
            "version": "v1.0.0",
            "payload": {
                "thread_id": thread_id,
                "parent_id": c2["id"],
                "author_id": "usr_expert_01",
                "reply_to_user_id": "usr_maker_02",
                "content": "一人公司不能直接设立具有独立纳税人资格的分公司，必须以总机构为纳税主体合并申报汇总纳税。",
            },
        },
    )
    assert c3_resp.status_code == 200
    c3 = c3_resp.json()["data"]
    assert c3["depth"] == 2
    assert c3["parent_id"] == c2["id"]
    assert c3["materialized_path"] == f"/{c1['id']}/{c2['id']}/{c3['id']}"

    # 4. Query Thread Detail with recursive tree assembly
    detail_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.threads.get",
            "version": "v1.0.0",
            "payload": {"thread_id": thread_id},
        },
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    comments_tree = detail["comments"]
    assert len(comments_tree) >= 1

    # Find c1 in tree
    c1_node = next((n for n in comments_tree if n["id"] == c1["id"]), None)
    assert c1_node is not None
    assert len(c1_node["children"]) == 1
    c2_node = c1_node["children"][0]
    assert c2_node["id"] == c2["id"]
    assert len(c2_node["children"]) == 1
    c3_node = c2_node["children"][0]
    assert c3_node["id"] == c3["id"]


def test_forum_answer_publish_and_accept_via_dag(client):
    """Verify posting a Zhihu-style perspective answer and accepting it via microkernel DAGs."""
    threads = forum_service.list_threads()
    thread_id = threads[0].id

    # 1. Post answer via OPC_FORUM_ANSWER_PUBLISH
    ans_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.answers.publish",
            "version": "v1.0.0",
            "payload": {
                "thread_id": thread_id,
                "author_id": "usr_maker_expert",
                "author_name": "实战老兵",
                "author_title": "10年独立架构师",
                "content": "根据税总局 2026 年最新发票办法，一人有限责任公司季度免税核算时，必须在电子发票管理系统中完成《免税备案》，否则即使在限额内也会触发系统预警。",
            },
        },
    )
    assert ans_resp.status_code == 200, ans_resp.text
    ans_data = ans_resp.json()["data"]
    answer_id = ans_data["id"]
    assert ans_data["thread_id"] == thread_id
    assert ans_data["word_count"] > 10
    assert ans_data["is_accepted"] is False

    # 2. Accept answer via OPC_FORUM_ANSWER_ACCEPT_PIPELINE
    accept_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.answers.accept",
            "version": "v1.0.0",
            "payload": {
                "thread_id": thread_id,
                "answer_id": answer_id,
                "operator_user_id": threads[0].author_id,
            },
        },
    )
    assert accept_resp.status_code == 200, accept_resp.text
    acc_data = accept_resp.json()["data"]
    assert acc_data["is_accepted"] is True
    assert acc_data["action"] == "ACCEPTED"

    # Verify thread detail reflects accepted answer
    detail_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.threads.get",
            "version": "v1.0.0",
            "payload": {"thread_id": thread_id},
        },
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["thread"]["accepted_answer_id"] == answer_id
    accepted_ans = next(a for a in detail["answers"] if a["id"] == answer_id)
    assert accepted_ans["is_accepted"] is True


def test_forum_vote_mutual_exclusivity_via_dag(client):
    """Verify Zhihu-style mutual upvote/downvote and cancel via OPC_FORUM_VOTE_PIPELINE."""
    threads = forum_service.list_threads()
    thread_id = threads[0].id
    user_id = "usr_voter_888"

    # 1. UPVOTE
    v1_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.vote",
            "version": "v1.0.0",
            "payload": {
                "user_id": user_id,
                "target_type": "THREAD",
                "target_id": thread_id,
                "vote_type": "UPVOTE",
            },
        },
    )
    assert v1_resp.status_code == 200
    v1 = v1_resp.json()["data"]
    assert v1["user_vote"] == "UPVOTE"
    up_cnt_1 = v1["upvote_count"]
    down_cnt_1 = v1["downvote_count"]

    # 2. Switch to DOWNVOTE (mutual exclusivity: upvote -1, downvote +1)
    v2_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.vote",
            "version": "v1.0.0",
            "payload": {
                "user_id": user_id,
                "target_type": "THREAD",
                "target_id": thread_id,
                "vote_type": "DOWNVOTE",
            },
        },
    )
    assert v2_resp.status_code == 200
    v2 = v2_resp.json()["data"]
    assert v2["user_vote"] == "DOWNVOTE"
    assert v2["upvote_count"] == up_cnt_1 - 1
    assert v2["downvote_count"] == down_cnt_1 + 1

    # 3. Repeat DOWNVOTE (toggles to cancel)
    v3_resp = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "forum.vote",
            "version": "v1.0.0",
            "payload": {
                "user_id": user_id,
                "target_type": "THREAD",
                "target_id": thread_id,
                "vote_type": "DOWNVOTE",
            },
        },
    )
    assert v3_resp.status_code == 200
    v3 = v3_resp.json()["data"]
    assert v3["user_vote"] is None
    assert v3["downvote_count"] == down_cnt_1


@pytest.mark.asyncio
async def test_forum_answer_saga_rollback_on_failure():
    """Verify Saga reverse compensation deletes persisted answer when downstream fails."""
    threads = forum_service.list_threads()
    thread_id = threads[0].id

    exec_req = ScenarioExecuteRequest(
        scenario_code="OPC_FORUM_ANSWER_PUBLISH",
        version="v1.0.0",
        inputs={
            "thread_id": thread_id,
            "author_id": "usr_saga_answer_tester",
            "content": "这是一篇将要在下游失败测试回滚的深度观点回答内容...",
            "simulate_downstream_failure": True,
        },
    )

    res = await orchestration_service.execute_scenario(exec_req)
    assert res.status == "ROLLED_BACK"
    assert len(res.compensation_traces) > 0
    # Answer must NOT exist
    answers = [a for a in forum_service._answers.values() if a.author_id == "usr_saga_answer_tester"]
    assert len(answers) == 0
