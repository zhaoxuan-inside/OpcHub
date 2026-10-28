"""Policy catalog behaviour: DB-only source of truth, gateway dispatch, RAG and hydration."""
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.domains.policies.service import policy_service
from src.domains.policies.models import PolicyCreate, PolicyMatchRequest
from src.infrastructure.database.persistence import (
    PersistenceUnavailableError,
    domain_persistence,
)
from src.core.rag.service import policy_rag_service
from tests.catalog_fixtures import load_catalog, seed_policies


@pytest.fixture(autouse=True)
def ensure_policy_fixtures():
    """Populate representative, test-owned policy rows (production ships no seeds)."""
    policy_service.clear()
    seed_policies(policy_service)
    yield
    policy_service.clear()


def test_policy_catalog_fixture_is_valid():
    """Test fixture contains the policy shapes used by the UI and matching engine."""
    seeds = load_catalog("policies.json")
    assert len(seeds) >= 4
    for pid, p in seeds.items():
        assert "title" in p
        assert "summary" in p
        assert "code" in p
        assert "region" in p
        assert "legal_basis" in p


def test_policy_service_starts_empty_without_database():
    """No runtime seed loading: an empty DB means an empty catalog."""
    policy_service.clear()
    assert policy_service.list_policies() == []


def test_policy_mutation_requires_database():
    """In strict mode, publishing without PostgreSQL is rejected instead of kept in memory."""
    policy_service.clear()
    previous = domain_persistence.strict
    domain_persistence.strict = True
    try:
        with pytest.raises(PersistenceUnavailableError):
            policy_service.create_policy(PolicyCreate(
                title="不应落内存的政策",
                policy_level="NATIONAL",
                category="TAX",
                subsidy_amount_max=1000.0,
                summary="无数据库时发布应被拒绝",
                eligible_conditions=[],
                legal_basis="测试依据",
            ))
    finally:
        domain_persistence.strict = previous


def test_policy_service_hydrates_from_fixture_rows():
    policies = policy_service.list_policies()
    assert len(policies) >= 4
    vat_policy = next((p for p in policies if p.id == "pol_vat_exemption_2026"), None)
    assert vat_policy is not None
    assert vat_policy.code == "POL-2026-081"
    assert vat_policy.region == "全国统一"


@pytest.mark.asyncio
async def test_policy_gateway_list_and_match():
    """Verify unified gateway dispatch scenario policies.list and policies.match."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "policies.list",
            "payload": {},
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        items = body["data"]
        assert isinstance(items, list)
        assert len(items) >= 4
        assert any(p["code"] == "POL-2026-081" for p in items)

        match_resp = await ac.post("/api/welcom/opc_world", json={
            "scenario": "policies.match",
            "payload": {
                "quarterly_income": 200000.0,
                "maker_type": "INDIVIDUAL",
                "region": "大湾区",
                "search_query": "AI算力微调",
            },
        })
        assert match_resp.status_code == 200
        match_body = match_resp.json()
        assert match_body["code"] == 200
        assert match_body["data"]["eligible"] is True
        assert len(match_body["data"]["matched_policies"]) >= 1


@pytest.mark.asyncio
async def test_policy_rag_semantic_search():
    """Verify RAG semantic vector search over the hydrated policy catalog."""
    results = await policy_rag_service.search_policies(
        query="小规模免税与增值税",
        top_k=3,
    )
    assert results["status"] == "SUCCESS"
    assert len(results["results"]) >= 1
    top_result = results["results"][0]
    assert "title" in top_result
    assert "summary" in top_result
    assert "code" in top_result


@pytest.mark.asyncio
async def test_policy_hydration_persistence_roundtrip():
    """Verify domain_persistence snapshot hydration."""
    snapshot_records = [p.model_dump() for p in policy_service.list_policies()]
    policy_service._policies.clear()
    assert len(policy_service.list_policies()) == 0

    hydrated_count = policy_service.hydrate_items(snapshot_records)
    assert hydrated_count == len(snapshot_records)
    assert len(policy_service.list_policies()) == len(snapshot_records)
