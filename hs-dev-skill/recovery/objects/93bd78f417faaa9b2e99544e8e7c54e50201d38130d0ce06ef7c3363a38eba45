"""Tests for SQLite-backed lightweight Vector Store and RAG services."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.rag import (
    cosine_similarity,
    LocalDeterministicEmbeddingProvider,
    VectorDocument,
    SQLiteVectorStore,
    PolicyRagService,
    ForumRagService,
)


@pytest.fixture
def mem_vector_store():
    """Isolated in-memory SQLite vector store for testing."""
    return SQLiteVectorStore(db_path=":memory:")

def test_cosine_similarity_math():
    """Verify cosine similarity calculation edge cases and accuracy."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    v4 = [0.5, 0.5, 0.0]

    assert cosine_similarity(v1, v2) == 1.0
    assert cosine_similarity(v1, v3) == 0.0
    assert 0.70 < cosine_similarity(v1, v4) < 0.72
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


@pytest.mark.asyncio
async def test_deterministic_embedding_provider():
    """Verify deterministic embedding provider properties."""
    provider = LocalDeterministicEmbeddingProvider(dim=64)
    text1 = "人工智能算力券补贴申报"
    text2 = "人工智能算力券补贴申报"
    text3 = "增值税小规模纳税人免征"

    vec1 = await provider.embed_query(text1)
    vec2 = await provider.embed_query(text2)
    vec3 = await provider.embed_query(text3)

    assert len(vec1) == 64
    assert vec1 == vec2  # Exactly deterministic
    assert vec1 != vec3  # Differentiable

    sim_same = cosine_similarity(vec1, vec2)
    sim_diff = cosine_similarity(vec1, vec3)
    assert sim_same == 1.0
    assert sim_diff < sim_same


def test_sqlite_vector_store_crud_and_search(mem_vector_store):
    """Verify CRUD and similarity search in SQLiteVectorStore."""
    doc1 = VectorDocument(
        doc_id="doc_1",
        collection="test_col",
        title="测试公文1",
        content="小规模纳税人增值税免征政策",
        metadata={"category": "TAX", "level": "国家级"},
        vector=[1.0, 0.0, 0.0, 0.0],
    )
    doc2 = VectorDocument(
        doc_id="doc_2",
        collection="test_col",
        title="测试公文2",
        content="人工智能大模型算力券补贴",
        metadata={"category": "SUBSIDY", "level": "省市级"},
        vector=[0.0, 1.0, 0.0, 0.0],
    )

    mem_vector_store.upsert_batch([doc1, doc2])
    assert mem_vector_store.count("test_col") == 2

    # Query close to doc2
    results = mem_vector_store.search_similarity(
        collection="test_col",
        query_vector=[0.1, 0.9, 0.0, 0.0],
        top_k=2
    )
    assert len(results) == 2
    assert results[0][0].doc_id == "doc_2"
    assert results[0][1] > results[1][1]

    # Query with metadata filter
    filtered = mem_vector_store.search_similarity(
        collection="test_col",
        query_vector=[0.1, 0.9, 0.0, 0.0],
        top_k=2,
        filter_meta={"category": "TAX"}
    )
    assert len(filtered) == 1
    assert filtered[0][0].doc_id == "doc_1"


@pytest.mark.asyncio
async def test_policy_rag_service_hybrid_search(mem_vector_store):
    """Verify PolicyRagService hybrid search and ranking with self-seeded corpus."""
    provider = LocalDeterministicEmbeddingProvider(dim=64)
    # Seed test-only policy docs into the vector store (upsert is synchronous)
    v1 = await provider.embed_query("人工智能算力补贴")
    mem_vector_store.upsert(VectorDocument(
        doc_id="pol_hz_ai_voucher",
        collection="policies",
        title="杭州高新区超级个体与小微人工智能算力券补贴",
        content="人工智能算力补贴。杭州高新区。大模型微调。",
        metadata={
            "policy_id": "pol_hz_ai_voucher",
            "policy_level": "省市级",
            "category": "SUBSIDY",
            "subsidy_amount_max": 50000.0,
            "summary": "人工智能算力券补贴",
            "eligible_conditions": ["杭州注册"],
            "legal_basis": "测试规约",
        },
        vector=v1,
    ))
    v2 = await provider.embed_query("增值税免征")
    mem_vector_store.upsert(VectorDocument(
        doc_id="pol_vat_free",
        collection="policies",
        title="小规模纳税人季度30万免征增值税",
        content="小规模纳税人增值税免征政策。",
        metadata={
            "policy_id": "pol_vat_free",
            "policy_level": "国家级",
            "category": "TAX",
            "subsidy_amount_max": 9000.0,
            "summary": "增值税免征",
            "eligible_conditions": ["小规模"],
            "legal_basis": "测试规约",
        },
        vector=v2,
    ))

    service = PolicyRagService(vector_store=mem_vector_store, embedding_provider=provider)
    res = await service.search_policies(query="人工智能算力补贴", top_k=3)
    assert res["status"] == "SUCCESS"
    assert res["total_matched"] >= 1
    # Top match should be AI compute voucher doc
    top_policy = res["results"][0]
    assert "算力" in top_policy["title"] or "人工智能" in top_policy["title"]


@pytest.mark.asyncio
async def test_forum_rag_service_qa(mem_vector_store):
    """Verify ForumRagService community search and expert Q&A with self-seeded corpus."""
    provider = LocalDeterministicEmbeddingProvider(dim=64)
    # Seed test-only forum thread into the vector store (upsert is synchronous)
    v = await provider.embed_query("Stripe 结汇")
    mem_vector_store.upsert(VectorDocument(
        doc_id="th_stripe_cross_border",
        collection="forum_threads",
        title="独立开发者 Stripe 绑定万里汇香港对公户结汇流程避坑指南",
        content="Stripe 结汇收款避免银行风控的实战流程。",
        metadata={
            "thread_id": "th_stripe_cross_border",
            "category_code": "DEV",
            "author_id": "usr_test",
            "upvote_count": 0,
            "comment_count": 0,
        },
        vector=v,
    ))

    service = ForumRagService(vector_store=mem_vector_store, embedding_provider=provider)
    qa_res = await service.ask_forum_rag(question="独立开发者如何结汇收款避免被银行风控？", top_k=2)
    assert qa_res["status"] == "SUCCESS"
    assert "ai_answer" in qa_res
    assert len(qa_res["referenced_threads"]) >= 1
    # Check that Stripe thread is among top referenced
    titles = [t["title"] for t in qa_res["referenced_threads"]]
    assert any("Stripe" in t or "结汇" in t for t in titles)


def test_gateway_dispatch_rag_scenarios():
    """Verify unified dispatch gateway executes RAG scenarios end-to-end."""
    # Seed test-only corpus into the shared vector store so gateway RAG has data
    import asyncio
    from src.core.rag import default_vector_store, LocalDeterministicEmbeddingProvider, VectorDocument
    provider = LocalDeterministicEmbeddingProvider(dim=128)

    async def _seed():
        pv = await provider.embed_query("算力券补贴")
        default_vector_store.upsert(VectorDocument(
            doc_id="gw_pol_ai_voucher",
            collection="policies",
            title="小微企业长三角算力券补贴",
            content="小微企业可以申领长三角算力券补贴政策。",
            metadata={
                "policy_id": "gw_pol_ai_voucher",
                "policy_level": "省市级",
                "category": "SUBSIDY",
                "subsidy_amount_max": 50000.0,
                "summary": "算力券补贴",
                "eligible_conditions": ["长三角"],
                "legal_basis": "测试规约",
            },
            vector=pv,
        ))
        tv = await provider.embed_query("算力券补贴")
        default_vector_store.upsert(VectorDocument(
            doc_id="gw_th_stripe",
            collection="forum_threads",
            title="小微企业 Stripe 结汇算力券申领经验",
            content="长三角算力券补贴申领流程，Stripe 结汇实战。",
            metadata={
                "thread_id": "gw_th_stripe",
                "category_code": "DEV",
                "author_id": "usr_test",
                "upvote_count": 0,
                "comment_count": 0,
            },
            vector=tv,
        ))

    asyncio.run(_seed())
    client = TestClient(app)

    # 1. Policy RAG Search Scenario
    res1 = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "external.rag.policy_search",
            "payload": {
                "query": "免税与小规模纳税人",
                "top_k": 3
            }
        }
    )
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["scenario"] == "external.rag.policy_search"
    assert body1["data"]["status"] == "SUCCESS"
    assert len(body1["data"]["results"]) > 0

    # 2. Forum RAG Q&A Scenario
    res2 = client.post(
        "/api/welcom/opc_world",
        json={
            "scenario": "external.rag.forum_qa",
            "payload": {
                "question": "小微企业可以申领长三角算力券补贴吗？",
                "top_k": 2
            }
        }
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["scenario"] == "external.rag.forum_qa"
    assert body2["data"]["status"] == "SUCCESS"
    assert "ai_answer" in body2["data"]
    assert len(body2["data"]["referenced_threads"]) > 0
