# 架构决策记录 (ADR)：全文检索与多维筛选引擎选型 (Elasticsearch)

- **编号**：ADR-004
- **状态**：ACCEPTED
- **日期**：2026-10-16
- **作者**：hardstone & Antigravity

---

## [VIBE_CONTRACT] 架构决策契约 (Machine-Actionable Decision)
```yaml
adr_decision_contract:
  adr_id: "ADR-004"
  status: "ACCEPTED"
  scope: "搜索中枢 / 政策全文倒排索引"
  locked_decision: "采用 Elasticsearch 8.x 作为全站全文搜索引擎，结合 IK Analysis (ik_max_word / ik_smart) 提供高精度中文分词、高亮显示与聚合筛选"

search_stack_versions:
  engine: "Elasticsearch >= 8.12.0"
  chinese_analyzer: "analysis-ik (IK Analyzer) >= 8.12.0"
  sync_pattern: "PostgreSQL 写操作通过异步任务或 CDC (如 Logstash/Debezium/Celery Hook) 同步至 ES"

guardrails:
  - "MUST: 官方政策原文全文检索、论坛帖子搜索、全局 Cmd+K 搜索由 Elasticsearch 负责，主写库仍以 PostgreSQL 为权威真理源"
  - "MUST: 搜索接口必须支持高亮标记 (Highlighting) 与拼音纠错降级"
  - "FORBIDDEN: 严禁将订单、支付流水、用户敏感鉴权信息存储于 Elasticsearch"
```

---

## [HUMAN_RATIONALE] 决策背景与多方案论证 (Human Rationale & Options)

### 1. 背景与问题阐述 (Context)
政策文件通常长达数千甚至上万字，包含大量专业法律与政务名词。PostgreSQL 自带的全文检索在中文分词精度（分词颗粒度、同义词库、热词更新）和复杂多维度分面聚合（Faceting Aggregations）上无法与专业搜索引擎相比。为了提供毫秒级、支持高亮显示与模糊容错的全局搜索体验（Cmd+K），需要引入专业搜索引擎。

### 2. 备选方案权衡 (Options Considered)

| 维度 | 方案 A：Elasticsearch 8.x (最终采纳) | 方案 B：Meilisearch | 方案 C：仅使用 PG 内置全文检索 (pg_trgm) |
| :--- | :--- | :--- | :--- |
| **中文分词与政务词库** | **极强**。IK 分词器支持自定义政务同义词库与热词热更新，分词精准度工业级验证 | 较好，但对于复杂政务长文档的精准分词控制力弱于 IK | 较弱，三元词组 (trigram) 检索占用空间大且无语义分词 |
| **聚合分析与分面筛选** | **行业天花板**。毫秒级完成地域、主体、金额范围的分面聚合统计 | 仅支持基础过滤，不支持复杂多层级聚合统计 | 依赖复杂 SQL GROUP BY，高并发下消耗大量 DB 连接 |
| **生态成熟度与 SDK** | 极度成熟，官方提供高性能 `elasticsearch-py` 异步驱动 | 发展迅速但小众，部分边缘特性生态不足 | 无需额外服务，但功能受限 |

### 3. 决策结果与详细理由 (Decision & Rationale)
采纳 **方案 A (Elasticsearch 8.x)**：
1. **强大的中文与分面搜索能力**：满足政策多维度标签统计（“各城市分别有多少条补贴”、“增值税类别的政策分布”）；
2. **极速全局搜索体验**：支撑前端快捷键 `Cmd+K` 的即时搜索与高亮渲染；
3. **职责分离架构**：PostgreSQL 专注于高可靠事务读写与向量混合检索，Elasticsearch 专注于高频只读全文搜索，构建起坚固的读写分离防御体系。
