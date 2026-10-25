# 首页重构 · 结构拆分与全面数据驱动 — 验收审计（2026-10-25）

## 需求原文

> 重构一个产品的首页。

经确认，范围为**结构与数据重构**（保持现有玻璃拟态视觉与信息架构不变），指标数据源启用后端 `home.overview` 聚合管线。

## 重构动机（现状问题）

1. **违反「无 mock」质量红线**：`HomeView.vue`（1599 行单文件）中 Bento 政策卡硬编码「深圳南山 ¥500,000 / 上海张江 / 成都高新」3 个假政策 chips；需求卡硬编码「¥15,000 Stripe 路由 / ¥8,500 VisionOS 官网」2 条假需求 pills，冒充平台真实数据。
2. **指标计数缺陷**：Hero「头脑风暴实战议题 X 篇」取自 `forum.feed.stream` 的 `limit=4` 分页结果，永远显示 ≤4。
3. **单文件臃肿**：模板 + 脚本 + 910 行 scoped 样式集于一身。
4. **后端能力闲置**：`OPC_HOME_OVERVIEW_PIPELINE` 聚合 DAG（含真实入驻创客数）已实现且有测试，但未注册网关路由；`home.metrics.collector` 中 `perks_saved_cny` 硬编码 0.0、`active_dags_count` 硬编码 0。

## 交付范围

### 后端（读走 DAG，符合框架约定）

| 文件 | 改动 |
| --- | --- |
| `config/gateway_routes.yaml` | 注册公开读 scenario `home.overview`（handler `home_overview_adapter` → `OPC_HOME_OVERVIEW_PIPELINE`） |
| `src/core/microkernel/registry.py` | `home.metrics.collector` 真实化：`perks_saved_cny` = PUBLISHED 特权 `value_cny` 实时求和；`active_dags_count` = ACTIVE DAG 配置实数；新增 `forum_threads_count`；`home.sitemap.builder` 复用上游计数免重复查询；`home.overview.aggregator` 透传 `products_count / forum_threads_count` |
| `src/core/gateway/adapters.py` | `home_overview_adapter` 失败兜底 dict 补齐新字段 |
| `tests/test_home_overview_dag_pipeline.py` | 原「未注册返回 404」现状断言反转为「注册后 200 + 全指标字段 + quick_links」；直连 DAG 用例补真实计数断言（与各域服务规模逐一比对，防止回退硬编码） |
| `tests/test_all_domains_persistence.py` | `test_home_overview_api` 同步反转（404 → 200 + 字段断言） |

### 前端（全部后端驱动 + 组件化拆分）

新目录 `frontend/src/components/home/`（7 组件 + 1 助手），`HomeView.vue` 由 1599 行缩至约 280 行，仅保留数据加载、exhibitionData 派生与登录守卫编排（事件契约 `open-login / open-register / switch-tab / toast` 不变）：

| 组件 | 职责 | 数据源 |
| --- | --- | --- |
| `HomeAnnouncementBar.vue` | 顶部公告胶囊 | 静态营销文案 |
| `HomeHeroSection.vue` | Hero + 五项指标条 | `home.overview`（读取失败整条隐藏，不阻塞页面） |
| `HomePillarsBento.vue` | 四支柱便当盒 | `products.list` / `policies.list` / `demands.list`（OPEN 过滤）/ `sop.flow.templates`（usage_count 排序取前 3），四路均配空态 |
| `HomeExhibitionFeed.vue` | 精选展厅 + 筛选 pills（筛选状态内聚） | 父组件派生的 `exhibitionData` |
| `HomeJourneySection.vue` | 演进路径四阶段 | 静态营销文案 |
| `HomeCtaBanner.vue` | 底部转化 | 登录态切换 |
| `HomeSiteFooter.vue` | 页脚 | 静态 |
| `spotlight.js` | 卡片鼠标聚光助手（`--mouse-x/--mouse-y`），消除 5 处重复 | — |

指标条口径升级为 5 项全真实：入驻认证创客 / 橱窗作品 / 政策收录 / 风暴议题 / 特权累计价值（¥10.4万 = 真实特权求和）。政策 chips 映射 `region + subsidy_amount_max + title`；SOP stepper 映射真实流程模板名（超长省略号截断 + title 悬停全名，延续 no-wrap 约定）；需求 pills 映射 `category 中文标签 + title + budget_cny`。锚点 `#showcaseBento` 与 hash-tab 路由兼容（`onHashChange` 只认 tab id，已核实）。

## 验收结论

### 自动化测试

- `test_home_overview_dag_pipeline.py`：2 passed（网关分发 + 直连 DAG，含指标真实性断言）
- `test_all_domains_persistence.py`：8 passed（含反转后的 `test_home_overview_api`）
- 全量回归：**455 passed / 5 skipped / 3 failed** —— `test_versioned_hot_reload` 两例为已知基线噪音；`test_home_overview_api` 一例为本次反转前旧断言（已同步修复，修复后该文件全绿）

### 线上接口验证（重启 8000 后 curl）

`home.overview` 返回 200：创客 10 / 作品 5 / 政策 6 / 议题 7 / 需求 6 / 特权价值 ¥104,500 / quick_links 9 项，12ms。与前端展示逐项一致。

> 运维注：重启时发现旧后端进程（无热重载启动）占用 8000 导致新进程 `Address already in use`，kill 旧进程后恢复。`start_backend.sh` 的 `--reload-dir` 仅监控 `src/`，`config/gateway_routes.yaml` 变更必须完整重启。

### 浏览器端到端（真实 GUI，127.0.0.1:3000）

1. 未登录首页完整渲染，DOM 快照逐项比对接口返回：指标条 `10 位 / 5 款 / 6 项 / 7 篇 / ¥10.4万` ✅（议题数突破旧 limit=4 上限）
2. 政策 chips = 真实数据：「全国统一 最高¥9,000 小微企业免征增值税 / 大湾区 最高¥200,000 智能算力券 / 长三角 税优减免 研发加计扣除」，假数据「深圳南山 ¥500,000」已消失 ✅
3. SOP stepper = 真实模板：「公司主体设立全流程 / 高新技术企业资质评定流程 / 软件著作权独立申报流程」✅
4. 需求 pills = 真实商机：「AI 智能体 ¥26,000 RAG 评测 / 财税合规 ¥8,000 纳税申报」，假数据「¥15,000 Stripe」已消失 ✅
5. 精选展厅筛选 pills、四类卡片（产品/政策/议题/特权）正常 ✅
6. 资源加载 0 失败（`performance` responseStatus ≥ 400 为空）；桌面 1280px 与移动 375px 均无横向滚动 ✅
7. 明暗双主题截图验收通过，验证后已恢复默认亮色 ✅

### 遗留与边界

- 静态营销文案（Hero 标题、Journey、CTA、页脚、公告）按约定保留——产品叙事不属于平台数据 mock
- 2 个 `test_versioned_hot_reload` 基线失败与本次无关
- SOP stepper 模板名在窄卡内省略号截断（悬停显示全名），为既有 stepper 布局的预期行为
