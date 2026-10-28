# OpcHub 前端交互对标与重构建议（2026-10-26）

> 文档类型：前端交互对标 / 只做研究与方案，不改代码
> 对标范围：11 个业务视图 + 共享卡片/互动/弹窗组件 + 管理端编排工作台
> 设计约束：`/DESIGN.md`（液态玻璃、内容优先、克制色彩、杜绝廉价图标）
> 技术约束：Vue 3 + Vite（`vue-router` 已在依赖中但未使用）

---

## 0. 一页纸结论

现在的前端不是「视觉不够炫」，而是**所有内容被同一套卡片语法压平了**：

- 政策、帖子、作品、需求、文书、特权，全部长成同一张卡；
- 每张卡底部固定挂 6–8 个同权图标，主行动被淹没；
- 详情靠页内替换，没有独立 URL，浏览器返回、刷新、分享都不可靠；
- 筛选/搜索/排序状态不落地，换页即丢；
- 管理端编排是「点击添加 + 手画 SVG」，缺拖拽、缩放、撤销、试跑；
- 平台真正的差异化「申报文书」仍以卡片瀑布为主入口，而不是向导。

**最值得抄的不是视觉，而是三类交互骨架：**

1. **URL 即状态 + 详情路由 + 分面筛选**（Discourse / Apache Answer / Taxonomy）
2. **一问一屏 + 检查答案 + 任务清单 + 文档组装**（Docassemble / GOV.UK Patterns）
3. **专业编辑器 + 可审阅 AI + 执行 trace**（n8n / Dify / Vue Flow / Vercel AI）

**如果只做三件事：**

1. 引入 `vue-router`，把「列表 / 详情 / 发布 / 编辑」变成真实路由，筛选参数进 URL；
2. 把卡片动作从 6–8 个收敛成「1 个主行动 + 1–2 个次行动 + 更多菜单」；
3. 把 SOP 文书与政策申报改成「向导 + 进度 + 检查答案 + 生成文书」的主流程。

---

## 1. 现状诊断（有代码依据，不是审美评价）

| # | 问题 | 证据 | 用户实际感受 |
|---|---|---|---|
| 1 | **一套卡片套所有内容类型** | `PolicyView`、`ForumView`、`ShowcaseView`、`DemandsView`、`SopView` 共用同一套卡片骨架与互动条 | 看什么都像同一份列表，无法一眼判断「这条内容能干什么」 |
| 2 | **互动图标过多且同权** | `ContentInteractionBar.vue` 渲染点赞、点踩、评论、喜欢、收藏、举报、评分；政策卡还额外挂「AI 提炼」「匹配资格」 | 每张卡 6–8 个图标，像工具栏；误触多，主行动不突出 |
| 3 | **详情是页内替换，不是路由** | `PolicyView.vue:926-933` 仅设置 `selectedPolicy`；`ForumView.vue:889-902` 用 `replaceState` 写 `#forum?post_id=` | 刷新丢详情、分享链接不稳、浏览器返回直接退出模块 |
| 4 | **筛选/搜索/排序不入 URL** | 各 View 使用本地 `ref` 保存 `currentCategory/currentSort/searchQuery` | 刷新回到默认；无法把「某分类 + 某关键词」发给别人 |
| 5 | **搜索交互单一** | 多数页面是「输入 + 点搜索按钮」，语义搜索与本地过滤混用 | 不知道有没有搜到、为什么搜到；无最近搜索/键盘导航/建议词 |
| 6 | **发布是长表单，不是向导** | `PublishForm.vue` 按 section 平铺所有字段；无分步、草稿、检查答案、错误汇总 | 第一次发布的人不知道要填多久、漏填后要来回找 |
| 7 | **SOP 的差异化被卡片埋没** | `SopDocPage.vue` 已有字段帮助/示例/坑点/实时预览，但入口仍是标准文书卡片流 | 平台最强的「引导填写」能力，用户第一眼看不到 |
| 8 | **管理端编排不可「编」** | `FrontendOrchView.vue:34-45` 点击添加、`88-93` 数字输入列宽；`GraphEditor.vue` 手写 SVG 节点/连线 | 不能拖拽、缩放、撤销、预览、试跑；改布局像改 JSON |
| 9 | **全局壳层缺基础设施** | `main.js` 只 `createApp`；`App.vue:29-121` 用 11 个 `v-if` 切视图；`Navbar.vue` 8 个平铺 tab | 无面包屑、无全局搜索、无命令面板、无统一抽屉/弹窗 |
| 10 | **角色门禁是死路** | 非管理员访问 `#backend-orch` 时 `activeTab` 不在 Maker 白名单，页面渲染空白 | 用户看到一片空白，不知道是没权限还是坏了 |

补充：`package.json` 已有 `vue-router`，但 `src` 内零引用，说明路由能力已经具备、只是没用起来。

---

## 2. 按模块的 GitHub 对标

> Star 数为 2026-10-26 抓取，仅作活跃度参考，不作为选型唯一依据。

### 2.1 总表

| 平台模块 | 推荐参照（GitHub） | 直接可抄的交互 | Vue 落地 |
|---|---|---|---|
| 头脑风暴 / 论坛 | [apache/answer](https://github.com/apache/answer) ★15.7k<br>[discourse/discourse](https://github.com/discourse/discourse) ★48k<br>[forem/forem](https://github.com/forem/forem) ★22.8k | 问题页「投票 + 回答 + 标签 + 相关」；未读追踪；草稿自动保存；Composer 预览；审核队列；键盘快捷键 | 直接照 Answer 的信息架构重排 `ForumView` / `ForumDetailView`；不换后端 |
| 政策中心 | [PolicyEngine/policyengine-app](https://github.com/PolicyEngine/policyengine-app) ★68（产品交互强）<br>[alphagov/govuk-design-system](https://github.com/alphagov/govuk-design-system) ★683<br>[uswds/uswds](https://github.com/uswds/uswds) ★7.2k | 参数滑杆 → 结果卡 →「你为什么符合/不符合」；Start page；Check answers；Task list；Error summary | 政策详情增加「资格自测」向导；免税测算从侧栏小工具升级为结果页 |
| 流程文书 / SOP | [jhpyle/docassemble](https://github.com/jhpyle/docassemble) ★992<br>[surveyjs/survey-library](https://github.com/surveyjs/survey-library) ★4.9k<br>[formbricks/formbricks](https://github.com/formbricks/formbricks) ★13.1k | 一问一屏引导访谈；进度；条件跳转；检查答案；文档组装；草稿续填 | 用现有 `required_fields` 生成 step；加 progress + review + 生成 PDF；表单引擎可先用自研 |
| 产品橱窗 / 需求集市 | [shadcn-ui/taxonomy](https://github.com/shadcn-ui/taxonomy) ★19.3k<br>[medusajs/medusa](https://github.com/medusajs/medusa) ★37k<br>[calcom/cal.com](https://github.com/calcom/cal.com) ★49.4k | 分类/搜索/分页/详情布局；商品规格与交付；服务预约与时区可用性 | 橱窗做「列表 + 详情 + 联系/交付」；需求做「预算 + 截止 + 竞标状态」；预约型需求可借 Cal.com |
| 生态特权 / 会员 | [antiwork/gumroad](https://github.com/antiwork/gumroad) ★10k<br>[novuhq/novu](https://github.com/novuhq/novu) ★40.2k | 单路径领取/结算/收据；权益到期提醒；通知 inbox | 特权卡只保留「查看条件 / 立即领取」；领取结果用 receipt 式确认页 |
| 合规指南 | [outline/outline](https://github.com/outline/outline) ★41k<br>[docmost/docmost](https://github.com/docmost/docmost) ★22.1k | 左侧目录树 + 全文搜索 + 面包屑 + 右侧目录 + 版本/评论 | 合规详情从卡片改成「文档阅读器」；法条/案例可互链 |
| 管理端后端编排 | [n8n-io/n8n](https://github.com/n8n-io/n8n) ★208k<br>[langgenius/dify](https://github.com/langgenius/dify) ★159k<br>[bcakmakoglu/vue-flow](https://github.com/bcakmakoglu/vue-flow) ★6.9k | 节点面板搜索/拖拽；连线校验；右侧节点设置抽屉；试跑与逐节点 trace；版本历史；启用开关 | 用 Vue Flow 替换 `GraphEditor` 手写 SVG；加 test-run 底部抽屉 |
| 前端布局编排 | [qmhc/grid-layout-plus](https://github.com/qmhc/grid-layout-plus) ★621<br>[Alfred-Skyblue/vue-draggable-plus](https://github.com/Alfred-Skyblue/vue-draggable-plus) ★4k<br>[measuredco/puck](https://github.com/measuredco/puck) ★13.5k | 拖拽/缩放栅格；组件树；属性面板；桌面/平板/手机预览；撤销/重做；发布 diff | `FrontendOrchView` 从「点击添加」升级为「拖拽 + 预览 + 撤销」 |
| 运营大盘 | [plausible/analytics](https://github.com/plausible/analytics) ★29.7k<br>[umami-software/umami](https://github.com/umami-software/umami) ★39.7k<br>[tremorlabs/tremor](https://github.com/tremorlabs/tremor) ★3.7k | 时间范围/对比/维度下钻；空数据诚实态；KPI + 趋势 + 明细 | `OpsView` 做「今日/7 日/30 日 + 模块下钻」，不要堆静态卡 |
| 消息箱 / 通知 | [novuhq/novu](https://github.com/novuhq/novu) ★40.2k | 全部/未读 tab；批量已读；偏好；乐观更新；未读 badge | 现有 `NotificationInbox` 加 tab/过滤/乐观已读即可 |
| 全局搜索 / 命令面板 | [xiaoluoboding/vue-command-palette](https://github.com/xiaoluoboding/vue-command-palette) ★590<br>[pacocoursey/cmdk](https://github.com/pacocoursey/cmdk) ★13k | ⌘K 唤起；模糊搜索；分组结果；键盘上下选择；最近访问 | 顶栏加搜索入口；先聚合现有 4 个 list 接口 |
| 全局组件底座 | [unovue/reka-ui](https://github.com/unovue/reka-ui) ★6.9k<br>[unovue/shadcn-vue](https://github.com/unovue/shadcn-vue) ★10.7k<br>[vueuse/vueuse](https://github.com/vueuse/vueuse) ★22.4k<br>[formkit/formkit](https://github.com/formkit/formkit) ★4.8k<br>[xiaoluoboding/vue-sonner](https://github.com/xiaoluoboding/vue-sonner) ★1.5k<br>[unovue/vaul-vue](https://github.com/unovue/vaul-vue) ★497 | 可访问 Dialog/Popover/Tabs/Select；表单校验；Toast（带撤销）；移动端 Drawer；防抖/滚动观察/URL 状态 | 替换 5 套手写 modal/drawer，统一 focus trap、Esc、ARIA |
| AI 辅助 | [vercel/ai](https://github.com/vercel/ai) ★27.5k<br>[vercel/ai-chatbot](https://github.com/vercel/ai-chatbot) ★21k<br>[open-webui/open-webui](https://github.com/open-webui/open-webui) ★156.8k<br>[vuepont/ai-elements-vue](https://github.com/vuepont/ai-elements-vue) ★1.2k | 流式输出；消息重试/复制/编辑；引用来源；工具调用状态；逐段采纳 | 政策 AI 提炼、SOP 代写统一成「右侧 AI 面板 + 引用 + 采纳」 |

### 2.2 重点参照拆解

#### A. Apache Answer：论坛不是「卡片流」，是「问题页」

**现状**：`ForumView` 是文章流 + `ForumDetailView`，卡片上同时有赞同/反对/回答/分享/删除/收藏/喜欢/评论/举报/评分。

**Answer 的做法**：

- 列表页只回答三个问题：**标题、标签、多少回答/多少投票、最后活跃**；
- 进入问题页后，左侧是问题与回答，右侧是「相关问题 / 标签 / 作者」；
- 回答区有独立的编辑器、草稿、预览；
- 投票与「采纳答案」是页面级主行动，不与收藏/举报混排；
- 用户声望、徽章、标签关注是独立信息层。

**建议抄**：

1. `ForumView` 卡片只保留：标题、摘要（2 行）、标签、作者、`N 回答 · N 赞同 · 最后活跃`；
2. 卡片主行动 = 「阅读 / 回答」；收藏/分享进「更多」；
3. `ForumDetailView` 顶部放「赞同 / 反对 / 回答」三个主行动，回答编辑器固定在回答列表上方；
4. 增加「未读/已读」状态与「我关注的问题」；
5. 举报、评分、点踩从卡片移除，只在详情「更多」里出现。

**不要抄**：Answer 的 Go 模板/后端；只借信息架构与交互层级。

#### B. PolicyEngine + GOV.UK：政策不是「文章」，是「可计算的服务」

**现状**：政策卡有「AI 提炼」「匹配资格」，侧栏有「增值税免税即时测算」，但三者是分散按钮/小工具；详情仍是文章阅读。

**PolicyEngine 的做法**：

- 先让用户建立「家庭/收入/地区」最小画像；
- 用滑杆/输入改参数，右侧即时给出「净收入变化 / 税负 / 受益/受损」；
- 结果不是一段 AI 文案，而是**可解释的计算结果 + 假设 + 来源**；
- 支持「这是怎么算的」展开。

**GOV.UK 的做法**：

- Start page：告诉用户「需要什么材料、要多久、谁可以申请」；
- One thing per page：一屏只问一个问题；
- Check your answers：提交前集中复核；
- Task list：多步骤事务显示「已完成 / 进行中 / 尚不能开始」；
- Error summary：提交失败时顶部汇总，点击跳到字段。

**建议抄**：

1. 政策详情增加「30 秒资格自测」：地区 → 主体类型 → 营收/人数 → 行业 → 结果；
2. 结果页给「符合 / 可能符合 / 不符合」+ **缺失条件** + **需要准备的材料** + **官方原文引用**；
3. 免税测算从侧栏挪到「工具」页或详情内嵌结果卡，保留输入摘要与「重新测算」；
4. AI 提炼不要直接弹一段文字，改成「要点 / 适用对象 / 申报材料 / 风险提示」四块，并标注来源段落。

**不要抄**：PolicyEngine 的美国税制模型；只借「参数 → 结果 → 解释」的交互。

#### C. Docassemble：SOP 不是「文书卡片」，是「引导访谈」

**现状**：`SopDocPage` 已支持字段帮助、示例、坑点、实时预览、保存/导出，但用户要先在卡片流里找到文书，再一次性面对所有字段。

**Docassemble 的做法**：

- 一次只问一个问题（或一组强相关字段）；
- 顶部有进度；
- 根据前序答案条件跳转；
- 最后「检查答案」→ 生成文档；
- 中断后可继续填。

**建议抄**：

1. 文书卡主按钮从「查看」改成「开始填写」，并显示「约 8 个问题 · 3 分钟」；
2. 把 `required_fields` 按 `section/stage` 切成 step；一屏 1–3 个字段；
3. 每步保留现有 `help/example/pitfalls`，但收进「为什么需要这个」折叠；
4. 增加「检查答案」页，按文书最终格式预览；
5. 增加自动保存草稿 + 「继续上次填写」入口；
6. 流程（多份文书）用 GOV.UK Task list：已完成 / 进行中 / 尚不能开始 / 不需要。

**不要抄**：Docassemble 的 YAML 运行时；只借「访谈 → 复核 → 组装」的流程。

#### D. Taxonomy / Medusa / Cal.com：橱窗与集市要有「商品语法」

**现状**：产品、需求、特权都复用同一套卡片；没有规格、库存、交付、截止、竞标状态等专属信息。

**建议抄**：

- **Taxonomy**：分类 + 搜索 + 分页 + 详情页的经典结构；筛选条件在 URL；空态有建议。
- **Medusa**：产品详情的「主图 / 规格 / 价格 / 交付 / 卖家」信息层级；变体选择不要用下拉堆叠。
- **Cal.com**：如果需求涉及预约咨询，直接借「选日期 → 选时段 → 填信息 → 确认」的四步。

**建议**：

1. 橱窗卡：封面/截图 + 一句话 + 作者 + 分类 + `N 赞`；主行动「查看详情」；次行动「收藏」；
2. 需求卡：预算区间 + 截止倒计时 + `N 人竞标` + 状态；主行动「查看 / 竞标」；
3. 特权卡：价值 + 剩余名额 + 有效期 + 使用条件；主行动「立即领取」；
4. 详情页统一「左内容 + 右行动卡（价格/截止/领取/联系）」；移动端行动卡吸底。

#### E. n8n / Dify / Vue Flow：编排后台要像「编辑器」，不是「表单」

**现状**：`GraphEditor.vue` 用绝对定位 div + SVG 画线；点击节点再点另一个节点连线；无 pan/zoom/minimap；`FrontendOrchView` 点击添加组件、输入列宽。

**n8n / Dify 的做法**：

- 左侧节点面板可搜索、可拖拽；
- 画布支持平移/缩放/框选/小地图；
- 连线有端口与合法性校验；
- 选中节点右侧开设置抽屉；
- 「执行此节点 / 执行到此节点 / 执行全流程」；
- 执行结果按节点展示输入/输出/耗时/错误；
- 版本历史、启用/停用、撤销/重做。

**建议**：

1. 用 `@vue-flow/core` 替换手写 SVG：pan/zoom、minimap、controls、edge reconnect；
2. 节点拖拽入画布，连线用端口，非法连接即时提示；
3. 右侧 Inspector 改成抽屉，字段分组；
4. 底部加「试跑」抽屉：JSON 入参 → 逐节点 trace → final output；
5. 顶部加 undo/redo、保存草稿、发布、版本对比；
6. `FrontendOrchView` 用 `grid-layout-plus`：拖拽/缩放、组件树、属性面板、桌面/平板/手机预览、发布前 diff。

#### F. Outline / Docmost：合规指南是「知识库」，不是「卡片列表」

**建议**：

- 左侧目录树（法律层级 / 主题 / 地区）；
- 顶部面包屑 + 搜索；
- 正文右侧「本文目录」；
- 法条与案例互相引用，点击跳转；
- 版本/生效日期/效力状态固定在标题下；
- 相关法条、相关案例、常见问题放在文末。

#### G. Novu：消息箱要有「收件箱语法」

**建议**：

- 全部 / 未读 / 系统 / 审核结果 四个 tab；
- 每条通知有类型图标、标题、摘要、时间、跳转目标；
- 支持单条已读、全部已读、按类型已读；
- 乐观更新：点击即变已读，失败回滚；
- 通知跳转要落到具体详情路由，而不是只切 tab。

#### H. Vercel AI / AI Elements Vue：AI 输出要「可审阅」

**建议**：

- 右侧固定 AI 面板，不遮挡正文；
- 生成中显示步骤/工具调用；
- 输出带引用角标，点开看原文；
- 每个段落可「采纳 / 重写 / 删除」；
- 失败可重试，保留上一次结果；
- 生成结果与手工编辑合并到同一份草稿，不产生第二份真相。

---

## 3. 跨模块的 7 条交互基线

### 3.1 路由与 URL 状态

- 引入 `vue-router`，路由建议：
  - `/` 首页
  - `/forum`、`/forum/:id`
  - `/products`、`/products/:id`
  - `/policies`、`/policies/:id`
  - `/demands`、`/demands/:id`
  - `/sop`、`/sop/docs/:id`、`/sop/flows/:id`
  - `/perks`、`/compliance`、`/compliance/:id`
  - `/profile`、`/membership`
  - `/admin/orchestration`、`/admin/layout`、`/admin/ops`、`/admin/moderation`
- 列表筛选进 query：`?q=&category=&sort=&page=&tag=`；
- 详情用 path param，不用 `selectedX` 本地状态；
- 浏览器返回/前进必须能复现「列表位置 + 筛选 + 详情」；
- 非授权路由重定向到首页并 toast，不渲染空白。

### 3.2 列表页语法

统一为四段：

1. **Page Header**：标题 + 一句话说明 + 主行动（发布/新建）；
2. **Filter Bar**：搜索框（即时/防抖）+ 分类 chips（带计数）+ 排序 + 视图切换 + 更多筛选；
3. **Active Filters**：已选条件 chip，可单个移除 / 全部清除；
4. **Results**：卡片/列表 + 加载骨架 + 空态 + 错误态 + 加载更多/分页 + 到底提示。

### 3.3 详情页语法

统一为：

- 面包屑（返回列表，保留筛选）；
- 标题 + 状态/分类/时间；
- 左侧正文（分节、可折叠、引用）；
- 右侧行动卡（主行动 + 次行动 + 关键信息）；
- 文末「相关推荐 / 相关法条 / 相关需求」；
- 评论/回答用 Drawer 或独立区块，不打断阅读；
- 移动端行动卡吸底。

### 3.4 卡片动作收敛

**规则：卡片上最多 3 个可点动作。**

| 内容类型 | 主行动 | 次行动 | 更多菜单 |
|---|---|---|---|
| 政策 | 测资格 / 看详情 | 收藏 | 分享、举报、AI 提炼 |
| 论坛 | 阅读 / 回答 | 赞同 | 收藏、分享、举报、删除 |
| 产品 | 查看详情 | 收藏 | 分享、举报 |
| 需求 | 查看 / 竞标 | 收藏 | 分享、举报 |
| 文书 | 开始填写 | 预览 | 收藏、分享、举报 |
| 特权 | 立即领取 | 查看条件 | 收藏、举报 |

- 点踩、评分只在详情出现；
- 「举报」不要放在卡片一级动作；
- 所有 icon-only 按钮必须有 `aria-label` 与 tooltip；
- 互动失败要有回滚与错误提示，不要假成功。

### 3.5 异步状态与乐观更新

- 用骨架屏替代「加载中」横幅；
- 投票/收藏/已读先本地更新，失败回滚；
- Toast 带「撤销」动作（`vue-sonner` 模式）；
- 列表请求加取消/竞态保护；
- 空态要区分：无数据 / 无搜索结果 / 无权限 / 加载失败。

### 3.6 向导式表单

- 一问一屏或一屏 1–3 个强相关字段；
- 顶部进度 + 「预计还需 X 步」；
- 字段级 help/example/pitfalls 收进可展开说明；
- 自动保存草稿，离开可恢复；
- 「检查答案」页按最终文书格式预览；
- 提交失败顶部 Error summary，点击定位字段；
- 成功后给「下一步」而不是只弹 toast。

### 3.7 命令面板与通知中心

- `⌘K / Ctrl+K` 打开全局搜索：政策、帖子、作品、需求、文书、功能入口；
- 分组结果 + 键盘上下 + Enter 跳转；
- 最近访问 / 常用功能；
- 通知中心与命令面板共用一套「跳转目标」注册表；
- 通知跳转落到具体详情，而不是只切 tab。

---

## 4. 管理端专项

### 4.1 后端编排（ConsoleView / GraphEditor）

| 现状 | 目标 | 参照 |
|---|---|---|
| 点击算子加入画布 | 拖拽入画布 + 搜索 + 分组 | n8n / Dify |
| 点击两节点连线 | 端口拖拽连线 + 合法性校验 | Vue Flow |
| 无缩放/平移 | pan/zoom/minimap/fit view | Vue Flow |
| 无撤销 | undo/redo + 草稿/发布 | n8n |
| 无试跑面板 | 底部抽屉：入参 → 逐节点 trace → 输出 | Dify |
| 无版本对比 | 版本列表 + diff + 回滚 | n8n |

### 4.2 前端布局编排（FrontendOrchView）

| 现状 | 目标 | 参照 |
|---|---|---|
| 点击添加组件 | 从组件库拖入画布 | grid-layout-plus |
| 数字输入列宽 | 拖拽/缩放 + 吸附 | grid-layout-plus |
| 无预览 | 桌面/平板/手机三档预览 | Puck |
| 无组件树 | 左侧树 + 选中联动 | Puck / Craft.js |
| 无撤销 | undo/redo | Puck |
| 无发布 diff | 保存前显示变更摘要 | n8n |

### 4.3 运营大盘（OpsView）

- 时间范围：今日 / 7 日 / 30 日 / 自定义；
- 对比：环比 / 同比；
- 维度下钻：内容域 → 具体内容 → 互动明细；
- 空数据要诚实显示「暂无埋点」，不要假实时；
- 图表组件可用 ECharts 或 Unovis（Vue 支持），不必引入 React 专用库。

---

## 5. Vue 3 技术选型

| 需求 | 推荐 | 说明 |
|---|---|---|
| 路由 | `vue-router` | 已在 `package.json`，直接启用 |
| URL 状态 | `vueuse` 的 `useRouteQuery` / `useDebounceFn` / `useIntersectionObserver` | 少写重复逻辑 |
| 无障碍组件 | `reka-ui` + `shadcn-vue` | Dialog/Drawer/Popover/Tabs/Select/Tooltip |
| 表单 | 自研 step 壳 + `formkit`（或 `surveyjs`） | SOP 字段已有 schema，先自研；复杂动态表单再上引擎 |
| 拖拽排序 | `vue-draggable-plus` | SOP 流程节点排序、后台列表排序 |
| 栅格编排 | `grid-layout-plus` | 前端布局编排 |
| 流程图 | `@vue-flow/core` | 后端编排画布 |
| Toast | `vue-sonner` | 堆叠、撤销、promise 状态 |
| Drawer | `vaul-vue` | 移动端筛选/评论/详情 |
| 命令面板 | `vue-command-palette` | ⌘K 全局搜索 |
| 图表 | ECharts / Unovis | 运营大盘 |
| 富文本 | 现有 `RichEditor` 可保留 | 先补预览/粘贴图片/快捷键，不急着换 |

**不推荐**：为了「高级感」引入 React-only 的 Aceternity/MagicUI 组件；当前栈是 Vue，移植成本高于收益。需要动效时优先 CSS + `motion-v`（如确有必要）。

---

## 6. 改造路线（按投入产出）

### P0：路由与列表骨架（3–5 天）

1. 新建 `src/router/index.js`，把 11 个视图挂到路由；
2. `App.vue` 用 `<RouterView />` 替换 `v-if` 链；
3. 列表筛选/排序/搜索写入 query，详情用 path param；
4. 非授权路由重定向 + toast，修掉 `#backend-orch` 空白页；
5. 抽 `ListPageLayout`、`DetailPageLayout`、`FilterBar`、`AsyncState` 四个壳组件。

**验收**：任意详情可刷新、可分享、可浏览器返回；筛选刷新不丢。

### P1：卡片与详情重做（1 周）

1. 拆 `ContentInteractionBar` 为 `CardActions` + `DetailActions`；
2. 按内容类型定义动作表（见 3.4）；
3. 先改政策与论坛两个高频模块；
4. 政策详情加「资格自测」入口与结果卡；
5. 论坛详情改成「问题 + 回答 + 回答编辑器」；
6. 统一骨架屏、空态、错误态、Toast 撤销。

**验收**：卡片首屏最多 3 个动作；详情页有明确主行动；互动失败不假成功。

### P2：SOP 向导化（1 周）

1. 文书卡主行动改「开始填写」，显示预计问题数/时间；
2. 按 `required_fields` 生成 step（1–3 字段/步）；
3. 加进度、自动保存、继续上次填写；
4. 加「检查答案」与最终文书预览；
5. 多文书流程改成 Task list；
6. AI 代写改成右侧可审阅面板（引用 + 采纳）。

**验收**：新用户能在 3 分钟内完成一份文书；中断后可恢复；提交前能复核。

### P3：管理端与全局能力（1 周）

1. Vue Flow 替换 `GraphEditor`；
2. 试跑抽屉 + 逐节点 trace；
3. `grid-layout-plus` 重做 `FrontendOrchView`；
4. OpsView 时间范围/下钻；
5. 命令面板 + 通知中心 tab/乐观已读；
6. 统一 Drawer/Dialog 到 reka-ui。

**验收**：编排可拖拽/缩放/撤销/试跑；⌘K 能跳转全站核心内容。

---

## 7. 验收标准（可量化）

- 任意内容详情：刷新不丢、分享可打开、浏览器返回回到原列表位置；
- 任意列表：筛选/排序/关键词刷新后保留；
- 卡片一级动作 ≤ 3 个；
- 发布/申报：可中断续填，提交前有检查答案，字段错误可一键定位；
- 互动：失败有明确提示与回滚，不出现「假成功」；
- 键盘：Tab 可达、Esc 关闭弹层、焦点不逃逸；
- 移动端：筛选/详情/行动卡可用，不出现横向溢出；
- Lighthouse Accessibility ≥ 90（关键页面）。

---

## 8. 参考仓库清单

| 仓库 | Star | 语言 | 用途 |
|---|---:|---|---|
| [apache/answer](https://github.com/apache/answer) | 15.7k | Go/React | Q&A 社区信息架构 |
| [discourse/discourse](https://github.com/discourse/discourse) | 48k | Ruby/Ember | 论坛机制、审核、草稿、快捷键 |
| [forem/forem](https://github.com/forem/forem) | 22.8k | Ruby | 长文社区与反应栏 |
| [PolicyEngine/policyengine-app](https://github.com/PolicyEngine/policyengine-app) | 68 | Python/React | 政策计算器交互 |
| [alphagov/govuk-design-system](https://github.com/alphagov/govuk-design-system) | 683 | Nunjucks | 政务服务模式（Start/Task list/Check answers） |
| [uswds/uswds](https://github.com/uswds/uswds) | 7.2k | JS | 政府站点可访问性 |
| [jhpyle/docassemble](https://github.com/jhpyle/docassemble) | 992 | Python/JS | 引导访谈 + 文档组装 |
| [surveyjs/survey-library](https://github.com/surveyjs/survey-library) | 4.9k | TypeScript | JSON 驱动多步表单 |
| [formbricks/formbricks](https://github.com/formbricks/formbricks) | 13.1k | TypeScript | 表单体验与预览 |
| [shadcn-ui/taxonomy](https://github.com/shadcn-ui/taxonomy) | 19.3k | TypeScript | 列表/分类/搜索/详情布局 |
| [medusajs/medusa](https://github.com/medusajs/medusa) | 37k | TypeScript | 商品/规格/交付 |
| [calcom/cal.com](https://github.com/calcom/cal.com) | 49.4k | TypeScript | 预约/时区/可用性 |
| [antiwork/gumroad](https://github.com/antiwork/gumroad) | 10k | Ruby/React | 领取/结算/收据单路径 |
| [outline/outline](https://github.com/outline/outline) | 41k | TypeScript | 知识库阅读器 |
| [docmost/docmost](https://github.com/docmost/docmost) | 22.1k | TypeScript | 文档树/版本/权限 |
| [n8n-io/n8n](https://github.com/n8n-io/n8n) | 208k | TypeScript | 工作流编辑器 |
| [langgenius/dify](https://github.com/langgenius/dify) | 159k | TypeScript/Python | 工作流 + 调试面板 |
| [bcakmakoglu/vue-flow](https://github.com/bcakmakoglu/vue-flow) | 6.9k | Vue | Vue 3 流程图 |
| [qmhc/grid-layout-plus](https://github.com/qmhc/grid-layout-plus) | 621 | Vue | Vue 3 拖拽栅格 |
| [Alfred-Skyblue/vue-draggable-plus](https://github.com/Alfred-Skyblue/vue-draggable-plus) | 4k | Vue | 拖拽排序 |
| [measuredco/puck](https://github.com/measuredco/puck) | 13.5k | React | 可视化编辑器交互参照 |
| [prevwong/craft.js](https://github.com/prevwong/craft.js) | 8.7k | React | 页面编辑器交互参照 |
| [plausible/analytics](https://github.com/plausible/analytics) | 29.7k | Elixir | 运营大盘 |
| [umami-software/umami](https://github.com/umami-software/umami) | 39.7k | TypeScript | 运营大盘 |
| [novuhq/novu](https://github.com/novuhq/novu) | 40.2k | TypeScript | 通知 inbox |
| [xiaoluoboding/vue-command-palette](https://github.com/xiaoluoboding/vue-command-palette) | 590 | Vue | ⌘K 命令面板 |
| [pacocoursey/cmdk](https://github.com/pacocoursey/cmdk) | 13k | React | 命令面板交互参照 |
| [unovue/reka-ui](https://github.com/unovue/reka-ui) | 6.9k | Vue | 无障碍组件原语 |
| [unovue/shadcn-vue](https://github.com/unovue/shadcn-vue) | 10.7k | Vue | 组件样式与组合 |
| [vueuse/vueuse](https://github.com/vueuse/vueuse) | 22.4k | Vue | 组合式工具 |
| [formkit/formkit](https://github.com/formkit/formkit) | 4.8k | Vue | 表单校验 |
| [xiaoluoboding/vue-sonner](https://github.com/xiaoluoboding/vue-sonner) | 1.5k | Vue | Toast |
| [unovue/vaul-vue](https://github.com/unovue/vaul-vue) | 497 | Vue | Drawer |
| [vercel/ai](https://github.com/vercel/ai) | 27.5k | TypeScript | AI 流式/工具调用交互 |
| [vuepont/ai-elements-vue](https://github.com/vuepont/ai-elements-vue) | 1.2k | Vue | AI 消息/引用组件 |

---

## 9. 不建议照搬

1. **不要为了「高级」再加一层动效**：当前问题是信息架构，不是缺 3D/粒子/滚动动画。
2. **不要把 React-only 组件硬移植到 Vue**：Aceternity/MagicUI 的视觉可以看，代码不建议搬。
3. **不要继续用无限滚动 + 无 URL 的瀑布流**：内容型平台需要可分享、可返回、可定位。
4. **不要把举报/评分/点踩放在卡片一级动作**：它们是低频负向操作，应该收进详情「更多」。
5. **不要让 AI 直接产出「一段不可审阅的文本」**：政策/文书场景需要引用、逐段采纳、可回滚。
6. **不要用假成功/假实时掩盖失败**：互动、刷新、测算失败都要诚实反馈。

---

## 10. 一句话总结

> 先把「每个模块该有的动作」和「每条内容的详情路径」设计清楚，再谈玻璃质感和动效。  
> 交互的下一步不是加按钮，而是**减按钮、加路径、加反馈**。
