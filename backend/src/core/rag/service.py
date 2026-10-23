"""RAG Service coordinating VectorStore, EmbeddingProviders, and AI Gateways."""
import asyncio
from typing import Any, Dict, List, Optional

from src.infrastructure.external_gateway.ai_gateway import siliconflow_gateway
from .embeddings import get_default_embedding_provider
from .vector_store import BaseVectorStore, VectorDocument, default_vector_store


class PolicyRagService:
    """RAG-enhanced policy semantic retriever and matcher."""

    COLLECTION_NAME = "policies"

    def __init__(self, vector_store: Optional[BaseVectorStore] = None, embedding_provider=None):
        self.vector_store = vector_store or default_vector_store
        self.embedding_provider = embedding_provider or get_default_embedding_provider()
        self._ensure_indexed()

    def _ensure_indexed(self):
        """Ensure default policies are indexed in vector store."""
        if self.vector_store.count(self.COLLECTION_NAME) > 0:
            return

        from src.domains.policies.service import policy_service
        policies = policy_service.list_policies()

        async def _index_all():
            docs = []
            for p in policies:
                # Text for embedding includes title, summary, conditions, and legal basis
                full_text = f"{p.title}。{p.summary}。适用条件：{'；'.join(p.eligible_conditions)}。依据：{p.legal_basis}"
                vec = await self.embedding_provider.embed_query(full_text)
                doc = VectorDocument(
                    doc_id=p.id,
                    collection=self.COLLECTION_NAME,
                    title=p.title,
                    content=full_text,
                    metadata={
                        "policy_id": p.id,
                        "code": getattr(p, "code", "POL-2026-001"),
                        "region": getattr(p, "region", "全国统一"),
                        "deadline": getattr(p, "deadline", "常年有效"),
                        "action_text": getattr(p, "action_text", "匹配资格"),
                        "policy_level": p.policy_level,
                        "category": p.category,
                        "subsidy_amount_max": p.subsidy_amount_max,
                        "summary": p.summary,
                        "eligible_conditions": p.eligible_conditions,
                        "legal_basis": p.legal_basis,
                    },
                    vector=vec,
                )
                docs.append(doc)
            self.vector_store.upsert_batch(docs)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_index_all())
            else:
                loop.run_until_complete(_index_all())
        except RuntimeError:
            asyncio.run(_index_all())

    async def search_policies(
        self,
        query: str,
        top_k: int = 5,
        region: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform semantic hybrid search on policy corpus."""
        if self.vector_store.count(self.COLLECTION_NAME) == 0:
            # Re-index synchronously if empty
            from src.domains.policies.service import policy_service
            policies = policy_service.list_policies()
            docs = []
            for p in policies:
                full_text = f"{p.title}。{p.summary}。适用条件：{'；'.join(p.eligible_conditions)}。依据：{p.legal_basis}"
                vec = await self.embedding_provider.embed_query(full_text)
                docs.append(VectorDocument(
                    doc_id=p.id,
                    collection=self.COLLECTION_NAME,
                    title=p.title,
                    content=full_text,
                    metadata={
                        "policy_id": p.id,
                        "code": getattr(p, "code", "POL-2026-001"),
                        "region": getattr(p, "region", "全国统一"),
                        "deadline": getattr(p, "deadline", "常年有效"),
                        "action_text": getattr(p, "action_text", "匹配资格"),
                        "policy_level": p.policy_level,
                        "category": p.category,
                        "subsidy_amount_max": p.subsidy_amount_max,
                        "summary": p.summary,
                        "eligible_conditions": p.eligible_conditions,
                        "legal_basis": p.legal_basis,
                    },
                    vector=vec,
                ))
            self.vector_store.upsert_batch(docs)

        query_vec = await self.embedding_provider.embed_query(query)
        filter_meta = {}
        if category:
            filter_meta["category"] = category

        vector_results = self.vector_store.search_similarity(
            collection=self.COLLECTION_NAME,
            query_vector=query_vec,
            top_k=top_k * 2,
            filter_meta=filter_meta if filter_meta else None
        )

        # Hybrid scoring with keyword and region boosts
        ranked_policies = []
        for doc, sim in vector_results:
            meta = doc.metadata
            score = sim * 10.0  # Base vector score out of 10

            # Boost if query keyword hits title or conditions directly
            if any(term in doc.title for term in query.split() if len(term) >= 2):
                score += 3.0
            if region and region in doc.content:
                score += 2.0

            ranked_policies.append({
                "id": meta.get("policy_id", doc.doc_id),
                "policy_id": meta.get("policy_id", doc.doc_id),
                "code": meta.get("code", "POL-2026-001"),
                "region": meta.get("region", "全国统一"),
                "deadline": meta.get("deadline", "常年有效"),
                "action_text": meta.get("action_text", "匹配资格"),
                "title": doc.title,
                "similarity_score": round(sim, 4),
                "final_relevance": round(score, 2),
                "policy_level": meta.get("policy_level", "国家级"),
                "category": meta.get("category", "TAX"),
                "subsidy_amount_max": meta.get("subsidy_amount_max", 0.0),
                "summary": meta.get("summary", ""),
                "eligible_conditions": meta.get("eligible_conditions", []),
                "legal_basis": meta.get("legal_basis", ""),
            })

        ranked_policies.sort(key=lambda x: x["final_relevance"], reverse=True)
        return {
            "status": "SUCCESS",
            "query": query,
            "total_matched": len(ranked_policies),
            "results": ranked_policies[:top_k]
        }


class ForumRagService:
    """RAG-enhanced community Q&A and experience retrieval service."""

    COLLECTION_NAME = "forum_threads"

    def __init__(self, vector_store: Optional[BaseVectorStore] = None, embedding_provider=None):
        self.vector_store = vector_store or default_vector_store
        self.embedding_provider = embedding_provider or get_default_embedding_provider()
        self.ai_gateway = siliconflow_gateway
        self._ensure_indexed()

    def _ensure_indexed(self):
        if self.vector_store.count(self.COLLECTION_NAME) > 0:
            return

        from src.domains.forum.service import ForumService
        forum_svc = ForumService()
        threads = list(forum_svc._threads.values())

        async def _index_all():
            docs = []
            for t in threads:
                full_text = f"{t.title}\n{t.content}"
                vec = await self.embedding_provider.embed_query(full_text)
                doc = VectorDocument(
                    doc_id=t.id,
                    collection=self.COLLECTION_NAME,
                    title=t.title,
                    content=full_text,
                    metadata={
                        "thread_id": t.id,
                        "category_code": t.category_code,
                        "author_id": t.author_id,
                        "upvote_count": t.upvote_count,
                        "comment_count": t.comment_count,
                    },
                    vector=vec,
                )
                docs.append(doc)
            self.vector_store.upsert_batch(docs)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_index_all())
            else:
                loop.run_until_complete(_index_all())
        except RuntimeError:
            asyncio.run(_index_all())

    async def search_threads(
        self,
        query: str,
        top_k: int = 15,
        category_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search forum threads via semantic vector similarity and NLP keyword weighting."""
        import re
        from src.domains.forum.service import forum_service
        all_threads = [t for t in forum_service._threads.values() if t.id not in getattr(forum_service, "_deleted_thread_ids", set())]
        if self.vector_store.count(self.COLLECTION_NAME) < len(all_threads) or self.vector_store.count(self.COLLECTION_NAME) == 0:
            docs = []
            for t in all_threads:
                full_text = f"{t.title}\n{t.content}"
                vec = await self.embedding_provider.embed_query(full_text)
                docs.append(VectorDocument(
                    doc_id=t.id,
                    collection=self.COLLECTION_NAME,
                    title=t.title,
                    content=full_text,
                    metadata={
                        "thread_id": t.id,
                        "category_code": (t.category_code or "GEN").upper(),
                        "author_id": t.author_id,
                        "upvote_count": t.upvote_count,
                        "comment_count": t.comment_count,
                    },
                    vector=vec,
                ))
            self.vector_store.upsert_batch(docs)

        query_vec = await self.embedding_provider.embed_query(query)
        cat_filter = category_code.upper() if category_code and category_code.upper() != "ALL" else None
        filter_meta = {"category_code": cat_filter} if cat_filter else None
        matches = self.vector_store.search_similarity(
            collection=self.COLLECTION_NAME,
            query_vector=query_vec,
            top_k=max(top_k * 2, 20),
            filter_meta=filter_meta
        )

        query_lower = query.strip().lower()
        tokens = [w for w in re.split(r'[\s,，.。!！?？、/\\;；]+', query_lower) if len(w) >= 2]
        if not tokens and len(query_lower) >= 2:
            tokens = [query_lower]

        scored_results = []
        for doc, sim in matches:
            tid = str(doc.metadata.get("thread_id", doc.doc_id))
            full_t = forum_service._threads.get(tid)
            t_dict = full_t.model_dump() if full_t else {
                "id": tid,
                "title": doc.title,
                "content": doc.content,
                "category_code": doc.metadata.get("category_code", "GEN"),
                "upvote_count": doc.metadata.get("upvote_count", 0),
                "comment_count": doc.metadata.get("comment_count", 0),
            }

            score = float(sim)
            title_lower = (t_dict.get("title") or "").lower()
            content_lower = (t_dict.get("content") or "").lower()
            tag_list = [str(tg).lower() for tg in (t_dict.get("tags") or [])]

            keyword_hits = 0
            for tok in tokens:
                if tok in title_lower:
                    score += 0.25
                    keyword_hits += 1
                elif any(tok in tag for tag in tag_list):
                    score += 0.15
                    keyword_hits += 1
                elif tok in content_lower:
                    score += 0.08
                    keyword_hits += 1

            bounded_sim = min(0.999, max(0.1, score))
            semantic_score = round(bounded_sim * 100, 1)

            t_dict["similarity"] = round(bounded_sim, 4)
            t_dict["similarity_score"] = round(bounded_sim, 4)
            t_dict["semantic_score"] = semantic_score
            t_dict["keyword_hits"] = keyword_hits
            scored_results.append((bounded_sim, t_dict))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_results[:top_k]]

    async def ask_forum_rag(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Answer question by retrieving community threads and synthesizing answer via LLM."""
        matched_threads = await self.search_threads(query=question, top_k=top_k)

        # Format context from retrieved threads
        context_snippets = []
        for i, item in enumerate(matched_threads, 1):
            snippet = item.get("content_snippet") or (item.get("content") or "")[:150]
            context_snippets.append(f"【参考经验 {i}】《{item.get('title')}》：{snippet}")
        context_text = "\n\n".join(context_snippets) if context_snippets else "暂无直接相关的社区经验。"

        prompt = (
            f"独立创客提问：{question}\n\n"
            f"社区检索到的经验依据：\n{context_text}\n\n"
            f"请为创客提供一份约150字、言之有物、合规避坑的落地解答。在回答中请直接点明参考的经验主题或要点。"
        )

        system_prompt = (
            "你是一位专精中国一人公司（OPC）与自由职业创客的AI互助专家。"
            "善于结合真实实战经验给出接地气、合规可靠的避坑建议。"
        )

        chat_res = await self.ai_gateway.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return {
            "status": "SUCCESS",
            "question": question,
            "ai_answer": chat_res.get("reply_text", "未能生成解答"),
            "model_used": chat_res.get("model", self.ai_gateway.default_model),
            "referenced_threads": matched_threads,
            "tokens_consumed": chat_res.get("usage", {}).get("total_tokens", 180)
        }


class ProductRagService:
    """RAG and NLP semantic similarity retriever for maker showcase products."""

    COLLECTION_NAME = "products"

    def __init__(self, vector_store: Optional[BaseVectorStore] = None, embedding_provider=None):
        self.vector_store = vector_store or default_vector_store
        self.embedding_provider = embedding_provider or get_default_embedding_provider()
        self._ensure_indexed()

    def _ensure_indexed(self):
        from src.domains.products.service import product_service
        products = list(product_service._products.values())
        if not products:
            return
        if self.vector_store.count(self.COLLECTION_NAME) >= len(products):
            return

        async def _index_all():
            docs = []
            for p in products:
                full_text = f"{p.title}。{p.tagline or ''}。{p.description or ''}。分类：{p.category or ''}"
                vec = await self.embedding_provider.embed_query(full_text)
                docs.append(VectorDocument(
                    doc_id=p.id,
                    collection=self.COLLECTION_NAME,
                    title=p.title,
                    content=full_text,
                    metadata={
                        "product_id": p.id,
                        "category": p.category or "",
                        "tagline": p.tagline or "",
                    },
                    vector=vec,
                ))
            self.vector_store.upsert_batch(docs)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_index_all())
            else:
                loop.run_until_complete(_index_all())
        except RuntimeError:
            asyncio.run(_index_all())

    async def search_products(
        self,
        query: str,
        top_k: int = 15,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search products via semantic vector similarity and NLP keyword weighting."""
        import re
        from src.domains.products.service import product_service
        products = list(product_service._products.values())
        if self.vector_store.count(self.COLLECTION_NAME) < len(products) or self.vector_store.count(self.COLLECTION_NAME) == 0:
            docs = []
            for p in products:
                full_text = f"{p.title}。{p.tagline or ''}。{p.description or ''}。分类：{p.category or ''}"
                vec = await self.embedding_provider.embed_query(full_text)
                docs.append(VectorDocument(
                    doc_id=p.id,
                    collection=self.COLLECTION_NAME,
                    title=p.title,
                    content=full_text,
                    metadata={
                        "product_id": p.id,
                        "category": p.category or "",
                        "tagline": p.tagline or "",
                    },
                    vector=vec,
                ))
            self.vector_store.upsert_batch(docs)

        query_vec = await self.embedding_provider.embed_query(query)
        cat_filter = category.strip() if category and category != "ALL" else None
        filter_meta = {"category": cat_filter} if cat_filter else None

        matches = self.vector_store.search_similarity(
            collection=self.COLLECTION_NAME,
            query_vector=query_vec,
            top_k=max(top_k * 2, 20),
            filter_meta=filter_meta
        )

        query_lower = query.strip().lower()
        tokens = [w for w in re.split(r'[\s,，.。!！?？、/\\;；]+', query_lower) if len(w) >= 2]
        if not tokens and len(query_lower) >= 2:
            tokens = [query_lower]

        scored_results = []
        for doc, sim in matches:
            pid = str(doc.metadata.get("product_id", doc.doc_id))
            prod = product_service._products.get(pid)
            p_dict = prod.model_dump() if prod else {
                "id": pid,
                "title": doc.title,
                "category": doc.metadata.get("category", ""),
                "tagline": doc.metadata.get("tagline", ""),
            }

            score = float(sim)
            title_lower = (p_dict.get("title") or "").lower()
            tagline_lower = (p_dict.get("tagline") or "").lower()
            desc_lower = (p_dict.get("description") or "").lower()
            cat_lower = (p_dict.get("category") or "").lower()

            keyword_hits = 0
            for tok in tokens:
                if tok in title_lower:
                    score += 0.3
                    keyword_hits += 1
                elif tok in cat_lower:
                    score += 0.2
                    keyword_hits += 1
                elif tok in tagline_lower:
                    score += 0.15
                    keyword_hits += 1
                elif tok in desc_lower:
                    score += 0.08
                    keyword_hits += 1

            bounded_sim = min(0.999, max(0.1, score))
            semantic_score = round(bounded_sim * 100, 1)

            p_dict["similarity"] = round(bounded_sim, 4)
            p_dict["similarity_score"] = round(bounded_sim, 4)
            p_dict["semantic_score"] = semantic_score
            p_dict["keyword_hits"] = keyword_hits
            scored_results.append((bounded_sim, p_dict))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_results[:top_k]]


# Singletons
policy_rag_service = PolicyRagService()
forum_rag_service = ForumRagService()
product_rag_service = ProductRagService()
