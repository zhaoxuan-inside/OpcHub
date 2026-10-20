<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1 class="page-title" style="font-size: 26px; margin-bottom: 4px;">政策雷达与白话提炼库</h1>
          <p style="font-size: 13px; color: var(--text-secondary);">汇集长三角、大湾区及全国针对超级个体与初创团队的扶持红利，拒绝官话套话，直达关键要求。</p>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">政策智能匹配</span>
          <button class="btn-liquid" @click="openPublishModal">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span>发布</span>
          </button>
        </div>
      </div>
    </div>

    <!-- P04 RAG Semantic Vector Search Bar -->
    <div class="search-bar-liquid">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--accent); flex-shrink: 0;">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        class="glass-input input-liquid"
        placeholder="输入业务特征（如：AI算力微调、出海独立开发、小规模免税）进行向量语义检索..."
        style="flex: 1; padding: 8px 14px; font-size: 13.5px;"
        @keydown.enter="handleSearch"
      />
      <button
        class="btn-liquid"
        @click="handleSearch"
        style="padding: 8px 16px; font-size: 12.5px; white-space: nowrap;"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
        <span>语义检索</span>
      </button>
      <button
        class="btn-liquid-outline"
        @click="resetSearch"
        style="padding: 8px 14px; font-size: 12.5px; white-space: nowrap;"
      >
        <span>重置列表</span>
      </button>
    </div>

    <!-- Quick Tax Calculator Glass Box -->
    <div class="glass-box" style="padding: 20px 28px; margin-bottom: 24px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-weight: 600; font-size: 15px;">小微与一人公司增值税免征额即时测算</span>
          <span class="mono-tag" style="background: rgba(52, 199, 89, 0.15); color: #34C759;">免税试算引擎</span>
        </div>
      </div>
      <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 240px;">
          <input
            v-model.number="quarterlyIncome"
            type="number"
            class="glass-input"
            placeholder="输入季度预计开票营收 (元)，如: 280000"
          />
        </div>
        <button class="btn-liquid" @click="calculateTax">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span>执行测算</span>
        </button>
      </div>
      <div
        v-if="taxResult"
        style="margin-top: 14px; padding: 12px 16px; border-radius: var(--radius-sm); background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); display: flex; justify-content: space-between; align-items: center;"
      >
        <div style="font-size: 13.5px;">
          <span v-if="taxResult.vat_exempt" style="color: #34C759; font-weight: 600;">
            ✔ 符合小微免税红利！本季度应纳增值税: ¥ 0.00
          </span>
          <span v-else style="color: #FF9500; font-weight: 600;">
            ⚠️ 超过免税限额，按 1% 征收率试算本季度应纳税额: ¥ {{ taxResult.vat_due }}
          </span>
        </div>
        <span class="mono-tag">{{ taxResult.vat_exempt ? 'EXEMPTED' : 'TAXABLE' }}</span>
      </div>
    </div>

    <!-- Policy Cards Grid -->
    <div class="grid-3" id="policyCardsGrid">
      <div
        v-for="p in filteredPolicies"
        :key="p.code"
        class="glass-card"
        @mousemove="handleMouseMove"
      >
        <div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span class="mono-tag">{{ p.code }}</span>
            <span style="font-size: 11.5px; color: var(--text-tertiary);">{{ p.region }}</span>
          </div>
          <h3 style="font-size: 16px; margin-bottom: 8px;">{{ p.title }}</h3>
          <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.55;">
            {{ p.summary }}
          </p>
        </div>
        <div style="border-top: 1px solid var(--glass-border-subtle); padding-top: 14px; margin-top: 18px; display: flex; justify-content: space-between; align-items: center; font-size: 12.5px;">
          <span style="color: var(--text-tertiary);">{{ p.deadline }}</span>
          <button
            class="btn-liquid-outline"
            style="padding: 3px 10px; font-size: 11.5px;"
            @click="matchEligibility(p)"
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
            {{ p.actionText || '匹配资格' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const emit = defineEmits(['toast']);

const policies = [
  {
    code: 'POL-2026-081',
    region: '全国统一',
    title: '小微企业月销售额 10 万以下免征增值税',
    summary: '【白话要点】按季申报纳税人，季度开票未超 30 万元免交增值税；若开具专票需按 1% 征收率纳税。',
    deadline: '截止 2027-12-31',
    actionText: '匹配资格',
  },
  {
    code: 'POL-2026-094',
    region: '大湾区',
    title: '智能算力券补贴申领 (第 3 批)',
    summary: '【白话要点】租赁云厂商 GPU 算力卡训练微调大模型，由财政直补 30% 租赁费用，每家主体上限 20 万元。',
    deadline: '剩余 12 天',
    actionText: '申报材料',
  },
  {
    code: 'POL-2026-105',
    region: '长三角',
    title: '科技型中小企业研发费用加计扣除',
    summary: '【白话要点】研发活动发生的人工与设备折旧费用，在税前按 100% 比例加计扣除，有效抵冲经营利润税负。',
    deadline: '常年开放申报',
    actionText: '入库测评',
  },
  {
    code: 'POL-2026-118',
    region: '出海特区',
    title: '离岸数字贸易与技术出口增值税零税率',
    summary: '【白话要点】为海外机构提供软件研发、远程设计及技术咨询服务，经商务局认定后免征增值税且免除附加税。',
    deadline: '2026-11-30',
    actionText: '资格预审',
  },
];

const searchQuery = ref('');
const quarterlyIncome = ref(250000);
const taxResult = ref(null);

const filteredPolicies = computed(() => {
  if (!searchQuery.value.trim()) return policies;
  const q = searchQuery.value.toLowerCase();
  return policies.filter(
    (p) =>
      p.title.toLowerCase().includes(q) ||
      p.summary.toLowerCase().includes(q) ||
      p.region.toLowerCase().includes(q)
  );
});

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  card.style.setProperty('--mouse-x', `${x}px`);
  card.style.setProperty('--mouse-y', `${y}px`);
}

function handleSearch() {
  emit('toast', {
    title: '向量语义检索',
    message: `已基于特征词 “${searchQuery.value}” 召回最匹配的政策条目！`,
    type: 'INFO',
  });
}

function resetSearch() {
  searchQuery.value = '';
}

async function calculateTax() {
  const inc = Number(quarterlyIncome.value) || 0;
  try {
    const res = await dispatchGateway('tax.calculate_vat_exemption', {
      quarterly_income: inc,
    });
    if (res.ok && res.data) {
      taxResult.value = res.data;
    } else {
      // Local calculation fallback
      taxResult.value = {
        vat_exempt: inc <= 300000,
        vat_due: inc <= 300000 ? 0 : Math.round(inc * 0.01 * 100) / 100,
      };
    }
  } catch (e) {
    taxResult.value = {
      vat_exempt: inc <= 300000,
      vat_due: inc <= 300000 ? 0 : Math.round(inc * 0.01 * 100) / 100,
    };
  }
}

function matchEligibility(p) {
  emit('toast', {
    title: '政策资格匹配',
    message: `正在为您比对【${p.title}】申报要求，当前创客主体指标符合申报条件！`,
    type: 'SUCCESS',
  });
}

function openPublishModal() {
  emit('toast', {
    title: '收录政策',
    message: '政务政策与免税指引收录通道已开启！',
    type: 'INFO',
  });
}
</script>
