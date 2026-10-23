<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :class="['opc-icon', `opc-icon-${name}`]"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-for="(s, i) in shapes" :key="i">
      <path v-if="s.t === 'path'" v-bind="attrsFor(s)" />
      <circle v-else-if="s.t === 'circle'" v-bind="attrsFor(s)" />
      <rect v-else-if="s.t === 'rect'" v-bind="attrsFor(s)" />
      <line v-else-if="s.t === 'line'" v-bind="attrsFor(s)" />
      <ellipse v-else-if="s.t === 'ellipse'" v-bind="attrsFor(s)" />
      <polygon v-else-if="s.t === 'polygon'" v-bind="attrsFor(s)" />
    </template>
  </svg>
</template>

<script setup>
import { computed } from 'vue';

/**
 * OpcIcon —— OpcHub 专属重绘线性图标库
 *
 * 设计约束（DESIGN.md）：
 * - 单色：只使用 currentColor，禁止任何硬编码色值；
 * - 线性：1.7 基准描边，圆形端点，24×24 网格；
 * - 液态玻璃：需要在体块内做浅填充时使用 fill + fo（fill-opacity），
 *   不使用渐变、投影或彩色。
 *
 * 用法：<OpcIcon name="flame" :size="14" />
 * 组件在 main.js 中全局注册，模板内无需 import。
 */

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 16 },
  strokeWidth: { type: [Number, String], default: 1.7 },
});

// ---- 形状构造器（仅用于让图标定义保持紧凑可读） ----
const P = (d, o = {}) => ({ t: 'path', d, ...o });
const C = (cx, cy, r, o = {}) => ({ t: 'circle', cx, cy, r, ...o });
const R = (x, y, w, h, rx, o = {}) => ({ t: 'rect', x, y, w, h, rx, ...o });
const E = (cx, cy, rx, ry, o = {}) => ({ t: 'ellipse', cx, cy, rx, ry, ...o });

const ICONS = {
  // ============ 通用 / UI ============
  search: [
    C(10.5, 10.5, 6.5, { fill: true, fo: 0.1 }),
    P('M15.4 15.4 20.5 20.5', { sw: 2 }),
  ],
  flame: [
    P(
      'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5Z',
      { fill: true, fo: 0.14 }
    ),
  ],
  bolt: [
    P('M13 2.5 4.5 13.5h6L10.5 21.5 20 10.5h-6.5L13 2.5Z', { fill: true, fo: 0.14 }),
  ],
  spark: [
    P(
      'M12 2.5C12 7.1 7.1 12 2.5 12 7.1 12 12 16.9 12 21.5 12 16.9 16.9 12 21.5 12 16.9 12 12 7.1 12 2.5Z',
      { fill: true, fo: 0.14 }
    ),
    C(12, 12, 1.4, { fill: true, fo: 0.9 }),
    C(19, 5, 1.1, { fill: true, fo: 0.9 }),
  ],
  bulb: [
    P('M9 18h6M10 21h4', { sw: 1.8 }),
    P(
      'M12 2.5A6.5 6.5 0 0 0 8.1 14.2c.6.5 1 1.2 1.1 2.1h5.6c.1-.9.5-1.6 1.1-2.1A6.5 6.5 0 0 0 12 2.5Z',
      { fill: true, fo: 0.1 }
    ),
    P('M9.6 12.4c.5-1 1.3-1.5 2.4-1.5s1.9.5 2.4 1.5', { sw: 1.4 }),
  ],
  target: [
    C(12, 12, 8.5, { fill: true, fo: 0.06 }),
    C(12, 12, 5),
    C(12, 12, 1.7, { fill: true, fo: 0.95 }),
  ],
  trophy: [
    P('M8 4h8v5a4 4 0 0 1-8 0V4Z', { fill: true, fo: 0.12 }),
    P('M8 5H5v2a3 3 0 0 0 3 3M16 5h3v2a3 3 0 0 1-3 3'),
    P('M12 13v5M8.5 21h7M9.5 18h5'),
  ],
  gem: [
    P('M6 3.5h12l3 5.5-9 11.5L3 9l3-5.5Z', { fill: true, fo: 0.1 }),
    P('M3 9h18M9 3.5 7.5 9 12 20.5 16.5 9 15 3.5', { sw: 1.3, op: 0.8 }),
  ],
  star: [
    P('m12 3 2.7 5.6 6.1.9-4.4 4.3 1.1 6.1-5.5-2.9-5.5 2.9 1.1-6.1L3.2 9.5l6.1-.9L12 3Z'),
  ],
  'star-filled': [
    P('m12 3 2.7 5.6 6.1.9-4.4 4.3 1.1 6.1-5.5-2.9-5.5 2.9 1.1-6.1L3.2 9.5l6.1-.9L12 3Z', {
      fill: true,
      fo: 0.9,
    }),
  ],
  check: [P('M5 12.5 9.5 17 19 6.5', { sw: 2 })],
  close: [P('M6 6 18 18M18 6 6 18', { sw: 2 })],
  alert: [
    P('M12 3.2 21.5 20H2.5L12 3.2Z', { fill: true, fo: 0.1 }),
    P('M12 9v4.6', { sw: 1.9 }),
    C(12, 17.2, 0.9, { fill: true, fo: 1 }),
  ],
  stop: [
    P('M8 3h8l5 5v8l-5 5H8l-5-5V8l5-5Z', { fill: true, fo: 0.1 }),
    P('M9 12h6', { sw: 2 }),
  ],
  info: [
    C(12, 12, 8.7, { fill: true, fo: 0.08 }),
    P('M12 11v5', { sw: 1.8 }),
    C(12, 7.8, 0.9, { fill: true, fo: 1 }),
  ],
  plus: [P('M12 5v14M5 12h14', { sw: 2 })],
  chevron: [P('M6.5 9.5 12 15l5.5-5.5', { sw: 2 })],
  'arrow-up': [P('M12 19V5M6.5 11 12 5l5.5 6', { sw: 2 })],
  'arrow-down': [P('M12 5v14M6.5 13 12 19l5.5-6', { sw: 2 })],
  'arrow-right': [P('M5 12h14M13 6l6 6-6 6', { sw: 2 })],

  // ============ 领域 / 业务语义 ============
  scroll: [
    P('M6 2.5h8l4.5 4.5v14.5H6V2.5Z', { fill: true, fo: 0.08 }),
    P('M14 2.5V7h4.5', { sw: 1.5 }),
    P('M9 11h6M9 14.5h6M9 18h3.5', { sw: 1.5 }),
    C(16, 18, 1.7, { fill: true, fo: 0.18 }),
  ],
  case: [
    P(
      'M3 7.5a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-10Z',
      { fill: true, fo: 0.1 }
    ),
    P('M12 10.5l3.2 5.6h-6.4L12 10.5Z', { sw: 1.5 }),
    P('M12 12.6v1.5', { sw: 1.5 }),
    C(12, 15.6, 0.55, { fill: true, fo: 1 }),
  ],
  scale: [
    P('M12 3.5v17M8.5 20.5h7M4.5 7.5h15'),
    P('M4.5 7.5 2 13h5L4.5 7.5Z', { fill: true, fo: 0.12, sw: 1.5 }),
    P('M19.5 7.5 17 13h5l-2.5-5.5Z', { fill: true, fo: 0.12, sw: 1.5 }),
    P('M2 13a2.5 2.5 0 0 0 5 0M17 13a2.5 2.5 0 0 0 5 0', { sw: 1.4 }),
  ],
  landmark: [
    P('M3 9.5 12 3.5l9 6H3Z', { fill: true, fo: 0.12 }),
    P('M6 10.5v7M10 10.5v7M14 10.5v7M18 10.5v7', { sw: 1.5 }),
    P('M4.5 17.5h15M3 20.5h18', { sw: 1.6 }),
  ],
  building: [
    P('M4.5 21V5.5a1 1 0 0 1 1-1H14a1 1 0 0 1 1 1V21', { fill: true, fo: 0.07 }),
    P('M15 9h3.5a1 1 0 0 1 1 1v11M3 21h18', { sw: 1.6 }),
    P('M8 8h1.5M11 8h1.5M8 11.5h1.5M11 11.5h1.5M8 15h1.5M11 15h1.5', { sw: 1.4 }),
  ],
  factory: [
    P('M3 20.5V10l5 3V10l5 3V10l5 3v7.5H3Z', { fill: true, fo: 0.1 }),
    P('M17 10V4.5h3.5V13', { sw: 1.5 }),
    P('M2.5 20.5h19', { sw: 1.7 }),
    P('M6.5 17h1.5M11 17h1.5M15.5 17h1.5', { sw: 1.4 }),
  ],
  calendar: [
    R(3.5, 5, 17, 15.5, 2, { fill: true, fo: 0.06 }),
    P('M3.5 9.5h17M8 3v4M16 3v4'),
    P('M7.5 13h.1M12 13h.1M16.5 13h.1M7.5 17h.1M12 17h.1', { sw: 2 }),
  ],
  clock: [
    C(12, 12, 8.5, { fill: true, fo: 0.05 }),
    P('M12 7v5.2l3.2 2', { sw: 1.8 }),
  ],
  pin: [
    P('M12 21.5s7-6.1 7-11A7 7 0 0 0 5 10.5c0 4.9 7 11 7 11Z', { fill: true, fo: 0.1 }),
    C(12, 10.5, 2.5),
  ],
  coin: [
    C(12, 12, 8.5, { fill: true, fo: 0.1 }),
    P('M9 8l3 4 3-4M12 12v4.5M9.5 13.6h5M9.5 15.6h5', { sw: 1.6 }),
  ],
  cash: [
    R(2.5, 6, 19, 12, 2, { fill: true, fo: 0.07 }),
    C(12, 12, 2.8),
    P('M5.5 9.5h1.5M17 14.5h1.5', { sw: 1.5 }),
  ],
  card: [
    R(2.5, 5, 19, 14, 2.5, { fill: true, fo: 0.07 }),
    P('M2.5 9.5h19', { sw: 1.8 }),
    P('M6 13.5h3M6 16.5h6', { sw: 1.5 }),
  ],
  gift: [
    P('M3.5 8.5h17v12h-17z', { fill: true, fo: 0.1 }),
    P('M2.5 5.5h19v3h-19z', { sw: 1.6 }),
    P('M12 5.5v15', { sw: 1.6 }),
    P(
      'M12 5.5C9 5.5 7.5 4 7.5 2.8S8.7 1 9.7 1.9s2.3 3.6 2.3 3.6ZM12 5.5c3 0 4.5-1.5 4.5-2.7S15.3 1 14.3 1.9 12 5.5 12 5.5Z',
      { sw: 1.5 }
    ),
  ],
  ticket: [
    P(
      'M3 8.5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v1.5a2 2 0 0 0 0 4V16a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4V8.5Z',
      { fill: true, fo: 0.08 }
    ),
    P('M14 7v10', { dash: '2 2', sw: 1.4 }),
  ],
  cap: [
    P('M2.5 9.5 12 5l9.5 4.5L12 14 2.5 9.5Z', { fill: true, fo: 0.1 }),
    P('M6.5 11.4v4.2c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5v-4.2'),
    P('M21.5 9.5v5', { sw: 1.6 }),
  ],
  monitor: [
    R(2.5, 4, 19, 12.5, 2, { fill: true, fo: 0.07 }),
    P('M9 20.5h6M12 16.5v4', { sw: 1.7 }),
    P('M6 8h6', { sw: 1.4 }),
  ],
  modules: [
    R(3.5, 3.5, 7, 7, 1.8, { fill: true, fo: 0.12 }),
    R(13.5, 3.5, 7, 7, 1.8),
    R(3.5, 13.5, 7, 7, 1.8),
    R(13.5, 13.5, 7, 7, 1.8),
  ],
  wrench: [
    P(
      'M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.3 2.3-2.4-.6-.6-2.4 2.3-2.3Z',
      { fill: true, fo: 0.1 }
    ),
  ],
  globe: [
    C(12, 12, 8.7, { fill: true, fo: 0.05 }),
    P('M3.3 12h17.4', { sw: 1.5 }),
    E(12, 12, 4, 8.7),
    P('M6 6.5c1.8 1.4 3.8 2 6 2s4.2-.6 6-2M6 17.5c1.8-1.4 3.8-2 6-2s4.2.6 6 2', {
      sw: 1.3,
      op: 0.8,
    }),
  ],
  file: [
    P('M6 2.5h8l4.5 4.5v14.5H6V2.5Z', { fill: true, fo: 0.07 }),
    P('M14 2.5V7h4.5', { sw: 1.5 }),
    P('M9 12h6M9 15.5h6', { sw: 1.5 }),
  ],
  'chart-bar': [
    P('M4 3.5v17M4 20.5h17', { sw: 1.6 }),
    P('M8 17v-5M12 17V9M16 17v-8', { sw: 2.1 }),
  ],
  'chart-up': [
    P('M4 20.5h17M4 20.5V3.5', { sw: 1.6 }),
    P('M7 15l4-4 3 2.5 5-6', { sw: 1.8 }),
    P('M16.5 7.5H19v2.5', { sw: 1.8 }),
  ],
  'chart-down': [
    P('M4 20.5h17M4 20.5V3.5', { sw: 1.6 }),
    P('M7 8l4 4 3-2.5 5 6', { sw: 1.8 }),
    P('M16.5 15.5H19V13', { sw: 1.8 }),
  ],
  database: [
    E(12, 6, 8, 3, { fill: true, fo: 0.08 }),
    P('M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6'),
    P('M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6'),
  ],
  users: [
    C(9, 8, 3.2, { fill: true, fo: 0.1 }),
    P('M3.5 20c0-3 2.5-5 5.5-5s5.5 2 5.5 5'),
    P('M16 5.5a3 3 0 0 1 0 5.9M17 15.2c2 .6 3.5 2.3 3.5 4.8', { sw: 1.6 }),
  ],
  rocket: [
    P('M12 2.5c3 1.5 5 5 5 9l-2.5 2.5h-5L7 11.5c0-4 2-7.5 5-9Z', {
      fill: true,
      fo: 0.12,
    }),
    P('M7 11.5 4 15l3 .5M17 11.5 20 15l-3 .5', { sw: 1.5 }),
    C(12, 8, 1.5),
    P('M10.5 14l1.5 6.5 1.5-6.5', { sw: 1.5 }),
  ],
  compass: [
    C(12, 12, 8.6, { fill: true, fo: 0.05 }),
    P('M15.5 8.5 13 13l-4.5 2.5L11 11l4.5-2.5Z', { fill: true, fo: 0.16 }),
    C(12, 12, 0.9, { fill: true, fo: 0.9 }),
  ],
  clipboard: [
    P(
      'M7 4.5H5.5a1 1 0 0 0-1 1V21h15V5.5a1 1 0 0 0-1-1H17',
      { fill: true, fo: 0.05 }
    ),
    R(8.5, 2.5, 7, 4, 1.2),
    P('M8 11h8M8 14.5h8M8 18h5', { sw: 1.5 }),
  ],
  book: [
    P('M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15Z', {
      fill: true,
      fo: 0.05,
    }),
    P('M8 2v20', { sw: 1.6 }),
    P('M11 7h5M11 11h5', { sw: 1.4 }),
  ],
  box: [
    P('M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5v-9Z', { fill: true, fo: 0.08 }),
    P('M3.5 7.5 12 12l8.5-4.5M12 12v9', { sw: 1.6 }),
  ],
  robot: [
    R(4, 6.5, 16, 12, 3, { fill: true, fo: 0.07 }),
    P('M12 3v3.5', { sw: 1.6 }),
    C(12, 2.4, 1.1, { fill: true, fo: 1 }),
    C(9, 12, 1.4, { fill: true, fo: 1 }),
    C(15, 12, 1.4, { fill: true, fo: 1 }),
    P('M9 15.5h6', { sw: 1.5 }),
    P('M4 11H2.5v3H4M20 11h1.5v3H20', { sw: 1.5 }),
  ],
  palette: [
    P(
      'M12 3a9 9 0 0 0 0 18c1.2 0 2-.8 2-1.8 0-.5-.2-.9-.5-1.2-.4-.4-.6-.8-.6-1.3 0-1 .8-1.7 1.8-1.7H16a5 5 0 0 0 5-5c0-3.9-4-7-9-7Z',
      { fill: true, fo: 0.07 }
    ),
    C(7.5, 11.5, 1.2, { fill: true, fo: 0.9 }),
    C(9.5, 7.5, 1.2, { fill: true, fo: 0.9 }),
    C(14, 7, 1.2, { fill: true, fo: 0.9 }),
    C(17, 10.5, 1.2, { fill: true, fo: 0.9 }),
  ],
  megaphone: [
    P('M3 10.5v3a2 2 0 0 0 2 2h2l9 5V3.5l-9 5H5a2 2 0 0 0-2 2Z', {
      fill: true,
      fo: 0.1,
    }),
    P('M7 15.5 8 21h3l-.7-4.5', { sw: 1.5 }),
    P('M18.5 8.5a5 5 0 0 1 0 7', { sw: 1.6 }),
  ],
  pen: [
    P('M4 20l1-4.5L16 4.5a2.1 2.1 0 0 1 3 3L8 18.5 4 20Z', {
      fill: true,
      fo: 0.1,
    }),
    P('M14 6.5l3 3', { sw: 1.5 }),
  ],
  timer: [
    C(12, 13, 8, { fill: true, fo: 0.05 }),
    P('M12 9v4.5l3 1.8', { sw: 1.8 }),
    P('M9.5 2h5M12 2v3', { sw: 1.7 }),
    P('M18.5 6.5l1.5-1.5', { sw: 1.6 }),
  ],
  shield: [
    P(
      'M12 2.5 20 5.8v5.7c0 5-3.4 9.3-8 10.5-4.6-1.2-8-5.5-8-10.5V5.8L12 2.5Z',
      { fill: true, fo: 0.12 }
    ),
    P('M8.5 12 11 14.5 15.5 9.5', { sw: 1.9 }),
  ],
  like: [
    P(
      'M7 10.5v10.5H4a1 1 0 0 1-1-1v-8.5a1 1 0 0 1 1-1h3Zm0 0 4.2-7.2A2 2 0 0 1 14.9 4l-.7 4.3h5.1a2 2 0 0 1 2 2.4l-1.6 8a2 2 0 0 1-2 1.6H7',
      { fill: true, fo: 0.06 }
    ),
  ],
  dislike: [
    P(
      'M7 10.5v10.5H4a1 1 0 0 1-1-1v-8.5a1 1 0 0 1 1-1h3Zm0 0 4.2 7.2A2 2 0 0 0 14.9 20l-.7-4.3h5.1a2 2 0 0 0 2-2.4l-1.6-8A2 2 0 0 0 17.8 4H7',
      { fill: true, fo: 0.06 }
    ),
  ],
  heart: [
    P(
      'M20.8 5.6a5.2 5.2 0 0 0-7.4 0L12 7l-1.4-1.4a5.2 5.2 0 1 0-7.4 7.4L12 21l8.8-7.9a5.2 5.2 0 0 0 0-7.5Z',
      { fill: true, fo: 0.08 }
    ),
  ],
  comment: [
    P(
      'M21 11.5a8.4 8.4 0 0 1-8.5 8.3 9 9 0 0 1-3.6-.8L3 21l1.9-5.4a8 8 0 0 1-1.4-4.5A8.4 8.4 0 0 1 12 2.8a8.4 8.4 0 0 1 9 8.7Z',
      { fill: true, fo: 0.07 }
    ),
  ],
  bookmark: [
    P('M6 3.5C6 2.67 6.67 2 7.5 2h9c.83 0 1.5.67 1.5 1.5V21L12 16.8 6 21V3.5Z', {
      fill: true,
      fo: 0.08,
    }),
  ],
  code: [
    P('M8.5 7 3.5 12l5 5M15.5 7l5 5-5 5M13.5 4l-3 16', { sw: 1.9 }),
  ],
  briefcase: [
    R(2.5, 7, 19, 13, 2, { fill: true, fo: 0.07 }),
    P('M8.5 7V5.5a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2V7', { sw: 1.6 }),
    P('M2.5 12.5h19', { sw: 1.5 }),
  ],
};

const shapes = computed(() => ICONS[props.name] || [C(12, 12, 8, { fill: true, fo: 0.08 })]);

function attrsFor(s) {
  const base = {
    fill: s.fill ? 'currentColor' : 'none',
    'fill-opacity': s.fill ? (s.fo ?? 0.12) : undefined,
    'stroke-width': s.sw ?? props.strokeWidth,
    'stroke-opacity': s.op ?? undefined,
    'stroke-dasharray': s.dash ?? undefined,
  };
  switch (s.t) {
    case 'path':
      return { ...base, d: s.d };
    case 'circle':
      return { ...base, cx: s.cx, cy: s.cy, r: s.r };
    case 'rect':
      return { ...base, x: s.x, y: s.y, width: s.w, height: s.h, rx: s.rx };
    case 'line':
      return { ...base, x1: s.x1, y1: s.y1, x2: s.x2, y2: s.y2 };
    case 'ellipse':
      return { ...base, cx: s.cx, cy: s.cy, rx: s.rx, ry: s.ry };
    case 'polygon':
      return { ...base, points: s.points };
    default:
      return base;
  }
}
</script>

<style scoped>
.opc-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
  overflow: visible;
}
</style>
