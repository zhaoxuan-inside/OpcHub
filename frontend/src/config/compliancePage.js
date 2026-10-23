/**
 * 合规指南 展示配置（配置与代码、数据分离）
 *
 * - 代码：frontend/src/views/ComplianceView.vue（组件逻辑与样式）
 * - 配置：本文件（分类 tab / 图标映射 / 徽章配色 / 排序 / 侧栏文案等可调参数）
 * - 数据：backend/data/seeds/compliance.json 及运行时 PostgreSQL 合规库
 *
 * 分类 key 与后端网关场景 compliance.laws / compliance.cases 对应；
 * 数据字段以后端 domain 模型为准。
 * icon 为 OpcIcon 图标名（单色重绘图标，不使用 Emoji）。
 */

/** 合规知识库分类 tab（法条 / 案例 / 热门打榜） */
export const COMPLIANCE_CATEGORIES = [
  { key: 'ALL',    label: '全部',   icon: 'shield', sort: 0 },
  { key: 'LAW',    label: '法条',   icon: 'scroll', sort: 1 },
  { key: 'CASE',   label: '案例',   icon: 'case',   sort: 2 },
  { key: 'HOT',    label: '热门',   icon: 'flame',  sort: 3 },
];

/** 法条图标映射（icon_name -> OpcIcon 图标名，展示层配置） */
export const COMPLIANCE_LAW_ICONS = {
  shield: 'shield',
  'credit-card': 'card',
  'file-text': 'file',
  code: 'code',
  globe: 'globe',
  'alert-triangle': 'alert',
};

/** 法条效力级别配色（收敛为灰阶，级别差异靠文字表达，不再用彩色） */
export const COMPLIANCE_LEVEL_COLORS = {
  法律: '#5B6472',
  行政法规: '#5B6472',
  部门规章: '#5B6472',
  地方性法规: '#5B6472',
};

/** 法条编号前缀配色（法条 code -> 展示色，收敛为统一灰阶） */
export const COMPLIANCE_LAW_COLORS = {
  'LAW-01': '#5B6472',
  'LAW-02': '#5B6472',
  'LAW-03': '#5B6472',
  'LAW-04': '#5B6472',
  'LAW-05': '#5B6472',
  'LAW-06': '#5B6472',
};

/** 排序切换项（热门打榜默认） */
export const COMPLIANCE_SORT_OPTIONS = [
  { key: 'hot',    label: '最热打榜', icon: 'flame' },
  { key: 'new',    label: '最新发布', icon: 'bolt' },
  { key: 'level',  label: '效力优先', icon: 'landmark' },
];

/** 今日热门打榜榜单长度（右侧侧栏 Top N） */
export const COMPLIANCE_HOT_RANK_LIMIT = 5;

/** 右侧侧栏「合规中心」快捷入口（发布法条/案例） */
export const COMPLIANCE_CENTER_ENTRY = {
  title: '合规指南中心',
  desc: '法条 · 案例 · 热门打榜',
  publishLabel: '发布法条 / 案例',
};

/** 右侧侧栏「免责声明」文案 */
export const COMPLIANCE_DISCLAIMER = {
  title: '免责声明',
  desc: '本页法条与案例内容仅供学习参考，不构成法律意见。具体合规义务请以国家现行法律法规及主管机关正式文件为准。',
  version: 'OpcHub 合规中心 v2.1',
};
