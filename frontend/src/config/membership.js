/**
 * 会员与积分中心 —— 展示配置（配置与代码、数据分离）
 *
 * - 代码：frontend/src/views/MembershipView.vue
 * - 配置：本文件（档位文案 / 图标 / 分区 / 流水筛选项）
 * - 数据：backend/data/seeds/membership_plans.json、reward_items.json、loyalty_rules.json
 */

export const MEMBERSHIP_TIER_META = {
  STANDARD: {
    label: '标准创客',
    short: 'STANDARD',
    icon: 'spark',
    tagline: '能看、能发、能互动',
  },
  PRO: {
    label: 'PRO 创客',
    short: 'PRO',
    icon: 'gem',
    tagline: '高频做政策、文书与申报的个体',
  },
  BLACK_DIAMOND: {
    label: '黑钻创客 VIP',
    short: 'BLACK DIAMOND',
    icon: 'gem',
    tagline: '要接单、要优先派单、要 1v1 的 OPC',
  },
};

export const MEMBERSHIP_TABS = [
  { key: 'store', label: '积分商城', icon: 'gift' },
  { key: 'plans', label: '会员权益', icon: 'gem' },
  { key: 'ledger', label: '积分明细', icon: 'chart-bar' },
  { key: 'earn', label: '赚积分', icon: 'bolt' },
];

export const REWARD_TYPE_META = {
  MEMBERSHIP: { label: '会员时长', icon: 'gem' },
  DIGITAL: { label: '数字权益', icon: 'bolt' },
  PHYSICAL: { label: '产品周边', icon: 'box' },
};

export const REWARD_GROUP_ORDER = ['MEMBERSHIP', 'DIGITAL', 'PHYSICAL'];

export const REWARD_GROUP_LABELS = {
  MEMBERSHIP: '会员时长',
  DIGITAL: '数字权益',
  PHYSICAL: '产品周边',
};

export const LEDGER_FILTERS = [
  { key: '', label: '全部' },
  { key: 'EARN', label: '获得' },
  { key: 'SPEND', label: '消耗' },
];

export const EARN_CATEGORY_META = {
  TASK: { label: '一次性任务', hint: '完善身份，长期有效' },
  CONTENT: { label: '发布内容', hint: '审核通过后即时入账' },
  INTERACTION: { label: '互动反馈', hint: '他人对你的内容产生互动' },
  READ: { label: '内容阅读', hint: '同一读者同一内容每日计一次' },
  BONUS: { label: '运营奖励', hint: '优质内容与持续活跃' },
};

export const EARN_CATEGORY_ORDER = ['TASK', 'CONTENT', 'INTERACTION', 'READ', 'BONUS'];

export const MEMBERSHIP_COPY = {
  pageTitle: '会员与晨光积分',
  pageSubtitle: '发内容赚积分，好内容涨等级；积分可兑换会员时长与产品周边。',
  pointsName: '晨光积分',
  emptyLedger: '还没有积分记录。发布一条政策、文书或参与互动，就会开始积累。',
  emptyOrders: '还没有兑换记录。',
  redeemNote: '积分一经兑换不可逆；会员时长可叠加顺延。',
};
