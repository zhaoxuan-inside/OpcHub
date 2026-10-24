"""Test compliance data separation, seed loading, database persistence, publish & gateway dispatch.

对齐 PolicyView 的数据层验证模式：合规知识（法条 / 案例 / 自检清单）
从 seeds JSON 加载并写入 PostgreSQL (domain_snapshots)，支持启动时 hydrate 重建。
"""
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.core.security import create_session_token
from src.domains.compliance.service import (
    compliance_service,
    _load_compliance_seeds,
)
from src.domains.compliance.models import CompliancePublishRequest, AuditEvaluateRequest


@pytest.fixture(autouse=True)
def ensure_compliance_seeds():
    """Ensure baseline seeds are loaded for each test."""
    compliance_service.clear()
    compliance_service._init_seeds()
    yield
    compliance_service.clear()
    compliance_service._init_seeds()


def test_compliance_seeds_file_separation():
    """Verify code / config / data separation: compliance.json exists with all three entity kinds."""
    seeds = _load_compliance_seeds()
    assert len(seeds.get("laws", [])) >= 6
    assert len(seeds.get("cases", [])) >= 3
    assert len(seeds.get("checkpoints", [])) >= 10

    for law in seeds["laws"]:
        for key in ("id", "code", "name", "title", "summary", "content", "level", "issuer", "published_at", "penalties", "law_ref", "icon_name", "hot_score"):
            assert key in law, f"law missing {key}"
    for case in seeds["cases"]:
        for key in ("id", "title", "badge", "industry", "violation", "consequence", "lesson", "badge_color", "hot_score"):
            assert key in case, f"case missing {key}"
    for chk in seeds["checkpoints"]:
        for key in ("id", "dimension_id", "title", "description", "severity", "weight", "advice", "legal_basis"):
            assert key in chk, f"checkpoint missing {key}"


def test_compliance_service_seed_initialization():
    """Verify ComplianceService populates from external data seeds on startup."""
    assert len(compliance_service.get_laws()) >= 6
    assert len(compliance_service.get_cases()) >= 3
    assert len(compliance_service.get_checkpoints()) >= 10

    law = next((l for l in compliance_service.get_laws() if l.id == "law_privacy"), None)
    assert law is not None
    assert law.code == "LAW-01"
    assert law.name == "个人信息保护"
    assert law.level == "法律"
    assert law.hot_score > 0


@pytest.mark.asyncio
async def test_compliance_gateway_list_and_audit():
    """Verify unified gateway dispatch scenarios return persisted knowledge base."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Dispatch compliance.laws
        resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.laws",
            "payload": {},
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        items = body["data"]
        assert isinstance(items, list)
        assert len(items) >= 6
        assert any(d["code"] == "LAW-01" for d in items)

        # 2. Dispatch compliance.cases
        cases_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.cases",
            "payload": {},
        })
        assert cases_resp.json()["code"] == 200
        assert len(cases_resp.json()["data"]) >= 3

        # 3. Backward-compatible compliance.dimensions alias still works
        alias_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.dimensions",
            "payload": {},
        })
        assert alias_resp.json()["code"] == 200
        assert len(alias_resp.json()["data"]) >= 6


@pytest.mark.asyncio
async def test_compliance_publish_law_and_case_via_gateway():
    """Verify logged-in maker can publish a law or case via compliance.publish.

    统一发布契约生效后 compliance.publish 要求登录（content:publish），
    请求需携带创客会话 token。
    """
    maker_token = create_session_token({
        "uid": "usr_compliance_writer",
        "email": "compliance_writer@opchub.cn",
        "nickname": "合规创客",
        "role": "MAKER",
        "must_change_password": False,
    })
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Publish a law
        law_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.publish",
            "token": maker_token,
            "payload": {
                "kind": "law",
                "title": "数据安全法 · 数据分类分级保护",
                "summary": "建立数据分类分级保护制度，开展数据全生命周期安全防护。",
                "content": "国家建立数据分类分级保护制度，对列入重要数据目录的数据实施重点保护。",
                "level": "法律",
                "issuer": "全国人民代表大会常务委员会",
                "published_at": "2021-09-01",
                "law_ref": "《中华人民共和国数据安全法》第二十一条",
            },
        })
        assert law_resp.json()["code"] == 200
        created_law = law_resp.json()["data"]
        assert "数据安全法" in created_law["title"]
        # Now appears in laws list
        laws = compliance_service.get_laws()
        assert any(l.title == created_law["title"] for l in laws)

        # 2. Publish a case
        case_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.publish",
            "token": maker_token,
            "payload": {
                "kind": "case",
                "title": "某隐私采集违规 App 被责令下架整改",
                "badge": "隐私违规下架 · 责令整改",
                "industry": "移动应用",
                "violation": "未经用户同意静默采集通讯录并用于营销推送",
                "consequence": "被网信部门责令下架并限期整改",
                "lesson": "任何个人信息采集都必须取得用户明示同意并提供撤回通道。",
            },
        })
        assert case_resp.json()["code"] == 200
        created_case = case_resp.json()["data"]
        assert "隐私采集" in created_case["title"]
        cases = compliance_service.get_cases()
        assert any(c.title == created_case["title"] for c in cases)

        # 3. Invalid kind is rejected
        bad_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.publish",
            "token": maker_token,
            "payload": {"kind": "unknown", "title": "x"},
        })
        assert bad_resp.json()["code"] != 200


@pytest.mark.asyncio
async def test_compliance_hydration_persistence_roundtrip():
    """Verify domain_persistence snapshot hydration rebuilds the in-memory catalog."""
    laws = compliance_service.get_laws()
    cases = compliance_service.get_cases()
    checkpoints = compliance_service.get_checkpoints()

    snapshot_records = (
        [dict(l.model_dump(mode="json"), _kind="law") for l in laws]
        + [dict(c.model_dump(mode="json"), _kind="case") for c in cases]
        + [dict(c.model_dump(mode="json"), _kind="checkpoint") for c in checkpoints]
    )
    compliance_service.clear()
    assert len(compliance_service.get_laws()) == 0

    hydrated_count = compliance_service.hydrate_items(snapshot_records)
    assert hydrated_count == len(snapshot_records)
    assert len(compliance_service.get_laws()) == len(laws)
    assert len(compliance_service.get_cases()) == len(cases)
    assert len(compliance_service.get_checkpoints()) == len(checkpoints)

    # Evaluation still works after hydration
    all_ids = [c.id for c in compliance_service.get_checkpoints()]
    report = compliance_service.evaluate_audit(AuditEvaluateRequest(passed_item_ids=all_ids))
    assert report.score == 100
