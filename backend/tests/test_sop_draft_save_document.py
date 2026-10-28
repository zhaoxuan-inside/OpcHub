"""测试：起草新文书 → 保存到「我的文书」完整链路。

覆盖用户反馈的缺陷：起草新文书不能创建新的文书。
验证：
1. 后端 sop.document.render 场景可渲染并持久化一份新文书（写入 PostgreSQL domain_snapshots）。
2. sop.document.list 可查回刚保存的文书。
3. 前端 SopDocPage 提供「保存文书」入口并调用 sop.document.render。
"""
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from src.main import app
from conftest import DEFAULT_ADMIN_TOKEN

ROOT = Path(__file__).resolve().parent.parent.parent
SOP_DOC_PAGE = ROOT / "frontend" / "src" / "components" / "sop" / "SopDocPage.vue"


async def _gw(ac, scenario, payload, token=None):
    ac.headers["Authorization"] = f"Bearer {token or DEFAULT_ADMIN_TOKEN}"
    return await ac.post("/api/welcom/opc_world", json={
        "scenario": scenario, "version": "v1.0.0", "payload": payload,
    })


@pytest.mark.asyncio
async def test_draft_save_document_full_flow():
    """起草新文书并保存：render 创建 → list 查回，完整闭环。"""
    from src.core.security import create_session_token
    maker_token = create_session_token({
        "uid": "usr_draft_test", "role": "MAKER", "nickname": "起草创客",
    })
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. 取一份标准文书模板（sop.documents 标准文书库）
        cat_res = await _gw(ac, "sop.documents", {"user_id": "usr_draft_test"})
        assert cat_res.json()["code"] == 200
        catalog = cat_res.json()["data"]["items"]
        assert len(catalog) > 0, "标准文书库应至少有一份可填写文书"
        template_id = catalog[0]["id"]

        # 2. 起草新文书并保存（sop.document.render 微内核 DAG 编排 + PostgreSQL 持久化）
        save_res = await _gw(ac, "sop.document.render", {
            "template_id": template_id,
            "form_data": {"company_name": "起草验证有限公司", "founder_name": "张创客"},
        }, token=maker_token)
        assert save_res.json()["code"] == 200
        doc = save_res.json()["data"]
        assert doc["id"]
        assert doc["user_id"] == "usr_draft_test"
        assert "起草验证有限公司" in doc["document_title"] or "起草验证有限公司" in doc["rendered_content"]
        assert doc["status"] == "READY"
        saved_doc_id = doc["id"]

        # 3. 我的文书列表应包含刚保存的文书（sop.document.list）
        list_res = await _gw(ac, "sop.document.list", {}, token=maker_token)
        assert list_res.json()["code"] == 200
        docs = list_res.json()["data"]
        assert isinstance(docs, list)
        assert any(d["id"] == saved_doc_id for d in docs), "刚保存的文书应出现在「我的文书」列表"

        # 4. 可按 ID 取回详情（sop.document.get）
        get_res = await _gw(ac, "sop.document.get", {"doc_id": saved_doc_id})
        assert get_res.json()["code"] == 200
        detail = get_res.json()["data"]
        assert detail["id"] == saved_doc_id


def test_sop_doc_page_has_save_button_and_calls_render():
    """前端起草页必须提供「保存文书」入口并调用 sop.document.render。"""
    source = SOP_DOC_PAGE.read_text(encoding="utf-8")

    # 1. 存在「保存文书」按钮（模板中渲染）
    assert "保存文书" in source
    assert "saveDocument" in source

    # 2. 保存动作调用后端 sop.document.render 场景（数据/代码三分离，数据落库）
    assert "sop.document.render" in source

    # 3. 保存成功后通知父组件刷新「我的文书」
    assert "saved" in source
    assert "emit('saved'" in source
