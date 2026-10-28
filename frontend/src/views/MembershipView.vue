<template>
  <div class="view-panel membership-view">
    <header class="mv-header">
      <div>
        <p class="mv-eyebrow">MEMBERSHIP &amp; POINTS</p>
        <h1 class="mv-title">{{ copy.pageTitle }}</h1>
        <p class="mv-subtitle">{{ copy.pageSubtitle }}</p>
      </div>
      <button class="btn-liquid-outline mv-refresh" :disabled="isLoading" @click="loadAll">
        <OpcIcon name="bolt" :size="13" />
        <span>{{ isLoading ? '同步中…' : '刷新' }}</span>
      </button>
    </header>

    <div class="mv-hero-grid">
      <!-- 积分资产 -->
      <section class="glass-panel mv-card mv-balance-card">
        <div class="mv-card-top">
          <span class="mv-label">{{ copy.pointsName }}</span>
          <span class="mv-level-pill">
            <OpcIcon name="spark" :size="12" />
            {{ account?.level_name || '微光' }} V{{ account?.level || 1 }}
          </span>
        </div>
        <div class="mv-balance">{{ formatPoints(account?.balance) }}</div>
        <div class="mv-balance-meta">
          今日 <span class="mv-earn">+{{ formatPoints(account?.today_earned) }}</span>
          · 本月 <span class="mv-earn">+{{ formatPoints(account?.month_earned) }}</span>
          · 累计获得 {{ formatPoints(account?.total_earned) }}
        </div>
        <div class="mv-progress">
          <div class="mv-progress-head">
            <span>成长值 {{ formatPoints(account?.growth) }}</span>
            <span>下一等级 {{ formatPoints(account?.next_level_growth) }}</span>
          </div>
          <div class="mv-progress-track">
            <div class="mv-progress-fill" :style="{ width: `${account?.level_progress || 0}%` }"></div>
          </div>
        </div>
        <div class="mv-actions">
          <button class="btn-liquid" @click="activeTab = 'store'">去兑换</button>
          <button class="btn-liquid-outline" @click="activeTab = 'ledger'">看明细</button>
        </div>
      </section>

      <!-- 会员状态 -->
      <section class="glass-panel mv-card mv-membership-card">
        <div class="mv-card-top">
          <span class="mv-label">当前会员</span>
          <span class="mv-tier-pill" :class="`tier-${tierKey.toLowerCase()}`">{{ sourceLabel }}</span>
        </div>
        <div class="mv-tier-name">{{ membership?.tier_name || '标准创客' }}</div>
        <p class="mv-tier-desc">{{ tierMeta.tagline }}</p>
        <div v-if="isActiveMembership" class="mv-meta-row">
          有效期至 <strong>{{ formatDate(membership?.expires_at) }}</strong>
          · 剩余 <strong>{{ membership?.days_left || 0 }}</strong> 天
        </div>
        <div v-else class="mv-meta-row">
          尚未开通付费会员。积分可以兑换会员时长，会员只提升额度与效率，不影响社区互动计数。
        </div>
        <div class="mv-actions">
          <button class="btn-liquid" @click="activeTab = 'plans'">
            {{ isActiveMembership ? '续期 / 升级' : '开通会员' }}
          </button>
          <button
            v-if="isActiveMembership"
            class="btn-liquid-outline"
            :disabled="isTogglingRenew"
            @click="toggleAutoRenew"
          >
            {{ membership?.auto_renew ? '关闭自动续费' : '开启自动续费' }}
          </button>
        </div>
      </section>
    </div>

    <!-- Tabs -->
    <nav class="mv-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="mv-tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <OpcIcon :name="tab.icon" :size="13" />
        <span>{{ tab.label }}</span>
      </button>
    </nav>

    <!-- 积分商城 -->
    <section v-if="activeTab === 'store'" class="mv-section">
      <div v-if="isLoading && rewardItems.length === 0" class="mv-empty">正在加载兑换目录…</div>
      <div v-for="group in rewardGroups" :key="group.type" class="mv-group">
        <div class="mv-group-head">
          <h2>{{ group.label }}</h2>
          <span>{{ group.items.length }} 件</span>
        </div>
        <div class="mv-reward-grid">
          <article
            v-for="item in group.items"
            :key="item.code"
            class="glass-card mv-reward-card"
          >
            <div class="mv-reward-top">
              <span class="mv-reward-icon"><OpcIcon :name="item.icon || 'gift'" :size="20" /></span>
              <span class="mv-type-pill">{{ typeMeta(item.type).label }}</span>
            </div>
            <h3 class="mv-reward-name">{{ item.name }}</h3>
            <p class="mv-reward-desc">{{ item.description }}</p>
            <div class="mv-reward-meta">
              <span class="mv-reward-price">{{ formatPoints(item.points_price) }} <small>积分</small></span>
              <span class="mv-stock">{{ stockText(item) }}</span>
            </div>
            <button
              class="btn-liquid mv-reward-btn"
              :disabled="isItemDisabled(item)"
              @click="openRedeem(item)"
            >
              {{ itemActionLabel(item) }}
            </button>
          </article>
        </div>
      </div>
      <div v-if="!isLoading && rewardItems.length === 0" class="mv-empty">兑换目录暂未开放。</div>
    </section>

    <!-- 会员权益 -->
    <section v-else-if="activeTab === 'plans'" class="mv-section">
      <div class="mv-plan-grid">
        <article
          v-for="plan in plans"
          :key="plan.code"
          class="glass-card mv-plan-card"
          :class="{ current: isCurrentPlan(plan), recommended: plan.recommended }"
        >
          <div class="mv-plan-top">
            <div>
              <span class="mv-plan-tier">{{ plan.tier_name }}</span>
              <h3 class="mv-plan-period">{{ periodLabel(plan) }}</h3>
            </div>
            <span v-if="plan.recommended" class="mv-badge-recommend">推荐</span>
            <span v-else-if="isCurrentPlan(plan)" class="mv-badge-current">当前</span>
          </div>
          <div class="mv-plan-price">
            <span class="mv-plan-points">{{ formatPoints(plan.points_price) }}</span>
            <span class="mv-plan-unit">积分</span>
            <span class="mv-plan-cash">参考价 ¥{{ plan.price_cny }}</span>
          </div>
          <ul class="mv-benefits">
            <li v-for="benefit in plan.benefits" :key="benefit">
              <OpcIcon name="check" :size="12" />
              <span>{{ benefit }}</span>
            </li>
          </ul>
          <button
            class="btn-liquid mv-plan-btn"
            :disabled="isPlanDisabled(plan)"
            @click="subscribePlan(plan)"
          >
            {{ planActionLabel(plan) }}
          </button>
        </article>
      </div>
      <p class="mv-footnote">
        会员只影响功能额度、分发排序与服务优先级，不会虚增点赞、收藏或评论计数。
        积分兑换价含 20% 溢价，现金开通更划算。
      </p>
    </section>

    <!-- 积分明细 -->
    <section v-else-if="activeTab === 'ledger'" class="mv-section">
      <div class="mv-ledger-toolbar">
        <div class="mv-filter-pills">
          <button
            v-for="filter in ledgerFilters"
            :key="filter.key"
            type="button"
            class="mv-filter-pill"
            :class="{ active: ledgerFilter === filter.key }"
            @click="ledgerFilter = filter.key"
          >
            {{ filter.label }}
          </button>
        </div>
        <span class="mv-ledger-total">共 {{ ledgerTotal }} 条</span>
      </div>

      <div v-if="filteredLedger.length === 0" class="mv-empty">{{ copy.emptyLedger }}</div>
      <div v-else class="mv-ledger-list">
        <div v-for="entry in filteredLedger" :key="entry.id" class="mv-ledger-row">
          <div class="mv-ledger-main">
            <div class="mv-ledger-title">
              {{ entry.title }}
              <span v-if="entry.note" class="mv-ledger-note">· {{ entry.note }}</span>
            </div>
            <div class="mv-ledger-meta">
              <span class="mono-tag">{{ entry.event_code }}</span>
              <span>{{ formatDateTime(entry.created_at) }}</span>
            </div>
          </div>
          <div class="mv-ledger-side">
            <span class="mv-ledger-delta" :class="entry.delta >= 0 ? 'earn' : 'spend'">
              {{ formatPointsDelta(entry.delta) }}
            </span>
            <span class="mv-ledger-balance">余额 {{ formatPoints(entry.balance_after) }}</span>
          </div>
        </div>
      </div>
      <button
        v-if="ledgerItems.length < ledgerTotal"
        class="btn-liquid-outline mv-load-more"
        :disabled="isLoadingLedger"
        @click="loadLedger(false)"
      >
        {{ isLoadingLedger ? '加载中…' : '加载更多' }}
      </button>

      <div class="mv-group-head mv-orders-head">
        <h2>兑换记录</h2>
        <span>{{ orders.length }} 笔</span>
      </div>
      <div v-if="orders.length === 0" class="mv-empty">{{ copy.emptyOrders }}</div>
      <div v-else class="mv-order-list">
        <div v-for="order in orders" :key="order.id" class="mv-order-row">
          <div>
            <div class="mv-order-name">{{ order.item_name }} <span class="mv-order-qty">×{{ order.qty }}</span></div>
            <div class="mv-ledger-meta">
              <span class="mono-tag">{{ order.item_type }}</span>
              <span>{{ formatDateTime(order.created_at) }}</span>
            </div>
          </div>
          <div class="mv-order-side">
            <span class="mv-order-cost">-{{ formatPoints(order.points_cost) }}</span>
            <span class="mv-order-status">{{ orderStatusLabel(order.status) }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 赚积分 -->
    <section v-else class="mv-section">
      <div class="mv-earn-summary glass-panel">
        <div>
          <span class="mv-label">每日获取上限</span>
          <strong>{{ formatPoints(rulesMeta.daily_global_cap) }} 积分</strong>
        </div>
        <div>
          <span class="mv-label">每月获取上限</span>
          <strong>{{ formatPoints(rulesMeta.monthly_global_cap) }} 积分</strong>
        </div>
        <div>
          <span class="mv-label">积分有效期</span>
          <strong>{{ rulesMeta.expiry_months }} 个月</strong>
        </div>
      </div>

      <div v-for="group in earnGroups" :key="group.category" class="mv-group">
        <div class="mv-group-head">
          <h2>{{ group.meta.label }}</h2>
          <span>{{ group.meta.hint }}</span>
        </div>
        <div class="mv-rule-list">
          <div v-for="rule in group.items" :key="rule.code" class="mv-rule-row">
            <div class="mv-rule-main">
              <span class="mv-rule-name">{{ rule.name }}</span>
              <span class="mv-rule-desc">{{ rule.description }}</span>
            </div>
            <div class="mv-rule-side">
              <span class="mv-rule-points">+{{ rule.points }}</span>
              <span class="mv-rule-cap">{{ capText(rule) }}</span>
            </div>
          </div>
        </div>
      </div>

      <p class="mv-footnote">
        会员与成长等级会放大实际到账积分（会员最高 1.5x、等级最高 1.3x，合计封顶 2.0x）。
        踩不直接扣积分，只影响内容质量分与排序。自赞、自评、同设备小号与互刷行为不计分；
        取消互动会回滚对应积分。
      </p>
    </section>

    <!-- 兑换确认 -->
    <Teleport to="body">
      <transition name="mv-fade">
        <div v-if="redeemTarget" class="mv-modal-overlay" @click.self="closeRedeem">
          <div class="mv-modal glass-panel">
          <div class="mv-modal-head">
            <div>
              <span class="mv-label">积分兑换</span>
              <h3>{{ redeemTarget.name }}</h3>
            </div>
            <button class="mv-modal-close" @click="closeRedeem"><OpcIcon name="close" :size="16" /></button>
          </div>

          <p class="mv-modal-desc">{{ redeemTarget.description }}</p>

          <div class="mv-modal-row">
            <span>兑换数量</span>
            <div class="mv-qty">
              <button type="button" :disabled="redeemQty <= 1" @click="redeemQty -= 1">−</button>
              <span>{{ redeemQty }}</span>
              <button type="button" :disabled="redeemQty >= 10" @click="redeemQty += 1">＋</button>
            </div>
          </div>

          <div v-if="redeemTarget.type === 'PHYSICAL'" class="mv-address-form">
            <div class="mv-address-title">收货信息</div>
            <div class="mv-address-grid">
              <input v-model="addressForm.name" class="glass-input" placeholder="收货人姓名" maxlength="30" />
              <input v-model="addressForm.phone" class="glass-input" placeholder="联系电话" maxlength="20" />
            </div>
            <input v-model="addressForm.detail" class="glass-input" placeholder="详细地址（省 / 市 / 区 / 街道门牌）" maxlength="120" />
          </div>

          <div class="mv-modal-total">
            <span>合计消耗</span>
            <strong>{{ formatPoints(redeemTotal) }} 积分</strong>
          </div>
          <div class="mv-modal-balance">
            当前余额 {{ formatPoints(account?.balance) }} 积分
            <span v-if="Number(account?.balance || 0) < redeemTotal" class="mv-modal-warn">· 余额不足</span>
          </div>

          <div class="mv-modal-actions">
            <button class="btn-liquid-outline" @click="closeRedeem">取消</button>
            <button
              class="btn-liquid"
              :disabled="isRedeeming || Number(account?.balance || 0) < redeemTotal || !addressValid"
              @click="confirmRedeem"
            >
              {{ isRedeeming ? '兑换中…' : '确认兑换' }}
            </button>
          </div>
          <p class="mv-modal-note">{{ copy.redeemNote }}</p>
        </div>
      </div>
    </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import {
  EARN_CATEGORY_META,
  EARN_CATEGORY_ORDER,
  LEDGER_FILTERS,
  MEMBERSHIP_COPY,
  MEMBERSHIP_TABS,
  MEMBERSHIP_TIER_META,
  REWARD_GROUP_LABELS,
  REWARD_GROUP_ORDER,
  REWARD_TYPE_META,
} from '@/config/membership';
import {
  formatDate,
  formatDateTime,
  formatPoints,
  formatPointsDelta,
} from '@/utils/loyalty';

const emit = defineEmits(['toast']);

const copy = MEMBERSHIP_COPY;
const tabs = MEMBERSHIP_TABS;
const ledgerFilters = LEDGER_FILTERS;

const isLoading = ref(true);
const isLoadingLedger = ref(false);
const isRedeeming = ref(false);
const isSubscribing = ref(false);
const isTogglingRenew = ref(false);

const account = ref(null);
const membership = ref(null);
const plans = ref([]);
const rewardItems = ref([]);
const orders = ref([]);
const ledgerItems = ref([]);
const ledgerTotal = ref(0);
const rules = ref([]);
const rulesMeta = reactive({ daily_global_cap: 1000, monthly_global_cap: 20000, expiry_months: 24 });

const activeTab = ref('store');
const ledgerFilter = ref('');

const redeemTarget = ref(null);
const redeemQty = ref(1);
const addressForm = reactive({ name: '', phone: '', detail: '' });

function toast(title, message, type = 'SUCCESS') {
  emit('toast', { title, message, type });
}

async function safeCall(scenario, payload = {}) {
  try {
    const res = await dispatchGateway(scenario, payload, { silent: true });
    return res.ok ? res.data : null;
  } catch (e) {
    return null;
  }
}

async function loadAll() {
  isLoading.value = true;
  const [accountData, membershipData, plansData, itemsData, ordersData, ledgerData, rulesData] = await Promise.all([
    safeCall('loyalty.account'),
    safeCall('loyalty.membership.me'),
    safeCall('loyalty.membership.plans'),
    safeCall('loyalty.rewards.items'),
    safeCall('loyalty.rewards.orders'),
    safeCall('loyalty.ledger', { limit: 50, offset: 0 }),
    safeCall('loyalty.rules'),
  ]);
  account.value = accountData;
  membership.value = membershipData;
  plans.value = Array.isArray(plansData?.items) ? plansData.items : [];
  rewardItems.value = Array.isArray(itemsData?.items) ? itemsData.items : [];
  orders.value = Array.isArray(ordersData?.items) ? ordersData.items : [];
  ledgerItems.value = Array.isArray(ledgerData?.items) ? ledgerData.items : [];
  ledgerTotal.value = Number(ledgerData?.total || 0);
  rules.value = Array.isArray(rulesData?.items) ? rulesData.items : [];
  if (rulesData) {
    rulesMeta.daily_global_cap = Number(rulesData.daily_global_cap || 1000);
    rulesMeta.monthly_global_cap = Number(rulesData.monthly_global_cap || 20000);
    rulesMeta.expiry_months = Number(rulesData.expiry_months || 24);
  }
  isLoading.value = false;
}

async function loadLedger(reset = true) {
  if (isLoadingLedger.value) return;
  isLoadingLedger.value = true;
  const offset = reset ? 0 : ledgerItems.value.length;
  const data = await safeCall('loyalty.ledger', { limit: 50, offset });
  if (data) {
    ledgerItems.value = reset
      ? (data.items || [])
      : [...ledgerItems.value, ...(data.items || [])];
    ledgerTotal.value = Number(data.total || 0);
  }
  isLoadingLedger.value = false;
}

const tierKey = computed(() => {
  const tier = membership.value?.tier || account.value?.membership_tier || 'STANDARD';
  return MEMBERSHIP_TIER_META[tier] ? tier : 'STANDARD';
});
const tierMeta = computed(() => MEMBERSHIP_TIER_META[tierKey.value]);
const isActiveMembership = computed(
  () => membership.value?.status === 'ACTIVE' && tierKey.value !== 'STANDARD'
);
const sourceLabel = computed(() => {
  const source = membership.value?.source;
  if (source === 'CASH') return '现金开通';
  if (source === 'POINTS') return '积分兑换';
  if (source === 'GRANT') return '官方赠礼';
  return isActiveMembership.value ? '会员' : '免费';
});

const rewardGroups = computed(() =>
  REWARD_GROUP_ORDER
    .map((type) => ({
      type,
      label: REWARD_GROUP_LABELS[type],
      items: rewardItems.value.filter((item) => item.type === type),
    }))
    .filter((group) => group.items.length > 0)
);

const filteredLedger = computed(() => {
  if (ledgerFilter.value === 'EARN') {
    return ledgerItems.value.filter((entry) => Number(entry.delta) > 0);
  }
  if (ledgerFilter.value === 'SPEND') {
    return ledgerItems.value.filter((entry) => Number(entry.delta) < 0);
  }
  return ledgerItems.value;
});

const earnGroups = computed(() =>
  EARN_CATEGORY_ORDER
    .map((category) => ({
      category,
      meta: EARN_CATEGORY_META[category] || { label: category, hint: '' },
      items: rules.value.filter((rule) => rule.category === category),
    }))
    .filter((group) => group.items.length > 0)
);

const redeemTotal = computed(() => {
  if (!redeemTarget.value) return 0;
  return Number(redeemTarget.value.points_price || 0) * Number(redeemQty.value || 1);
});

const addressValid = computed(() => {
  if (!redeemTarget.value || redeemTarget.value.type !== 'PHYSICAL') return true;
  return Boolean(addressForm.name.trim() && addressForm.phone.trim() && addressForm.detail.trim());
});

function typeMeta(type) {
  return REWARD_TYPE_META[type] || { label: type, icon: 'gift' };
}

function periodLabel(plan) {
  return Number(plan.period_months) >= 12 ? '年卡' : '月卡';
}

function isCurrentPlan(plan) {
  return Boolean(
    isActiveMembership.value
    && membership.value?.tier === plan.tier
    && Number(membership.value?.plan_code === plan.code)
  );
}

function planActionLabel(plan) {
  const rank = { STANDARD: 0, PRO: 1, BLACK_DIAMOND: 2 };
  if (isActiveMembership.value && rank[membership.value?.tier] > rank[plan.tier]) {
    return '已含更高档权益';
  }
  if (Number(account.value?.balance || 0) < plan.points_price) return '积分不足';
  if (isCurrentPlan(plan)) return '续期';
  if (membership.value?.tier === plan.tier && isActiveMembership.value) return '续期';
  return '积分兑换';
}

function isPlanDisabled(plan) {
  const rank = { STANDARD: 0, PRO: 1, BLACK_DIAMOND: 2 };
  if (isActiveMembership.value && rank[membership.value?.tier] > rank[plan.tier]) return true;
  return isSubscribing.value || Number(account.value?.balance || 0) < plan.points_price;
}

function stockText(item) {
  if (Number(item.stock) < 0) return '不限量';
  return `剩余 ${formatPoints(item.stock)}`;
}

function itemActionLabel(item) {
  if (Number(item.stock) === 0) return '已兑完';
  if (item.type === 'MEMBERSHIP' && isLowerTierItem(item)) return '已含更高档权益';
  if (Number(account.value?.balance || 0) < Number(item.points_price || 0)) return '积分不足';
  if (
    item.type === 'MEMBERSHIP'
    && isActiveMembership.value
    && membership.value?.tier === (item.meta?.tier || '')
  ) {
    return '续期';
  }
  return '兑换';
}

function isLowerTierItem(item) {
  if (item.type !== 'MEMBERSHIP' || !isActiveMembership.value) return false;
  const rank = { STANDARD: 0, PRO: 1, BLACK_DIAMOND: 2 };
  return rank[membership.value?.tier] > rank[item.meta?.tier || 'STANDARD'];
}

function isItemDisabled(item) {
  return Number(item.stock) === 0
    || isLowerTierItem(item)
    || Number(account.value?.balance || 0) < Number(item.points_price || 0);
}

function openRedeem(item) {
  redeemTarget.value = item;
  redeemQty.value = 1;
  addressForm.name = '';
  addressForm.phone = '';
  addressForm.detail = '';
}

function closeRedeem() {
  if (isRedeeming.value) return;
  redeemTarget.value = null;
}

async function confirmRedeem() {
  if (!redeemTarget.value || isRedeeming.value) return;
  if (!addressValid.value) {
    toast('收货信息不完整', '实物兑换需要填写收货人、电话与详细地址。', 'WARN');
    return;
  }
  isRedeeming.value = true;
  const payload = {
    item_code: redeemTarget.value.code,
    qty: redeemQty.value,
    idempotency_key: `redeem:${redeemTarget.value.code}:${Date.now()}`,
  };
  if (redeemTarget.value.type === 'PHYSICAL') {
    payload.address = {
      name: addressForm.name.trim(),
      phone: addressForm.phone.trim(),
      detail: addressForm.detail.trim(),
    };
  }
  const res = await dispatchGateway('loyalty.rewards.redeem', payload);
  isRedeeming.value = false;
  if (res.ok) {
    toast('兑换成功', res.data?.message || '积分已扣减，权益已生效。', 'SUCCESS');
    redeemTarget.value = null;
    await loadAll();
  }
}

async function subscribePlan(plan) {
  if (isSubscribing.value) return;
  isSubscribing.value = true;
  const res = await dispatchGateway('loyalty.membership.subscribe', {
    plan_code: plan.code,
    pay_method: 'POINTS',
    idempotency_key: `subscribe:${plan.code}:${Date.now()}`,
  });
  isSubscribing.value = false;
  if (res.ok) {
    toast('会员已开通', res.data?.message || '权益即刻生效。', 'SUCCESS');
    await loadAll();
  }
}

async function toggleAutoRenew() {
  if (isTogglingRenew.value) return;
  isTogglingRenew.value = true;
  const enabled = !membership.value?.auto_renew;
  const res = await dispatchGateway('loyalty.membership.auto-renew', { enabled });
  isTogglingRenew.value = false;
  if (res.ok) {
    membership.value = res.data;
    toast(enabled ? '已开启自动续费' : '已关闭自动续费', enabled ? '到期前 3 天会提醒你。' : '到期后将不再自动扣费。', 'SUCCESS');
  }
}

function capText(rule) {
  if (rule.once) return '一次性';
  const parts = [];
  if (rule.per_target_cap) parts.push(`单篇 ${rule.per_target_cap}`);
  if (rule.daily_cap) parts.push(`每日 ${rule.daily_cap}`);
  if (rule.monthly_cap) parts.push(`每月 ${rule.monthly_cap}`);
  return parts.length ? `上限 ${parts.join(' · ')}` : '不限';
}

function orderStatusLabel(status) {
  return {
    PENDING_PAYMENT: '待支付',
    PAID: '待发货',
    SHIPPED: '已发货',
    COMPLETED: '已完成',
    CANCELLED: '已取消',
  }[status] || status;
}

onMounted(loadAll);
</script>

<style scoped>
.membership-view {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding-bottom: 64px;
}

.mv-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.mv-eyebrow {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--text-tertiary);
  margin: 0 0 8px;
}

.mv-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.mv-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

.mv-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  padding: 7px 16px;
  flex-shrink: 0;
}

.mv-hero-grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.mv-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.mv-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.mv-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.mv-level-pill,
.mv-tier-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--accent-glass);
  color: var(--accent);
  border: 1px solid var(--glass-border-subtle);
}

.mv-tier-pill.tier-black_diamond {
  color: var(--text-primary);
  background: var(--glass-surface-subtle);
}

.mv-balance {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 44px;
  font-weight: 600;
  letter-spacing: -0.04em;
  line-height: 1.1;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.mv-balance-meta {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 20px;
}

.mv-earn {
  color: var(--accent);
}

.mv-progress {
  margin-bottom: 22px;
}

.mv-progress-head {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.mv-progress-track {
  height: 3px;
  border-radius: 999px;
  background: var(--glass-border-subtle);
  overflow: hidden;
}

.mv-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent-glow);
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.mv-tier-name {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.mv-tier-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 18px;
}

.mv-meta-row {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 20px;
}

.mv-meta-row strong {
  color: var(--text-primary);
  font-weight: 600;
}

.mv-actions {
  display: flex;
  gap: 10px;
  margin-top: auto;
}

.mv-actions .btn-liquid,
.mv-actions .btn-liquid-outline {
  font-size: 12.5px;
  padding: 7px 18px;
}

.mv-tabs {
  display: flex;
  gap: 4px;
  padding: 5px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  width: fit-content;
  margin-bottom: 28px;
}

.mv-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12.5px;
  padding: 7px 16px;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.mv-tab:hover {
  color: var(--text-primary);
}

.mv-tab.active {
  background: var(--glass-surface-solid);
  color: var(--text-primary);
  box-shadow: var(--glass-specular);
}

.mv-section {
  min-height: 240px;
}

.mv-group {
  margin-bottom: 36px;
}

.mv-group-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.mv-group-head h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.mv-group-head span {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.mv-reward-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.mv-reward-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  min-height: 210px;
}

.mv-reward-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.mv-reward-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-glass);
  color: var(--accent);
}

.mv-type-pill {
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  padding: 3px 8px;
  border-radius: var(--radius-full);
  border: 1px solid var(--glass-border-subtle);
}

.mv-reward-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.mv-reward-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.55;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mv-reward-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.mv-reward-price {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.mv-reward-price small {
  font-size: 10px;
  font-weight: 400;
  color: var(--text-tertiary);
}

.mv-stock {
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.mv-reward-btn,
.mv-plan-btn {
  width: 100%;
  font-size: 12px;
  padding: 7px 12px;
  margin-top: auto;
}

.mv-plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.mv-plan-card {
  padding: 22px;
  display: flex;
  flex-direction: column;
  position: relative;
}

.mv-plan-card.current {
  border-color: var(--accent);
}

.mv-plan-card.recommended::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  box-shadow: inset 0 0 0 1px var(--accent-glow);
}

.mv-plan-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.mv-plan-tier {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.mv-plan-period {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 4px 0 0;
}

.mv-badge-recommend,
.mv-badge-current {
  font-size: 10px;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  background: var(--accent-glass);
  color: var(--accent);
  border: 1px solid var(--glass-border-subtle);
  flex-shrink: 0;
}

.mv-plan-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.mv-plan-points {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 26px;
  font-weight: 600;
  color: var(--text-primary);
}

.mv-plan-unit {
  font-size: 11px;
  color: var(--text-tertiary);
}

.mv-plan-cash {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-tertiary);
}

.mv-benefits {
  list-style: none;
  padding: 0;
  margin: 0 0 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mv-benefits li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.mv-benefits li :deep(svg) {
  color: var(--accent);
  flex-shrink: 0;
  margin-top: 3px;
}

.mv-ledger-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.mv-filter-pills {
  display: flex;
  gap: 4px;
}

.mv-filter-pill {
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 5px 14px;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 0.18s ease;
}

.mv-filter-pill:hover {
  color: var(--text-primary);
}

.mv-filter-pill.active {
  background: var(--glass-surface-solid);
  border-color: var(--glass-border-subtle);
  color: var(--text-primary);
}

.mv-ledger-total {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.mv-ledger-list {
  border-top: 1px solid var(--glass-border-subtle);
}

.mv-ledger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.mv-ledger-title {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 4px;
}

.mv-ledger-note {
  font-weight: 400;
  color: var(--text-tertiary);
}

.mv-ledger-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.mono-tag {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 10px;
  letter-spacing: 0.04em;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.mv-ledger-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
  flex-shrink: 0;
}

.mv-ledger-delta {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 14px;
  font-weight: 600;
}

.mv-ledger-delta.earn {
  color: var(--accent);
}

.mv-ledger-delta.spend {
  color: var(--text-secondary);
}

.mv-ledger-balance {
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.mv-load-more {
  display: block;
  margin: 20px auto 0;
  font-size: 12px;
  padding: 6px 20px;
}

.mv-orders-head {
  margin-top: 40px;
}

.mv-order-list {
  border-top: 1px solid var(--glass-border-subtle);
}

.mv-order-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.mv-order-name {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 4px;
}

.mv-order-qty {
  color: var(--text-tertiary);
  font-weight: 400;
}

.mv-order-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
}

.mv-order-cost {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 13px;
  color: var(--text-secondary);
}

.mv-order-status {
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.mv-earn-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 20px 24px;
  margin-bottom: 28px;
}

.mv-earn-summary > div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mv-earn-summary strong {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 18px;
  color: var(--text-primary);
}

.mv-rule-list {
  border-top: 1px solid var(--glass-border-subtle);
}

.mv-rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 13px 4px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.mv-rule-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.mv-rule-name {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

.mv-rule-desc {
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.5;
}

.mv-rule-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
  flex-shrink: 0;
}

.mv-rule-points {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
}

.mv-rule-cap {
  font-size: 10px;
  color: var(--text-tertiary);
}

.mv-empty {
  padding: 48px 0;
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
}

.mv-footnote {
  margin-top: 24px;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--text-tertiary);
}

/* Modal */
.mv-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgba(8, 10, 16, 0.42);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.mv-modal {
  width: 100%;
  max-width: 460px;
  padding: 26px;
  background: var(--glass-surface-solid);
  border: 1px solid var(--glass-border);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.24), var(--glass-specular);
}

.mv-modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.mv-modal-head h3 {
  font-size: 19px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 4px 0 0;
}

.mv-modal-close {
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
}

.mv-modal-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 18px;
}

.mv-modal-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.mv-qty {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mv-qty button {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  color: var(--text-primary);
  cursor: pointer;
}

.mv-qty button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.mv-address-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.mv-address-title {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
}

.mv-address-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mv-modal-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-top: 14px;
  border-top: 1px solid var(--glass-border-subtle);
  font-size: 13px;
  color: var(--text-secondary);
}

.mv-modal-total strong {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 20px;
  color: var(--text-primary);
}

.mv-modal-balance {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 6px;
}

.mv-modal-warn {
  color: var(--status-danger);
}

.mv-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.mv-modal-actions .btn-liquid,
.mv-modal-actions .btn-liquid-outline {
  font-size: 12.5px;
  padding: 7px 18px;
}

.mv-modal-note {
  font-size: 10.5px;
  color: var(--text-tertiary);
  line-height: 1.6;
  margin: 14px 0 0;
}

.mv-fade-enter-active,
.mv-fade-leave-active {
  transition: opacity 0.2s ease;
}

.mv-fade-enter-from,
.mv-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .mv-hero-grid,
  .mv-earn-summary {
    grid-template-columns: 1fr;
  }
  .mv-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .mv-tabs {
    width: 100%;
    overflow-x: auto;
  }
}
</style>
