# 任务计划：TASK-029 管理员 Python 脚本运行时热注册（RBAC §3.2 四道防火墙）

- **任务编号**：TASK-029
- **任务分级**：`M` (Medium)
- **优先级**：`P0`
- **执行人**：agent
- **计划开始时间**：`2026-10-17T14:10:00Z`
- **意图**：`BUILD / IMPLEMENT`（补齐设计已定义但未实现的运行时动态算子能力）
- **关联设计**：
  - [opchub_rbac_auth_architecture.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_rbac_auth_architecture.md) §1.1 / §2 / §3.2
  - [_04_framework_detailed_design.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_04_framework_detailed_design.md) §3.2

---

## 1. 目标与范围

实现设计文档要求的「Python 脚本安全上传与热注册机制」四道防火墙，使 ADMIN 可在**不重启、不改代码**的前提下，把业务处理脚本注册为微内核原子算子，并立即被 DAG 编排执行。

| # | 设计要求（RBAC §3.2） | 实现落点 |
|---|---|---|
| 1 | AST 静态词法/语法沙箱扫描 | `core/microkernel/sandbox.py`：`FORBIDDEN_MODULES/CALLS/ATTRIBUTES` + `ASTSecurityScanner` |
| 2 | 入口规约核验（必须导出 async 入口） | `load_operator_from_source()`：默认入口 `action_entry`，否则首个 `async def`；参数 0/1/2 自适应 |
| 3 | 受限隔离命名空间编译加载 | `compile()` + `exec()` 至 `__builtins__` 白名单命名空间（无 I/O、无反射） |
| 4 | 注册进 ActionRegistry + 审计日志 | `core/microkernel/script_ingestion.py`：`registry.register()` + 结构化审计（签名哈希/管理员ID/时间戳） |

**接口**（对齐设计 §1.1 `POST /api/v1/scripts/upload`，仅 ADMIN）：
- `POST /api/v1/scripts/upload` 上传并注册
- `GET /api/v1/scripts/operators` 列出动态算子
- `POST /api/v1/scripts/{name}/unregister` 注销
- `GET /api/v1/scripts/audit` 审计日志
- `POST /api/v1/microkernel/sandbox/validate` 已有的静态校验端点保留

---

## 2. 关键实现决策

1. **入口签名**：运行时算子契约为 `(inputs, context) -> dict`（`dispatcher` 调用约定）。脚本入口按参数个数自适应：0 参 → `()`；1 参 → `(inputs,)`；≥2 参 → `(inputs, context)`。默认入口名 `action_entry`（兼容设计文档命名）。
2. **受限执行**：`exec` 是设计明文指定的加载方式（"受限隔离执行命名空间编译加载"）。安全保证来自：AST 扫描先行 + `__builtins__` 仅注入白名单（无 `open/print/eval/exec/__import__/getattr`）+ 禁用 dunder 反射属性。
3. **审计**：采用结构化 JSON 日志（经 `StructuredJsonFormatter` 输出，容器 stdout 落盘）+ 内存审计登记，与项目既有审计模式（`_ops_audit_log`）一致；当前 DB Schema 无脚本审计表，未新增表以保持契约稳定。
4. **内置算子保护**：动态脚本不得覆盖内置算子；同名动态算子需显式 `overwrite=true`。
5. **注销能力**：为 `dispatcher`/`registry` 增加 `unregister`，支撑管理与测试清理。

---

## 3. 验证证据 (Evidence)

- **新增测试**：`backend/tests/test_dynamic_operator_upload.py` —— **13 passed**，覆盖：
  - 正常上传 → 进入方法池与元数据池
  - 运行时注册的算子被 DAG 节点编排执行成功
  - 四道防火墙拒绝：`import os` / `eval()` / `__class__` 反射 / 非 async 入口 / 声明的入口不存在
  - 权限：无 token 与 MAKER token 均 403
  - 内置算子名冲突拒绝、重复名需 overwrite、注销与 404、审计日志、列表端点
- **全量回归**：`python3 -m pytest tests/ -q` → **178 passed**（0 fail / 0 error）
- **静态检查**：`pyflakes src/ tests/` → 仅剩 1 项有意 re-export
- **端到端 smoke**：
  1. `POST /scripts/upload` → `REGISTERED`，`entry=action_entry`，`sig=sig_sha256_...`
  2. `GET /scripts/operators` → `['dynamic.tax_check']`
  3. `POST /microkernel/dag/execute`（引用动态算子）→ `SUCCESS`，输出 `{'vat_exempt': True, 'declared_income': 250000.0}`
  4. 恶意脚本 → `400 Forbidden import`；无 ADMIN → `403`
  5. `GET /scripts/audit` → 审计记录生成

---

## 4. 已知缺口与后续建议 (Open Items)

1. **ADMIN 账号初始化途径缺失**：`user_service.register_by_email` 固定 `role="MAKER"`，系统当前无创建 ADMIN 用户的入口。TASK-028 清空种子后尤其明显。建议后续提供管理员初始化（如环境变量指定 ADMIN 邮箱或受控 API）。
2. **RBAC/ABAC 守卫未全局落地**：设计 §2 的 `abac_owner_guard` 及场景级权限校验尚未实现；本次仅在脚本摄取端点实现了 ADMIN 门禁。
3. **审计持久化**：当前为结构化日志 + 内存登记；若需强不可篡改与长期留存，建议新增审计表或写入归档对象存储。

> **结论**：设计文档 §3.2 四道防火墙已全部落地，运行时动态算子能力可用并经验证。
