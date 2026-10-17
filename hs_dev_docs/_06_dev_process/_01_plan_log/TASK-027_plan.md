# 任务计划：TASK-027 全业务领域服务 PostgreSQL 关系持久化与邮箱注册登录认证中心

- **任务编号**：TASK-027
- **任务分级**：`L` (Large)
- **优先级**：`P0`
- **执行人**：agent
- **计划开始时间**：`2026-10-17T18:32:00Z`
- **关联设计与 ADR**：
  - [ADR-002_relational_storage.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_01_tech_selection/ADR-002_relational_storage.md)
  - [ADR-003_vector_matching.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_01_tech_selection/ADR-003_vector_matching.md)
  - [_01_database_schema.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_01_database_schema.md)

---

## 1. 目标与范围 (Goal & Scope)

1. **核心业务领域层真正的 PostgreSQL 关系持久化落地**：
   - 彻底改造 `backend/src/domains/*/service.py`（用户、政策、论坛、需求商机、产品展位、SOP 文书、特权权益等）。
   - 将内存字典全面重构为基于 SQLAlchemy 2.0 `AsyncSession` / Repository 模式的数据读写。
   - 保留离线开发/单测环境下的安全 Fallback，确保全部自动化单测在有/无活跃 PostgreSQL 容器时均稳定运行。
2. **邮箱注册与创客登录认证中心 (Auth & Security Domain)**：
   - 在 `users` 表结构中补充 `password_hash` 安全加密凭证。
   - 实现原生基于 PBKDF2-HMAC-SHA256 的密码哈希与比对验证算法。
   - 新增统一网关算子：`auth.register`（邮箱注册、格式校验、重名防重、默认创客角色赋予）、`auth.login`（邮箱/密码鉴权、Token 签发、登录时间记录）、`auth.session`（会话校验与用户信息恢复）。
3. **前端液态玻璃认证交互系统**：
   - 顶部导航栏动态根据当前登录状态显示【登录 / 注册】或【当前创客头像、昵称、VIP 徽标与退出】。
   - 新增液态玻璃质感的设计规范弹窗：【邮箱快速注册】与【创客账号登录】。
   - 注册/登录成功后实时同步全局状态，发帖、发需求、保存文书时自动关联真实当前登录用户的 `user_id`。
4. **全套自动化测试验证与门禁检查**：
   - 编写 `test_auth_and_persistence.py` 覆盖真实落盘与认证流程。
   - 全工程回归测试保持 100% 绿灯。
   - 跑通 `verify_consistency.py` 质量门禁。

---

## 2. 详细执行路线 (Milestones)

- **Step 1**: 扩充 `User` 模型字段 `password_hash`，建立安全密码哈希与会话 Token 模块 (`backend/src/core/security.py`)。
- **Step 2**: 建设通用数据访问层（Repository / Persistence Helper）及各 Service（`UserService`, `PolicyService`, `ForumService`, `DemandService`, `ProductService`, `SopService`, `PerkService`）的异步数据库持久化支持。
- **Step 3**: 新增 `auth.register`、`auth.login`、`auth.session` 微内核 DAG 编排与统一网关场景分发。
- **Step 4**: 前端新增【邮箱注册】与【创客登录】液态玻璃模态弹窗及导航栏登录态交互。
- **Step 5**: 编写测试套件 `test_auth_and_persistence.py`，全量执行 pytest 测试。
- **Step 6**: 运行一致性校验，编写验收备忘，推进 TASK-027 状态流转并提交代码。
