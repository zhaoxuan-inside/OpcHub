# OpcHub 前端交互重构交付记录（2026-10-27）

> 依据：`hs_dev_docs/_02_product_design/frontend_interaction_benchmarks_20261026.md`
> 范围：路由骨架、列表/详情交互、卡片动作收敛、政策资格向导、SOP 引导填写、管理端编排、全局命令面板
> 设计约束：`/DESIGN.md`

---

## 1. 重构结果一页纸

| 能力 | 重构前 | 重构后 |
|---|---|---|
| 页面导航 | `App.vue` 内 11 个 `v-if` + hash 切换 | `vue-router` + HTML5 history，真实 URL |
| 详情 | 页内 `selectedX` 替换，刷新丢失 | `/policies/:id`、`/forum/:id`、`/products/:id` 等深链 |
| 列表筛选 | 组件内 `ref`，刷新回默认 | `?category=&sort=&q=` 写入 URL，可分享/返回 |
| 卡片动作 | 6–8 个同权图标 | 3 个可见动作 + 「更多」菜单 |
| 政策资格 | 一次 API + toast | 30 秒三步向导，给符合度、税额、匹配政策 |
| SOP 文书 | 所有字段一次平铺 | 分组步骤 + 进度 + 检查答案 + 自动保存草稿 |
| 管理端编排 | 点击添加 + 手写 SVG | Vue Flow：拖拽/缩放/端口连线/小地图/撤销/重做 |
| 前端布局 | 数字输入列宽 | grid-layout-plus：拖拽/缩放/三档预览/撤销 |
| 全局搜索 | 无 | ⌘K / Ctrl+K 命令面板，聚合全站内容 |
| 旧链接 | `#forum?post_id=` | 启动时自动迁移到 `/forum/:id` |

---

## 2. 新增文件

| 文件 | 作用 |
|---|---|
| `frontend/src/router/index.js` | 路由表、鉴权/角色守卫、旧路径重定向、滚动行为 |
| `frontend/src/stores/auth.js` | 全局会话/角色状态、localStorage 水合、`ensureSession` |
| `frontend/src/components/CommandPalette.vue` | ⌘K 全局搜索与快捷跳转 |
| `frontend/src/components/policy/PolicyEligibilityWizard.vue` | 政策资格自测向导 |
| `frontend/src/main.js` | 安装路由 + 旧 hash 链接迁移 |
| `frontend/server.py` | SPA history fallback（刷新 `/policies/:id` 不 404） |

## 3. 路由表

```text
/                         首页（公开）
/forum/:id?               头脑风暴列表 / 帖子详情
/products/:id?            产品橱窗列表 / 作品详情
/policies/:id?            政策中心列表 / 政策详情
/demands/:id?             需求集市列表 / 需求详情
/sop                      流程文书（?view=guide|mydocs|flows）
/sop/docs/:id             标准文书详情/填写
/sop/flows/:id            平台流程详情
/sop/my-docs/:id          我的文书详情
/sop/my-flows/:id         我的流程详情
/sop/flow-builder         流程编排
/perks/:id?               生态特权列表 / 详情
/compliance/:id?          合规指南列表 / 详情
/membership               会员中心
/profile                  创客档案
/change-password          修改密码
/admin/orchestration      后端编排（ADMIN）
/admin/layout             前端布局（ADMIN）
/admin/ops                运营大盘（ADMIN）
/admin/moderation         内容治理（ADMIN）
```

旧路径（`/policy`、`/product`、`/backend-orch` 等）与旧 hash（`#forum?post_id=xxx`）自动迁移。

## 4. 关键交互改动

### 4.1 卡片动作收敛

`ContentInteractionBar.vue` 新增折叠模式：

- `variant="band"` 或 `compact` 卡片：只显示点赞 / 评论 / 收藏 / 更多；
- 详情 `show-labels`：保持完整带文字动作；
- 「更多」菜单收纳：喜欢、点踩、举报、评分摘要；
- 卡片一级动作从 6–8 个降到 3 个 + 1 个更多。

### 4.2 政策中心

- 卡片点击 → `/policies/:id`，刷新/分享/返回可用；
- 搜索、分类、排序写入 URL；
- 「匹配资格」→ 三步向导：主体/地区/营收 → 业务方向 → 结果；
- 结果包含：是否符合、适用征收率、预计税收优惠、匹配政策、法规依据、下一步建议；
- 发布页由 `?compose=1` 控制，刷新可恢复。

### 4.3 头脑风暴

- 列表/详情/发帖三种模式由路由驱动；
- 帖子详情 `/forum/:id`，直接打开可加载详情；
- 分类、排序、密度、搜索写入 URL；
- 旧 `#forum?post_id=` 链接自动迁移。

### 4.4 SOP

- 标准文书详情 `/sop/docs/:id`，流程详情 `/sop/flows/:id`；
- 文书填写改成「向导」：
  - 按 `section` 或每 3 个字段分组；
  - 进度条 + 步骤点；
  - 每一步只显示当前字段；
  - 最后「检查答案」逐项复核，可点「修改」跳回；
  - `localStorage` 自动保存草稿，重新打开可恢复；
- 保存成功后清理本地草稿。

### 4.5 管理端

- `ConsoleView` 三个面板改为按需挂载（Vue Flow 需要可测量视口）；
- `GraphEditor.vue` 重写为 Vue Flow：
  - 拖拽节点、端口连线、pan/zoom、小地图、框选、Delete 删除；
  - 撤销/重做（保留 50 步）；
  - 环路/重边/自连校验；
  - 入口/出口设置；
  - 节点设置与连线列表仍保留在右侧 Inspector；
- `FrontendOrchView.vue` 重写为 grid-layout-plus：
  - 组件库拖入/点击加入；
  - 拖拽/缩放栅格；
  - 桌面/平板/手机三档预览；
  - 撤销/重做；
  - 保存时按视觉顺序持久化组件顺序与 span。

### 4.6 全局壳层

- `CommandPalette`：⌘K / Ctrl+K，聚合政策、帖子、作品、需求、文书、流程、特权 + 功能入口；
- 顶栏新增搜索入口；
- 通知消息箱保留全部/未读筛选、全部已读、单条已读/删除；
- 旧 `ContentInteractionBar` 的评论抽屉继续复用。

---

## 5. 验证记录

### 构建

```bash
cd frontend
node node_modules/vite/bin/vite.js build
# ✓ built，路由级 code splitting 生效
```

### 浏览器实测

| 场景 | 结果 |
|---|---|
| `/policies` → 点击卡片 → URL `/policies/:id` | PASS |
| 直接刷新 `/policies/:id` | PASS（详情恢复） |
| 浏览器返回列表 | PASS |
| 筛选分类/排序 → URL 变化 → 刷新保留 | PASS |
| 政策「匹配资格」三步向导 → 结果卡 | PASS |
| `/forum` → 详情 → 刷新 | PASS |
| `/sop` → 文书 → URL `/sop/docs/:id` → 刷新 | PASS |
| `/sop` 返回列表 | PASS |
| 非管理员访问 `/admin/...` | PASS（回首页，不再空白） |
| 未登录访问 `/policies` | PASS（回首页并打开登录，带 `redirect`） |
| ⌘K 搜索「政策」 | PASS（分组结果 + 键盘选择） |
| 前端布局：添加组件 / 撤销 / 三档预览 | PASS |
| 后端编排：创建临时场景 → 锁定 → 添加节点 / 撤销 | PASS（测试后已删除临时场景） |

### 后端测试

```bash
python3 -m pytest backend/tests -q
# 478 passed, 5 skipped, 1 failed
```

唯一失败为既有基线：`test_container_packaging_and_health.py::test_docker_compose_configuration`
期望 `docker-compose.yml` 中存在旧服务名 `opchub-server`，当前部署文件已改为
`postgres / redis / backend / frontend` 四服务。该失败与本次前端重构无关。

---

## 6. 已知限制

1. **SOP 种子数据**：当前 3 份标准文书的 `required_fields` 为 0，因此向导在演示数据上不会展示步骤；有字段的文书会自动启用向导。
2. **管理端图编辑器**：只有 `source = managed` 的场景会挂载 Vue Flow；系统预置的 `runtime` 场景仍是只读视图，这是既有产品语义。
3. **会员/个人中心**：保留原有视觉与逻辑，只接入路由；后续可继续做会员权益页的交互收敛。
4. **Docker compose 测试**：旧测试断言未更新，建议后续单独清理。

---

## 7. 视觉层 v2（2026-10-27 追加）

上一轮主要改交互骨架，视觉层保留过多；本轮补了一轮可见的视觉重构：

- 暖纸色画布 + 墨色文字 + 更克制的蓝色强调，降低糖果色弥散；
- 卡片统一为「纸张」：白底、细线、18px 圆角、无夸张浮起/光晕；
- 顶栏改为一体式工作台条：选中 tab 为墨色胶囊，命令搜索收进右侧；
- 首页 Hero 改为非对称编辑式布局：左侧主张与数据，右侧 OPC 能力控制台；
- Bento 区增加 01–04 编号与左对齐 section 语法；
- 列表筛选：分类选中为墨色胶囊，排序改为下划线式；
- 首页各 section 统一左对齐标题与筛选样式；
- 修复窄视口下 fixed-feed 布局把政策/论坛侧栏压住内容流的问题。

### 部署提醒

本地 `localhost:3000` 是 Vite 源站；Docker `opchub-frontend`（映射 13000）之前跑的是 2 天前镜像，因此会看到旧 UI。已执行：

```bash
docker build -t opchub-frontend:latest -f frontend/Dockerfile .
FRONTEND_PORT=13000 docker compose up -d --no-deps frontend
```

如果部署到其他服务器，需要重新构建并导出/推送前端镜像，单纯重启旧容器不会更新 UI。

---

## 8. 视觉层 v3：工作区编辑式重构

在 v2 色板基础上，进一步重排页面结构，而不是只换颜色：

- 新增 `WorkspaceHeader.vue`，统一 7 个工作区的页头：
  - 政策雷达 / 头脑风暴 / 产品橱窗 / 需求集市 / 生态特权 / 合规指南 / 流程文书；
  - 每个页头包含 mono eyebrow、标题、说明与 3 个实时指标。
- 首页：
  - 展廊从三列卡片改为「行式索引」：编号 + 分类/指标 + 标题 + 摘要 + 作者 + 行动；
  - 演进路径从卡片网格改为 01–04 时间线；
  - 底部 CTA 从玻璃卡改为墨色块，形成整页收束。
- 全站内容面：
  - 详情页改为阅读纸张：顶部墨线、灰底面包屑、编号化 section 标题；
  - 发布表单 section 自动编号（01 / 02 / …）；
  - 空态改为虚线纸面 + 大标题排版；
  - 管理端表格改为 mono 表头、细线行、hover 高亮。
- 窄屏：
  - 释放 `fixed-screen-feed` 固定滚动，页面正常纵向滚动，侧栏不再覆盖内容流。
- Docker：
  - 重新构建 `opchub-frontend` 镜像并重启 13000 容器；
  - 当前镜像内 `dist` 与本地最新构建一致。
