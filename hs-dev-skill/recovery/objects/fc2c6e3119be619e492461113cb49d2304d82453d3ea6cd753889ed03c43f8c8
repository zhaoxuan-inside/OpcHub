# 任务计划：TASK-032 领域服务 PostgreSQL 持久化 · 写后落库 + 启动回灌

- **任务编号**：TASK-032
- **任务分级**：`L` (Large)
- **优先级**：`P0`
- **执行人**：agent
- **意图**：`IMPLEMENT / FIX`（补齐领域服务持久化，使平台工作状态跨进程重启不丢失；修复用户域凭据/档案写库失效的真实缺陷）
- **关联设计**：
  - [_01_database_schema.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_01_database_schema.md)（新增 §1.17 审计表 / §1.18 领域快照表）
  - [_04_framework_detailed_design.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_04_framework_detailed_design.md) §3.3 统一入站网关
  - [opchub_rbac_auth_architecture.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_rbac_auth_architecture.md) §1.1

---

## 1. 问题 (Problem)

TASK-028 已清除全部业务 mock/种子数据，但暴露了一个遗留缺口：**除 `user` 域外，所有领域服务以进程内字典作为唯一主存路径**，重启即丢数据。TASK-028 的交接记录亦明确标注“domain services 仍以内存为主路径，DB 持久化待补”。

进一步排查发现 `user` 域自身也存在**真实的持久化缺陷**：

1. `update_profile()` 修改了 ORM 对象却**从不 `commit()`** → 档案更新静默丢失（疑似“持久化”，实则未落库）；
2. `change_password()` 仅改内存 `password_hash` 与 `must_change_password` → 重启后**新密码失效、且强制改密标记丢失**（内置 admin 首次登录强制改密被绕过，属安全缺陷）；
3. `hydrate` 缺失：重启后 `get_profile(uid)` 因内存索引为空而返回空档案；
4. `login_by_email()` / `get_session_by_token()` 未从 DB `metadata_payload` 读取 `must_change_password`。

设计约束：领域服务方法基本为**同步**（被 DAG 同步算子与适配器调用），而数据库访问为**异步**，不能简单地把全部方法改成 `async`。

---

## 2. 实现方案 (Implementation)

### ① 领域聚合文档快照表 `domain_snapshots`

新增 ORM 模型 `DomainSnapshot`（`(domain, entity_id)` 复合主键 + `payload JSONB`），以 JSONB 文档持久化每个聚合的当前状态，天然契合“同步领域模型 ⇄ 异步存储”的边界。

### ② 写后持久化 + 启动回灌层 `persistence.py`

新增 `src/infrastructure/database/persistence.py`：

- `DomainPersistence.register(domain, hydrator)`：登记「文档族 → 内存索引重建函数」；
- `initialize()`：启动时探测 DB；可用则逐族 `load_domain_snapshots()` 回灌内存索引；不可用则整体降级为 no-op（保持平台既有优雅降级契约）；
- `write()/write_raw()/delete()`：**写后**（write-behind）——把落库协程调度到当前事件循环，绝不阻塞同步调用方；
- `_schedule()`：将写任务**串行链式排队**，保证同一聚合的多次变更按发生顺序落库（避免 view/comment count 等回写乱序）；
- `flush()`：关停前等待在途写任务。

仓储侧新增 `load_domain_snapshots` / `upsert_domain_snapshot` / `delete_domain_snapshot`，其中 UPSERT 使用 `INSERT ... ON CONFLICT DO UPDATE`（原子，避免并发写主键冲突），删除使用 `DELETE`。

### ③ 领域服务接线（15 个文档族）

| 服务 | 文档族 |
| --- | --- |
| forum | `forum.threads` / `forum.comments` / `forum.upvotes` / `forum.bookmarks` |
| products | `products.items` |
| policies | `policies.items` |
| demands | `demands.items` / `demands.bids` |
| perks | `perks.items` / `perks.claims` |
| sop | `sop.templates` / `sop.documents` |
| moderation | `moderation.items` |
| orchestration | `orchestration.dag_configs` / `orchestration.layouts` |

每个服务在变更点调用 `domain_persistence.write/delete`，并实现 `hydrate_*` 回灌函数（含 `upvotes`/`bookmarks`/`bids`/`claims` 等复合键结构）。`telemetry`（只读聚合）与 `compliance`（静态规则）无变更状态，无需持久化。

### ④ 用户域修复（以 `users` 表为唯一真实来源）

- 仓储新增 `get_user_by_uid` / `list_users` / `update_user_fields`（**含 `commit()`**，可更新昵称、公司、`password_hash` 与 `metadata_payload`）；
- `UserService.hydrate_from_db()`：启动时由 `users` 表回灌 `_users_by_uid` / `_users_by_email`；
- `update_profile()`：改为经 `update_user_fields()` 真正落库（修复静默丢失）；
- `change_password()`：改为 `async`，持久化新 `password_hash` 并写入 `metadata_payload.must_change_password=False`（修复重启后改密丢失）；
- `activate_entitlement()` / `deactivate_entitlement()`：改为 `async`，把 `active_entitlements` / `tier_name` 落库到 `metadata_payload`；
- `login_by_email()` / `get_session_by_token()`：从 DB `metadata_payload` 还原 `must_change_password`（修复首次登录强制改密在重启后被绕过）。

### ⑤ 生命周期接线

`main.py` lifespan：启动时 `ensure_schema_and_seed()` → `user_service.hydrate_from_db()` → `domain_persistence.initialize()`；关停时 `domain_persistence.flush()` → `dispose_engine()`（新增 `core/database.dispose_engine()` 释放连接池）。

### ⑥ 测试同步

- `activate_entitlement` / `deactivate_entitlement` / `change_password` 转 `async` 后同步更新调用点：`adapters.py`、`registry.py`（DAG 算子）与 `test_user_dag_pipeline.py`。
- `tests/conftest.py`：**默认套件强制数据库不可用**（`db_repository.is_ready` 打桩返回 False），保证单元测试封闭、可复现、无需基础设施——与平台“无库优雅降级”契约一致。
- 新增 `tests/test_domain_persistence.py`（封闭单测，注入 FakeRepo 验证回灌 / 写后 / 串行 / 降级）。
- 新增 `tests/test_db_persistence_integration.py`（**opt-in**，需 `OPCHUB_IT_DATABASE_URL`，默认 skip）端到端验证真实 PostgreSQL 重启持久化。

---

## 3. 验证证据 (Evidence)

- **全量回归（封闭）**：`python3 -m pytest tests/ -q` → **199 passed / 5 skipped**（0 fail / 0 error；5 项为需显式开启的 DB 集成用例）
- **静态检查**：`python3 -m pyflakes src/ tests/` → 仅剩 1 项有意 re-export（`orchestration/models.py:4`）
- **真实 PostgreSQL 集成**（`pgvector/pgvector:pg18`，`OPCHUB_IT_DATABASE_URL` 指向本地库）：
  `python3 -m pytest tests/test_db_persistence_integration.py -q` → **5 passed**（连续两轮通过，证明可重复）
  - forum 帖子/评论/点赞/收藏、products、policies、demands+投标、perks+核销、sop 模板+文书、orchestration DAG 配置+布局：**清空内存后回灌一致**；
  - 用户注册 → 档案更新 → 改密后：重启回灌档案字段正确、**新密码可登录**、`must_change_password` 持久化为 False。
- **端到端重启验证（真实 app lifespan + 统一网关）**：经 `POST /api/welcom/opc_world` 发帖/发布产品/点赞 → 关闭应用（flush）→ 清空全部内存索引 → 重新打开应用（lifespan 回灌）→ 网关查询：帖子与产品均恢复，`upvote_count` 正确保留。
- **写序与原子性**：并发写同一 `domain_snapshots` 主键不再产生 `UniqueViolationError`（改 `ON CONFLICT DO UPDATE`）；写任务串行链保证顺序。

---

## 4. 兼容性与迁移 (Migration Notes)

- **首次部署**：`ensure_schema_and_seed()` 会 `create_all` 自动建出 `domain_snapshots`（及既有表）；无需手工 DDL。
- **无库环境**：`domain_snapshots` 相关路径整体 no-op，平台退回“纯内存 + 优雅降级”，功能语义不变。
- **数据归属**：用户账号/凭据/权益以 `users` 表为准；`domain_snapshots` 不承载用户记录，避免双写分歧。
- **集成测试开关**：设置 `OPCHUB_IT_DATABASE_URL=postgresql+asyncpg://<user>:<pwd>@<host>:5432/<db>` 即可启用 DB 集成用例；未设置时自动跳过。
