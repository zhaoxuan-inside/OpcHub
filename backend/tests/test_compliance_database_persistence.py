"""Compliance catalog behaviour: DB-only source of truth, publish flow, gateway and hydration."""
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.core.security import create_session_token
from src.domains.compliance.service import compliance_service
from src.domains.compliance.models import AuditEvaluateRequest
from src.infrastructure.database.persistence import (
    PersistenceUnavailableError,
    domain_persistence,
)
from tests.catalog_fixtures import load_catalog, seed_compliance


@pytest.fixture(autouse=True)
def ensure_compliance_fixtures():
    """Populate representative, test-owned compliance rows (production ships no seeds)."""
    compliance_service.clear()
    seed_compliance(compliance_service)
    yield
    compliance_service.clear()


def test_compliance_catalog_fixture_is_valid():
    """Test fixture contains all three entity kinds with the field shapes used by the UI."""
    seeds = load_catalog("compliance.json")
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


def test_compliance_service_starts_empty_without_database():
    """No runtime seed loading: an empty DB means an empty knowledge base."""
    compliance_service.clear()
    assert compliance_service.get_laws() == []
    assert compliance_service.get_cases() == []
    assert compliance_service.get_checkpoints() == []


def test_compliance_mutation_requires_database():
    """In strict mode, publishing without PostgreSQL is rejected instead of kept in memory."""
    previous = domain_persistence.strict
    domain_persistence.strict = True
    try:
        with pytest.raises(PersistenceUnavailableError):
            compliance_service.publish_entry({
                "kind": "law",
                "title": "不应落内存的法条",
                "summary": "无数据库时发布应被拒绝",
                "content": "测试正文",
            })
    finally:
        domain_persistence.strict = previous


def test_compliance_service_hydrates_from_fixture_rows():
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
    """Verify unified gateway dispatch scenarios return the hydrated knowledge base."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
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

        cases_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.cases",
            "payload": {},
        })
        assert cases_resp.json()["code"] == 200
        assert len(cases_resp.json()["data"]) >= 3

        alias_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "compliance.dimensions",
            "payload": {},
        })
        assert alias_resp.json()["code"] == 200
        assert len(alias_resp.json()["data"]) >= 6


@pytest.mark.asyncio
async def test_compliance_publish_law_and_case_via_gateway():
    """Verify logged-in maker can publish a law or case via compliance.publish."""
    maker_token = create_session_token({
        "uid": "usr_compliance_writer",
        "email": "compliance_writer@opchub.cn",
        "nickname": "合规创客",
        "role": "MAKER",
        "must_change_password": False,
    })
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
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
        assert any(l.title == created_law["title"] for l in compliance_service.get_laws())

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
        assert any(c.title == created_case["title"] for c in compliance_service.get_cases())

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

    all_ids = [c.id for c in compliance_service.get_checkpoints()]
    report = compliance_service.evaluate_audit(AuditEvaluateRequest(passed_item_ids=all_ids))
    assert report.score == 100
