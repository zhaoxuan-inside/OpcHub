# 支撑平台治理底座：分租户·分用户·分权限·分项目 — 验收审计（2026-11-01）

## 需求原文

> 支持平台（运维，运营，编排）应该需要支持，分租户，分用户，分权限，分项目进行操作的
> 能力，这样才是一个完整的支持平台的能力。

方案确认（四项决策）：租户=组织实体+成员管理；**可配置 RBAC**（角色/权限点入库、管理 UI
勾选）；**三平台同步交付**；编排目录**项目完全隔离**（跨项目复用走显式机制）。

## 交付范围（3 个提交）

### Commit 1 `860b4d6` — 后端治理域 + 网关 scope 强制

| 模块 | 说明 |
| --- | --- |
| `src/domains/platform/{models,service,adapters}.py` | 租户/项目/角色/角色绑定四实体（id 前缀 tnt_/prj_/rol_/bnd_）；`domain_persistence` write-behind + 启动 hydrate，**变异前 require()**（strict：无 DB 拒绝授权变更，不静默降级）；无需 SQL 迁移 |
| 可配置 RBAC | 角色=权限点列表；7 内置角色种子（平台超管["*"]/平台创客/租户管理员/租户成员/项目所有者/编辑者/查看者）；租户自定义角色（TENANT/PROJECT 域、归属租户、builtin 不可删改）；有效权限 = PLATFORM ∪ 活动租户 TENANT ∪ 活动项目 PROJECT 绑定并集；**令牌不携带 scope 授权 → 变更即时生效** |
| legacy 兼容 | users.role 与 token role claim 原样保留；静态矩阵先行短路（ADMIN 通配直通、MAKER/GUEST 存量不变）——旧场景零回归 |
| `core/gateway/router.py` | RouteRule/register 新增 `scope` 字段；dispatch 组合授权（legacy 矩阵 OR scope 绑定）+ scope 隔离强制（未登录 401 / 缺活动上下文 `scope_required` / 非成员 `scope_denied`，均记审计 `scope.denied:{scenario}`）；scope 值注入 ctx |
| `core/rbac.py` | 新增 12 个权限点（platform:tenant/user/role/audit、tenant:member/project/role、project:manage/member、orchestration:read/write、page:ops/bizops_console）并入 HIGH_RISK 首登闸门 |
| 21 个 `platform.*` 场景 | tenants/projects 成员管理（双重权威：平台 OR 租户/项目 scope，service 层断言）、角色 CRUD + 权限点目录、用户管理（角色/停用/密码重置强制轮换；内置管理员保护；不能降级/停用自己）、`platform.scope.my`（切换器数据源）、`platform.audit.list` |
| 保护规则 | 最后一名租户管理员/项目所有者不可移除；移出租户级联移出其全部项目；项目成员须先在册于所属租户 |

### Commit 2 `da20344` — 编排目录项目隔离

| 模块 | 说明 |
| --- | --- |
| 资产挂项目 | 三类 Asset + ReleaseApproval 增 `project_id`；创建即 stamp 活动项目（超管缺省为未归属，legacy 兼容） |
| 完全隔离 | 目录读取收敛为 `orchestration:read + scope:project`（gateway_routes 11.1 段 29 条路由全部落 scope）：项目成员只见本项目资产 + 平台内置资产，非本项目**按不存在处理（不泄露存在性）**；写/锁/审批/回滚 = `orchestration:write + scope:project`；引用解析（子图→算子、场景→子图/算子）按可见性过滤 |
| `orchestration.assets.copy` | 跨项目显式复制（唯一复用通道）：目标项目需编排写权限、源资产需对发起人可读；**编码全局唯一**（运行时算子池按名注册的既有约束），占用时自动派生空闲编码、显式 new_code 尊重指定；版本机原样保留溯源 |
| 缺陷修复 | `_validate_scenario_graph` 引用了**从未定义**的 `_resolve_operator_handler`（0664ed2 引入；场景引用自建算子 + strict 校验必崩 AttributeError），收敛为 `_resolve_custom_operator_version` |
| 行为变更 | 目录读取从"展示开放"收敛为项目隔离（未登录 401）——对应"项目完全隔离"决策；`test_orchestration_catalog` 读策略断言随之更新 |

### Commit 3 `7bbef11` — 三平台同步接入

| 模块 | 说明 |
| --- | --- |
| `packages/api` | 活动租户/项目 scope 存储（localStorage 同源共享 + 变更广播）；dispatch 自动注入 context |
| `packages/ui` | ScopeProvider（my_scope 镜像；前端权限判定与后端同构：超管通配 + 三层角色并集）、ScopeSwitcher（租户→项目级联 + 角色徽标）、PermissionGate（单权限/anyOf）、ScopeEmptyHint |
| `packages/admin`（新） | 用户/租户/项目/角色管理共享页，三平台共挂 `/platform/*`：成员面板（添加/调角色/移出）、可配置角色权限点勾选、密码重置；全部按权限显隐（后端始终强制） |
| orchestration | 头部切换器 + 平台管理导航（按权限）；回滚/提交审批/驳回/通过、复制到项目均经 `PermissionGate("orchestration:write")`；算子行内"复制到项目"（目标限持有写权限的项目） |
| ops（新壳） | 登录/切换器/总览（治理范围 + 审计事件数）+ **审计与日志检索页**（`platform.audit.list` 真实数据，按动作过滤，`platform:audit_read` 把守）；运行记录/指标看板/瀑布图/调试仍留 M2 里程碑 |
| bizops（新壳） | 登录/切换器/总览（治理范围）；埋点/漏斗/实验读出如实标注 M3 交付（依赖主站埋点） |
| `frontend/server.py` | `/console/ops`、`/console/bizops` 挂载（泛化为三应用循环）；三 SPA 构建全绿（367/353/351KB JS） |

## 关键设计决策与边界

1. **编码全局唯一**：运行时算子池/MicroFlow 流程按名注册是全局的，真复合键隔离会造成
   同名算子发布互相覆盖（运行时正确性风险）。隔离交付在可见性与可操作性维度；
   同名需求经"复制到项目"自动派生新编码解决。
2. **主站工作台豁免**：平台超管（ADMIN）在 scope 路由直通、无项目上下文保持 legacy 全局
   视角 —— 主站 Vue 编排工作台无需改造；项目成员统一经支撑平台 SPA 操作。
3. **令牌不携带 scope 授权**：授权每次 dispatch 从内存注册表现算，权限变更即时生效，
   规避 7 天无状态令牌的陈旧授权窗口。
4. **授权数据 strict 持久化**：PostgreSQL 不可用时拒绝治理域变更（PersistenceUnavailableError），
   不允许授权静默降级为纯内存态。
5. **运行时执行暂不入项目隔离**：场景发布物化为全局 DAG 配置、执行入口（orchestration
  .scenarios.execute）保持 page:orchestrate —— 运行时隔离留待 M2 运维平台一并设计。

## 验收结论

### 自动化（backend/tests）

- `test_platform_governance.py`（23 例）：内置角色种子 / 权限点目录 / legacy 矩阵不回归；
  租户创建（创建人自动成为租户管理员）/ 编码唯一 / 非平台权限拒绝 / 普通用户列表过滤；
  成员添加幂等 / 最后管理员保护 / 移出级联项目；dispatch 租户域创建（MAKER+TENANT 绑定
  放行、缺上下文 403 scope_required）；项目隔离（成员放行并注入 project_id、非成员
  scope_denied、超管直通、查看者不能写）；自定义角色全生命周期（创建/未知权限点 400/
  builtin 不可删/授权后 dispatch 放行 + 成员管理放行）；用户管理（角色设置/自降级保护/
  内置管理员保护/密码重置强制轮换）；my_scope 结构。
- `test_orchestration_project_isolation.py`（10 例）：资产 stamp 与成员可见性过滤（B 项目
  成员看不到 A 资产、详情不泄露存在性、内置全局可见）；无上下文管理员 legacy 全局视角；
  跨项目写拒绝（编辑者仅限本项目、缺上下文纵深拒绝）；复制到项目（版本机保留/目标权限
  校验/自动派生编码/显式编码冲突拒绝）；审批单挂项目并按上下文过滤；dispatch 层成员经
  网关读目录 + 未登录 401 + 锁-建算子全链路。
- 全量回归：**661 passed / 9 failed（与基线完全一致：8 个需 mock 服务器 + 1 个
  moderation guard），断言除目录读策略有意变更外零改动。**

### 构建

- 三个 SPA `tsc -b + vite build` 全绿：orchestration 367.65KB（gzip 111.57KB）、
  ops 353.41KB、bizops 350.85KB。
- `frontend/server.py` 语法校验通过，三平台路由挂载。

### 上线注意

- 后端需**完整重启**（gateway_routes.yaml 新增 21 条 platform 路由 + 编排段 scope 改造；
  防旧进程占用 8000）。
- 首个动作建议：以内置管理员登录任一平台 → 平台管理 → 创建租户（自动成为租户管理员）→
  添加成员 → 创建项目（自动成为项目所有者）→ 项目成员获得编排读写。
