# 架构决策记录 (ADR)：向量检索与语义匹配架构选型 (pgvector)

- **编号**：ADR-003
- **状态**：ACCEPTED
- **日期**：2026-10-16
- **作者**：hardstone & Antigravity

---

## [VIBE_CONTRACT] 架构决策契约 (Machine-Actionable Decision)
```yaml
adr_decision_contract:
  adr_id: "ADR-003"
  status: "ACCEPTED"
  scope: "智能推荐引擎 / 政策向量检索"
  locked_decision: "采用 PostgreSQL 原生扩展 pgvector 存储政策 Embedding 向量，并使用 HNSW 索引实现高精度近邻语义匹配"

vector_stack_versions:
  vector_extension: "pgvector >= 0.7.0"
  embedding_dimension: "1536 (OpenAI text-embedding-3-small) 或 1024 (BAAI/bge-large-zh-v1.5)"
  index_type: "HNSW (Hierarchical Navigable Small World)"
  metric: "cosine (余弦相似度) 或 inner product"

guardrails:
  - "MUST: 政策向量表必须与政策主实体表处于同一 PostgreSQL 实例，通过外键直接关联，避免跨库数据不一致"
  - "MUST: 向量检索必须采用 HNSW 索引（参数 `m=16, ef_construction=64`），确保万级政策检索耗时小于 15ms"
  - "FORBIDDEN: 在 MVP 阶段禁止引入独立的外部向量数据库（如 Milvus / Pinecone / Chroma），杜绝过度工程化"
```

---

## [HUMAN_RATIONALE] 决策背景与多方案论证 (Human Rationale & Options)

### 1. 背景与问题阐述 (Context)
政策匹配不仅需要传统精确字段筛选（如“必须在杭州”），更需要基于创客业务描述进行“语义匹配”。例如创客输入“我在做一款针对跨境电商的自动化文案生成工具”，系统需智能关联到“数字文化出海创新券”或“跨境电商小微主体扶持”，这无法靠关键词完全命中，必须依赖向量 Embedding 检索。

### 2. 备选方案权衡 (Options Considered)

| 维度 | 方案 A：PostgreSQL + pgvector (最终采纳) | 方案 B：独立部署 Milvus / Qdrant | 方案 C：云厂商全托管向量库 |
| :--- | :--- | :--- | :--- |
| **运维复杂度** | **极低**。直接作为 PG 扩展运行，零额外服务进程，统一备份与容灾 | **高**。需独立部署分布式组件、etcd、MinIO 等，一人维护负担重 | **中**。绑定云厂商，存在长期的账单开销与网络延迟 |
| **混合检索能力 (Hybrid Query)** | **完美原生支持**。可在单条 SQL 中同时使用 `WHERE city = 'hangzhou'` 与 `ORDER BY embedding <=> query_vec` | 弱。需两阶段跨服务查询并在应用层手动合并过滤 | 同方案 B |
| **性能与容量** | 支持数百万级向量低延迟检索，完全满足 OPC 业务规模 | 适合亿级超大规模，对当前项目严重性能过剩 | 适合海量多租户 |

### 3. 决策结果与详细理由 (Decision & Rationale)
采纳 **方案 A (pgvector)**：
1. **统一数据源**：关系业务数据与向量数据在同一张表或同一个库中，彻底消除了数据双写同步的分布式事务问题；
2. **极简极客运维**：一个 Docker 容器或一台云数据库即可搞定全套关系+向量检索，极大降低基础设施硬开销；
3. **强大的 HNSW 索引**：pgvector 0.7+ 版本的 HNSW 算法在万级到百万级数据量下性能极高，毫秒级召回。
