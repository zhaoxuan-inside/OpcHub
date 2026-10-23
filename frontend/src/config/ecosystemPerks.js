/**
 * 生态特权 优惠公告板 —— 展示配置（配置与代码、数据分离）
 *
 * - 代码：frontend/src/views/PerksView.vue（组件逻辑与样式）
 * - 配置：本文件（分类标签 / 图标 / 配色 / 排序 / 阈值等可调参数）
 * - 数据：backend/data/seeds/perks.json 及运行时公告库
 *
 * 分类 key 必须与后端 backend/config/application.yaml `perks.categories` 保持一致；
 * badgeClass 对应 PerksView.vue 内的 scoped 样式类（样式属于代码层）；
 * icon 为 OpcIcon 图标名（单色重绘图标，不使用 Emoji）。
 */

export const PERK_CATEGORIES = [
  { key: 'TOKEN',   label: 'Token 优惠',   icon: 'coin',    badgeClass: 'cat-token',   sort: 1 },
  { key: 'SERVER',  label: '服务器优惠',   icon: 'monitor', badgeClass: 'cat-server',  sort: 2 },
  { key: 'SAAS',    label: 'SaaS 服务',    icon: 'modules', badgeClass: 'cat-saas',    sort: 3 },
  { key: 'AI',      label: 'AI 与算力',    icon: 'spark',   badgeClass: 'cat-ai',      sort: 4 },
  { key: 'FINANCE', label: '结算与支付',   icon: 'card',    badgeClass: 'cat-finance', sort: 5 },
  { key: 'INFRA',   label: '基础设施',     icon: 'wrench',  badgeClass: 'cat-infra',   sort: 6 },
  { key: 'OTHER',   label: '其他优惠',     icon: 'gift',    badgeClass: 'cat-other',   sort: 7 },
];

/** 置顶热荐的优先级阈值（priority >= 该值显示「热荐」） */
export const PERK_FEATURED_PRIORITY = 90;

/** 分类展示顺序（tab / 侧栏快捷筛选 / 发布表单下拉共用） */
export const PERK_CATEGORY_ORDER = [...PERK_CATEGORIES].sort((a, b) => a.sort - b.sort);

/** 排序切换项 */
export const PERK_SORT_OPTIONS = [
  { key: 'relevance', label: '综合推荐', icon: 'spark' },
  { key: 'value', label: '优惠最高', icon: 'coin' },
  { key: 'ending', label: '即将截止', icon: 'timer' },
  { key: 'latest', label: '最新发布', icon: 'bolt' },
];

/** 发布状态（与后端 application.yaml `perks.statuses` 保持一致） */
export const PERK_STATUSES = ['PUBLISHED', 'OFFLINE'];

/** 提报默认参数（与后端 application.yaml `perks.default_priority / default_quota` 保持一致） */
export const PERK_PUBLISH_DEFAULT_PRIORITY = 60;
export const PERK_PUBLISH_DEFAULT_QUOTA = 100;
