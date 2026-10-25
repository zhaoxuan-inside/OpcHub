# 任务验收备忘：TASK-029 消息箱/评论抽屉头部重叠修复（全局 header 规则收窄）

- **任务编号**：TASK-029
- **任务标题**：消息箱弹窗内容显示重叠修复
- **分级**：`S`
- **执行人**：agent
- **完成时间**：`2026-10-25T17:45:00+08:00`
- **状态**：`VERIFIED_AND_ACCEPTED`

---

## 1. 问题与根因

**现象**：打开消息箱弹窗，标题「消息箱 / 发布内容的审核结果与平台通知」与「全部 / 未读」筛选行、空态文案互相重叠错位。

**根因**：`frontend/src/style.css` 存在裸元素选择器 `header { position: fixed; top: 12px; ... }`（本意仅为顶部导航栏定位）。`NotificationInbox.vue` 与 `ContentCommentDrawer.vue` 均为 `Teleport to="body"` 的弹层，其内部 `<header class="inbox-head">` / `<header class="ccd-header">` 同样命中该规则——弹窗头部被 `position: fixed` 钉在视口顶部并脱离文档流，与弹窗其余内容叠置。同时两个弹层容器复用 `.glass-box`，被连带 `padding: 32px / margin-bottom: 32px`，与组件内部自带的 24px 侧边距叠加造成过度内缩。

## 2. 修复内容

1. **`frontend/src/style.css`**：全局规则收窄为 `header.app-topbar { ... }`，并附注释说明为何不得使用裸元素选择器（全库仅此一处裸 `header` 引用，`grep` 复核无其他全局 `header` 规则）。
2. **`frontend/src/components/Navbar.vue`**：根元素 `<header>` 补 `app-topbar` 类，导航栏定位行为不变。
3. **`frontend/src/components/NotificationInbox.vue`**：`.inbox-head` 补 `position: relative`（弹层内 header 恒参与文档流，防未来同类全局规则回归）；`.inbox-window` 补 `padding: 0; margin: 0` 抵消 `.glass-box` 连带值。
4. **`frontend/src/components/ContentCommentDrawer.vue`**：`.ccd-header` 补 `position: relative`；`.ccd-panel` 补 `padding: 0; margin: 0`，与消息箱同构修复。
5. `CreatePageLayout.vue` 的 `.create-page-head` 自带 `position: sticky / top: 0 / z-index: 20`，本就覆盖了 global 的 fixed 定位；收窄后其意外继承的 `max-width: 1240px / margin: 0 auto` 一并消失，行为更干净，无需改动。

## 3. 验证

- `vite build` 重建 dist（构建通过，产物 hash 更新）。
- 浏览器实测（`http://127.0.0.1:3000`，注入临时会话驱动空态）：消息箱弹窗标题、副标题、筛选 pills、空态「暂无消息」全部在弹窗内正常排布，无重叠；顶部导航栏仍固定于页首，定位无回归；验证后临时会话已清除。
- 评论抽屉与消息箱为同一根因、同一修复模式（纯属性增补，不改任何既有规则），未单独走 UI E2E。

## 4. 遗留观察（不在本任务范围）

- `http://127.0.0.1:8000/console` 由后端 FastAPI 直接返回 dist HTML，但后端无 `/assets` 静态路由，资产 404 导致该入口白屏；实际工作台入口为 `python3 -m frontend.server`（端口 3000，/api 代理至 8000）。 landing 页「进入工作台」链接指向 8000/console，属既有缺陷，待单列任务处理。
