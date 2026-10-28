"""Lightweight SQLite-backed RAG and Vector Retrieval Engine."""
from .embeddings import (
    cosine_similarity,
    LocalDeterministicEmbeddingProvider,
    SiliconFlowEmbeddingProvider,
    get_default_embedding_provider,
)
from .vector_store import (
    BaseVectorStore,
    VectorDocument,
    SQLiteVectorStore,
    PGVectorStore,
    get_vector_store,
    default_vector_store,
)
from .service import (
    PolicyRagService,
    ForumRagService,
    ProductRagService,
    policy_rag_service,
    forum_rag_service,
    product_rag_service,
)

__all__ = [
    "cosine_similarity",
    "LocalDeterministicEmbeddingProvider",
    "SiliconFlowEmbeddingProvider",
    "get_default_embedding_provider",
    "BaseVectorStore",
    "VectorDocument",
    "SQLiteVectorStore",
    "PGVectorStore",
    "get_vector_store",
    "default_vector_store",
    "PolicyRagService",
    "ForumRagService",
    "ProductRagService",
    "policy_rag_service",
    "forum_rag_service",
    "product_rag_service",
]
