<template>
  <section class="section-container">
    <div class="section-header">
      <h2 class="section-title">一人公司演进路径 · 从单点萌芽到自主商业实体</h2>
      <p class="section-desc">
        「晨昏线外」伴随超级个体成长的四个核心阶段，提供不同周期的关键基础设施。
      </p>
    </div>

    <div class="journey-grid">
      <div class="journey-card glass-card" @mousemove="trackCardSpotlight">
        <div class="journey-step-num">PHASE 01</div>
        <h4 class="journey-card-title">立项与政策锁定</h4>
        <p class="journey-card-desc">
          借助政策中心测算全国优惠税率与落地园区，筛选最契合主营赛道的落地城市与初创免租扶持。
        </p>
        <div class="journey-feature-tag">政策中心 · 城市匹配</div>
      </div>

      <div class="journey-card glass-card" @mousemove="trackCardSpotlight">
        <div class="journey-step-num">PHASE 02</div>
        <h4 class="journey-card-title">合规注册与设立</h4>
        <p class="journey-card-desc">
          AI 辅助生成标准化公司章程与工商设立公函，指导银行基本户设立与首年合规税务零申报。
        </p>
        <div class="journey-feature-tag">流程文书 · AI 公函生成</div>
      </div>

      <div class="journey-card glass-card" @mousemove="trackCardSpotlight">
        <div class="journey-step-num">PHASE 03</div>
        <h4 class="journey-card-title">产品发布与商业化</h4>
        <p class="journey-card-desc">
          作品上架超级个体橱窗，通过全网创客打榜获取早期种子用户，验证产品商业变现模型。
        </p>
        <div class="journey-feature-tag">产品橱窗 · Upvote 打榜</div>
      </div>

      <div class="journey-card glass-card" @mousemove="trackCardSpotlight">
        <div class="journey-step-num">PHASE 04</div>
        <h4 class="journey-card-title">生态协同与规模化</h4>
        <p class="journey-card-desc">
          在需求集市撮合外部专家弥补能力短板，领取平台专属云服务器、AI 算力与财税折扣券。
        </p>
        <div class="journey-feature-tag">需求集市 · 生态特权</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { trackCardSpotlight } from './spotlight';
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

/* Journey Grid */
.journey-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.journey-card {
  padding: 24px 20px;
}

.journey-step-num {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.journey-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.journey-card-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.55;
  margin-bottom: 14px;
}

.journey-feature-tag {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-tertiary);
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 10px;
}

@media (max-width: 1024px) {
  .journey-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 680px) {
  .journey-grid {
    grid-template-columns: 1fr;
  }
}
</style>
