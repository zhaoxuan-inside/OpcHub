# OpcHub Console —— 三大支撑平台

基于 MicroFlow 的上层承载平台（框架 README："观测的汇聚、查询、看板、告警由上层承载"）。
适配+剪枝自开源项目（shadcn-admin / React Flow / SigNoz / jaeger-ui / Umami / GrowthBook /
Nacos3 模式），许可证均为 MIT/Apache-2.0；AGPL/公平代码项目仅借鉴交互模式。

## 子项目

| 目录 | 平台 | 状态 |
|---|---|---|
| `orchestration/` | 编排管理：算子/子图/场景全生命周期（创建→持锁编辑→发布/审批→回滚→删除，React Flow 画布）、项目隔离、实验域、配置中心（灰度发布） | M1 已交付 |
| `ops/` | 运维：运行记录（节点瀑布真实计时）+ 指标看板（调量/成功率/P95）+ 审计检索 + 调试工作台 | M2 已交付 |
| `bizops/` | 运营：KPI 总览 + 按日趋势 + 业务漏斗 + 留存 + 实验读出（全量真实数据：实体计数+审计足迹+运行记录，零埋点依赖） | M3 已交付 |

共享：`packages/ui`（设计系统 + ScopeProvider/切换器/权限门）、`packages/api`（统一网关
客户端 + 活动租户/项目 scope 存储）、`packages/admin`（平台管理共享页：租户/项目/角色/用户）。

## 治理底座（分租户 · 分用户 · 分权限 · 分项目）

三个平台共用同一套授权模型，全部由后端 `src/domains/platform` 强制：

- **分租户**：租户=组织实体，成员经邀请进入（租户管理员/租户成员）；
- **分项目**：项目挂在租户下，编排目录资产归属项目且项目间完全隔离，
  跨项目复用走显式"复制到项目"（编码全局唯一，占用时自动派生新编码）；
- **分权限**：可配置 RBAC —— 角色即权限点集合（内置 7 角色 + 租户自定义角色），
  有效权限 = 平台 ∪ 活动租户 ∪ 活动项目 的角色并集，变更即时生效；
- **分用户**：平台级用户管理（角色/停用/密码重置强制首登轮换）。

前端：每个 SPA 头部有"租户 → 项目"级联切换器，`dispatch` 自动把活动范围注入请求
context；写操作按钮经 `PermissionGate` 按权限显隐（后端始终强制）。

## 开发

```bash
# 本机为 Samba 共享盘（不支持 symlink），一律 --no-bin-links + node 直调
npm install --no-bin-links                        # 根目录共享依赖（react/clsx/@tanstack/react-query 供 packages/* 向上解析）
npm install --prefix orchestration --no-bin-links  # 三个应用各自安装（4601/4602/4603）
cd orchestration && node node_modules/vite/bin/vite.js    # dev（/api 代理到 3000）
node node_modules/vite/bin/vite.js build                  # build → dist/
```

构建产物由 `frontend/server.py` 挂载：`/console/orchestration`、`/console/ops`、
`/console/bizops`。
