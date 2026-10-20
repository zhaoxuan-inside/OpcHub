# 任务计划：TASK-030 完整 RBAC/ABAC · 内置管理员强制改密 · 审计与归档

- **任务编号**：TASK-030
- **任务分级**：`L` (Large)
- **优先级**：`P0`
- **执行人**：agent
- **意图**：`BUILD / IMPLEMENT`（补齐设计要求的权限体系与合规审计）
- **关联设计**：
  - [opchub_rbac_auth_architecture.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_rbac_auth_architecture.md) §1.1 / §2 / §3.2
  - [opchub_legal_compliance_spec.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_legal_compliance_spec.md) §80

---

## 1. 交付内容

### ① 内置管理员 + 首次登录强制改密
- `config.py`：`OPCHUB_ADMIN_EMAIL` / `OPCHUB_ADMIN_INITIAL_PASSWORD` / `OPCHUB_ADMIN_NICKNAME`（含安全默认值）。
- `user_service._ensure_builtin_admin()`：幂等预置 `uid=usr_admin_builtin` 的 ADMIN，`must_change_password=True`；启动时同步持久化到 DB。
- 登录响应与 token 携带 `must_change_password`；新增 `POST /api/v1/auth/change-password`。
- 网关强制门禁：`must_change_password` 身份执行高危权限（page:orchestrate / data:schema_manage / script:upload_python / review:audit_all）一律 403，改密后放行。

### ② 完整 RBAC + ABAC（声明式，配置驱动）
- `core/rbac.py`：14 项权限矩阵 + 三级角色（ADMIN 通配 / USER(MAKER) / GUEST）+ `parse_identity` + `resolve_resource_owner` / `is_owner_or_admin`。
- `gateway_routes.yaml`：**22 个受控场景**声明 `required_permission`；`user.profile.update` 声明 `owner_check`（ABAC）。
- `gateway/router.py`：调度前统一执行 RBAC（未登录→401 引导登录；越权→403）+ ABAC（非本人→403），并写入审计。
- 网关以 token 身份为准，**不再信任客户端传入的 `context.user_id`**（防身份伪造）。

### ③ 审计表 + 归档存储（加密留存 ≥180 天）
- 新增 ORM：`audit_logs`（热）+ `audit_logs_archive`（冷）。
- `core/crypto.py`：HMAC-SHA256 keystream 字段级加密（审计 detail 加密落盘）。
- `core/audit.py`：`record()`（内存 + DB）、`list_logs()`、`archive_older_than(days)`、`list_archived()`。
- `repository.py`：`insert_audit_log` / `list_audit_logs` / `archive_audit_logs` / `list_archived_audit_logs` / `ensure_builtin_admin`。
- 端点（ADMIN）：`GET /admin/audit/logs`、`GET /admin/audit/archive`、`POST /admin/audit/archive/run`；启动时自动执行一次保留期归档。

---

## 2. 验证证据 (Evidence)

- **全量回归**：`pytest tests/` → **192 passed**（0 fail / 0 error）
- **静态检查**：`pyflakes src/ tests/` → 仅剩 1 项有意 re-export
- **新增测试**：`tests/test_rbac_abac_and_audit.py`（14 passed）覆盖权限矩阵、网关 RBAC 三级、ABAC 归属、内置 admin 首登/设防/改密/错误旧密、审计查询、归档迁移、审计端点 ADMIN 门禁
- **网关测试适配**：`tests/conftest.py` 为测试客户端注入 ADMIN 身份；异步 httpx 测试显式注入；清空 user_service 的 fixture 重新注入内置 admin
- **端到端 smoke**：
  1. admin 登录 → `ADMIN` / `must_change_password=True`
  2. 高危场景改密前 → `403 首次登录安全策略`
  3. 改密后 → `200`
  4. RBAC：GUEST → `401`；MAKER 调 ADMIN 场景 → `403`
  5. ABAC：改他人档案 → `403 abac_denied=True`
  6. 审计查询/归档端点 → `200`

---

## 3. 说明与后续 (Notes)

- 网关对「未登录」返回 401（引导登录）、对「已登录但越权」返回 403，符合设计 §2 的“未登录游客执行写操作必须返回统一指令引导登录”。
- ABAC 归属解析已覆盖 product / demand / forum thread / comment / sop_document / user；未来新增「修改/删除」类场景时，只需在 `gateway_routes.yaml` 声明 `owner_check` 即可启用，无需改代码。
- 审计冷数据当前为 DB 归档表（`audit_logs_archive`）；如需异地/对象存储长期冷备可在后续扩展。
