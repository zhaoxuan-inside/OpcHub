# 支撑平台功能完整交付 M1/M2/M3 — 验收审计（2026-11-01）

## 需求原文

> 完整，正确，高效，人性化的实现支持平台的功能（功能借鉴同等定位的开源项目），
> 不允许存在假代码，桩代码，死代码。

## 交付总览（4 提交：Phase 0+1 `febd6a1` / Phase 2 `f21b640` / Phase 3 `3f739da` + 本文档）

### Phase 0 — UI 内核 + 死代码清零
- `packages/ui` 自研 Modal/Toast(队列+自动消退)/Select/Textarea/Field（零第三方依赖）；
- 移除三处 `auth.logout` 死分发（后端无会话存储，登出=客户端清 token，契约如实）。

### Phase 1 — 编排管理收口（借鉴 Kestra 画布 / GrowthBook 实验 / Nacos 配置 / Argo CD 发布）
| 块 | 交付 |
| --- | --- |
| 资产全生命周期 | useAssetLock（60s 心跳续期/接管，进 Kit）+ AssetLockBanner 三态；算子页创建（沙箱脚本 Textarea）→ 持锁草稿编辑 → 直接发布/提交第二人审批 → 回滚 → 删除；版本历史组件三类共用；全部 `{action,payload}` 信封 + PermissionGate |
| 画布编辑器 | @xyflow/react（MIT，主站 @vue-flow 同族）：调色板加节点/连线成环拒绝(DFS)/Delete 删除/入口出口检查器/JSON↔图双向同步/撤销栈/MiniMap/只读态；拓扑分列布局与节点类型推断与主站 GraphEditor 语义 1:1 |
| 实验域（绿地 `src/domains/experiment`） | 变体/权重/流量门控；sha256 稳定分桶+粘性分配；状态机 DRAFT→RUNNING⇄STOPPED→ARCHIVED（运行中仅调权重/流量）；outcome.report 真实结果；readout 聚合；OPC_EXPERIMENT_PIPELINE 元管线资产化；assign/outcome 专用适配器（宿主自然载荷）；**主体身份一律取登录态，代查仅限管理者**（修复越权冒充分桶缺陷）；新权限 experiment:manage/read 并入内置项目角色 |
| 配置中心（绿地 `src/domains/configcenter`） | 命名空间→配置项（JSON/TEXT 校验）→版本机（DRAFT→PUBLISHED→SUPERSEDED）→灰度发布（百分比分桶+白名单直通，全量提升稳定版）→回滚清除灰度；resolve 宿主数据面调用（确定性解析，NOT_FOUND 诚实返回）；OPC_CONFIGCENTER_PIPELINE 资产化（132 flows/0 unmapped） |
| ExperimentsPage/ConfigsPage | 桩页替换为真实产品：创建向导/状态机/试算工具/读出表；命名空间侧栏/配置编辑器/历史 diff（复用 diff.ts）/灰度发布 Modal/resolve 试算 |

### Phase 2 — 运维平台（借鉴 SigNoz/jaeger-ui）
- **运行记录落库桥**：`orchestration_service._execute_via_microflow` 唯一收口插桩，每次场景执行一条 `ops.run_records` 快照（write-behind+hydrate；内存封顶 5000；保留期 14 天可配启动清理；节点 output 截断 2KB）；
- **节点真实时长**：MicroFlow4Python 框架节点执行体 monotonic 计时写入 meta.durationMs（框架提交 `3e0fffa`，243 tests 全绿）——瀑布图零造假；
- ops.runs.list/detail/metrics（读时聚合调量/成功率/avg/P95）+ platform.audit.list 扩 result 过滤；
- Ops SPA：运行记录（过滤表 → jaeger 式瀑布：时长比例条+状态+错误）、指标看板（recharts 柱图+KPI+明细）、调试工作台（场景选择+入参 JSON+执行+节点迹）；审计页结果过滤。

### Phase 3 — 运营平台（借鉴 Umami/GrowthBook 读出；全量真实数据，零埋点依赖）
- 三数据源：实体计数（与 OPS_DASHBOARD 同口径）+ 审计流足迹（样本上限 5000 如实披露）+ 运行记录（14 天窗口）；
- bizops.overview/actions/trend/funnel/retention 五场景（page:bizops_console 把守）；漏斗口径如实标注"足迹去重非严格时序"；
- Bizops SPA 四页：总览（KPI 卡+14 天趋势线）、业务漏斗（步骤选择+转化柱图）、留存（活跃矩阵+D1/D7）、实验读出（与编排平台实验域同源）。

## 防造假纪律

- 每个数据面板标注口径与样本量；NOT_FOUND/空态诚实返回，不填充假数；
- 瀑布图时长来自框架真实计时（此前恒 0 视为造假风险，已修框架）；
- 数据面主体解析一律取登录态，代查需管理者权限（堵住灰度分桶冒充）；
- 测试隔离：bizops fixture 清空前置测试审计污染，防止跨测试样本串味。

## 验证

- 新增 pytest 25 例（实验 6/配置 4/运行记录 6/运营 5/治理随回归）；全量回归 **682 passed / 9 known**（基线不变：8 个需 mock 服务器 + 1 个 moderation guard）；
- 三 SPA `tsc -b && vite build` 全绿；前端调用场景与后端注册核对**零缺失**；占位文案 grep 归零；
- MicroFlow 框架 243 tests 全绿（节点计时扩展）。

## 已知边界（如实）

1. 场景执行入口（orchestration.scenarios.execute）保持 page:orchestrate 管理员把守 —— 项目成员经发布审批进入运行时（运行时隔离边界维持 M1.5 决策）；
2. 漏斗为足迹去重口径（非严格时序归因），时序归因待 MicroFlow T14 控制面事件序号；
3. 编排 SPA 构建体积 500KB+（@xyflow/react），待 manualChunks 分包优化。
