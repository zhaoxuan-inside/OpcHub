# 任务计划：TASK-031 架构修复 · 消除双入口，业务 REST 全量收口统一网关

- **任务编号**：TASK-031
- **任务分级**：`L` (Large)
- **优先级**：`P0`
- **执行人**：agent
- **意图**：`FIX / REFACTOR`（修复与设计 §3.3 相悖的“双入口”架构问题，不改变业务语义）
- **关联设计**：
  - [_04_framework_detailed_design.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_04_framework_detailed_design.md) §3.3 统一入站网关与场景动态路由规约
  - [_02_api_contracts.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_02_api_contracts.md)（原 REST 契约，已标注为历史）
  - [opchub_rbac_auth_architecture.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_rbac_auth_architecture.md) §3.2

---

## 1. 问题 (Problem)

设计 §3.3 明确要求：**全平台所有业务请求收口至单一入站端点 `POST /api/welcom/opc_world`**（别名 `/api/welcome/opc_world`、`/api/v1/dispatch`），后端**零 HTTP 接口改造**扩展新业务。但实现层长期存在**双入口**：

1. `main.py` 中除统一网关外，还并行挂载了 **50+ 个业务 REST 端点**（forum / products / policies / demands / perks / sop / user / auth / home / moderation / compliance / orchestration / frontend / ops dashboard）；
2. 这些 REST 端点与网关场景**各自直连同一批领域服务**，形成事实上的旁路（Bypass），破坏 RBAC/ABAC 统一门禁与审计一致性；
3. 阶段 6 验收要求“**零 Bypass**”，双入口架构直接不达标。

---

## 2. 修复方案 (Fix)

### ① 保留 (平台 / 基础设施，非业务场景)

| 类别 | 端点 |
| --- | --- |
| 统一网关入口 | `POST /api/welcom/opc_world`、`/api/welcome/opc_world`、`/api/v1/dispatch`、`/api/v1/gateway/dispatch` |
| 网关治理 | `GET .../rules`、`POST .../reload` |
| 系统探针 / 落地页 | `/`、`/app`、`/favicon.ico`、`/livez`、`/readyz`、`/healthz`、`/health` |
| 微内核平台自省 | `GET /api/v1/microkernel/methods`、`POST .../dag/execute`、`POST .../sandbox/validate` |
| 动态算子管理（§3.2 四重防火墙，ADMIN） | `POST /api/v1/scripts/upload`、`GET .../operators`、`POST .../{name}/unregister`、`GET .../audit` |
| 安全审计管理（ADMIN） | `GET /api/v1/admin/audit/logs`、`GET .../archive`、`POST .../archive/run` |

### ② 删除 (全部业务 REST，共 500+ 行)

forum（threads/comments/upvote/bookmark）、`home/overview`、sop（templates/documents）、products（list/publish/upvote）、policies（list/publish/match）、demands（list/publish/bids）、perks（list/publish/claim）、auth（register/login/session/change-password）、user（profile/entitlements）、`ops/dashboard`、`microkernel/dag/configs`、`frontend/layouts`、orchestration（operators/operators.mode/scenarios.execute）、`admin/moderation/*`、`compliance/*`。

### ③ 能力零丢失：补齐 4 个原仅存在于 REST 的场景

删除前先确认每个业务 REST 能力都有场景等价物。经逐一比对，发现 **4 个能力无场景**，补充适配器 + `gateway_routes.yaml` 规则：

| 新增场景 | 适配器 | 所需权限 | 原 REST |
| --- | --- | --- | --- |
| `forum.upvote` | `forum_upvote_adapter` | `forum:post_comment` | `POST /forum/upvote` |
| `forum.bookmark` | `forum_bookmark_adapter` | `forum:post_comment` | `POST /forum/bookmark` |
| `auth.change-password` | `auth_change_password_adapter` | （登录态） | `POST /auth/change-password` |
| `orchestration.operators.mode` | `operator_mode_adapter` | `page:orchestrate` | `POST /orchestration/operators/mode` |

### ④ 网关语义增强

- `router.py`：将处理器异常映射为**语义化信封 code**，在保持“HTTP 200 + 标准信封”设计的前提下还原 REST 语感：`KeyError → 404`、`ValueError → 400`、`PermissionError → 403`、其它 `→ 500`。
- `router.py`：解析出的会话 token 注入 `ctx["token"]`，使 `auth.change-password` 等场景可直接从上下文取用凭据。
- `main.py`：清理因删除端点而失效的 import（telemetry / forum / sop / products / policies / demands / perks / user models / orchestration / moderation / compliance）。

### ⑤ 测试适配

- `tests/conftest.py` 新增 `dispatch()` / `gw_data()` 辅助函数，统一经 `POST /api/welcom/opc_world` 发起业务请求。
- 迁移 9 个测试文件（forum / domain publishing / moderation / compliance+legal / all-domains persistence / auth persistence / ops telemetry / composable microkernel / RBAC）+ 2 个改密用例至统一网关，断言改为校验信封 `code` 与 `data`。

---

## 3. 验证证据 (Evidence)

- **全量回归**：`python3 -m pytest tests/ -q` → **192 passed**（0 fail / 0 error）
- **静态检查**：`python3 -m pyflakes src/ tests/` → 仅剩 1 项有意 re-export（`orchestration/models.py:4`）
- **零 Bypass 校验**：全仓（排除 `hs_dev_docs/` 历史文档）grep 已无任何业务 REST 路径引用：
  `grep -rnE '/api/v1/(forum|home|sop|products|policies|demands|perks|user|ops|frontend|orchestration|compliance)' --exclude-dir=hs_dev_docs .` → 0 命中
- **路由清单核对**：应用启动后业务相关路由仅剩统一网关 + 平台/管理端点（29 条），业务 REST 全部消失。
- **场景注册**：`gateway_routes.yaml` 业务场景由 50 → **54**（新增上述 4 个），全部可经统一入口调度。

---

## 4. 兼容性与迁移 (Migration Notes)

- **对外契约变更**：客户端不再直连业务 REST，必须统一调用 `POST /api/welcom/opc_world`，请求体携带 `scenario` + `version` + `payload`（+ 可选 `token` / `context`）。
- **状态码语义**：HTTP 层恒为 200，业务结果以信封 `code` 表达（200 成功 / 400 参数 / 401 未登录 / 403 越权 / 404 不存在 / 500 内部错误）。
- **鉴权**：身份来自 `Authorization: Bearer <token>`、`context.token` 或 `payload.token`；客户端传入的 `context.user_id` 不被信任。
- **历史 REST 契约**：`_02_api_contracts.md` 中的分节 REST 路径已标注为历史（Legacy），以本任务与 `gateway_routes.yaml` 为准。
