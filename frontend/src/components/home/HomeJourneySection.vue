<template>
  <section class="section-container">
    <div class="section-header">
      <div class="section-eyebrow"><span class="mono-tag">03 / JOURNEY</span><span>一人公司演进路径</span></div>
      <h2 class="section-title">从单点萌芽，到自主商业实体</h2>
      <p class="section-desc">
        「晨昏线外」把超级个体的成长拆成四个阶段，每个阶段只解决最关键的基础设施问题。
      </p>
    </div>

    <div class="journey-list">
      <div v-for="(phase, idx) in phases" :key="phase.title" class="journey-row">
        <div class="journey-phase">
          <span class="journey-num">{{ String(idx + 1).padStart(2, '0') }}</span>
          <span class="journey-label">PHASE</span>
        </div>
        <div class="journey-body">
          <h3 class="journey-card-title">{{ phase.title }}</h3>
          <p class="journey-card-desc">{{ phase.desc }}</p>
        </div>
        <div class="journey-tag">{{ phase.tag }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
const phases = [
  {
    title: '立项与政策锁定',
    desc: '测算全国优惠税率与落地园区，筛选最契合主营赛道的城市与初创免租扶持。',
    tag: '政策中心 · 城市匹配',
  },
  {
    title: '合规注册与设立',
    desc: '辅助生成标准化公司章程与工商设立公函，指导银行基本户设立与首年合规税务零申报。',
    tag: '流程文书 · 引导填写',
  },
  {
    title: '产品发布与商业化',
    desc: '作品上架超级个体橱窗，通过全网创客打榜获取早期种子用户，验证商业变现模型。',
    tag: '产品橱窗 · 打榜曝光',
  },
  {
    title: '生态协同与规模化',
    desc: '在需求集市撮合外部专家弥补能力短板，领取平台专属云服务器、AI 算力与财税折扣。',
    tag: '需求集市 · 生态特权',
  },
];
</script>

<style scoped>
.section-container {
  margin-bottom: 80px;
}

.section-header {
  text-align: left;
  max-width: none;
  margin: 0 0 24px;
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
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 680;
  letter-spacing: -0.045em;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.section-desc {
  max-width: 680px;
  font-size: 13.5px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.journey-list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--glass-border);
}

.journey-row {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr) 210px;
  gap: 28px;
  align-items: start;
  padding: 24px 6px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.journey-phase {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.journey-num {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.05em;
  color: var(--text-primary);
}

.journey-label {
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
}

.journey-body {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.journey-card-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 640;
  letter-spacing: -0.025em;
  color: var(--text-primary);
}

.journey-card-desc {
  max-width: 640px;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-secondary);
}

.journey-tag {
  justify-self: end;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.04em;
  color: var(--text-tertiary);
  border: 1px solid var(--glass-border-subtle);
  border-radius: 999px;
  padding: 4px 9px;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .journey-row {
    grid-template-columns: 56px minmax(0, 1fr);
    gap: 12px;
  }

  .journey-tag {
    grid-column: 2;
    justify-self: start;
  }

  .journey-num {
    font-size: 18px;
  }
}
</style>
