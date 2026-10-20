<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <h1 class="page-title" style="font-size: 26px; margin: 0;">需求外包与商机集市</h1>
            <span class="mono-tag" style="background: rgba(52, 199, 89, 0.12); color: #34C759; border-color: rgba(52, 199, 89, 0.3);">
              企业商机撮合
            </span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary);">
            真实企业付费委托 · 托管资金保障 · 专为超级个体与技术顾问打造
          </p>
        </div>
        <button class="btn-liquid" @click="openPublishModal">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          <span>发布需求</span>
        </button>
      </div>

      <!-- Demand Category Filter Tabs -->
      <div style="display: flex; gap: 8px; margin-top: 16px; border-top: 1px solid var(--glass-border-subtle); padding-top: 12px; flex-wrap: wrap;">
        <button
          v-for="cat in categories"
          :key="cat.key"
          class="btn-liquid-outline"
          :class="{ active: selectedCategory === cat.key }"
          :style="cat.key === 'LEGAL' ? { color: '#FF9500', borderColor: 'rgba(255,149,0,0.3)' } : {}"
          style="padding: 4px 12px; font-size: 12px;"
          @click="selectedCategory = cat.key"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- Demands Cards Grid -->
    <div class="grid-3" id="demandCardsGrid">
      <div
        v-for="d in filteredDemands"
        :key="d.id"
        class="glass-card"
        @mousemove="handleMouseMove"
      >
        <div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span
              class="mono-tag"
              :style="d.category === 'LEGAL' ? { background: 'rgba(255,149,0,0.15)', color: '#FF9500' } : {}"
            >
              {{ d.catName }} · ¥{{ d.budget }}
            </span>
            <span style="font-size: 11.5px; color: #34C759; font-family: var(--font-mono);">
              资金已托管
            </span>
          </div>
          <h3 style="font-size: 16px; margin-bottom: 8px;">{{ d.title }}</h3>
          <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.55;">
            {{ d.desc }}
          </p>
        </div>
        <div style="border-top: 1px solid var(--glass-border-subtle); padding-top: 14px; margin-top: 18px; display: flex; justify-content: space-between; align-items: center; font-size: 12.5px;">
          <span style="color: var(--text-tertiary);">{{ d.bids }} 人已竞标</span>
          <button
            class="btn-liquid"
            style="padding: 4px 12px; font-size: 12px;"
            @click="handleBid(d)"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            竞标
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const emit = defineEmits(['open-register', 'toast']);

const categories = [
  { key: 'ALL', label: '全部商机' },
  { key: 'DEV', label: '技术开发' },
  { key: 'AI', label: 'AI智能体' },
  { key: 'TAX', label: '财税合规' },
  { key: 'LEGAL', label: '法律求助' },
];

const selectedCategory = ref('ALL');

const demands = [
  {
    id: 'dmd-1',
    category: 'AI',
    catName: 'AI智能体',
    budget: '35,000',
    title: '外贸 CRM 系统的垂直行业 Agent 工作流搭建',
    desc: '需要基于 FastAPI + PostgreSQL + pgvector 打造私有知识库问答与自动邮件生成插件，周期 3 周。',
    bids: 3,
  },
  {
    id: 'dmd-2',
    category: 'DEV',
    catName: '技术开发',
    budget: '18,000',
    title: '跨端桌面工具 (Electron / Tauri) 界面重构与性能调优',
    desc: '将老旧代码升级为 Vue3 组合式 API 并适配深色/浅色液态毛玻璃界面，具备良好现代美感。',
    bids: 1,
  },
  {
    id: 'dmd-3',
    category: 'DEV',
    catName: '技术顾问',
    budget: '60,000',
    title: '出海 SaaS 平台长期兼职 DevOps 与合规架构顾问',
    desc: '负责 AWS Terraform 编排、Stripe Webhook 支付链路稳定性监控与自动化数据库备份保障。',
    bids: 5,
  },
  {
    id: 'dmd-4',
    category: 'LEGAL',
    catName: '法律求助',
    budget: '12,000',
    title: '出海独立 SaaS 平台隐私协议与 GDPR 合规审查求助',
    desc: '寻求资深涉外法务或合规律师，起草符合欧盟 GDPR 与美区 CCPA 标准的隐私政策与用户数据出境评估报告。',
    bids: 2,
  },
  {
    id: 'dmd-5',
    category: 'TAX',
    catName: '财税合规',
    budget: '8,000',
    title: '独立开发者季度纳税申报与离岸公司简易做账辅导',
    desc: '辅导香港公司与内地个体户合规纳税申报，并指导电子税务局增值税零税率备案流程。',
    bids: 4,
  },
];

const filteredDemands = computed(() => {
  if (selectedCategory.value === 'ALL') return demands;
  return demands.filter((d) => d.category === selectedCategory.value);
});

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  card.style.setProperty('--mouse-x', `${x}px`);
  card.style.setProperty('--mouse-y', `${y}px`);
}

function handleBid(d) {
  const token = localStorage.getItem('opchub_session_token');
  if (!token) {
    emit('toast', {
      title: '需创客准入',
      message: '请先完成商用入驻注册或登录后参与商机竞标！',
      type: 'INFO',
    });
    emit('open-register');
    return;
  }
  d.bids = (d.bids || 0) + 1;
  emit('toast', {
    title: '竞标成功提交',
    message: `您对【${d.title}】的商务报价与技术案已直达委托发起人！`,
    type: 'SUCCESS',
  });
}

function openPublishModal() {
  const token = localStorage.getItem('opchub_session_token');
  if (!token) {
    emit('toast', {
      title: '需创客准入',
      message: '请先登录创客账号后发布外包寻源委托！',
      type: 'INFO',
    });
    emit('open-register');
    return;
  }
  emit('toast', {
    title: '发布需求',
    message: '企业商机寻源发布窗口已就绪！',
    type: 'INFO',
  });
}
</script>
