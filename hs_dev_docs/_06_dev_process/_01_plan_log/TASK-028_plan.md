# 任务计划：TASK-028 清除业务 Mock 数据 · 清空初始库 · 清理死代码与桩代码

- **任务编号**：TASK-028
- **任务分级**：`L` (Large)
- **优先级**：`P0`
- **执行人**：agent
- **计划开始时间**：`2026-10-17T13:20:00Z`
- **意图**：`FIX / REFACTOR`（代码对齐已验收设计与需求文档）
- **关联设计与需求**：
  - [opchub_mvp_prd.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_02_feature_spec/_01_human_prd/opchub_mvp_prd.md)
  - [opchub_composable_framework_architecture.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_composable_framework_architecture.md)
  - [_04_framework_detailed_design.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_04_framework_detailed_design.md)
  - [_01_database_schema.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_01_database_schema.md)
  - [stage_6_delivery_signoff.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_acceptance/stage_6_delivery_signoff.md)

---

## 1. 目标与范围 (Goal & Scope)

遵循开发者裁定：**仅外部能力依赖（`infrastructure/external_gateway/`）允许保留 Mock；其余任何位置不得存在 Mock 数据、死代码与桩代码。**

1. **清除业务 Mock 数据**：将运营大盘、首页统计、微内核算子默认值等处的硬编码假数据改为真实聚合/真实空值。
2. **清空为空白初始库**：移除 user/policies/perks/products/demands/forum/moderation/sop/compliance/repository 的内存与 DB 演示种子，初始为空，真实计数。
3. **清理死代码**：删除死模块、死函数/方法、未使用导入、重复端点、死配置字段。
4. **修复桩代码**：修复无视输入返回固定值的伪实现、无条件成功掩盖失败、外部代理字段错位返回 None。
5. **移除原型首页**：`/` 与 `/app` 不再渲染原型 HTML，返回纯 API 提示页。

---

## 2. 文档契约基线（判定依据）

| 契约来源 | 关键约束 |
| :--- | :--- |
| 架构文档 §5.1-3 / 详设 §4.1 | 仅 `external_gateway` 提供 `mock_mode` 脱网自测 Mock（**唯一允许 Mock 的位置**） |
| 详设 §3.3-3 | 「代码中零硬编码」铁律：端点/端口/路由/策略全部配置驱动 |
| DB Schema §1 | 16 张核心表持久化，业务数据落 PostgreSQL |
| stage_6 验收 | 全页面 DAG 驱动、配置化零硬编码、消除死代码 |
| PRD REQ-01~07 | 政策/Perks/SOP/橱窗/需求/论坛/合规 七大领域能力 |

---

## 3. 详细执行路线 (Milestones)

- **Step 1 运营数据真实化**：`telemetry/service.py` 改为真实领域计数聚合，无埋点指标返回 0；`main.py` home/overview 走真实聚合，移除硬编码统计。
- **Step 2 清空初始库**：移除 `user/policies/perks/products/demands/forum/moderation/sop/compliance/repository` 全部演示种子；保留 SOP 4 阶段与 DAG 编排蓝图等功能结构。
- **Step 3 算子默认值去假**：`registry.py` 各算子去除假默认身份/金额/时间戳；`policy_matcher` 接入真实 `policy_service`；修复 3 个外部代理算子字段错位。
- **Step 4 桩代码修复**：`payment_gateway.create_split_order` 失败如实返回 ERROR；删除 `gov_crawler.search_open_policies` 假搜索死函数。
- **Step 5 死代码清理**：删除死模块 `core/gateway/registry.py`、死函数 `demands_bid_adapter`/`has_scenario`/`get_stats`/`register_compensator`/`get_db_session`/`get_user_by_uid`/`create_demand_bid`；清理 30+ 未使用导入；合并 `welcom/welcome` reload 重复端点；清理死配置字段。
- **Step 6 配置驱动补全**：让 `docs_url`/`redoc_url`/`server_host`/`server_port`/`gateway_routes_config_file` 被真实消费，对齐详设 §3.3-3。
- **Step 7 首页改造**：`/` 与 `/app` 返回纯 API 提示页，不再渲染原型。
- **Step 8 测试同步与验证**：测试自建数据替代种子依赖；`test_ops_*` 断言改真实 0 值；全量 pytest 与 pyflakes 门禁。

---

## 4. 验证证据 (Evidence)

- **全量回归**：`python3 -m pytest tests/ -q` → **165 passed**（0 failed / 0 error）。
- **静态检查**：`python3 -m pyflakes src/` → 仅剩 1 项有意 re-export（`orchestration.models` 的 `OperatorDescriptor`，供 `main.py` 契约导入）。
- **端到端行为**：
  - `/api/v1/home/overview` → 真实聚合（空白库全 0）
  - `/api/v1/ops/dashboard` → dau/uv/pv=0，trends=1，logs=0（无假数据）
  - 各 `products/policies/demands/perks/forum/moderation/compliance` 列表 → 空白库返回 `[]`
  - `/api/v1/sop/templates` → stages=4（功能结构），templates=0（空白初始库）
  - `/api/v1/user/profile`（未登录）→ `usr_guest` / `GUEST`
- **Mock 边界确认**：生产代码扫描，除 `infrastructure/external_gateway/` 外无 mock/演示身份/TODO。

---

## 5. 已知偏差与后续建议 (Open Items)

1. **全 REST 端点 vs 全 DAG 驱动**：`main.py` 保留了一批直接调用领域服务的 REST 端点（与统一网关 DAG 场景路由并存）。stage_6 验收声称「零 Bypass」，此为架构层面的既有双重接口，未在本次范围内重构。
2. **PostgreSQL 真实持久化**：领域服务仍以进程内存储为运行时主路径（repository 提供 DB 能力），本次清空种子后需后续把领域服务完整接入 DB 持久化。
3. **运维部署端口**：`scripts/quickstart.*` 与 `Dockerfile` 仍以 CLI 硬编码端口启动；`main.py` 已支持 `__main__` 配置驱动启动。

> **结论**：本次变更使生产代码达到「外部网关外无 Mock、无死代码、无桩代码、初始库为空、数据真实」的状态，全量测试与静态检查通过。
