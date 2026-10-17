"""Embedding providers for lightweight RAG vector indexing."""
import hashlib
import math
from typing import List, Optional
from src.core.config import settings


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate cosine similarity between two numeric vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    sim = dot / (norm_a * norm_b)
    return round(float(sim), 6)


class LocalDeterministicEmbeddingProvider:
    """Zero-dependency local embedding provider producing deterministic high-entropy vectors."""

    def __init__(self, dim: Optional[int] = None):
        self.dim = dim or getattr(settings, "rag_vector_dim", 128)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Compute L2-normalized dense embedding vectors for input texts."""
        embeddings = []
        for text in texts:
            vec = [0.0] * self.dim
            # Tokens include single characters and 2-grams
            clean_text = text.strip()
            if not clean_text:
                embeddings.append(vec)
                continue

            tokens = [clean_text[i:i+2] for i in range(max(1, len(clean_text) - 1))] + list(clean_text)
            for tok in tokens:
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dim
                weight = 1.0 + (h % 7) * 0.1
                vec[idx] += weight

            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            norm_vec = [round(x / norm, 6) for x in vec]
            embeddings.append(norm_vec)

        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Compute embedding vector for a single query."""
        res = await self.embed_texts([query])
        return res[0] if res else [0.0] * self.dim


class SiliconFlowEmbeddingProvider:
    """Hybrid embedding provider that uses SiliconFlow API when available, falling back to local."""

    def __init__(self, model: Optional[str] = None, dim: Optional[int] = None):
        from src.infrastructure.external_gateway.ai_gateway import siliconflow_gateway
        self.gateway = siliconflow_gateway
        self.model = model or getattr(settings, "rag_embedding_model", "BAAI/bge-large-zh-v1.5")
        self.fallback_provider = LocalDeterministicEmbeddingProvider(dim=dim)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            res = await self.gateway.get_embeddings(texts=texts, model=self.model)
            if res.get("status") == "SUCCESS" and "embeddings" in res and res["embeddings"]:
                return res["embeddings"]
        except Exception as exc:
            import logging
            logging.getLogger("opchub.rag").debug("SiliconFlow embedding call fallback: %s", exc)
        return await self.fallback_provider.embed_texts(texts)

    async def embed_query(self, query: str) -> List[float]:
        res = await self.embed_texts([query])
        return res[0] if res else [0.0] * self.fallback_provider.dim


def get_default_embedding_provider():
    """Factory creating configured embedding provider."""
    return SiliconFlowEmbeddingProvider()
