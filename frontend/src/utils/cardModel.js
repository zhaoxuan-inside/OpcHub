/**
 * 统一卡片视图模型 (Unified Card View Model)
 *
 * 产品橱窗 / 政策中心 / 需求集市 / 流程文书 / 生态特权 / 合规指南
 * 六类业务卡片的**数据模型统一**入口：把各 domain 的不同原始字段归一化成
 * 同一套卡片字段，前端卡片组件只消费这份统一模型，样式由全局 .opc-card 体系承载。
 *
 * 归一化后的统一卡片模型：
 * {
 *   id: string,              // 唯一标识
 *   title: string,           // 标题（product.title / policy.title / demand.title / perk.name / law.title / sop.name）
 *   summary: string,         // 摘要（tagline / summary / description）
 *   iconType: 'img'|'icon'|'initials',   // 图标类型
 *   iconUrl: string,         // iconType=img 时使用
 *   iconName: string,        // iconType=icon 时使用（OpcIcon 图标名）
 *   iconInitials: string,    // iconType=initials 时使用
 *   iconClass: string,       // 图标主题 class（分类配色，如 emblem-tax / cat-token）
 *   category: string,        // 分类 key
 *   categoryLabel: string,   // 分类显示名
 *   badges: Array<{ text: string, class?: string, style?: object }>,  // 徽章
 *   highlights: Array<{ icon: string, text: string, class?: string }>, // 快速指标 chips（icon 为 OpcIcon 图标名）
 *   footer: {
 *     avatarText: string,    // 页脚头像文字（首字母）
 *     avatarIcon: string,    // 页脚头像图标名（可选，优先于 avatarText）
 *     avatarStyle: object,   // 页脚头像样式（可选）
 *     name: string,          // 作者 / 发布方
 *     meta: string,          // 页脚副信息（日期 / 级别 / 地区）
 *   },
 *   actions: Array<{ key: string, label: string, class: string, icon?: string, handler?: Function }>,
 *   interaction: { targetType: string, targetId: string, targetTitle: string },  // 互动条
 *   raw: object,             // 原始 domain 数据（详情页等仍可访问）
 * }
 */

/**
 * 通用头像样式：收敛为液态玻璃灰阶质感（不再使用彩虹色渐变）。
 * 头像差异通过首字母与字形表达，不通过颜色。
 */
export function hashAvatarStyle(seed = '', fallback = '创') {
  return {
    background: 'linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--glass-border-subtle)',
  };
}

/**
 * 首字母（中文取首字，英文取首字母）。
 */
export function initialsOf(text = '', fallback = '创') {
  const clean = String(text || '').replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
  return clean.slice(0, 1) || fallback;
}

/* ------------------------------------------------------------------ */
/* 各 domain 的归一化函数                                              */
/* ------------------------------------------------------------------ */

/** 产品橱窗 (products) */
export function productCard(item = {}) {
  return {
    id: item.id,
    title: item.title,
    summary: item.tagline || item.description || '',
    iconType: item.icon_url ? 'img' : 'initials',
    iconUrl: item.icon_url,
    iconInitials: initialsOf(item.title),
    iconClass: '',
    category: item.category || '独立商业作品',
    categoryLabel: item.category || '独立商业作品',
    badges: [
      { text: item.category || '独立商业作品', class: 'badge-cat' },
      { text: formatPricing(item.pricing_model, item.price_cny), class: 'badge-pricing', pricingClass: getPricingClass(item.pricing_model) },
    ],
    highlights: [],
    footer: {
      avatarText: (item.author_name || item.author || '创')[0] || '创',
      avatarStyle: hashAvatarStyle(item.author_name || item.author),
      name: item.author_name || item.author || '@创客',
      meta: formatDateShort(item.created_at),
    },
    actions: [],
    interaction: { targetType: 'PRODUCT', targetId: item.id, targetTitle: item.title },
    raw: item,
  };
}

/** 政策中心 (policies) */
export function policyCard(item = {}) {
  const catMap = { TAX: '税费减免', SUBSIDY: '创业补贴', RENT: '场地免租', TALENT: '人才激励' };
  const label = catMap[String(item.category || '').toUpperCase()] || item.category || '政务红利';
  return {
    id: item.id,
    title: item.title,
    summary: item.summary || '',
    iconType: 'icon',
    iconName: { TAX: 'coin', SUBSIDY: 'bolt', RENT: 'building', TALENT: 'cap' }[String(item.category || '').toUpperCase()] || 'landmark',
    iconClass: 'emblem-' + String(item.category || '').toLowerCase() || 'emblem-default',
    category: item.category,
    categoryLabel: label,
    badges: [
      { text: label, class: 'badge-cat badge-' + String(item.category || '').toLowerCase() },
      { text: item.policy_level || '国家级', class: 'badge-level ' + getLevelClass(item.policy_level) },
      { text: item.region || '全国统一', class: 'badge-region' },
    ],
    highlights: [
      { icon: 'coin', text: formatSubsidy(item.subsidy_amount_max), class: 'chip-subsidy' },
      { icon: 'calendar', text: item.deadline || '常年开放申报', class: 'chip-deadline' },
    ],
    footer: {
      avatarIcon: 'landmark',
      name: item.region || '全国统一',
      meta: item.policy_level || '政府扶持',
    },
    actions: [],
    interaction: { targetType: 'POLICY', targetId: item.id || item.code, targetTitle: item.title },
    raw: item,
  };
}

/** 需求集市 (demands) */
export function demandCard(item = {}) {
  return {
    id: item.id,
    title: item.title,
    summary: item.description || '',
    iconType: 'icon',
    iconName: categoryIcon(item.category),
    iconClass: '',
    category: item.category,
    categoryLabel: item.category || '外包需求',
    badges: [
      { text: item.category || '外包需求', class: 'badge-cat' },
      { text: `¥${formatBudget(item.budget_cny)} 预算`, class: 'badge-pricing pricing-onetime' },
    ],
    highlights: [
      { icon: 'timer', text: `${formatDeadline(item.deadline_at)} 截止`, class: 'chip-deadline' },
    ],
    footer: {
      avatarText: initialsOf(item.creator_name || item.creator_id),
      avatarStyle: hashAvatarStyle(item.creator_name || item.creator_id),
      name: item.creator_name || item.creator_id || '@企业委托方',
      meta: formatDateShort(item.created_at),
    },
    actions: [],
    interaction: { targetType: 'DEMAND', targetId: item.id, targetTitle: item.title },
    raw: item,
  };
}

/** 生态特权 (perks) */
export function perkCard(item = {}) {
  return {
    id: item.id,
    title: item.name,
    summary: item.summary || '',
    iconType: 'icon',
    iconName: { TOKEN: 'coin', SERVER: 'monitor', SAAS: 'modules', AI: 'spark', FINANCE: 'card', INFRA: 'wrench', OTHER: 'gift' }[String(item.category || '').toUpperCase()] || 'gift',
    iconClass: 'cat-' + String(item.category || '').toLowerCase(),
    category: item.category,
    categoryLabel: item.category || '生态优惠',
    badges: [
      { text: item.category || '生态优惠', class: 'badge-cat cat-' + String(item.category || '').toLowerCase() },
      { text: item.provider || '', class: 'badge-provider' },
    ],
    highlights: [
      { icon: 'coin', text: formatValue(item.value_cny), class: 'chip-value' },
      { icon: 'calendar', text: validityText(item), class: 'chip-validity' },
    ],
    footer: {
      avatarIcon: 'gift',
      name: item.provider || '生态伙伴',
      meta: item.redeem_url ? '生态伙伴直达' : '生态伙伴公告',
    },
    actions: [],
    interaction: { targetType: 'PERK', targetId: item.id, targetTitle: item.name },
    raw: item,
  };
}

/** 合规指南 (laws / cases) */
export function complianceCard(item = {}) {
  const isLaw = item && ('law_ref' in item || 'content' in item);
  return {
    id: item.id,
    title: item.title,
    summary: item.summary || item.lesson || '',
    iconType: 'icon',
    iconName: isLaw
      ? ({ shield: 'shield', 'credit-card': 'card', 'file-text': 'file', code: 'code', globe: 'globe' }[item.icon_name] || 'alert')
      : 'case',
    iconClass: isLaw ? 'law-' + (item.code || '').toLowerCase() : '',
    category: isLaw ? '法条' : '案例',
    categoryLabel: isLaw ? (item.name || '法条') : '避坑案例',
    badges: isLaw
      ? [
          { text: item.name || '法条', class: 'badge-cat' },
          { text: item.level || '国家级', class: 'badge-level' },
        ]
      : [{ text: item.badge || '避坑案例', class: 'badge-case' }],
    highlights: isLaw
      ? [
          { icon: 'alert', text: item.penalties || '', class: 'chip-penalty' },
          { icon: 'scroll', text: item.law_ref || '', class: 'chip-law' },
        ]
      : [{ icon: 'bolt', text: item.violation || '', class: 'chip-violation' }],
    footer: {
      avatarIcon: isLaw ? 'scroll' : 'case',
      name: isLaw ? (item.issuer || '发布机关') : '典型踩坑案例',
      meta: isLaw ? (item.level || '国家级') : '监管处罚',
    },
    actions: [],
    interaction: { targetType: isLaw ? 'LAW' : 'CASE', targetId: item.id, targetTitle: item.title },
    raw: item,
  };
}

/** 流程文书 (SOP documents / flows) */
export function sopCard(item = {}) {
  return {
    id: item.id,
    title: item.name || item.document_title,
    summary: item.summary || item.description || item.rendered_content || '',
    iconType: 'initials',
    iconInitials: initialsOf(item.author_name || '文'),
    iconClass: item.is_official ? 'sop-official' : '',
    category: item.category || '文书',
    categoryLabel: item.category || '文书',
    badges: item.is_official
      ? [{ text: '官方认证', class: 'badge-official' }]
      : item.status
        ? [{ text: statusLabel(item.status), class: 'badge-status' }]
        : [],
    highlights: [
      { icon: 'check', text: `${item.field_count ?? item.step_count ?? 0} 项`, class: 'chip-count' },
      { icon: 'users', text: `${item.usage_count ?? 0} 人使用`, class: 'chip-usage' },
    ],
    footer: {
      avatarText: initialsOf(item.author_name || '编'),
      avatarStyle: hashAvatarStyle(item.author_name),
      name: item.author_name || '平台编辑部',
      meta: formatDateShort(item.published_at || item.created_at),
    },
    actions: [],
    interaction: { targetType: 'SOP_DOCUMENT', targetId: item.id, targetTitle: item.name },
    raw: item,
  };
}

/* ------------------------------------------------------------------ */
/* 内部工具（与各页面原格式化逻辑对齐）                                 */
/* ------------------------------------------------------------------ */
function getPricingClass(model) {
  return model === 'FREE' ? 'pricing-free' : model === 'ONETIME' ? 'pricing-onetime' : 'pricing-sub';
}

function formatPricing(model, price) {
  if (model === 'FREE') return '免费';
  if (model === 'ONETIME') return `¥${Number(price || 0).toLocaleString()}`;
  if (model === 'SUBSCRIPTION') return `¥${Number(price || 0).toLocaleString()}/月`;
  return model || '免费';
}

function formatDateShort(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return '—';
  }
}

function categoryIcon(category) {
  const map = {
    DEV: 'code', DESIGN: 'palette', MARKETING: 'megaphone', WRITING: 'pen', AI: 'robot',
    WEB: 'globe', LEGAL: 'scale', FINANCE: 'coin', OTHER: 'box',
  };
  return map[category] || 'box';
}

function formatBudget(v) {
  return Number(v || 0).toLocaleString();
}

function formatDeadline(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  } catch {
    return '—';
  }
}

function formatValue(v) {
  if (!v || v <= 0) return '价值面议';
  return `价值 ¥${Number(v).toLocaleString()}`;
}

function validityText(item) {
  if (item.ends_at) {
    try {
      const d = new Date(item.ends_at);
      return `截至 ${d.getMonth() + 1}月${d.getDate()}日`;
    } catch {
      return '长期有效';
    }
  }
  return '长期有效';
}

function getLevelClass(level) {
  if (level === '国家级') return 'level-national';
  if (level === '省市级') return 'level-provincial';
  return 'level-park';
}

function formatSubsidy(amount) {
  if (!amount || amount <= 0) return '法定全额免征';
  return `最高补贴 ¥${Number(amount).toLocaleString()}`;
}

function statusLabel(status) {
  const map = { OPEN: '招募中', IN_PROGRESS: '进行中', CLOSED: '已关闭', PENDING_REVIEW: '待审核', READY: '已完成' };
  return map[status] || status || '';
}

/* 统一归一化入口：按页面类型分发 */
export function normalizeCard(item = {}, kind = 'product') {
  switch (kind) {
    case 'policy': return policyCard(item);
    case 'demand': return demandCard(item);
    case 'perk': return perkCard(item);
    case 'compliance': return complianceCard(item);
    case 'sop': return sopCard(item);
    case 'product':
    default: return productCard(item);
  }
}
