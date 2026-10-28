"""Operator-flow tests for the forum (头脑风暴 / 知乎式问答) domain.

Every flow asserted here is declared in ``config/scenarios/forum.yaml`` and runs
on the operator kernel through ``orchestration_service.execute_scenario``;
identity is carried in ``context``. The legacy ``forum_service`` module is only
used as a data/query shim (mapping views + read models).
"""
from __future__ import annotations

import pytest

from src.core.entity import entity_store
from src.domains.forum.service import forum_service
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service

PUBLISH = "OPC_FORUM_THREAD_PUBLISH"
UPDATE = "OPC_FORUM_THREAD_UPDATE_PIPELINE"
DELETE_THREAD = "OPC_FORUM_THREAD_DELETE_PIPELINE"
ANSWER_PUBLISH = "OPC_FORUM_ANSWER_PUBLISH"
ANSWER_ACCEPT = "OPC_FORUM_ANSWER_ACCEPT_PIPELINE"
ANSWER_DELETE = "OPC_FORUM_ANSWER_DELETE_PIPELINE"
COMMENT_PUBLISH = "OPC_FORUM_COMMENT_PUBLISH"
COMMENT_DELETE = "OPC_FORUM_COMMENT_DELETE_PIPELINE"
VOTE = "OPC_FORUM_VOTE_PIPELINE"
FOLLOW = "OPC_FORUM_FOLLOW_PIPELINE"
DETAIL = "OPC_FORUM_DETAIL_PIPELINE"
LIST = "OPC_FORUM_LIST_PIPELINE"
FEED = "OPC_FORUM_FEED_STREAM_PIPELINE"

MAKER = {"user_id": "usr_forum_author", "user_role": "MAKER", "nickname": "算核测试发帖人"}
OTHER = {"user_id": "usr_forum_expert", "user_role": "MAKER", "nickname": "算核测试回答人"}
STRANGER = {"user_id": "usr_forum_stranger", "user_role": "MAKER", "nickname": "算核测试路人"}
ADMIN = {"user_id": "usr_forum_admin", "user_role": "ADMIN", "nickname": "平台管理员"}

THREAD_PAYLOAD = {
    "title": "算子内核迁移测试：一人公司季度免税核算",
    "content": "这里是一段足够长的帖子正文，用于验证论坛发帖的算子编排与计数维护逻辑。",
    "category_code": "TAX",
}

ENTITIES = (
    "forum.thread",
    "forum.answer",
    "forum.comment",
    "forum.vote",
    "forum.follow",
    "forum.tombstone",
)


def _purge() -> None:
    for entity in ENTITIES:
        spec = entity_store.spec(entity)
        adapter = entity_store.adapter(entity)
        for row in list(adapter.all()):
            adapter.delete(spec.key_of(row))
    forum_service.invalidate_feed_cache()


@pytest.fixture(autouse=True)
def clean_forum_state():
    _purge()
    yield
    _purge()


async def _run(scenario: str, inputs: dict, context: dict | None = None):
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=dict(inputs),
            context=dict(context or {}),
        )
    )


async def _publish(**overrides) -> dict:
    payload = dict(THREAD_PAYLOAD, **overrides)
    res = await _run(PUBLISH, payload, MAKER)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["created_thread"]


async def _answer(thread_id: str, **overrides) -> dict:
    payload = dict(
        {"thread_id": thread_id, "content": "这是一条足够长的深度观点回答内容，用于算子流测试。"},
        **overrides,
    )
    res = await _run(ANSWER_PUBLISH, payload, OTHER)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["created_answer"]


async def _comment(thread_id: str, context: dict, **overrides) -> dict:
    payload = dict({"thread_id": thread_id, "content": "启发很大的评论内容"}, **overrides)
    res = await _run(COMMENT_PUBLISH, payload, context)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["created_comment"]


# --------------------------------------------------------------- thread publish
@pytest.mark.asyncio
async def test_thread_publish_binds_author_from_context_and_zeroes_counters():
    # Without an explicit author_id the gateway-bound context identity is used.
    res = await _run(PUBLISH, THREAD_PAYLOAD, MAKER)

    assert res.status == "SUCCESS", res.error_message
    thread = res.final_output["created_thread"]
    assert thread["id"].startswith("thr_")
    assert thread["author_id"] == MAKER["user_id"]
    assert thread["author_name"] == MAKER["nickname"]
    assert thread["title"] == THREAD_PAYLOAD["title"]
    assert thread["category_code"] == "TAX"
    assert thread["status"] == "PUBLISHED"
    assert thread["is_official"] is False
    for counter in ("view_count", "upvote_count", "downvote_count", "comment_count", "answer_count", "follow_count"):
        assert thread[counter] == 0
    assert isinstance(thread["hot_score"], float)

    # Legacy publish contract: an explicitly supplied author_id wins (the gateway
    # only binds the token identity when the payload omits it).
    explicit = await _run(PUBLISH, dict(THREAD_PAYLOAD, author_id="usr_legacy_author"), MAKER)
    assert explicit.final_output["created_thread"]["author_id"] == "usr_legacy_author"

    # The legacy shim reads the very same document out of the entity store.
    stored = forum_service.get_thread(thread["id"], record_view=False)
    assert stored.author_id == MAKER["user_id"]
    assert forum_service._threads[thread["id"]].title == THREAD_PAYLOAD["title"]


@pytest.mark.asyncio
async def test_thread_publish_admin_is_stamped_official():
    res = await _run(PUBLISH, dict(THREAD_PAYLOAD, title="管理员代发公告帖"), ADMIN)
    assert res.status == "SUCCESS", res.error_message
    assert res.final_output["created_thread"]["is_official"] is True


@pytest.mark.asyncio
async def test_thread_publish_rejects_short_title_and_unauthenticated_caller():
    short = await _run(PUBLISH, dict(THREAD_PAYLOAD, title="短"), MAKER)
    assert short.status == "FAILED"
    assert "5 个字符" in (short.error_message or "")
    assert entity_store.count("forum.thread") == 0

    anonymous = await _run(PUBLISH, THREAD_PAYLOAD, {})
    assert anonymous.status == "GUARD_REJECTED"
    assert "登录" in (anonymous.error_message or "")
    assert entity_store.count("forum.thread") == 0


@pytest.mark.asyncio
async def test_thread_publish_moderation_prescreen_blocks_confirmed_violation():
    res = await _run(
        PUBLISH,
        {
            "title": "高价收代开假发票中介渠道合作",
            "content": "急需批量代开发票抵扣增值税额度，有渠道的私信详谈，价格好商量。",
        },
        MAKER,
    )
    assert res.status == "FAILED"
    assert "内容合规" in (res.error_message or "")
    assert entity_store.count("forum.thread") == 0


# ---------------------------------------------------------------- thread update
@pytest.mark.asyncio
async def test_thread_edit_author_admin_and_non_author():
    thread = await _publish()
    tid = thread["id"]

    author = await _run(
        UPDATE,
        {"thread_id": tid, "title": "作者修订后的帖子标题", "content": "作者修订之后的正文内容，长度必须满足门禁要求。"},
        MAKER,
    )
    assert author.status == "SUCCESS", author.error_message
    assert author.final_output["updated_thread"]["title"] == "作者修订后的帖子标题"

    stranger = await _run(
        UPDATE,
        {"thread_id": tid, "title": "路人尝试篡改帖子标题", "content": "这不是路人的帖子，应当被拒绝编辑。"},
        STRANGER,
    )
    assert stranger.status == "GUARD_REJECTED"
    assert "权限" in (stranger.error_message or "")

    admin = await _run(
        UPDATE,
        {"thread_id": tid, "title": "管理员合规修订标题", "content": "管理员依据社区治理协议修订了这篇帖子的正文内容。"},
        ADMIN,
    )
    assert admin.status == "SUCCESS", admin.error_message
    assert admin.final_output["updated_thread"]["title"] == "管理员合规修订标题"

    too_short = await _run(
        UPDATE,
        {"thread_id": tid, "title": "短", "content": "正文内容长度足够的修订版本，用于校验标题门禁。"},
        MAKER,
    )
    assert too_short.status == "FAILED"
    assert "5 个字符" in (too_short.error_message or "")
    assert forum_service.get_thread(tid, record_view=False).title == "管理员合规修订标题"


@pytest.mark.asyncio
async def test_thread_delete_requires_owner_or_admin():
    thread = await _publish(title="将被路人删除的帖子")
    tid = thread["id"]

    denied = await _run(DELETE_THREAD, {"thread_id": tid}, STRANGER)
    assert denied.status == "GUARD_REJECTED"
    assert entity_store.get("forum.thread", {"key": tid}) is not None

    deleted = await _run(DELETE_THREAD, {"thread_id": tid}, MAKER)
    assert deleted.status == "SUCCESS", deleted.error_message
    assert deleted.final_output["deleted"] is True
    assert entity_store.get("forum.thread", {"key": tid}) is None
    assert tid in forum_service._deleted_thread_ids

    missing = await _run(DELETE_THREAD, {"thread_id": tid}, MAKER)
    assert missing.status == "FAILED"
    assert "not found" in (missing.error_message or "").lower()


# --------------------------------------------------------------------- answers
@pytest.mark.asyncio
async def test_answer_publish_updates_thread_counter_and_word_stats():
    thread = await _publish()
    tid = thread["id"]

    answer = await _answer(tid, content="根据最新发票管理办法，季度免税核算必须先完成备案。")

    assert answer["id"].startswith("ans_")
    assert answer["thread_id"] == tid
    assert answer["author_id"] == OTHER["user_id"]
    assert answer["is_accepted"] is False
    assert answer["word_count"] == len("根据最新发票管理办法，季度免税核算必须先完成备案。")
    assert answer["read_minutes"] == 1

    refreshed = forum_service.get_thread(tid, record_view=False)
    assert refreshed.answer_count == 1

    detail = await _run(DETAIL, {"thread_id": tid}, MAKER)
    assert detail.status == "SUCCESS", detail.error_message
    assert detail.final_output["detail"]["thread"]["answer_count"] == 1
    assert len(detail.final_output["detail"]["answers"]) == 1


@pytest.mark.asyncio
async def test_answer_accept_toggles_and_enforces_thread_author():
    thread = await _publish(title="问答采纳流程测试帖")
    tid = thread["id"]
    answer = await _answer(tid)

    denied = await _run(ANSWER_ACCEPT, {"thread_id": tid, "answer_id": answer["id"]}, OTHER)
    assert denied.status == "GUARD_REJECTED"
    assert "权限" in (denied.error_message or "")

    accepted = await _run(ANSWER_ACCEPT, {"thread_id": tid, "answer_id": answer["id"]}, MAKER)
    assert accepted.status == "SUCCESS", accepted.error_message
    assert accepted.final_output["accept_result"]["is_accepted"] is True
    assert accepted.final_output["accept_result"]["action"] == "ACCEPTED"
    assert forum_service.get_thread(tid, record_view=False).accepted_answer_id == answer["id"]
    assert forum_service._answers[answer["id"]].is_accepted is True

    unaccepted = await _run(ANSWER_ACCEPT, {"thread_id": tid, "answer_id": answer["id"]}, MAKER)
    assert unaccepted.status == "SUCCESS", unaccepted.error_message
    assert unaccepted.final_output["accept_result"]["action"] == "UNACCEPTED"
    assert forum_service.get_thread(tid, record_view=False).accepted_answer_id is None
    assert forum_service._answers[answer["id"]].is_accepted is False


@pytest.mark.asyncio
async def test_answer_delete_requires_author_and_cascades_counters_and_votes():
    thread = await _publish(title="回答删除级联测试帖")
    tid = thread["id"]
    answer = await _answer(tid)
    aid = answer["id"]
    comment = await _comment(tid, OTHER, target_type="ANSWER", target_id=aid)

    voted = await _run(VOTE, {"target_type": "ANSWER", "target_id": aid, "vote_type": "UPVOTE"}, STRANGER)
    assert voted.status == "SUCCESS", voted.error_message
    assert (STRANGER["user_id"], "ANSWER", aid) in forum_service._votes

    accepted = await _run(ANSWER_ACCEPT, {"thread_id": tid, "answer_id": aid}, MAKER)
    assert accepted.status == "SUCCESS", accepted.error_message
    assert forum_service.get_thread(tid, record_view=False).accepted_answer_id == aid

    denied = await _run(ANSWER_DELETE, {"answer_id": aid}, STRANGER)
    assert denied.status == "GUARD_REJECTED"

    deleted = await _run(ANSWER_DELETE, {"answer_id": aid}, OTHER)
    assert deleted.status == "SUCCESS", deleted.error_message
    assert deleted.final_output["answer_deleted"] is True
    assert deleted.final_output["removed_count"] == 1
    assert forum_service.get_thread(tid, record_view=False).answer_count == 0
    assert forum_service.get_thread(tid, record_view=False).comment_count == 0
    assert forum_service.get_thread(tid, record_view=False).accepted_answer_id is None
    assert (STRANGER["user_id"], "ANSWER", aid) not in forum_service._votes

    detail = await _run(DETAIL, {"thread_id": tid}, MAKER)
    detail_data = detail.final_output["detail"]
    assert detail_data["answers"] == []
    flat: list[str] = []

    def _walk(nodes):
        for node in nodes:
            flat.append(node["id"])
            _walk(node.get("children") or [])

    _walk(detail_data["comments"])
    assert comment["id"] not in flat


# -------------------------------------------------------------------- comments
@pytest.mark.asyncio
async def test_nested_comment_materialized_path_and_reply_target():
    thread = await _publish(title="嵌套评论物化路径测试帖")
    tid = thread["id"]
    answer = await _answer(tid)

    root = await _comment(tid, OTHER, target_type="ANSWER", target_id=answer["id"])
    assert root["depth"] == 0
    assert root["root_id"] == root["id"]
    assert root["materialized_path"] == f"/{root['id']}"

    child = await _comment(tid, MAKER, parent_id=root["id"])
    assert child["depth"] == 1
    assert child["parent_id"] == root["id"]
    assert child["root_id"] == root["id"]
    assert child["reply_to_user_id"] == OTHER["user_id"]
    assert child["materialized_path"] == f"/{root['id']}/{child['id']}"

    grandchild = await _comment(tid, STRANGER, parent_id=child["id"], content="三级追问：跨省分支机构如何合并申报？")
    assert grandchild["depth"] == 2
    assert grandchild["materialized_path"] == f"/{root['id']}/{child['id']}/{grandchild['id']}"

    assert forum_service.get_thread(tid, record_view=False).comment_count == 3
    # Nested replies hang on the thread by default (target_id defaults to thread_id),
    # so only the level-0 comment is attributed to the answer — same as legacy.
    assert forum_service._answers[answer["id"]].comment_count == 1

    detail = await _run(DETAIL, {"thread_id": tid}, MAKER)
    tree = detail.final_output["detail"]["comments"]
    assert len(tree) == 1
    assert tree[0]["id"] == root["id"]
    assert tree[0]["children"][0]["id"] == child["id"]
    assert tree[0]["children"][0]["children"][0]["id"] == grandchild["id"]


@pytest.mark.asyncio
async def test_comment_publish_rejects_missing_thread_and_foreign_parent():
    missing = await _run(
        COMMENT_PUBLISH, {"thread_id": "thr_missing", "content": "评论内容"}, OTHER
    )
    assert missing.status == "FAILED"
    assert "not found" in (missing.error_message or "").lower()

    thread_a = await _publish(title="父评论归属校验帖 A")
    thread_b = await _publish(title="父评论归属校验帖 B")
    foreign_parent = await _comment(thread_a["id"], OTHER)

    cross = await _run(
        COMMENT_PUBLISH,
        {"thread_id": thread_b["id"], "parent_id": foreign_parent["id"], "content": "跨帖挂载子回复"},
        MAKER,
    )
    assert cross.status == "FAILED"
    assert "父评论" in (cross.error_message or "")

    orphan = await _run(
        COMMENT_PUBLISH,
        {"thread_id": thread_b["id"], "parent_id": "cmt_missing", "content": "父评论不存在"},
        MAKER,
    )
    assert orphan.status == "FAILED"
    assert "父评论不存在" in (orphan.error_message or "")


@pytest.mark.asyncio
async def test_comment_delete_removes_whole_subtree_and_rebalances_counters():
    thread = await _publish(title="评论子树删除测试帖")
    tid = thread["id"]
    answer = await _answer(tid)

    root = await _comment(tid, OTHER, target_type="ANSWER", target_id=answer["id"])
    child = await _comment(tid, MAKER, parent_id=root["id"])
    sibling = await _comment(tid, MAKER, target_type="ANSWER", target_id=answer["id"], content="另一条一级评论")
    await _run(VOTE, {"target_type": "COMMENT", "target_id": child["id"], "vote_type": "UPVOTE"}, STRANGER)

    denied = await _run(COMMENT_DELETE, {"comment_id": root["id"]}, STRANGER)
    assert denied.status == "GUARD_REJECTED"

    deleted = await _run(COMMENT_DELETE, {"comment_id": root["id"]}, OTHER)
    assert deleted.status == "SUCCESS", deleted.error_message
    assert deleted.final_output["comment_deleted"] is True
    assert deleted.final_output["removed_count"] == 2
    assert forum_service.get_thread(tid, record_view=False).comment_count == 1
    assert forum_service._answers[answer["id"]].comment_count == 1
    assert (STRANGER["user_id"], "COMMENT", child["id"]) not in forum_service._votes

    detail = await _run(DETAIL, {"thread_id": tid}, MAKER)
    ids = [node["id"] for node in detail.final_output["detail"]["comments"]]
    assert ids == [sibling["id"]]
    assert entity_store.get("forum.comment", {"key": root["id"]}) is None


# ----------------------------------------------------------------------- votes
@pytest.mark.asyncio
async def test_vote_mutual_exclusion_switch_and_cancel():
    thread = await _publish(title="互斥投票测试帖")
    tid = thread["id"]
    thread_id = tid

    first = await _run(VOTE, {"target_type": "THREAD", "target_id": thread_id, "vote_type": "UPVOTE"}, MAKER)
    assert first.status == "SUCCESS", first.error_message
    assert first.final_output["vote_result"] == {
        "user_vote": "UPVOTE",
        "upvote_count": 1,
        "downvote_count": 0,
        "target_type": "THREAD",
        "target_id": thread_id,
        "action": "UPVOTED",
    }

    switched = await _run(VOTE, {"target_type": "THREAD", "target_id": thread_id, "vote_type": "DOWNVOTE"}, MAKER)
    result = switched.final_output["vote_result"]
    assert result["user_vote"] == "DOWNVOTE"
    assert result["upvote_count"] == 0
    assert result["downvote_count"] == 1
    assert result["action"] == "SWITCHED"

    cancelled = await _run(VOTE, {"target_type": "THREAD", "target_id": thread_id, "vote_type": "DOWNVOTE"}, MAKER)
    result = cancelled.final_output["vote_result"]
    assert result["user_vote"] is None
    assert result["upvote_count"] == 0
    assert result["downvote_count"] == 0
    assert result["action"] == "CANCELLED"

    # Votes are independent per user; the ledger is keyed by (user, target).
    await _run(VOTE, {"target_type": "THREAD", "target_id": thread_id, "vote_type": "UPVOTE"}, MAKER)
    others = await _run(VOTE, {"target_type": "THREAD", "target_id": thread_id, "vote_type": "DOWNVOTE"}, OTHER)
    assert others.final_output["vote_result"]["upvote_count"] == 1
    assert others.final_output["vote_result"]["downvote_count"] == 1
    assert forum_service._votes[(MAKER["user_id"], "THREAD", thread_id)] == "UPVOTE"
    assert forum_service._votes[(OTHER["user_id"], "THREAD", thread_id)] == "DOWNVOTE"
    assert len(forum_service._votes) == 2


@pytest.mark.asyncio
async def test_vote_on_answer_and_comment_targets():
    thread = await _publish(title="回答与评论投票测试帖")
    tid = thread["id"]
    answer = await _answer(tid)
    comment = await _comment(tid, MAKER, target_type="ANSWER", target_id=answer["id"])

    on_answer = await _run(VOTE, {"target_type": "ANSWER", "target_id": answer["id"], "vote_type": "UPVOTE"}, MAKER)
    assert on_answer.status == "SUCCESS", on_answer.error_message
    assert forum_service._answers[answer["id"]].upvote_count == 1

    on_comment = await _run(VOTE, {"target_type": "COMMENT", "target_id": comment["id"], "vote_type": "DOWNVOTE"}, OTHER)
    assert on_comment.status == "SUCCESS", on_comment.error_message
    assert forum_service._comments[comment["id"]].downvote_count == 1


@pytest.mark.asyncio
async def test_vote_failures_missing_target_anonymous_and_bad_target_type():
    thread = await _publish(title="投票失败路径测试帖")

    missing = await _run(VOTE, {"target_type": "THREAD", "target_id": "thr_missing", "vote_type": "UPVOTE"}, MAKER)
    assert missing.status == "FAILED"
    assert "not found" in (missing.error_message or "").lower()

    anonymous = await _run(
        VOTE, {"target_type": "THREAD", "target_id": thread["id"], "vote_type": "UPVOTE"}, {}
    )
    assert anonymous.status == "GUARD_REJECTED"

    bad_type = await _run(
        VOTE, {"target_type": "PRODUCT", "target_id": thread["id"], "vote_type": "UPVOTE"}, MAKER
    )
    assert bad_type.status == "FAILED"
    assert "target_type" in (bad_type.error_message or "") or "取值不在允许范围" in (bad_type.error_message or "")


# ---------------------------------------------------------------------- follow
@pytest.mark.asyncio
async def test_follow_toggles_and_maintains_follow_count():
    thread = await _publish(title="关注议题测试帖")
    tid = thread["id"]

    first = await _run(FOLLOW, {"thread_id": tid}, MAKER)
    assert first.status == "SUCCESS", first.error_message
    assert first.final_output["follow_result"] == {
        "thread_id": tid,
        "is_following": True,
        "follow_count": 1,
    }
    assert (MAKER["user_id"], tid) in forum_service._follows

    second = await _run(FOLLOW, {"thread_id": tid}, MAKER)
    assert second.final_output["follow_result"]["is_following"] is False
    assert second.final_output["follow_result"]["follow_count"] == 0
    assert (MAKER["user_id"], tid) not in forum_service._follows

    await _run(FOLLOW, {"thread_id": tid}, MAKER)
    other = await _run(FOLLOW, {"thread_id": tid}, OTHER)
    assert other.final_output["follow_result"]["follow_count"] == 2

    detail = await _run(DETAIL, {"thread_id": tid}, MAKER)
    assert detail.final_output["detail"]["thread"]["is_following"] is True


# ---------------------------------------------------------------------- detail
@pytest.mark.asyncio
async def test_detail_assembles_answers_comments_and_viewer_state():
    thread = await _publish(title="详情装配测试帖")
    tid = thread["id"]
    answer = await _answer(tid)
    comment = await _comment(tid, OTHER, target_type="ANSWER", target_id=answer["id"])
    await _run(VOTE, {"target_type": "THREAD", "target_id": tid, "vote_type": "UPVOTE"}, MAKER)
    await _run(VOTE, {"target_type": "ANSWER", "target_id": answer["id"], "vote_type": "UPVOTE"}, MAKER)

    as_viewer = await _run(DETAIL, {"thread_id": tid}, MAKER)
    detail = as_viewer.final_output["detail"]
    assert detail["thread"]["user_vote"] == "UPVOTE"
    assert detail["thread"]["upvote_count"] == 1
    assert detail["thread"]["view_count"] == 1
    assert detail["answers"][0]["user_vote"] == "UPVOTE"
    assert detail["answers"][0]["upvote_count"] == 1
    assert detail["comments"][0]["id"] == comment["id"]

    anonymous = await _run(DETAIL, {"thread_id": tid}, {})
    assert anonymous.status == "SUCCESS", anonymous.error_message
    assert anonymous.final_output["detail"]["thread"]["user_vote"] is None
    assert anonymous.final_output["detail"]["thread"]["view_count"] == 2

    missing = await _run(DETAIL, {"thread_id": "thr_missing"}, MAKER)
    assert missing.status == "FAILED"
    assert "not found" in (missing.error_message or "").lower()


# ------------------------------------------------------------------ list / feed
@pytest.mark.asyncio
async def test_list_paginates_and_filters_by_category():
    for index in range(5):
        await _publish(title=f"分页测试帖子第 {index + 1} 篇", category_code="DEV" if index < 3 else "BIZ")

    first = await _run(LIST, {"id": "DEV", "page": 1, "page_length": 2})
    assert first.status == "SUCCESS", first.error_message
    page_one = first.final_output["feed"]
    assert page_one["total"] == 3
    assert page_one["page"] == 1
    assert page_one["page_size"] == 2
    assert page_one["page_length"] == 2
    assert page_one["has_more"] is True
    assert len(page_one["items"]) == 2
    assert all(item["category_code"] == "DEV" for item in page_one["items"])

    second = await _run(LIST, {"id": "DEV", "page": 2, "page_length": 2})
    page_two = second.final_output["feed"]
    assert page_two["page"] == 2
    assert len(page_two["items"]) == 1
    assert page_two["has_more"] is False
    assert {item["id"] for item in page_one["items"]}.isdisjoint({item["id"] for item in page_two["items"]})

    all_pages = await _run(LIST, {"id": "ALL", "page": 1, "page_size": 10})
    assert all_pages.final_output["feed"]["total"] == 5


@pytest.mark.asyncio
async def test_feed_cursor_pagination_and_hotness_order():
    threads = []
    for index in range(5):
        threads.append(await _publish(title=f"Feed 游标测试帖子 {index + 1}"))
    hot_thread = threads[-1]
    await _run(VOTE, {"target_type": "THREAD", "target_id": hot_thread["id"], "vote_type": "UPVOTE"}, MAKER)
    await _run(VOTE, {"target_type": "THREAD", "target_id": hot_thread["id"], "vote_type": "UPVOTE"}, OTHER)

    maded = await _run(FEED, {"category_code": "ALL", "cursor": 0, "limit": 2, "sort_by": "latest"})
    assert maded.status == "SUCCESS", maded.error_message
    feed = maded.final_output["feed_result"]
    assert feed["total"] == 5
    assert feed["cursor"] == 0
    assert feed["limit"] == 2
    assert feed["has_more"] is True
    assert feed["next_cursor"] == 2
    assert feed["prefetch_hint"]["recommended_prefetch_cursor"] == 2
    assert feed["cache_hit"] is False and feed["cache_removed"] is True
    assert feed["items"][0]["id"] == threads[-1]["id"]  # latest-first
    assert all("top_answers" in item for item in feed["items"])

    second = await _run(FEED, {"category_code": "ALL", "cursor": 2, "limit": 2, "sort_by": "latest"})
    page_two = second.final_output["feed_result"]
    assert page_two["cursor"] == 2
    assert page_two["has_more"] is True
    assert {item["id"] for item in feed["items"]}.isdisjoint({item["id"] for item in page_two["items"]})

    hot = await _run(FEED, {"category_code": "ALL", "cursor": 0, "limit": 5, "sort_by": "hot"})
    hot_items = hot.final_output["feed_result"]["items"]
    assert hot_items[0]["id"] == hot_thread["id"]
    assert hot_items[0]["hot_score"] > hot_items[-1]["hot_score"]

    unanswered = await _run(FEED, {"category_code": "ALL", "cursor": 0, "limit": 5, "sort_by": "unanswered"})
    assert len(unanswered.final_output["feed_result"]["items"]) == 5


@pytest.mark.asyncio
async def test_feed_viewer_annotation_is_per_caller():
    thread = await _publish(title="观察者标注测试帖")
    tid = thread["id"]
    answer = await _answer(tid)
    await _run(VOTE, {"target_type": "THREAD", "target_id": tid, "vote_type": "UPVOTE"}, MAKER)
    await _run(VOTE, {"target_type": "ANSWER", "target_id": answer["id"], "vote_type": "UPVOTE"}, MAKER)
    await _run(FOLLOW, {"thread_id": tid}, MAKER)

    mine = await _run(FEED, {"category_code": "ALL", "cursor": 0, "limit": 5}, MAKER)
    item = mine.final_output["feed_result"]["items"][0]
    assert item["user_vote"] == "UPVOTE"
    assert item["is_following"] is True
    assert item["top_answers"][0]["user_vote"] == "UPVOTE"

    theirs = await _run(FEED, {"category_code": "ALL", "cursor": 0, "limit": 5}, STRANGER)
    other_item = theirs.final_output["feed_result"]["items"][0]
    assert other_item["user_vote"] is None
    assert other_item["is_following"] is False
    assert other_item["top_answers"][0]["user_vote"] is None
