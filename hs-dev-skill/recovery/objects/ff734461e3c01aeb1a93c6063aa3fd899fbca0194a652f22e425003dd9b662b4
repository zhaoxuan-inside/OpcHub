# OpcHub Project Design Charter (DESIGN.md)

> **Document Type**: Project-level Macro Product Taste & Design System Charter  
> **Status**: APPROVED  
> **Target Audience**: All Frontend/UI Agents, Engineers, and Designers  
> **Rule of Law**: All feature PRDs and UI components MUST declare `Inherits: /DESIGN.md`. Do not redefine global colors, typography, or philosophy in individual features.

---

## 1. Visual Theme & Atmosphere (视觉隐喻与调性)

### 1.1 具象参照物 (Concrete References)
- **Primary Inspiration**: **Linear (极速响应与键盘优先)** + **Vercel (极简黑白灰高对比与现代工程美学)** + **Stripe Dashboard (高信任感数据密度与严谨金融级信息呈现)**。
- **Anti-Slop 审美红线**：
  - 拒绝一切空洞无意义的大色块插画、紫粉色渐变大阴影与泛滥的弥散光；
  - 拒绝低信息密度的“巨大卡片占满全屏”；
  - 拒绝冗长繁杂的表单与弹窗轰炸。
- **Core Feeling (核心体感)**：
  - **Fast & Sharp**（干净利落）：操作即时响应，微交互克制（150ms 缓动）；
  - **High Signal-to-Noise**（高信噪比）：重要政策要点一目了然，无废话公文；
  - **Solopreneur-First**（超级个体工匠感）：兼具极客控制台的高效与商业化产品的严谨。

---

## 2. Color Palette & Semantic Roles (色彩矩阵与语义角色)

### 2.1 基础色盘 (Neutrals - 60% 基础)
| Token | Hex (Light) | Hex (Dark) | 用途说明 |
| :--- | :--- | :--- | :--- |
| `surface-bg` | `#f8fafc` (Slate-50) | `#090d16` (Deep Midnight) | 全局底色 |
| `surface-card` | `#ffffff` | `#111827` (Gray-900) | 卡片/容器背景 |
| `surface-subtle` | `#f1f5f9` (Slate-100) | `#1f2937` (Gray-800) | 输入框、次级容器、hover 状态 |
| `border-default` | `#e2e8f0` (Slate-200) | `#374151` (Gray-700) | 基础分割线与外边框 |
| `border-focus` | `#3b82f6` (Blue-500) | `#60a5fa` (Blue-400) | 聚焦与选中态高亮边框 |
| `text-primary` | `#0f172a` (Slate-900) | `#f9fafb` (Gray-50) | 正文主标题、关键数据 |
| `text-secondary` | `#475569` (Slate-600) | `#9ca3af` (Gray-400) | 说明文案、次要指标 |
| `text-muted` | `#94a3b8` (Slate-400) | `#6b7280` (Gray-500) | 占位符、辅助时间戳 |

### 2.2 强调色与变现标识语义色 (Accents - 30% 结构 + 10% 聚焦)
| Token | Hex | 语义用途 |
| :--- | :--- | :--- |
| `accent-primary` | `#2563eb` (Blue-600) | 核心主操作（CTA）、超链接、导航高亮 |
| `status-free` | `#10b981` (Emerald-500) | 🟢 **免费体验 / 审核通过 / 已领取** |
| `monetize-creator` | `#8b5cf6` (Purple-500) | 🟣 **创客付费 / 橱窗收录 / 打榜置顶** |
| `monetize-vendor` | `#f59e0b` (Amber-500) | 🟠 **厂商赞助 / 独家返佣 / 大客户 Deals** |
| `monetize-trade` | `#3b82f6` (Blue-500) | 🔵 **撮合交易 / 履约担保 / 外包佣金** |
| `status-danger` | `#ef4444` (Red-500) | 🔴 政策即将截止、操作异常、风险拦截 |

---

## 3. Typography & Information Hierarchy (字体与信息层级)

### 3.1 字体族 (Font Stack)
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", monospace-code, sans-serif;
```
- 代码与数字（金额、Token量、截止日期）优先采用等宽字体 `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` 强化对齐。

### 3.2 字体排阶 (Scale)
- **H1 (页面主标)**：`28px / 1.2` · Bold · Tracking `-0.02em`
- **H2 (区块标题)**：`20px / 1.3` · SemiBold · Tracking `-0.01em`
- **H3 (卡片标题)**：`16px / 1.4` · SemiBold
- **Body (常规正文)**：`14px / 1.6` · Regular
- **Small (说明/时间/标签)**：`12px / 1.4` · Medium

---

## 4. Spacing, Borders & Density (间距、圆角与信息密度)

- **Density Mode**: **Compact to Balanced**。单屏展示尽可能多的有效业务卡片，减少无意义留白。
- **Border Radius (圆角)**:
  - 容器/卡片: `8px` (`rounded-lg`)
  - 按钮/输入框/Badge: `6px` (`rounded-md`)
  - 浮层/弹窗: `12px` (`rounded-xl`)
- **Elevation (阴影)**:
  - 默认无重阴影，主要靠 `1px border-default` 划分层级；
  - 悬浮态（Hover）仅添加轻微高光：`box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05)`。

---

## 5. Responsive & Multi-Client Principles (薄前端跨端原则)

因为 OpcHub 采取“**重后端、薄前端**”架构，支持 Web、微信小程序、多端桌面与插件扩展：
1. **API-First 数据驱动**：所有 UI 状态（标签、变现标记、按钮状态机）均由后端 JSON 契约直接驱动，前端不硬编码业务判断；
2. **移动端/小程序优先对齐**：卡片布局采用 CSS Grid / Flexbox 弹性断点，桌面端 3 列，平板 2 列，手机 1 列，卡片内容高度自适应；
3. **极简 DOM**：杜绝深层嵌套，无复杂重型 Canvas 或大型三方库，保证秒开与低内存开销。

---

## 6. Ten-Star Experience Checklist (10 星惊喜体验准则)

1. **Aha Moment (前 30 秒惊喜)**：未登录用户进入首页，输入 2 个标签即可看到“你可领取的扶持政策与算力礼包”，不强制强阻断注册；
2. **Keyboard First (键盘无障碍)**：支持 `Cmd+K` / `Ctrl+K` 全局搜索政策、Perks 与外包需求；
3. **High Signal Cards (高信噪比卡片)**：每张政策卡片必有“100字大白话 + 申报倒计时 + 官方直达”；
4. **Transparent Badges (变现透明)**：所有商业化链接明码标出“返佣/赞助/上架”，保持真实信任感。
