# 晨昏线外 (Beyond Terminator) Design Charter (DESIGN.md)

> **Document Type**: Project-level Macro Product Taste & Design System Charter  
> **Aesthetic Direction**: **Apple VisionOS Liquid Glass & iA Writer Minimalist Editorial** (晶莹液态玻璃折射、空间呼吸弥散、极简排版、零廉价图标、克制高信噪比)  
> **Status**: APPROVED  
> **Rule of Law**: All feature PRDs and UI components MUST declare `Inherits: /DESIGN.md`. 坚决拒绝粗糙廉价图标堆叠、生硬呆板灰底与冗余按钮。

---

## 1. Visual Philosophy & Metaphor (视觉哲学与设计心智)

### 1.1 具象参照物 (Concrete References)
- **Primary Inspiration**: **Apple VisionOS / macOS Sequoia Aero Glass (空间液态玻璃折射与高光)** + **iA Writer (纯粹、聚焦内容、精工文字节奏感)**。
- **Core Principles**:
  - **Liquid Glass & Refractive Aura (液态玻璃与折射光晕)**：通过底层柔和流动的液态弥散光球（Ambient Mesh Orbs），配合多层 `backdrop-filter: blur(24px) saturate(190%)` 与顶部微内发光高光（Specular Highlight `inset 0 1px 1px`），彻底打破呆板沉闷感，赋予界面如晶莹水面般的呼吸感与空间深度；
  - **Content-First (内容即界面)**：界面元素最大限度后退，让文字、政策、流程与核心数据本身成为视觉主角，去除一切纯装饰性的无意义组件；
  - **Zero Cheap Icons (杜绝廉价图标)**：坚决不用任何 Emoji 或五颜六色的通用图标包。除极必要的单色精密几何微线段与液态胶囊标记外，95% 的信息层级依靠**排版字阶、字重、灰度与间距**来表达；
  - **Surgical Restraint on Colors & Buttons (克制色彩与按钮收敛)**：全站以纯净液态玻璃与灰阶为主基调，全页面仅保留 1 个核心行动点（如顶栏或弹窗），其余卡片通过柔和的玻璃整卡悬停或文本微链接（如 `阅读细则 ›`）进行交互，避免到处都是按钮的视觉压迫感；
  - **Dual-Mode Harmony (黑白双态原生调校)**：白天模式如珍珠母贝与晶莹白玻璃般温润通透，深色模式如黑曜石与深空发光星云般专注深邃。

---

## 2. Color Palette & Design Tokens (Liquid Glass 双态色盘)

### 2.1 日间模式 (Light Mode - Iridescent Pearl & Liquid Glass)
| Token | Hex / Value | 语义与用途 |
| :--- | :--- | :--- |
| `bg-canvas` | `#F8F9FD` | 浅蓝灰纯净底布 |
| `glass-surface` | `rgba(255, 255, 255, 0.65)` | 液态玻璃表面（透出底层弥散流光） |
| `glass-border` | `rgba(255, 255, 255, 0.8)` | 水晶折射 1px 外边框 |
| `glass-specular` | `inset 0 1px 1px rgba(255, 255, 255, 0.95)` | 顶部高光反射条 |
| `text-primary` | `#121316` | 极高对比深墨黑 |
| `text-secondary`| `#4B4E56` | 正文与白话说明 |
| `text-tertiary` | `#7D828D` | 单色时间戳、等宽编号 |
| `accent` | `#0071E3` | 苹果经典蓝 |

### 2.2 深色模式 (Dark Mode - Cosmic Obsidian & Luminous Glass)
| Token | Hex / Value | 语义与用途 |
| :--- | :--- | :--- |
| `bg-canvas` | `#090A0F` | 深邃宇宙夜空黑 |
| `glass-surface` | `rgba(18, 20, 29, 0.6)` | 悬浮黑曜石液态玻璃面 |
| `glass-border` | `rgba(255, 255, 255, 0.14)` | 暗夜冷光发丝边框 |
| `glass-specular` | `inset 0 1px 1px rgba(255, 255, 255, 0.35)` | 顶部微光高光 |
| `text-primary` | `#F5F7FA` | 纯净浅色文字 |
| `text-secondary`| `#A6ACBA` | 柔和次级文案 |
| `text-tertiary` | `#757C8A` | 辅助编码与弱化标签 |
| `accent` | `#2997FF` | 空间发光蓝（仅用于关键链接） |

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
