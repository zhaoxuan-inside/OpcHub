/**
 * 内置图标资产 —— 平台重绘线性图标库（OpcIcon）中可用于产品/公告展示的子集。
 *
 * 约束：平台素材不支持用户上传或外部链接，图标选择统一走 IconPicker，
 * 值以 `icon:<name>` 形式存入既有 icon_url 字段（空串/None 表示使用首字占位）。
 */

export const BUILTIN_ICON_NAMES = [
  // 产品语义
  'rocket', 'bolt', 'spark', 'bulb', 'gem', 'star', 'target', 'compass',
  // 技术语义
  'code', 'database', 'modules', 'monitor', 'robot', 'wrench', 'shield',
  // 商业语义
  'coin', 'cash', 'card', 'chart-up', 'briefcase', 'globe', 'users',
  // 创作语义
  'palette', 'pen', 'megaphone', 'book', 'flame', 'box', 'file', 'clipboard',
];

export const ICON_LABELS = {
  rocket: '发布 / 增长', bolt: '性能 / 效率', spark: '创意 / 灵感', bulb: '点子 / 方案',
  gem: '精品 / 价值', star: '推荐 / 优选', target: '定位 / 目标', compass: '导航 / 方向',
  code: '开发 / 代码', database: '数据 / 存储', modules: '模块 / 集成', monitor: '应用 / 桌面',
  robot: 'AI / 智能体', wrench: '工具 / 维护', shield: '安全 / 合规',
  coin: '收益 / 定价', cash: '资金 / 预算', card: '支付 / 账单', 'chart-up': '增长 / 数据',
  briefcase: '商务 / 企业', globe: '出海 / 全球', users: '社区 / 用户',
  palette: '设计 / 创意', pen: '写作 / 记录', megaphone: '推广 / 营销', book: '知识 / 文档',
  flame: '热度 / 趋势', box: '产品 / 交付', file: '文档 / 材料', clipboard: '清单 / 流程',
};

/**
 * 解析历史数据的图标语义：`icon:<name>` 前缀 → 图标名；其余（外链 URL、空值）
 * 一律返回 null，由调用方回退到首字占位渐变块。
 */
export function resolveProductIcon(iconUrl) {
  const v = (iconUrl || '').trim();
  if (v.startsWith('icon:')) {
    const name = v.slice(5);
    return BUILTIN_ICON_NAMES.includes(name) || name ? name : null;
  }
  return null;
}
