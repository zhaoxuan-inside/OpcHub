<template>
  <section id="showcaseBento" class="section-container">
    <div class="section-header">
      <div class="section-eyebrow"><span class="mono-tag">02 / CAPABILITIES</span><span>四大核心支柱</span></div>
      <h2 class="section-title">四大核心支柱 · 解构超级个体的商业全景</h2>
      <p class="section-desc">
        我们为一人公司定制了从找政策、备文书，到拓市场、求合作的完整能力链路。
      </p>
    </div>

    <div class="bento-grid">
      <!-- Bento 1: 政策中心 (Large) -->
      <div class="bento-card bento-span-2" @mousemove="trackCardSpotlight" @click="$emit('card-click', 'policy')">
        <div class="bento-content">
          <div class="card-top-meta">
            <span class="bento-index">01</span>
            <span class="mono-tag accent-tag">POL-RADAR // 实时聚合</span>
            <span class="card-status-badge">全域覆盖</span>
          </div>
          <h3 class="bento-title">政策中心 · 精准洞悉各省市一人公司专项扶持</h3>
          <p class="bento-text">
            打破信息不对称与晦涩公文壁垒。独家收录深圳、上海、杭州、成都等城市针对 OPC、独立开发者的无偿资助、税收减免与算力免租政策，AI 智能评估匹配度。
          </p>

          <div class="bento-preview-pills">
            <template v-if="hotPolicies.length > 0">
              <div
                v-for="policy in hotPolicies.slice(0, 3)"
                :key="policy.id || policy.code"
                class="policy-chip"
              >
                <span class="city-dot"></span>
                <span class="city-name">{{ policy.region || '全国' }}</span>
                <span class="policy-amount">{{ policyAmountText(policy) }}</span>
                <span class="policy-brief">{{ policy.title }}</span>
              </div>
            </template>
            <div v-else class="bento-empty-hint">政策库持续收录中 · 点击查看已有红利</div>
          </div>
        </div>
        <div class="bento-action-row">
          <span class="action-text">查看全部政策中心数据库</span>
          <span class="action-arrow">→</span>
        </div>
      </div>

      <!-- Bento 2: 产品橱窗 (Vertical) -->
      <div class="bento-card" @mousemove="trackCardSpotlight" @click="$emit('card-click', 'product')">
        <div class="bento-content">
          <div class="card-top-meta">
            <span class="bento-index">02</span>
            <span class="mono-tag">SHOWCASE // 独立作品秀场</span>
            <span class="card-status-badge hot">HOT 榜单</span>
          </div>
          <h3 class="bento-title">产品橱窗 · 独立作品高光舞台</h3>
          <p class="bento-text">
            打造超级个体的 Product Hunt。优秀商业产品打榜 Upvote，全站置顶曝光与公测获客直达。
          </p>
          <div class="mini-showcase-box">
            <template v-if="hotProducts.length > 0">
              <div
                v-for="(p, pIdx) in hotProducts.slice(0, 2)"
                :key="p.id"
                class="mini-product-item"
              >
                <div class="mini-prod-avatar" :class="{ alt: pIdx > 0 }">
                  <img v-if="p.icon_url" :src="p.icon_url" :alt="p.title" style="width: 100%; height: 100%; object-fit: contain; padding: 2px;" />
                  <span v-else>{{ getInitials(p.title) }}</span>
                </div>
                <div class="mini-prod-info">
                  <div class="mini-prod-title">{{ p.title }}</div>
                  <div class="mini-prod-sub">{{ p.tagline || p.description }}</div>
                </div>
                <div class="mini-upvote"><OpcIcon name="like" :size="11" /> {{ p.upvote_count ?? p.upvotes ?? 0 }}</div>
              </div>
            </template>
            <div v-else class="bento-empty-hint">暂无上架作品 · 点击探索首发</div>
          </div>
        </div>
        <div class="bento-action-row">
          <span class="action-text">探索创客产品打榜</span>
          <span class="action-arrow">→</span>
        </div>
      </div>

      <!-- Bento 3: AI 文书与 SOP (Vertical) -->
      <div class="bento-card" @mousemove="trackCardSpotlight" @click="$emit('card-click', 'sop')">
        <div class="bento-content">
          <div class="card-top-meta">
            <span class="bento-index">03</span>
            <span class="mono-tag">SOP-DOC // 智能公函与文书</span>
            <span class="card-status-badge ai">AI 增强</span>
          </div>
          <h3 class="bento-title">流程文书 · 标准化法商合规</h3>
          <p class="bento-text">
            无需聘请昂贵法务与中介。工商设立公函、银行开户指引、财务零申报 SOP 一键生成。
          </p>
          <div class="sop-mini-stepper">
            <template v-if="topSopTemplates.length > 0">
              <template v-for="(tpl, tplIdx) in topSopTemplates" :key="tpl.id">
                <div v-if="tplIdx > 0" class="stepper-line"></div>
                <div class="stepper-node" :class="{ active: tplIdx === 0 }">
                  <div class="step-num">{{ String(tplIdx + 1).padStart(2, '0') }}</div>
                  <div class="step-desc" :title="tpl.name">{{ tpl.name }}</div>
                </div>
              </template>
            </template>
            <div v-else class="bento-empty-hint">流程模板整理中 · 点击查看全部文书</div>
          </div>
        </div>
        <div class="bento-action-row">
          <span class="action-text">生成标准化合规文书</span>
          <span class="action-arrow">→</span>
        </div>
      </div>

      <!-- Bento 4: 需求集市与撮合 (Large) -->
      <div class="bento-card bento-span-2" @mousemove="trackCardSpotlight" @click="$emit('card-click', 'demand')">
        <div class="bento-content">
          <div class="card-top-meta">
            <span class="bento-index">04</span>
            <span class="mono-tag">MARKET // 技能交易撮合</span>
            <span class="card-status-badge">即时对接</span>
          </div>
          <h3 class="bento-title">需求集市 · 超级个体的分布式协同网络</h3>
          <p class="bento-text">
            一个人办公司，不代表单打独斗。当需要出海海外支付集成、UI 品牌设计或跨境法务支持时，在集市一键发布需求，与平台认证创客快速联名撮合。
          </p>
          <div class="demands-mini-stream">
            <template v-if="hotDemands.length > 0">
              <div
                v-for="demand in hotDemands.slice(0, 2)"
                :key="demand.id"
                class="demand-pill"
              >
                <span class="demand-type">{{ demandCategoryLabel(demand.category) }}</span>
                <span class="demand-title">{{ demand.title }}</span>
                <span class="demand-budget">¥{{ formatCny(demand.budget_cny) }}</span>
              </div>
            </template>
            <div v-else class="bento-empty-hint">暂无在招企业委托 · 点击发布或浏览商机</div>
          </div>
        </div>
        <div class="bento-action-row">
          <span class="action-text">浏览需求撮合与商机</span>
          <span class="action-arrow">→</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { trackCardSpotlight } from './spotlight';

const props = defineProps({
  hotProducts: {
    type: Array,
    default: () => [],
  },
  hotPolicies: {
    type: Array,
    default: () => [],
  },
  hotDemands: {
    type: Array,
    default: () => [],
  },
  sopTemplates: {
    type: Array,
    default: () => [],
  },
});

defineEmits(['card-click']);

const topSopTemplates = computed(() => (
  [...props.sopTemplates]
    .sort((a, b) => (Number(b.usage_count) || 0) - (Number(a.usage_count) || 0))
    .slice(0, 3)
));

const DEMAND_CATEGORY_LABELS = {
  DEV: '技术开发',
  AI: 'AI 智能体',
  TAX: '财税合规',
  LEGAL: '法律求助',
  BIZ: '商业运营',
};

function demandCategoryLabel(category) {
  return DEMAND_CATEGORY_LABELS[category] || category || '企业委托';
}

function formatCny(value) {
  return Number(value || 0).toLocaleString('zh-CN');
}

function policyAmountText(policy) {
  if (Number(policy.subsidy_amount_max) > 0) return `最高 ¥${formatCny(policy.subsidy_amount_max)}`;
  if (policy.category === 'TAX') return '税优减免';
  return '专项扶持';
}

function getInitials(name) {
  if (!name) return 'OP';
  const clean = name.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
  return clean.slice(0, 2).toUpperCase() || 'OP';
}
</script>

<style scoped>
.section-container {
  margin-bottom: 72px;
}

.section-header {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 36px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.section-desc {
  font-size: 14.5px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Bento Grid */
.bento-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.bento-span-2 {
  grid-column: span 2;
}

.bento-card {
  background: var(--glass-surface);
  backdrop-filter: var(--blur-strength);
  -webkit-backdrop-filter: var(--blur-strength);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow), var(--glass-specular);
  padding: 30px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--transition-liquid);
}

.bento-card:hover {
  background: var(--glass-surface-hover);
  border-color: var(--glass-border-hover);
  box-shadow: var(--glass-shadow-hover), var(--glass-glow-halo);
  transform: translateY(-4px) scale(1.006);
}

.card-top-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.accent-tag {
  background: var(--accent-glass);
  color: var(--accent);
  border-color: rgba(0, 113, 227, 0.2);
}

.card-status-badge {
  font-size: 11px;
  font-family: var(--font-mono);
  padding: 2px 7px;
  border-radius: var(--radius-xs);
  background: var(--status-success-soft);
  color: var(--status-success);
}

.card-status-badge.hot {
  background: var(--status-warning-soft);
  color: var(--status-warning);
}

.card-status-badge.ai {
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
}

.bento-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.bento-text {
  font-size: 13.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 22px;
}

.bento-empty-hint {
  padding: 12px 0;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 12px;
}

.bento-preview-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.policy-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px;
  min-width: 0;
}

.city-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.city-name {
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.policy-amount {
  font-family: var(--font-mono);
  color: var(--text-secondary);
  font-weight: 600;
  white-space: nowrap;
}

.policy-brief {
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.mini-showcase-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.mini-product-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-sm);
}

.mini-prod-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}

.mini-prod-avatar.alt {
  background: var(--accent);
}

.mini-prod-info {
  flex: 1;
  min-width: 0;
}

.mini-prod-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mini-prod-sub {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mini-upvote {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
}

.sop-mini-stepper {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
}

.stepper-node {
  flex: 1;
  padding: 8px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  text-align: center;
  min-width: 0;
}

.stepper-node.active {
  background: var(--accent-glass);
  border-color: var(--accent);
}

.stepper-node .step-num {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
  margin-bottom: 2px;
}

.stepper-node.active .step-num {
  color: var(--accent);
  font-weight: 700;
}

.stepper-node .step-desc {
  font-size: 11px;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stepper-line {
  width: 12px;
  height: 1px;
  background: var(--glass-border-subtle);
  flex-shrink: 0;
}

.demands-mini-stream {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.demand-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.demand-type {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--glass-surface);
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

.demand-title {
  flex: 1;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.demand-budget {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
}

.bento-action-row {
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12.5px;
  color: var(--accent);
  font-weight: 500;
}

.bento-card:hover .action-arrow {
  transform: translateX(4px);
}

.action-arrow {
  transition: transform 0.2s ease;
}

@media (max-width: 1024px) {
  .bento-grid {
    grid-template-columns: 1fr;
  }
  .bento-span-2 {
    grid-column: span 1;
  }
}

/* ---- v2 editorial overrides ---- */
.section-container {
  margin-bottom: 80px;
}

.section-header {
  text-align: left;
  max-width: none;
  margin: 0 0 28px;
}

.section-eyebrow {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.section-title {
  font-size: 32px;
  font-weight: 680;
  letter-spacing: -0.045em;
  margin-bottom: 8px;
}

.section-desc {
  max-width: 660px;
  font-size: 13.5px;
}

.bento-grid {
  gap: 14px;
}

.bento-card {
  padding: 24px;
  border-radius: 18px;
  background: var(--glass-surface);
  box-shadow: var(--glass-shadow);
  border-color: var(--glass-border);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.bento-card:hover {
  transform: none;
  background: var(--glass-surface);
  border-color: var(--glass-border-hover);
  box-shadow: var(--glass-shadow-hover);
}

.card-top-meta {
  gap: 10px;
  margin-bottom: 14px;
}

.bento-index {
  margin-right: auto;
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
}

.bento-title {
  font-size: 19px;
  letter-spacing: -0.03em;
  line-height: 1.28;
}

.bento-text {
  font-size: 12.5px;
  line-height: 1.65;
  margin-bottom: 20px;
}

.bento-action-row {
  color: var(--text-primary);
  font-size: 11px;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding-top: 12px;
}

.policy-chip,
.mini-product-item,
.stepper-node,
.demand-pill {
  border-radius: 8px;
  background: var(--glass-surface-subtle);
  border-color: var(--glass-border-subtle);
}

.card-status-badge {
  font-size: 9px;
  letter-spacing: 0.04em;
}

@media (max-width: 1024px) {
  .bento-grid { grid-template-columns: 1fr; }
  .bento-span-2 { grid-column: span 1; }
}

</style>
