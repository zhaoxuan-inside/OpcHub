<template>
  <Teleport to="body">
    <transition name="pw-fade">
      <div v-if="visible" class="pw-overlay" @click.self="close">
        <section class="pw-panel" role="dialog" aria-modal="true" aria-labelledby="policy-wizard-title">
          <header class="pw-header">
            <div>
              <div class="pw-kicker">POLICY ELIGIBILITY // 30 秒自测</div>
              <h2 id="policy-wizard-title" class="pw-title">申报资格自测</h2>
              <p class="pw-subtitle">
                {{ policy?.title || '按你的经营情况，匹配可申报的政策与材料清单' }}
              </p>
            </div>
            <button type="button" class="pw-close" aria-label="关闭" @click="close">
              <OpcIcon name="close" :size="16" />
            </button>
          </header>

          <div class="pw-steps" aria-label="自测进度">
            <div
              v-for="(step, index) in steps"
              :key="step.key"
              class="pw-step"
              :class="{ active: stepIndex === index, done: stepIndex > index }"
            >
              <span class="pw-step-index">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="pw-step-label">{{ step.label }}</span>
            </div>
          </div>

          <div class="pw-body">
            <template v-if="stepIndex === 0">
              <div class="pw-field-grid">
                <label class="pw-field">
                  <span class="pw-label">经营主体</span>
                  <select v-model="form.makerType" class="pw-input">
                    <option value="INDIVIDUAL">个体工商户 / 个人经营</option>
                    <option value="OPC">一人有限责任公司</option>
                  </select>
                </label>

                <label class="pw-field">
                  <span class="pw-label">经营所在地</span>
                  <input v-model.trim="form.region" class="pw-input" list="pw-region-list" placeholder="如：杭州" />
                  <datalist id="pw-region-list">
                    <option v-for="region in regions" :key="region" :value="region" />
                  </datalist>
                </label>

                <label class="pw-field pw-field-wide">
                  <span class="pw-label">季度含税销售额（元）</span>
                  <div class="pw-money-row">
                    <span class="pw-currency">¥</span>
                    <input
                      v-model.number="form.quarterlyIncome"
                      class="pw-input pw-money-input"
                      type="number"
                      min="0"
                      step="1000"
                      placeholder="如：250000"
                    />
                  </div>
                  <span class="pw-help">用于判断增值税免征额与小微优惠档位，仅在本机参与测算。</span>
                </label>
              </div>
            </template>

            <template v-else-if="stepIndex === 1">
              <div class="pw-field-grid">
                <label class="pw-field pw-field-wide">
                  <span class="pw-label">你正在做的事（可选）</span>
                  <textarea
                    v-model.trim="form.business"
                    class="pw-input pw-textarea"
                    rows="3"
                    placeholder="如：做 AI 写作工具，客户主要是海外中小商家"
                  ></textarea>
                  <span class="pw-help">描述越具体，匹配到的行业专项政策越准确。</span>
                </label>

                <label class="pw-field pw-field-wide">
                  <span class="pw-label">行业关键词（可选，逗号分隔）</span>
                  <input
                    v-model.trim="form.keywords"
                    class="pw-input"
                    placeholder="如：人工智能, 跨境电商, 软件服务"
                  />
                </label>

                <div class="pw-policy-echo">
                  <span class="pw-policy-echo-label">当前查看的政策</span>
                  <strong>{{ policy?.title || '全量政策匹配' }}</strong>
                  <span v-if="policy?.region" class="pw-policy-echo-meta">{{ policy.region }} · {{ policy.policy_level }}</span>
                </div>
              </div>
            </template>

            <template v-else>
              <div v-if="isMatching" class="pw-state">
                <span class="pw-spinner"></span>
                正在比对政策库与你的经营指标…
              </div>

              <div v-else-if="matchError" class="pw-state pw-state-error">
                <OpcIcon name="alert" :size="18" />
                <div>
                  <strong>测算未完成</strong>
                  <p>{{ matchError }}</p>
                </div>
              </div>

              <template v-else-if="result">
                <div class="pw-result-hero" :class="result.eligible ? 'is-eligible' : 'is-review'">
                  <div class="pw-result-icon">
                    <OpcIcon :name="result.eligible ? 'check' : 'alert'" :size="22" />
                  </div>
                  <div class="pw-result-main">
                    <span class="pw-result-kicker">
                      {{ result.eligible ? 'ELIGIBLE // 可直接申报' : 'REVIEW // 需要补充条件' }}
                    </span>
                    <h3 class="pw-result-title">
                      {{ result.eligible ? '当前指标符合申报条件' : '当前指标暂未完全满足' }}
                    </h3>
                    <p class="pw-result-desc">{{ result.explanation || '平台已根据你的主体、地区与营收完成初步比对。' }}</p>
                  </div>
                </div>

                <div class="pw-metrics">
                  <div class="pw-metric">
                    <span class="pw-metric-label">适用征收率</span>
                    <strong class="pw-metric-value">{{ formatRate(result.applicable_tax_rate) }}</strong>
                  </div>
                  <div class="pw-metric">
                    <span class="pw-metric-label">预计税收优惠</span>
                    <strong class="pw-metric-value">{{ formatMoney(result.estimated_tax_savings) }}</strong>
                  </div>
                  <div class="pw-metric">
                    <span class="pw-metric-label">匹配政策</span>
                    <strong class="pw-metric-value">{{ result.matched_policies?.length || 0 }} 项</strong>
                  </div>
                </div>

                <div v-if="result.legal_basis" class="pw-legal">
                  <span class="pw-legal-label">法规依据</span>
                  <span>{{ result.legal_basis }}</span>
                </div>

                <div v-if="result.matched_policies?.length" class="pw-matched">
                  <div class="pw-matched-title">匹配到的政策</div>
                  <button
                    v-for="item in result.matched_policies"
                    :key="item.id || item.code"
                    type="button"
                    class="pw-matched-item"
                    @click="openPolicy(item)"
                  >
                    <span class="pw-matched-name">{{ item.title }}</span>
                    <span class="pw-matched-meta">
                      {{ item.region }} · {{ formatMoney(item.subsidy_amount_max) }}
                    </span>
                  </button>
                </div>

                <div class="pw-next-steps">
                  <div class="pw-next-title">下一步建议</div>
                  <ol>
                    <li>核对政策原文中的申报条件与截止日期。</li>
                    <li>在「流程文书」中生成对应的登记 / 申报材料。</li>
                    <li>材料准备齐全后，再通过官方渠道提交。</li>
                  </ol>
                </div>
              </template>
            </template>
          </div>

          <footer class="pw-footer">
            <button v-if="stepIndex > 0 && stepIndex < 2" type="button" class="btn-liquid-outline pw-btn" @click="stepIndex -= 1">
              上一步
            </button>
            <span class="pw-footer-spacer"></span>
            <button v-if="stepIndex < 2" type="button" class="btn-liquid pw-btn" :disabled="!canNext" @click="next">
              {{ stepIndex === 1 ? '开始匹配' : '下一步' }}
            </button>
            <template v-else>
              <button type="button" class="btn-liquid-outline pw-btn" @click="reset">重新测算</button>
              <button v-if="result?.matched_policies?.length" type="button" class="btn-liquid pw-btn" @click="openPolicy(result.matched_policies[0])">
                查看匹配政策
              </button>
            </template>
          </footer>
        </section>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  visible: { type: Boolean, default: false },
  policy: { type: Object, default: null },
  initialIncome: { type: [Number, String], default: 250000 },
  initialRegion: { type: String, default: '杭州' },
});

const emit = defineEmits(['close', 'toast', 'open-policy']);

const steps = [
  { key: 'profile', label: '基本情况' },
  { key: 'business', label: '业务方向' },
  { key: 'result', label: '匹配结果' },
];

const regions = ['全国统一', '北京', '上海', '深圳', '广州', '杭州', '成都', '武汉', '南京', '苏州', '厦门', '重庆'];
const stepIndex = ref(0);
const isMatching = ref(false);
const matchError = ref('');
const result = ref(null);

const form = reactive({
  makerType: 'INDIVIDUAL',
  region: '杭州',
  quarterlyIncome: 250000,
  business: '',
  keywords: '',
});

watch(
  () => props.visible,
  (visible) => {
    if (!visible) return;
    stepIndex.value = 0;
    result.value = null;
    matchError.value = '';
    isMatching.value = false;
    form.makerType = 'INDIVIDUAL';
    form.region = props.initialRegion || '杭州';
    form.quarterlyIncome = Number(props.initialIncome) || 250000;
    form.business = props.policy?.title || '';
    form.keywords = '';
  },
  { immediate: true }
);

const canNext = computed(() => {
  if (stepIndex.value === 0) {
    return Boolean(form.region) && Number(form.quarterlyIncome) >= 0;
  }
  if (stepIndex.value === 1) return true;
  return true;
});

function next() {
  if (!canNext.value) return;
  if (stepIndex.value === 0) {
    stepIndex.value = 1;
    return;
  }
  runMatch();
}

async function runMatch() {
  stepIndex.value = 2;
  isMatching.value = true;
  matchError.value = '';
  result.value = null;

  const keywords = form.keywords
    .split(/[,，、\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  const res = await dispatchGateway('policies.match', {
    quarterly_income: Number(form.quarterlyIncome) || 0,
    maker_type: form.makerType,
    region: form.region,
    search_query: form.business || props.policy?.title || '',
    industry_keywords: keywords,
  });

  if (res.ok && res.data) {
    result.value = res.data;
  } else {
    matchError.value = res.error || '匹配服务暂时不可用，请稍后重试。';
    emit('toast', {
      title: '资格匹配失败',
      message: matchError.value,
      type: 'ERROR',
    });
  }
  isMatching.value = false;
}

function reset() {
  stepIndex.value = 0;
  result.value = null;
  matchError.value = '';
}

function close() {
  emit('close');
}

function openPolicy(item) {
  emit('open-policy', item);
  emit('close');
}

function formatRate(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${(number * 100).toFixed(number > 0 && number < 0.01 ? 2 : 1)}%`;
}

function formatMoney(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return '¥0';
  return `¥${number.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`;
}
</script>

<style scoped>
.pw-overlay {
  position: fixed;
  inset: 0;
  z-index: 999998;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 18px;
  background: rgba(8, 10, 16, 0.36);
  backdrop-filter: blur(12px) saturate(150%);
  -webkit-backdrop-filter: blur(12px) saturate(150%);
}

.pw-panel {
  width: min(760px, 100%);
  max-height: min(88vh, 820px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 22px;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.97));
  border: 1px solid var(--glass-border);
  box-shadow: 0 34px 100px rgba(0, 0, 0, 0.3), var(--glass-specular);
}

.pw-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 24px 16px;
}

.pw-kicker {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  margin-bottom: 6px;
}

.pw-title {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.03em;
  line-height: 1.2;
  color: var(--text-primary);
}

.pw-subtitle {
  margin: 6px 0 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--text-secondary);
}

.pw-close {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 50%;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pw-close:hover {
  color: var(--text-primary);
}

.pw-steps {
  display: flex;
  gap: 6px;
  padding: 0 24px 16px;
}

.pw-step {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-tertiary);
  font-size: 11.5px;
  font-weight: 600;
}

.pw-step.active {
  color: var(--accent);
  border-color: rgba(0, 113, 227, 0.28);
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
}

.pw-step.done {
  color: var(--status-success);
  border-color: rgba(46, 160, 67, 0.24);
}

.pw-step-index {
  font-family: var(--font-mono, monospace);
  font-size: 9.5px;
  letter-spacing: 0.06em;
}

.pw-step-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pw-body {
  flex: 1;
  min-height: 220px;
  overflow-y: auto;
  padding: 8px 24px 20px;
}

.pw-field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.pw-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pw-field-wide {
  grid-column: 1 / -1;
}

.pw-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.pw-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.pw-input:focus {
  border-color: rgba(0, 113, 227, 0.45);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.08);
}

.pw-textarea {
  resize: vertical;
  min-height: 78px;
}

.pw-money-row {
  position: relative;
}

.pw-currency {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary);
  font-size: 12px;
}

.pw-money-input {
  padding-left: 26px;
}

.pw-help {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-tertiary);
}

.pw-policy-echo {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px dashed var(--glass-border-subtle);
  background: var(--glass-surface);
}

.pw-policy-echo-label {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.pw-policy-echo strong {
  font-size: 13px;
  color: var(--text-primary);
}

.pw-policy-echo-meta {
  font-size: 11px;
  color: var(--text-secondary);
}

.pw-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 200px;
  color: var(--text-secondary);
  font-size: 13px;
}

.pw-state-error {
  justify-content: flex-start;
  color: var(--status-danger);
  padding: 18px;
  border-radius: 12px;
  background: var(--status-danger-soft);
}

.pw-state-error p {
  margin: 4px 0 0;
  font-size: 12px;
}

.pw-spinner {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--glass-border-subtle);
  border-top-color: var(--accent);
  animation: pwSpin 0.8s linear infinite;
}

@keyframes pwSpin {
  to { transform: rotate(360deg); }
}

.pw-result-hero {
  display: flex;
  gap: 14px;
  padding: 18px;
  border-radius: 16px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
}

.pw-result-hero.is-eligible {
  border-color: rgba(46, 160, 67, 0.28);
  background: var(--status-success-soft);
}

.pw-result-hero.is-review {
  border-color: rgba(196, 126, 0, 0.26);
  background: var(--status-warning-soft);
}

.pw-result-icon {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-surface-solid, #fff);
  color: var(--status-success);
}

.is-review .pw-result-icon {
  color: var(--status-warning);
}

.pw-result-kicker {
  font-family: var(--font-mono, monospace);
  font-size: 9.5px;
  letter-spacing: 0.07em;
  color: var(--text-tertiary);
}

.pw-result-title {
  margin: 4px 0 5px;
  font-size: 17px;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.pw-result-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.pw-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 14px;
}

.pw-metric {
  padding: 13px 14px;
  border-radius: 12px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pw-metric-label {
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.pw-metric-value {
  font-size: 17px;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.pw-legal {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  padding: 11px 13px;
  border-radius: 10px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border-subtle);
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--text-secondary);
}

.pw-legal-label {
  flex-shrink: 0;
  font-weight: 700;
  color: var(--text-tertiary);
}

.pw-matched {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pw-matched-title,
.pw-next-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.pw-matched-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
}

.pw-matched-item:hover {
  border-color: rgba(0, 113, 227, 0.28);
}

.pw-matched-name {
  font-size: 12.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pw-matched-meta {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-tertiary);
}

.pw-next-steps {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border-subtle);
}

.pw-next-steps ol {
  margin: 8px 0 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--text-secondary);
}

.pw-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px 18px;
  border-top: 1px solid var(--glass-border-subtle);
}

.pw-footer-spacer {
  flex: 1;
}

.pw-btn {
  min-width: 96px;
  justify-content: center;
}

.pw-fade-enter-active,
.pw-fade-leave-active {
  transition: opacity 0.18s ease;
}

.pw-fade-enter-from,
.pw-fade-leave-to {
  opacity: 0;
}

.pw-fade-enter-active .pw-panel,
.pw-fade-leave-active .pw-panel {
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.pw-fade-enter-from .pw-panel,
.pw-fade-leave-to .pw-panel {
  transform: translateY(10px) scale(0.98);
}

@media (max-width: 640px) {
  .pw-overlay {
    padding: 0;
    align-items: stretch;
  }

  .pw-panel {
    max-height: 100vh;
    height: 100vh;
    border-radius: 0;
    border: none;
  }

  .pw-field-grid,
  .pw-metrics {
    grid-template-columns: 1fr;
  }

  .pw-steps {
    padding: 0 16px 12px;
  }

  .pw-body,
  .pw-header {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>
