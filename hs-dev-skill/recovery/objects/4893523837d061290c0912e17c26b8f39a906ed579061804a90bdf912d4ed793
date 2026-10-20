# 架构决策记录 (ADR)：核心关系型数据库与持久化选型

- **编号**：ADR-002
- **状态**：ACCEPTED
- **日期**：2026-10-16
- **作者**：hardstone & Antigravity

---

## [VIBE_CONTRACT] 架构决策契约 (Machine-Actionable Decision)
```yaml
adr_decision_contract:
  adr_id: "ADR-002"
  status: "ACCEPTED"
  scope: "后端持久层 / 关系型数据库"
  locked_decision: "核心业务数据采用 PostgreSQL 16+ 存储，ORM 采用 SQLAlchemy 2.0 异步模式结合 asyncpg 驱动，数据库结构迁移使用 Alembic"

db_stack_versions:
  db_engine: "PostgreSQL >= 16.0"
  db_driver: "asyncpg >= 0.29.0"
  orm_framework: "SQLAlchemy >= 2.0.28"
  migration_tool: "Alembic >= 1.13.0"

guardrails:
  - "MUST: 所有数据库 I/O 必须通过 async/await 异步会话 (AsyncSession) 执行，严禁混入同步阻塞驱动"
  - "MUST: 政策元数据、厂商扩展字段等半结构化信息统一采用 PostgreSQL 原生 JSONB 类型存储并建立 GIN 索引"
  - "MUST: 所有的表结构变更必须通过 Alembic 生成版本化可回滚的迁移脚本，严禁直接在生产环境执行手工 DDL"
```

---

## [HUMAN_RATIONALE] 决策背景与多方案论证 (Human Rationale & Options)

### 1. 背景与问题阐述 (Context)
OpcHub 拥有用户、审核流水、SOP 进度、交易佣金等强事务强一致性关系数据，同时也有政策详情、厂商权益参数等半结构化数据。需要一款既具备严苛 ACID 事务保障，又具备灵活扩展能力的顶级开源关系型数据库。

### 2. 备选方案权衡 (Options Considered)

| 维度 | 方案 A：PostgreSQL 16+ (最终采纳) | 方案 B：MySQL 8.0 | 方案 C：MongoDB |
| :--- | :--- | :--- | :--- |
| **JSON 半结构化支持** | **原生 JSONB + GIN 索引**，查询与检索速度媲美专用文档数据库 | 支持 JSON 字段，但索引能力与嵌套查询语法相对笨拙 | 天然文档模型，但缺乏强事务关系建模能力 |
| **生态扩展能力 (Extensions)** | **业界最强**。原生支持 `pgvector` 向量扩展，避免引入额外向量数据库 | 无成熟原生向量插件，需依赖外部 Milvus/Qdrant | 仅云上 Atlas 提供向量搜索，自建运维成本高 |
| **异步高并发性能** | 配合 `asyncpg` 性能极其卓越，内存管理优异 | 异步驱动生态相比略逊色 | 异步支持良好但事务成本高 |

### 3. 决策结果与详细理由 (Decision & Rationale)
采纳 **方案 A (PostgreSQL 16+)**：
1. **JSONB 原生能力**：满足政策多变字段与厂商不同 Deals 规则的高效存储；
2. **为 pgvector 奠定基石**：无需部署单独的独立向量库，直接在单机 PostgreSQL 内即可兼顾事务与高维向量搜索；
3. **企业级开源首选**：成熟度与社区活跃度极高，单机足以支撑数百万级创客数据。
