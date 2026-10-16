# OpcHub Project Design Charter (DESIGN.md)

> **Document Type**: Project-level Macro Product Taste & Design System Charter  
> **Aesthetic Direction**: **Anthropic Humanist & Editorial Craft** (克制、温暖、高信噪比、人本主义工匠感)  
> **Status**: APPROVED  
> **Rule of Law**: All feature PRDs and UI components MUST declare `Inherits: /DESIGN.md`. 拒绝千篇一律的冰冷 SaaS 蓝与塑料渐变。

---

## 1. Visual Philosophy & Metaphor (视觉哲学与心智隐喻)

### 1.1 具象参照物 (Concrete References)
- **Primary Inspiration**: **Anthropic (Claude.ai / Anthropic Research)** + **The Atlantic / Monocle (典雅出版物级可读性)**。
- **Core Spirit**:
  - **Warm & Organic (温暖沉静)**：象牙白与温润暖沙纸质底色，取代刺眼惨白与生硬死黑；
  - **Editorial Typography (出版物排版)**：衬线标题与精致无衬线正文相得益彰，带来深厚智力感与可信赖度；
  - **Crafted & Restrained (克制工匠)**：告别一切花哨浮夸的毛玻璃与荧光大色块，用纤细温润的 1px 分割线与优雅字距传递极致高级感；
  - **High Respect (尊重创作者精力)**：信息密度适度舒适，没有催促感与认知压迫感。

---

## 2. Color Palette & Design Tokens (Anthropic 色盘)

### 2.1 基础色系 (Warm Neutrals)
| Token | Hex | 语义与用途 |
| :--- | :--- | :--- |
| `surface-canvas` | `#FAF7F2` | 全站底层纸质感底色（Warm Ivory Sand） |
| `surface-card` | `#FFFFFF` | 卡片与容器主底色 |
| `surface-subtle` | `#F2ECE4` | 输入框、次级容器、hover 状态 |
| `border-default` | `#E5DFD5` | 优雅细边框与分割线 |
| `border-focus` | `#C86544` | 焦点高亮细边框 |
| `text-ink` | `#1A1918` | 正文主标题、关键数据（深墨色） |
| `text-body` | `#3D3B39` | 正文内容（温和暖炭黑） |
| `text-muted` | `#787570` | 辅助说明文案、时间戳 |
| `text-subtle` | `#9E9A93` | 禁用与次级占位符 |

### 2.2 标志性品牌与变现标识色 (Anthropic Accents)
| Token | Hex | 语义用途 |
| :--- | :--- | :--- |
| `anthropic-coral` | `#D97757` | **核心主色 (CTA)**：赤陶珊瑚红（Anthropic 标志色） |
| `anthropic-coral-dark`| `#C15F3C` | 主操作悬停与激活态 |
| `anthropic-clay` | `#E8D8CB` | 柔和赤陶浅底（用于徽章背景） |
| `sage-green` | `#4F7363` | 🟢 **免费基础项 / 认证已通过** |
| `sage-light` | `#EBF2EE` | 浅灰鼠尾草绿背景 |
| `terracotta-badge` | `#B85D3B` | 🟣 **创客付费 / 橱窗收录 / 打榜置顶** |
| `warm-amber` | `#B87B28` | 🟠 **厂商合作 / 专属优惠 / 返佣 Deals** |
| `amber-light` | `#FBF3E6` | 浅暖琥珀背景 |
| `slate-blue` | `#4A607A` | 🔵 **服务撮合 / 履约担保 / 外包佣金** |
| `blue-light` | `#EEF3F8` | 浅黛蓝背景 |

---

## 3. Typography & Typesetting (字体即性格)

### 3.1 字体栈 (Font Stack)
```css
/* 标题：人文主义与雅致衬线 */
font-family-display: "Newsreader", "Ibarra Real Nova", "Songti SC", "Noto Serif SC", Georgia, serif;

/* 正文与交互组件：极高清晰度无衬线 */
font-family-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;

/* 数字与代码：精工等宽 */
font-family-mono: ui-monospace, SFMono-Regular, "Menlo", "Consolas", monospace;
```

### 3.2 排版韵律
- **行高 (Line-height)**：正文保持 `1.7` 充裕行距，段落最大宽度控制在 `75ch` 以内，确保最舒服的阅读心流；
- **微圆角 (Subtle Radii)**：卡片 `6px` ~ `8px`，按钮 `5px`，拒绝大钝角药丸圆角，保留书页式的挺括棱角感。

---

## 4. Interaction & Motion (克制灵动的交互手艺)

- **微交互**：所有 Hover 采用 `120ms` 柔和渐变；
- **全状态可感知**：每一个按钮均有 Default、Hover、Active、Focus-visible 状态；
- **声效与反馈**：操作触发清晰利落的轻量 Toast 或抽屉平滑滑出，无晃眼弹跳。
