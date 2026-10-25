<template>
  <footer class="editorial-footer">
    <div class="footer-inner">
      <div class="footer-brand-col">
        <div class="footer-brand-title">
          <BrandLogo :size="24" />
          <span>晨昏线外</span>
          <span class="footer-brand-ver">Beyond the Line</span>
        </div>
        <p class="footer-brand-text">
          全国领先的面向超级个体与一人公司 (One Person Company) 的全周期商业操作系统。于晨昏线外，赋能每一份独立创造的商业势能。
        </p>
      </div>

      <div class="footer-links-col">
        <div class="footer-col-heading">平台四大支柱</div>
        <ul class="footer-links-list">
          <li><a @click.prevent="$emit('footer-nav', 'policy')">政策中心与城市招商</a></li>
          <li><a @click.prevent="$emit('footer-nav', 'sop')">合规文书与流程 SOP</a></li>
          <li><a @click.prevent="$emit('footer-nav', 'product')">超级个体产品橱窗</a></li>
          <li><a @click.prevent="$emit('footer-nav', 'demand')">创客需求集市撮合</a></li>
        </ul>
      </div>

      <div class="footer-links-col">
        <div class="footer-col-heading">创客成长生态</div>
        <ul class="footer-links-list">
          <li><a @click.prevent="$emit('footer-nav', 'forum')">头脑风暴社区</a></li>
          <li><a @click.prevent="$emit('footer-nav', 'perks')">生态伙伴优惠公告</a></li>
          <li><a @click.prevent="$emit('footer-nav', 'compliance')">合规法务指南</a></li>
        </ul>
      </div>

      <div class="footer-links-col">
        <div class="footer-col-heading">平台治理与信任</div>
        <ul class="footer-links-list">
          <li><span>用户服务协议</span></li>
          <li><span>隐私合规保护</span></li>
          <li><span>商业数据云端加密存管</span></li>
          <li><span>电信级审计与数据加密</span></li>
        </ul>
      </div>
    </div>

    <div class="footer-bottom-bar">
      <div>© 2026 晨昏线外 Beyond Terminator. All Rights Reserved.</div>
    </div>
  </footer>
</template>

<script setup>
import BrandLogo from '../BrandLogo.vue';

defineEmits(['footer-nav']);
</script>

<style scoped>
.editorial-footer {
  margin-top: 80px;
  border-top: 1px solid var(--glass-border-subtle);
  padding: 56px 0 32px;
}

.footer-inner {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 32px;
  margin-bottom: 40px;
}

.footer-brand-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.footer-brand-ver {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 400;
}

.footer-brand-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 320px;
}

.footer-col-heading {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 14px;
}

.footer-links-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12.5px;
}

.footer-links-list a {
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s ease;
}

.footer-links-list a:hover {
  color: var(--accent);
}

.footer-links-list span {
  color: var(--text-tertiary);
}

.footer-bottom-bar {
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-tertiary);
  flex-wrap: wrap;
  gap: 12px;
}

@media (max-width: 1024px) {
  .footer-inner {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 680px) {
  .footer-inner {
    grid-template-columns: 1fr;
  }
}
</style>
