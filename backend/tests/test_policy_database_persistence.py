"""Test policy data separation, seed loading, database persistence, and gateway dispatch."""
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.domains.policies.service import (
    policy_service,
    _load_policy_seeds,
    DEFAULT_POLICY_SEEDS,
)
from src.domains.policies.models import PolicyCreate, PolicyMatchRequest
from src.infrastructure.database.persistence import domain_persistence
from src.core.rag.service import policy_rag_service


@pytest.fixture(autouse=True)
def ensure_policy_seeds():
    """Ensure baseline seeds are loaded for each test."""
    policy_service._policies.clear()
    policy_service._init_seeds()
    yield


def test_policy_seeds_file_separation():
    """Verify code, config, and data separation: policies.json exists and is valid."""
    seeds = _load_policy_seeds()
    assert len(seeds) >= 4
    assert "pol_vat_exemption_2026" in seeds
    assert "pol_ai_compute_voucher_hz" in seeds
    assert "pol_rnd_deduction_100" in seeds
    assert "pol_offshore_trade_2026" in seeds

    for pid, p in seeds.items():
        assert "title" in p
        assert "summary" in p
        assert "code" in p
        assert "region" in p
        assert "legal_basis" in p


def test_policy_service_seed_initialization():
    """Verify PolicyService populates from external data seeds on startup."""
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
        # 1. Dispatch policies.list
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

        # 2. Dispatch policies.match
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
    """Verify RAG semantic vector search over external policy data."""
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
