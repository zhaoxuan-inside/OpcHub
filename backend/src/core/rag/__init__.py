"""Lightweight SQLite-backed RAG and Vector Retrieval Engine."""
from .embeddings import (
    cosine_similarity,
    LocalDeterministicEmbeddingProvider,
    SiliconFlowEmbeddingProvider,
    get_default_embedding_provider,
)
from .vector_store import (
    VectorDocument,
    SQLiteVectorStore,
    default_vector_store,
)
from .service import (
    PolicyRagService,
    ForumRagService,
    policy_rag_service,
    forum_rag_service,
)

__all__ = [
    "cosine_similarity",
    "LocalDeterministicEmbeddingProvider",
    "SiliconFlowEmbeddingProvider",
    "get_default_embedding_provider",
    "VectorDocument",
    "SQLiteVectorStore",
    "default_vector_store",
    "PolicyRagService",
    "ForumRagService",
    "policy_rag_service",
    "forum_rag_service",
]
