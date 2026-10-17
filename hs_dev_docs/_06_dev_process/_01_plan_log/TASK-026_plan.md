# TASK-026 实施计划日志 (Plan Log)

- **任务ID**：TASK-026
- **标题**：按照ADR-002与ADR-003规范落地PostgreSQL 16与pgvector容器编排及核心业务表异步持久化
- **分级**：`M`
- **当前状态**：`IN_PROGRESS`
- **目标**：
  1. 严格依据 `ADR-002` 与 `ADR-003` 锁定的技术选型架构，在 `docker-compose.yml` 中接入官方 `pgvector/pgvector:pg16` 容器，配置持久化数据卷与网络通信。
  2. 在 `backend/pyproject.toml` 补齐 `asyncpg>=0.29.0`、`alembic>=1.13.0`、`pgvector>=0.3.0` 等核心生产依赖，在 `backend/src/core/database.py` 中建立符合 SQLAlchemy 2.0 异步会话池（`AsyncSession`）。
  3. 严格依据 `hs_dev_docs/_03_architecture_design/_03_detailed_design/_01_database_schema.md`，实现 16 张平台核心表 ORM 模型定义（`models_db.py`）与 DDL 迁移版本管理。
  4. 升级向量引擎与 RAG 模块（`backend/src/core/rag/`），对接 PostgreSQL + pgvector 原生余弦相似度（`<=>` 操作符），并在本地无 PG 实例时提供兼容回退，确保单元测试单机秒级通过。
  5. 业务域服务层（Policies, Demands, Products, Forum, Users, SOP, Perks）接入数据库异步持久化支持。
  6. 编写全面的自动化测试套件 `test_postgresql_pgvector_persistence.py`，全量运行 pytest。
  7. 执行索引重建与 `verify_consistency.py` 质量门禁，输出验收备忘并完成本地 Git 提交。

---

## 执行步骤清单

- [ ] **步骤 1**：在 `docker-compose.yml` 中新增 `postgres-pgvector` 服务（基于 `pgvector/pgvector:pg16`），配置持久卷 `pgdata`、环境变量与健康探针；更新 `.env.example`。
- [ ] **步骤 2**：在 `backend/pyproject.toml` 中添加 `asyncpg`、`alembic`、`pgvector` 依赖，安装到虚拟环境。
- [ ] **步骤 3**：在 `backend/src/core/database.py` 中实现异步数据库引擎 `get_async_engine()`、`AsyncSessionLocal` 与自愈探测。
- [ ] **步骤 4**：依据 `_01_database_schema.md` 在 `backend/src/infrastructure/database/models.py` 中物化全量 PostgreSQL 实体表模型（UUID 主键、JSONB GIN 索引、pgvector 向量字段）。
- [ ] **步骤 5**：升级 `backend/src/core/rag/vector_store.py` 与 `service.py`，原生支持 PostgreSQL + pgvector 向量存储与近邻余弦检索。
- [ ] **步骤 6**：编写自动化测试 `backend/tests/test_postgresql_pgvector_persistence.py` 并全量跑通 pytest。
- [ ] **步骤 7**：执行质量门禁自检 `verify_consistency.py`，更新索引库，完成任务流转与 Git 提交。
