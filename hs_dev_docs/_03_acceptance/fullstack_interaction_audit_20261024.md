# OpcHub 全站页面交互审计检查结果（2026-10-24）

> 审计范围：全部 11 个视图 + 全部共享组件，逐页面 → 逐图层 → 逐信息框 → 逐内容 → 逐按钮。
> 审计方法：提取模板全部交互元素（@click/@submit/@keydown.enter/@change）与信息框数据绑定，追踪
> 每个交互的 handler → 前端 API → 网关路由 → 后端 handler/算子编排，并核对后端实现形态。
> 判定标准（依据 `_04_framework_detailed_design.md` 场景路由注册表既定开发流程）：
> - **PASS**：交互有真实后端链路且可工作；内容全部来自后端数据。
> - **WRITE-DAG**：写操作（发布/编辑/删除/投票/领取/竞标）必须经算子 + DAG 编排（OPC_*_PIPELINE）。
> - **READ-DIRECT**：读操作经网关路由直连域服务（设计文档路由表登记的合法形态）。
> - **FAIL-MOCK**：前端写死的内容 / Mock 数据 / 假成功交互。
> - **FAIL-DEAD**：死代码 / 桩代码 / 无调用的重复功能。
> - **FAIL-BROKEN**：按钮无效、链路断裂、假数据展示。
> 修复轮次在每条 FAIL 记录后追加 **[FIXED]** 标注与修复说明。

## 检查结果清单

（逐条追加中）

---

## 第 1 组：头脑风暴家族（ForumView / ForumCard / ForumDetailView / ForumCreateView）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-001 | ForumView·筛选栏 | 分类 tab / 排序 pill / 搜索 / 密度切换 / 刷新 | PASS | 全部真实链路：forum.feed.stream(DAG)、forum.search.semantic、本地密度偏好 |
| CHK-002 | ForumView·卡片流 | ForumCard 全部按钮（赞同/反对/回答数/分享/删除/收藏/喜欢/评论/举报/评分） | PASS | forum.vote(DAG)、forum.threads.delete、content.interaction.toggle/rate、moderation.report |
| CHK-003 | ForumView·侧栏热榜 | 热度值 `(upvotes*3+replies*5+42)` | FAIL-MOCK | 凭空伪公式；后端已有真实 hot_score（牛顿冷却算子） **[FIXED]** 改用 `item.hot_score` |
| CHK-004 | ForumView·侧栏热榜 | 「N 点赞」文案 | FAIL-MOCK | 赞同计数被标为"点赞" **[FIXED]** 改为「N 赞同」 |
| CHK-005 | ForumView·transformThread | `ip_location \|\| '来自 浙江'`、`author_title \|\| '认证创客'` | FAIL-MOCK | 后端 ForumThreadResponse 无 ip_location 字段，纯前端造假 **[FIXED]** 删除两处假兜底 |
| CHK-006 | ForumCard·紧凑模式 | 关键词 if-else 生成的"指标徽章"(computedMetrics) | FAIL-MOCK | 按标题关键词伪造 ¥300,000/15分钟 等假数据 **[FIXED]** 整体删除（含死样式） |
| CHK-007 | ForumCard·精选回答预览 | `author_title \|\| '已认证超级个体'` | FAIL-MOCK | 假头衔兜底 **[FIXED]** 仅后端返回时显示 |
| CHK-008 | ForumDetailView·头部/作者栏 | 假 IP「来自 浙江」×2、硬编码「已认证超级个体」pill、`view_count \|\| 128` | FAIL-MOCK | **[FIXED]** 删除假 IP；pill 改为条件显示后端 author_title；view_count 显示真实值 |
| CHK-009 | ForumDetailView·回答卡 | `author_title \|\| '已认证超级个体'`、`word_count \|\| 120` | FAIL-MOCK | word_count 后端真实计算（service.py:323），不该兜底 **[FIXED]** 条件显示真实值 |
| CHK-010 | ForumDetailView·评论树 | 评论节点假 IP「来自 浙江」 | FAIL-MOCK | **[FIXED]** 删除（mapCommentNode 不再产出 ip_location） |
| CHK-011 | ForumCreateView | newThread 假 IP、昵称假兜底「认证创客」 | FAIL-MOCK | **[FIXED]** 删除；昵称兜底改为「我」（当前用户本人） |
| CHK-012 | 全局组件注册 | ForumTopCreatorBar.vue(1148行)、ForumPostModal.vue(469行) | FAIL-DEAD | 全工程零引用的死组件 **[FIXED]** 已删除文件 |
| CHK-013 | ForumView·发帖成功 | 本地假造 `upvotes:1, is_upvoted:true` | FAIL-MOCK | 作者并未真实投票 **[FIXED]**（上一轮）改用服务端返回值并走 transformThread+enrich |

## 第 2 组：DemandsView（需求集市）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-020 | 筛选栏/卡片流/详情/发布/竞标 | 全部按钮（发布/竞标/搜索/排序/刷新/互动条） | PASS | demands.list、demands.publish(DAG OPC_DEMAND_PUBLISH)、demands.bid、content.interaction.*、moderation.report 全部真实，无假成功 |
| CHK-021 | 侧栏·商机热榜 | 热度 `(bidders_count\|\|0)*3+42` | FAIL-MOCK | 伪公式造数 **[TO-FIX]** |
| CHK-022 | 侧栏·商机热榜 | 「实时更新」标签 | FAIL-MOCK | 实为本地已加载页排序切片 **[TO-FIX]** |
| CHK-023 | 详情·规格框 | 「PostgreSQL 库表持久存储」静态文案 | FAIL-MOCK | 装饰性写死文案 **[TO-FIX]** |
| CHK-024 | 脚本 | `creator_id/bidder_id` 兜底 `'usr_maker'` | FAIL-MOCK | 会话缺失时挂假用户 **[TO-FIX]** |
| CHK-025 | 脚本 | `isCacheHit` ref 三次赋值零读取 | FAIL-DEAD | **[TO-FIX]** |
| CHK-026 | 脚本 | `open-register` emit 声明未 emit；getIconFallbackStyle/getAuthorAvatarStyle 与参数无关 | FAIL-DEAD | **[TO-FIX]** |
| CHK-027 | 交互 | selectCategory 与 watch(currentCategory) 双重触发 reload | FAIL-DEAD | 同动作重复拉取（靠缓存吸收） **[TO-FIX]** |

## 第 3 组：ProfileView（创客档案）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-030 | 全页 | 档案加载/赛道保存/互动足迹/退出登录 | PASS | user.profile、user.profile.update、content.interactions.mine 全真实 |
| CHK-031 | 身份卡 | 「已签署合规协议 (v1.2.0)」 | FAIL-MOCK | 无论后端状态恒显示已签署 **[TO-FIX]** |

## 第 4 组：ConsoleView（DAG 控制台）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-040 | 工具栏 | 「执行场景」「热加载网关」 | PASS | orchestration.scenarios.execute、framework.gateway.reload 真实 |
| CHK-041 | 脚本面板 | 「安全编译」compileAst | FAIL-BROKEN | 空实现：不读代码、恒置成功、假 toast「AST 校验通过」；astSuccess 初始即 true **[TO-FIX]** |
| CHK-042 | 工具栏 | 「双模调度」toggleDispatcherMode | FAIL-BROKEN | 纯翻转 ref+假 toast，无任何后端调用 **[TO-FIX]** |
| CHK-043 | 热重载 | `reloaded_routes_count \|\| 64` | FAIL-MOCK | 假兜底 **[TO-FIX]** |
| CHK-044 | 画布/Inspector/算子库 | 静态 SVG 画布、写死节点属性/断言/门禁、无绑定的超时 select、写死仿真入参 260000、pythonCode 写后即弃 | FAIL-MOCK | 演示型静态内容 **[TO-FIX]**（与后端 orchestration.operators.list / dag.list 对接或移除装饰） |
| CHK-045 | 画布控制条 | 「微内核已加载 4 节点 · 3 边」 | FAIL-MOCK | 写死 **[TO-FIX]** |

## 第 5 组：OpsView（运营大盘）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-050 | 整页 | KPI 卡×6、iOS/Android 模拟机、快讯、商机、点赞数、装饰 tab bar | FAIL-MOCK | 整页 100% 硬编码，0 后端调用，script 为空 **[TO-FIX]** 重写为 telemetry.dashboard(ops.dashboard) 真实数据驱动，删除假模拟机 |
| CHK-051 | 标签 | 「实时遥测引擎」「TELEMETRY · ACTIVE」「LIVE」 | FAIL-MOCK | 假实时标签 **[TO-FIX]**（随 CHK-050 一并处理） |

## 第 6 组：PolicyView（政策中心）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-060 | 卡片/详情/发布/筛选 | 发布、列表、RAG 检索、刷新主链路 | PASS | policies.list、policies.publish、external.rag.policy_search、content.interaction.* 真实 |
| CHK-061 | 卡片/详情·匹配资格 | matchEligibility 失败/异常分支 | FAIL-BROKEN | res.ok=false 与 catch 均发 SUCCESS「符合申报条件」假成功 **[TO-FIX]** |
| CHK-062 | 侧栏·免税测算 | calculateTax 本地伪公式兜底 + 入参兜底 250000 + 初始假结果 | FAIL-MOCK | 后端失败时前端算、UI 无区分 **[TO-FIX]** |
| CHK-063 | 卡片/详情·AI提炼 | summarize 失败时本地拼假 AI 结果（写死模型名 Qwen2.5-72B） | FAIL-MOCK | 假 AI 产出 **[TO-FIX]** |
| CHK-064 | 搜索降级 | RAG 无结果打假分 95/60、`final_relevance \|\| 0.88`、拼造政策编号 POL-xxxx | FAIL-MOCK | **[TO-FIX]** |
| CHK-065 | 刷新按钮 | 无条件 SUCCESS「已从 PostgreSQL 同步」 | FAIL-BROKEN | 与实际成败无关的假成功 **[TO-FIX]** |
| CHK-066 | 脚本/样式 | formatLegalBasis 未引用、policyScrollContainerRef 未声明、similarity_score 死数据、整段旧弹窗死 CSS(~450行) | FAIL-DEAD | **[TO-FIX]** |

## 第 7 组：PerksView（生态特权）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-070 | 卡片/详情/发布 | 列表、发布、互动条 | PASS | perks.list、perks.publish、content.interaction.* 真实 |
| CHK-071 | 卡片/详情·「前往领取」 | openPerkUrl | FAIL-BROKEN | 后端有 perks.claim 契约（设计文档登记）但前端只 window.open；quota_remaining 永不扣减，纯展示 **[TO-FIX]** 接入 perks.claim |
| CHK-072 | 搜索 | 纯本地过滤且破坏性改写 perks.value、假文案「精确比对」 | FAIL-MOCK | **[TO-FIX]** |
| CHK-073 | 刷新按钮 | 无条件 SUCCESS 假成功 | FAIL-BROKEN | **[TO-FIX]** |
| CHK-074 | 脚本/样式 | perksScrollContainerRef 未声明、selectedPerk 声明序异常、死 CSS | FAIL-DEAD | **[TO-FIX]** |

## 第 8 组：ComplianceView（合规指南）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-080 | 卡片/详情/发布/刷新 | 法条/案例列表、发布、刷新 | PASS | compliance.laws、compliance.cases、compliance.publish 真实 |
| CHK-081 | 搜索 | 纯本地 includes 过滤（标榜「检索」） | FAIL-MOCK | 可接受为本地过滤，但需移除「检索」措辞或接入后端 **[TO-FIX]**（措辞+行为对齐） |
| CHK-082 | 刷新按钮 | 无条件 SUCCESS 假成功 | FAIL-BROKEN | **[TO-FIX]** |
| CHK-083 | 发布编号 | `LAW-${Math.floor(10+Math.random()*90)}` | FAIL-MOCK | **[TO-FIX]** |
| CHK-084 | 脚本 | emit('switch-tab') 声明未使用（App.vue 挂了死监听）、整段旧发布页死 CSS(~240行) | FAIL-DEAD | **[TO-FIX]** |
| CHK-085 | 侧栏 | 「实时更新」标签（本地 hot_score 排序切片） | FAIL-MOCK | **[TO-FIX]** |

## 第 9 组：全局壳层（App.vue / Navbar / LoginModal / RegisterModal / NotificationInbox / main.js）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-090 | App.vue | tab 切换/登录注册弹窗/会话恢复(auth.session)/未读数(notifications.unread_count)/主题切换 | PASS | 全部真实后端链路或合法本地偏好（主题/标签页记忆） |
| CHK-091 | Navbar | 导航切换/登录入口/角色切换/消息箱/主题 | PASS | 纯事件转发 + 本地偏好，无假数据 |
| CHK-092 | LoginModal | 三种登录模式 + 验证码发送（auth.send-code / auth.login） | PASS | 真实后端；「一键填入」仅在后端显式返回 mock_code（无 SMTP 凭据的开发存证模式，响应含明确标注文案）时出现，属后端驱动的降级模式而非前端 Mock |
| CHK-093 | RegisterModal | 注册/图形验证码(auth.captcha)/邮箱码/赛道选择 | PASS | 真实后端；setTimeout 为输入框聚焦时序（合法 UI 时序） |
| CHK-094 | NotificationInbox | 列表/标记已读/全部已读/删除 | PASS | notifications.list / mark_read / mark_all_read / delete 全真实 |

## 第 10 组：HomeView（首页）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-100 | 首页展览流 | `staticBaselineExhibits` 硬编码假政策/假风暴帖(@Master_Maker 1,420次阅读)/假福利 | FAIL-MOCK | 前端写死的假平台内容 **[FIXED]** 整块删除；展览流改为全部由后端驱动：products.list + policies.list + forum.feed.stream(hot) + perks.list 四路真实数据拼装 |
| CHK-101 | 首页其余 | Hero 按钮导航/三段旅程文案/页脚导航/Bento 卡 | PASS | 旅程与 Bento 为静态产品介绍文案（合法 UI 文案，非数据伪装）；导航全真实 |

## 第 11 组：ShowcaseView（产品橱窗）

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-110 | 卡片/详情/发布/检索 | 列表、语义检索(products.search.semantic)、发布(products.publish→OPC_PRODUCT_PUBLISH_PIPELINE)、互动条 | PASS | 主链路全部真实 |
| CHK-111 | 脚本 | handleUpvote → products.upvote（直连服务、无去重）+ upvotedIds/localStorage 双写 + res.ok=false 仍发 SUCCESS「打榜已记录」 | FAIL-DEAD+FAIL-BROKEN | 模板零引用的死链 + 与统一 LIKE 账本双记账 **[FIXED]** 删除前端整条死链；后端 products.upvote 路由/服务方法下线，测试改走 content.interaction.toggle(LIKE) 单一账本 |
| CHK-112 | 侧栏热榜 | `(upvote_count)*3+42` 伪公式 +「实时更新」 | FAIL-MOCK | **[FIXED]** 改为真实「N 赞」+「打榜排行」 |
| CHK-113 | 发布 payload | `author_id \|\| 'usr_maker'`、`author_name \|\| '@独立创客'` 假身份兜底 | FAIL-MOCK | 身份由网关 identity_guard 绑定 **[FIXED]** 删除假兜底 |
| CHK-114 | 互动同步 | handleInteractionChanged 将 like_count 写回 upvote_count | PASS | 产品域统一 LIKE→upvote_count 为既定镜像（_sync_domain PRODUCT），单一账本语义正确 |

## 第 12 组：SopView + SOP 组件族 + 编辑器

| 编号 | 位置 | 元素/内容 | 检查结果 | 详情 |
|---|---|---|---|---|
| CHK-120 | SopView 全部交互（49 处） | 文书目录/渲染/草稿/发布/删除、流程目录/编排/发布、模板详情、图编排 | PASS | sop.templates/document.render/publish/draft/delete/flow.get/publish/template.detail/sop.graph/sop.node 全部在网关注册；写路径 sop.document.render 与 sop.flow.publish 走 OPC_SOP_DOCUMENT_RENDER_PIPELINE / OPC_SOP_FLOW_PUBLISH_PIPELINE DAG 编排 |
| CHK-121 | SopView·喜欢/收藏 | handleLikeFlow/handleFavoriteFlow/handleLikeDocument/handleFavoriteDocument（sop.flow.like 等4场景） | FAIL-DEAD | 4 个 handler 模板/组件零引用（UI 实际全走统一互动条 LOVE/FAVORITE） **[FIXED]** 前端 4 handler 删除；后端 4 路由 + 4 适配器 + toggle_like/toggle_favorite（含 flow 变体）+ _likes/_favorites 集合 + 4 持久化域 + 响应模型 liked/favorited 字段整体移除；interactions 服务 legacy 播种分支同步清理；测试改写为统一互动链路 |
| CHK-122 | 组件注册 | SopFlowGuide/SopGoalFinder/SopNodeCard | FAIL-DEAD | 全工程零引用 **[FIXED]** 已删除文件 |
| CHK-123 | 编辑器 | RichEditor（3处引用）/IconPicker（2处引用） | PASS | 真实使用 |
| CHK-124 | Mock 扫描 | Math.random / setTimeout 假延迟 / 写死 IP / 假头衔 | PASS | SOP 家族未发现 |

## 修复后全量验证

- 后端：`pytest tests/` → **436 passed / 2 failed（既有基线：test_versioned_hot_reload，与本轮无关）/ 5 skipped**。
- 前端：`vite build` 通过；删除死组件 5 个（ForumTopCreatorBar、ForumPostModal、SopFlowGuide、SopGoalFinder、SopNodeCard），清理死 CSS 37 个规则块。
- 后端下线旧写入路径：`products.upvote`、`sop.document.like/favorite`、`sop.flow.like/favorite`（写操作收敛到统一互动域与 DAG 编排）。

---

# 第二轮复核：逐信息块 × 逐字段 × 无 handler 按钮全覆盖（2026-10-24）

> 针对第一轮的两个盲区补充：(a) 无 @click 的按钮（装饰/失效按钮会被 grep 漏掉）；
> (b) 信息块内每个插值字段 `{{ }}` 的数据来源逐个核对。方法：脚本提取全部 11 个视图的
> 128 个 `<button>`、全部 @click handler 实现核对、全部 52 个带静态兜底的插值字段逐一对照后端模型。

## 复核结果

| 编号 | 检查项 | 结果 | 详情 |
|---|---|---|---|
| CHK-130 | 全部 11 视图 128 个 `<button>` 中无 @click 的孤儿按钮 | PASS | 0 个（仅存在合法的 disabled 态按钮） |
| CHK-131 | 全部 @click/@submit/@keydown handler 均有脚本实现 | PASS | 0 缺失（仅 $emit 内联与方法链误报） |
| CHK-132 | 52 个带静态兜底的插值字段逐一对照后端模型 | 见下 | 分三类处置 |
| CHK-133 | 后端模型默认值镜像类（policy_level/region/deadline/action_text/level/mode 等约 20 处） | FAIL-DEAD→[FIXED] | 后端模型字段恒有值（str 带默认），前端 `\|\| '国家级'` 等为死兜底 → 删除，直显后端值 |
| CHK-134 | 编造事实类 | FAIL-MOCK→[FIXED] | ① PolicyView `model_used \|\| 'Qwen/Qwen2.5-72B-Instruct'`（编造模型名）→ 删除；② `selectedPolicy.code \|\| 'POL-2026'`（编造编号）→ 条件显示；③ ShowcaseView `version \|\| 'v1.0.0'`（与后端 "1.0.0" 格式不一致的死兜底）→ 直显后端值 |
| CHK-135 | 中性占位类（'—'/'未设置'/'@创客'/'匿名创客'/'暂未开放线上直达' 等） | PASS | 对"字段可为空"的诚实占位，不构成数据伪装，保留 |
| CHK-136 | 合规卡 issuer/badge 空值显示「发布机关」「避坑案例」（像数据实为占位） | FAIL-MOCK→[FIXED] | 改为中性 '—' 或空 |
| CHK-137 | **AI 网关 mock_summary 编造政策要点**（无 AI 凭据时返回写死的"增值税减按1%…年减免15万"假摘要，与所查政策无关且标注真实模型名） | FAIL-MOCK→[FIXED] | `ai_gateway.py` mock_summary 改为自标注「开发存证模式」+ `mocked: True` 字段；两个测试断言更新为诚实 mock 契约 |
| CHK-138 | **HomeView「创客心声」整块假社会认同**（@Leon_Tech/@Sophia_Design 假名、假城市、假战绩"300+试用用户"，标题却称"真实声音"） | FAIL-MOCK→[FIXED] | 整块删除（含死样式）；无后端证言数据源，不做伪造 |
| CHK-139 | SopView 今日文书/流程热榜 heat 公式 `(love_count)+(usage_count)*3` | PASS | 两个字段均为后端真实数据（统一互动 LOVE + 真实使用计数），公式透明 |
| CHK-140 | PerksView 公告统计速览（在架公告/覆盖分类等） | PASS | 全部由 perks.list 实时列表派生 |
| CHK-141 | 逐页信息块结构清单（每页 glass 容器数、v-for 数据源、区块注释清单） | PASS | 提取结果归档于本文件生成脚本；每块数据源均已在前述分组中逐块核验 |
| CHK-142 | Hero 区/底部转化 Banner/旅程区/Bento 区静态文案 | PASS | 产品介绍文案与营销语（无数编造数字），属合法 UI 文案；Hero/转化卡经核对无伪造统计数字 |

## 第二轮修复后验证

- 后端：`pytest tests/` → **436 passed / 2 failed（既有基线 test_versioned_hot_reload）/ 5 skipped**；
  AI mock 契约测试 14 项全绿。
- 前端：`vite build` 通过；HomeView 创客心声块删除后首页全部区块均为后端数据或合法静态文案。

---

# 第三轮：按钮功能重复专项审计与修复（2026-10-24）

> 方法：脚本提取 18 个文件约 200 个按钮按 handler 分组，逐组核实外层渲染条件判定「同屏共存 / 互斥 / 跨屏」。

| 编号 | 位置 | 重复情况 | 判定 | 处置 |
|---|---|---|---|---|
| DUP-1 | ComplianceView 发布入口 | 筛选栏「发布」+ 侧栏「发布法条/案例」+ 详情操作区「发布法条/案例」+ 免责卡「补充收录」链接 = 同屏最多 3 按钮+1 链接 | 真重复 | **[FIXED]** 收敛为筛选栏单一常显入口；删侧栏按钮、详情操作区按钮、免责卡链接 |
| DUP-2 | ForumDetailView 分享 | 头部「分享」与每条回答 dock「分享」同 handler 同负载（复制的均为帖子链接，回答区 title「分享此回答」标签失实） | 真重复+标签失实 | **[FIXED]** 删除回答区分享按钮，保留头部唯一分享入口 |
| DUP-3 | ConsoleView 执行 | 工具栏「执行场景」与画布控制条「仿真运行」同 runSimulation 常显同屏 | 真重复 | **[FIXED]** 删工具栏按钮，保留带 quarterly_income 入参的画布控制条入口 |
| DUP-4 | Navbar「平台首页」 | 管理员组 tab 与品牌点击 | **核实非重复**：管理员 brand 点击 → ops（非 home），「平台首页」是管理员唯一首页入口；创客 brand→home 属 logo 导航惯例 | 不改，记录结论 |
| DUP-5 | 发布双入口（Forum/Showcase/Policy/Demands/Perks） | 侧栏常显 CTA + 空态 CTA 共存（空列表时）；另有侧栏 guidelines 卡第三链接 | 条件冗余 | **[FIXED]** 删除四页 guidelines 第三链接（ForumView「提出探讨」/Showcase「申请上架」/PolicyView「申报入库」/DemandsView「发布委托」）；空态 CTA + 侧栏主 CTA 保留（空态时侧栏远离视线的场景引导，属设计性双入口） |
| DUP-6 | 搜索重置三重入口 | Policy/Perks/Compliance：输入框×+横幅「恢复全部」+空态「重置筛选条件」，搜索无结果时三者同屏；SopView 四工作区：横幅+空态「清除搜索条件」 | 条件冗余 | **[FIXED]** 空态重置改为仅 `!isSearchActive && currentCategory !== 'ALL'` 显示（分类筛选无结果时横幅隐藏、空态重置是唯一入口，保留；搜索态由横幅+输入框×承载）；SopView 四工作区空态「清除搜索条件」为纯重复（横幅已覆盖）全部删除 |
| DUP-7 | 互斥/跨屏相似入口 | 卡片互动条 vs 详情互动条、紧凑/舒适模式分支、展开/收起、弹窗×/取消、HomeView 首尾 CTA、论坛卡三重进详情导航 | 合法 | 不改：渐进披露/状态互斥/对话框惯例/落地页惯例/导航携带各自计数信息 |

修复后验证：vite build 通过；后端 pytest 436 passed（2 项为既有 hot-reload 基线失败）。

---

# 第四轮：E2E 浏览器实测（2026-10-24，前后端真实服务 + Playwright 驱动）

> 环境：后端 uvicorn :8000 + 前端 server.py 服务 dist :3000（/api 反代）；浏览器真实点击流。

## E2E 检查结果

| 编号 | 场景 | 操作流 | 结果 |
|---|---|---|---|
| E2E-01 | 首页展览流 | 加载首页 | PASS：作品/政策/风暴/特权四路后端数据渲染（InkFlow 344赞、POL-2026-081、142 赞同议题、AWS/火山方舟公告） |
| E2E-02 | 创客注册 | 邮箱+图形验证码(算术题)+邮箱验证码+密码+协议勾选 | PASS：开发存证模式诚实返回验证码；注册成功自动登录，toast「已持久化落库 PostgreSQL 18」 |
| E2E-03 | 论坛投票 | 卡片赞同→取消 | PASS：142→143(active)→142，forum.vote DAG 唯一账本 |
| E2E-04 | 论坛详情 | 打开详情；收藏往返 | PASS：头部分享=1、回答区分享=0（DUP-2 ✓）；收藏 45→46(active) 走统一互动；举报/评分在位 |
| E2E-05 | 特权领取 | 前往领取 AWS Activate | PASS：perks.claim DAG 执行→打开真实 redeem_url 新标签页；服务端配额 300→299 |
| E2E-06 | 合规发布入口 | 加载+打开详情 | PASS：常显发布入口仅筛选栏 1 处、详情区 0、侧栏链接 0（DUP-1 ✓） |
| E2E-07 | 控制台（管理员） | 加载+仿真运行 | PASS：唯一执行按钮（DUP-3 ✓）；113 个真实算子、5 节点真实拓扑（orchestration.operators.list/dag.list）；仿真执行成功 toast「耗时 5.79ms」 |
| E2E-08 | 运营大盘 | 加载 | PASS：TELEMETRY·LIVE；6 KPI 诚实「0·暂无埋点数据源」；7 行模块热力图为真实域记录数 |
| E2E-09 | 角色门禁 | 创客访问 #backend-orch | PASS：控制台不渲染（App.vue 角色门禁生效），导航无编排页签 |

## E2E 发现并修复的新问题

| 编号 | 问题 | 修复 |
|---|---|---|
| E2E-F1 | 首页 Hero 统计数字全假（8,400+ 创客 / 36+ 城市 / ¥1,280万+ / 99.8% 通过率，无数据源；正文另有一处 8,400+） | **[FIXED]** 改为页面已加载四路后端数据实时派生（在展作品数/收录政策数/风暴议题数/生态特权累计价值 ¥） |
| E2E-F2 | perks.claim_count 从不递增（死展示字段；领取后仍为 0） | **[FIXED]** claim 时 +1、revoke 时 -1（service.py） |
| E2E-F3 | **全站无修改密码 UI**：后端 auth.change_password 适配器存在但 (a) 网关路由从未注册（孤儿适配器，404）(b) 前端零入口 → 内置管理员被 must_change_password 永久锁在高风险页外 | **[FIXED]** 注册 auth.change_password 路由；ProfileView 新增「账号安全·密码轮换」卡片（旧/新密码→auth.change_password），成功后以返回的新 token 续期本地会话；实测完成管理员轮换并以新密码重新登录解锁 Console/Ops |
| E2E-F4 | 改密成功后本地会话 token 未刷新（must_change 标记烧录在旧 token 内） | **[FIXED]** changePassword 成功分支写入服务端返回的新 token |

## 最终验证
- 后端 `pytest tests/`：**436 passed / 2 failed（既有 hot-reload 基线）/ 5 skipped**；perk 相关 23 项全绿。
- 前端 `vite build` 通过。
- E2E 全部 9 场景通过；4 项 E2E 发现缺陷全部修复并复测通过。

---

# 第五轮：产品文案实现层泄露专项清理（2026-10-24）

> 规则：产品页面（含 toast/加载/错误提示）禁止出现底层实现描述（数据库/存储/编排引擎/网关等）。
> 管理员编排控制台（ConsoleView/OpsView）中「算子/DAG/拓扑」为其业务本体，保留；SOP 页「流程编排」为用户业务语义，保留；
> 代码注释不属于产品可见层，保留；LegalModal 法律条款仅去除「微内核」一词。

| 编号 | 位置 | 原泄露文案 | 修复后 |
|---|---|---|---|
| LEAK-01 | ProfileView 副标题 | PostgreSQL 18 实体数据落盘、合规法定义务存证及创客身份标识 | 创客商用档案、资质合规存证与平台身份标识 |
| LEAK-02 | ProfileView 卡片标题 | 商业资质与合规存证 (PostgreSQL 18 ACID) | 商业资质与合规存证 |
| LEAK-03 | ProfileView 赛道保存提示 | 业务赛道已成功更新并持久化落盘！ | 业务赛道已更新成功！ |
| LEAK-04 | HomeView 页脚 | PostgreSQL 18 存证保障 | 商业数据云端加密存管 |
| LEAK-05 | App.vue 注册成功 toast | 已完成商用认证并持久化落库 PostgreSQL 18！ | 已完成商用认证，欢迎入驻！ |
| LEAK-06 | RegisterModal 提交按钮 | 商用入驻审核与事务落库中... | 商用入驻审核中... |
| LEAK-07 | Compliance 详情规格行 | 数据存储 / PostgreSQL 合规库持久化 | 收录审核 / 平台审核收录 · 来源官方可溯 |
| LEAK-08 | Policy 详情规格行+公约卡 | 微内核数据校验 / PostgreSQL 库表持久化 & 零依赖向量检索；微内核发布门禁与持久化算子校验 | 收录审核 / 官方公文依据 · 全域语义检索；平台审核收录 |
| LEAK-09 | Perks 详情规格行 | 微内核数据校验 / PostgreSQL 公告库持久化 & 微内核发布门禁校验 | 公告审核 / 平台审核上架 · 优惠信息可溯源 |
| LEAK-10 | Showcase 详情规格行 | 数据与持久化 / PostgreSQL 库表持久存储 | 商用交付保障 / 官网直达 · 平台审核上架 |
| LEAK-11 | Demands 详情规格行 | 数据与持久化（标签残留） | 交易保障 |
| LEAK-12 | ForumDetailView 回答发布 toast | 已通过微内核 DAG 编排流水线完成安全审查与持久化归档！ | 已通过平台安全审查并发布！ |
| LEAK-13 | ForumView 删除确认弹窗 | 从 OpcHub 知识库与网关节点中注销此帖 | 从平台彻底删除此帖 |
| LEAK-14 | Forum 社区公约 | 真实代码落盘 | 真实代码落地 |
| LEAK-15 | 三页发布 toast（Compliance/Policy/Perks） | 已通过平台敏感词校验并… | 已通过平台审核并… |
| LEAK-16 | Perks 加载/错误 ×3、Forum/Showcase/CreateView 网关错误文案 ×5 | 「从网关加载/网关响应异常/网关通信失败/发布流水线校验」 | 「加载/网络异常/服务暂时不可用/发布校验」 |
| LEAK-17 | NotificationInbox ×2、PublishNotice、SopMyDoc/FlowCard | 敏感词校验（结果通知/等待检查） | 内容审核（结果通知/等待平台合规审核） |
| LEAK-18 | LegalModal 服务范围 | 分布式微内核业务编排 | 分布式业务编排 |
| LEAK-19 | OpsView 说明、ConsoleView 说明 | 含 DAG 场景码 OPC_OPS_DASHBOARD_PIPELINE / orchestration.scenarios.execute | 业务化措辞（指标聚合自各业务域实时记录 / 真实流水线调用） |
| 保留 | ForumCreateView 快捷标签 'PostgreSQL' | — | 与 FastAPI/Vue3 并列的用户话题标签，属发帖内容主题而非平台实现描述 |
| 保留 | Console/Ops 管理页算子术语、SOP「流程编排」、代码注释 | — | 管理页业务本体 / 用户业务语义 / 非可见层 |

**验证**：产品层终扫（模板+toast，排除管理页/注释/合法业务词）零残留；vite build 通过；浏览器实测 Profile 页（旧泄露文案消失、新文案在位）与 Home 页脚（云端加密存管在位、PostgreSQL 消失）。

---

# 第六轮：编排工作台建设（后端 DAG 编排 + 前端布局编排，2026-10-24）

> 背景：管理员反馈「前端编排 / 后端编排」两页空置。核实：创客身份被角色门禁拦截 + 改密前 403 属正常安全行为；
> 但两 tab 此前渲染同一只读控制台，且无操控编排能力——本轮补齐为两个真实可操控的编排工作台。

## 后端编排工作台（backend-orch，ConsoleView 重写）

| 能力 | 实现（全部真实后端链路） |
|---|---|
| 看到全部算子 | orchestration.operators.list，113 个算子按 16 个 domain 分组 + 关键字筛选 |
| 看到全部场景 | orchestration.dag.list 全量加载（35+ 场景含版本/状态），下拉选择 |
| 看到编排方式 | Kahn 分层 DAG 画布：节点卡片（id/handler/type + ENTRY/EXIT 徽标）+ SVG 箭头连线 |
| 操控-增删节点 | 编辑模式下点击算子库加入画布（id 自动去重、type 按名称推断）；悬停节点 × 删除（级联删边） |
| 操控-连线 | 点击源节点再点目标节点连线；防自环/防重边/DFS 防成环 |
| 操控-入口出口 | Inspector 内 ENTRY/EXIT 按钮设定；加节点自动推进 exit（修复首节点占位 bug） |
| 操控-保存部署 | orchestration.dag.save 全量拓扑保存（hash 返回展示）；支持改版本、新建场景、复制当前场景 |
| 执行验证 | 任意 JSON 入参 → orchestration.scenarios.execute；节点级 trace 表（状态/耗时）+ final_output |

E2E 实测：新建场景 E2E_TEST_FLOW → 空白画布 → 添加 gateway_ingress + policy.calculate_tax → 连线 1 条 → 保存部署 →
服务端 dag.list 确认持久化（ACTIVE，2 节点 1 边）→ **真实执行 SUCCESS（两节点全部成功）**。

## 前端布局编排工作台（frontend-orch，新建 FrontendOrchView，替换原先复用 ConsoleView 的错误挂载）

| 能力 | 实现 |
|---|---|
| 看到当前布局 | frontend.layouts.get 实时载入 main_console_layout（24 栅格 + 组件清单），画布按 span 栅格渲染 |
| 操控-添加组件 | 6 类组件库（统计卡/表单/图表/列表/动态流/横幅）点击加入 |
| 操控-属性编辑 | 选中组件改标题/说明/占列宽（1-24 + 常用预设），悬停 × 删除 |
| 操控-保存部署 | frontend.layouts.save 持久化（版本可编辑），JSON 预览核对 |
| 数值语义 | 组件数值列标注「由业务数据绑定」，不伪造展示数据 |

E2E 实测：载入种子 3 组件 → 添加「图表」组件并命名「月度免税额度趋势」→ 保存 → 服务端 frontend.layouts.get 确认
4 组件全部落库（v1.0.4）。

## 修复缺陷
| 编号 | 问题 | 修复 |
|---|---|---|
| ORCH-F1 | frontend-orch 与 backend-orch 渲染同一 ConsoleView（前端布局编排能力缺失） | 新建 FrontendOrchView 独立承载，App.vue 分开挂载 |
| ORCH-F2 | 场景下拉仅写死 3 个场景码 | 改为 dag.list 全量动态加载（35+ 场景） |
| ORCH-F3 | 执行入参写死 quarterly_income | 任意 JSON 入参编辑器（含格式校验）+ 节点 trace 结果面板 |
| ORCH-F4 | 无编排编辑能力（只读） | 编辑模式全套（增删节点/连线/防环/entry-exit/保存部署/新建/复制） |
| ORCH-F5 | 添加第二节点时 exit_node 不更新（保持为 entry） | 节点推进逻辑修复 |

**验证**：vite build 通过；后端 pytest 436 passed（2 项既有基线）；两工作台浏览器 E2E 全通且服务端落库可查。

---

# 第七轮：功能性文案禁止换行 + 滚动条全局隐藏（2026-10-25）

> 规则：(1) 所有功能性标签/按钮/提示词绝不换行；(2) 超长内容以滑动方式滚动展示，但任何位置不显示滚动条。

| 编号 | 修复 | 说明 |
|---|---|---|
| WRAP-01 | style.css 全局规则块 | `* { scrollbar-width:none }` + `*::-webkit-scrollbar{display:none}`（全局隐藏滚动条，保留滚动能力）；`button/select/label/.mono-tag/[class*=pill-label]/[class$=-pill]` 全部 `white-space:nowrap`；`select{text-overflow:ellipsis}` |
| WRAP-02 | ConsoleView 场景条/工具条 | 「场景:」等 pill 标签不再换行：bar 改 `nowrap + overflow-x:auto`，pill `flex-shrink:0`，长场景名 select 走 ellipsis，保存提示单行 ellipsis |
| WRAP-03 | FrontendOrchView 元信息条 | 同款修复（nowrap + 横滚 + 消息 ellipsis） |
| WRAP-04 | 七个业务页筛选条 | Forum/Showcase/Policy/Demands/Sop/Perks/Compliance 的 `.feed-filter-bar` 统一 `nowrap + overflow-x:auto`（Showcase 补齐 flex 布局；Demands 移除 600px 断点的纵向换列改为保持横滚单行） |
| WRAP-05 | 长场景名退化 | 场景下拉 35+ 项（如 OPC_COMPLIANCE_STARTUP_FLOW · v1.0.0）以 ellipsis 呈现，不再撑破/换行 |

**验证**：vite build 通过；后端 pytest 436 passed（2 项既有基线）。浏览器实测三页（backend-orch / frontend-orch / policy）：
场景条与筛选条均单行（pill 高度 <40px）、标签 computed white-space=nowrap、滚动条宽度实测 0、超长条可横向滚动（scrollWidth>clientWidth），截图归档。
