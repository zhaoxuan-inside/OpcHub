# OpcHub Project Design Charter (DESIGN.md)

> **Document Type**: Project-level Macro Product Taste & Design System Charter  
> **Aesthetic Direction**: **Apple & iA Writer Minimalist Editorial** (极致克制、留白呼吸感、无廉价图标、灰阶单色、精工排版)  
> **Status**: APPROVED  
> **Rule of Law**: All feature PRDs and UI components MUST declare `Inherits: /DESIGN.md`. 坚决拒绝粗糙廉价图标堆叠、花哨彩虹色块与冗余按钮。

---

## 1. Visual Philosophy & Metaphor (视觉哲学与设计心智)

### 1.1 具象参照物 (Concrete References)
- **Primary Inspiration**: **Apple (Human Interface Guidelines / Apple.com Editorial)** + **iA Writer (纯粹、聚焦内容、精工文字节奏感)**。
- **Core Principles**:
  - **Content-First (内容即界面)**：界面元素最大限度后退，让文字、政策、流程与核心数据本身成为视觉主角，去除一切纯装饰性的无意义组件；
  - **Zero Cheap Icons (杜绝廉价图标)**：坚决不用任何 Emoji 或五颜六色的通用图标包。除极必要的单色精密几何微线段（如搜索、暗黑切换）外，95% 的信息层级依靠**排版字阶、字重、灰度与间距**来表达；
  - **Surgical Restraint on Colors & Buttons (克制色彩与按钮收敛)**：全站以纯净单色灰阶为主基调，全页面仅保留 1 个核心行动点（如顶栏或弹窗），其余卡片通过柔和的整卡悬停或文本微链接（如 `阅读细则 ›`）进行交互，避免到处都是按钮的视觉压迫感；
  - **Dual-Mode Harmony (黑白双态原生调校)**：白天模式如苹果官网般通透无瑕，深色模式如专业编辑终端般深邃专注。

---

## 2. Color Palette & Design Tokens (Apple 灰阶双态色盘)

### 2.1 日间模式 (Light Mode - Crisp & Pristine)
| Token | Hex / Value | 语义与用途 |
| :--- | :--- | :--- |
| `bg-base` | `#FFFFFF` | 纯白主画布底色 |
| `bg-subtle` | `#F5F5F7` | 苹果经典浅灰底（容器、模块底色） |
| `bg-card` | `#FFFFFF` | 卡片独立表面 |
| `border-hairline`| `rgba(0, 0, 0, 0.08)` | 1px 极细微分割线 |
| `border-strong`  | `rgba(0, 0, 0, 0.16)` | 悬停态或活动状态边界 |
| `text-primary`   | `#1D1D1F` | 苹果光学深墨黑（标题、关键数值） |
| `text-secondary` | `#6E6E73` | 正文、说明文案 |
| `text-tertiary`  | `#86868B` | 辅助标签、单色时间戳、索引编号 |
| `accent`         | `#0071E3` | 苹果官方经典深蓝（仅用于高价值链接与极少数关键 CTA） |

### 2.2 深色模式 (Dark Mode - Deep Pro Tone)
| Token | Hex / Value | 语义与用途 |
| :--- | :--- | :--- |
| `bg-base` | `#000000` | 苹果极致纯黑背景（省电、纯粹） |
| `bg-subtle` | `#121214` | 深炭微暗层（容器底色） |
| `bg-card` | `#161618` | 悬浮卡片表面 |
| `border-hairline`| `rgba(255, 255, 255, 0.08)` | 暗态微弱发丝分割线 |
| `border-strong`  | `rgba(255, 255, 255, 0.18)` | 焦点高亮细边框 |
| `text-primary`   | `#F5F5F7` | 亮浅灰纯净文字 |
| `text-secondary` | `#A1A1A6` | 次级正文与说明 |
| `text-tertiary`  | `#86868B` | 弱化辅助字 |
| `accent`         | `#2997FF` | 苹果暗态高对比蓝 |

---

## 3. Typography & Typesetting (字阶与排版手艺)

### 3.1 字体栈 (Font Stack)
```css
/* 标题与重要展示：苹果官方 SF Pro Display 级排版 */
font-family-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Helvetica Neue", sans-serif;

/* 正文与阅读：呼吸感与极高清晰度 */
font-family-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", sans-serif;

/* 数字、编码、状态标签与内参编号：iA Writer 风格等宽排版 */
font-family-mono: "SF Mono", "iA Writer Mono", "Menlo", "Consolas", monospace;
```

### 3.2 排版韵律与光学追踪
- **大标题收紧字距 (Negative Letter-spacing)**：大标题设置 `letter-spacing: -0.03em; line-height: 1.15;`，塑造瑞士国际主义与苹果发布会级的高级质感；
- **等宽编号索引 (Mono Tagging)**：条目与流程前缀使用 `SF Mono`（如 `01`、`POL-2026-081`），字体设置 `11px`，字母间距展开 `letter-spacing: 0.06em;`；
- **呼吸感留白**：模块之间保留至少 `64px` 充裕间距，正文保持 `1.6` ~ `1.7` 行高，确保极致专注的沉浸阅读体验。

---

## 4. Interaction & Motion (克制且精准的微动效)

- **微动效曲线**：采用苹果标志性的缓动贝塞尔曲线 `cubic-bezier(0.16, 1, 0.3, 1)`，过渡时间 `200ms`；
- **去繁就简的交互反馈**：卡片悬停仅做 `1px` 微升与边框微加深，不产生夸张阴影或变形；
- **轻量抽屉与弹窗**：涉及付费或重要操作时，从底部微浮起轻量毛玻璃 Modal，操作明确、无视觉干扰。
