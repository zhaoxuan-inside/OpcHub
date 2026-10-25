<template>
  <section class="section-container">
    <div class="glass-box bottom-cta-box" @mousemove="trackCardSpotlight">
      <div class="bottom-cta-orb"></div>
      <div class="bottom-cta-inner">
        <div class="mono-tag" style="background: var(--accent-glass); color: var(--accent); margin-bottom: 16px;">
          JOIN THE OPC REVOLUTION
        </div>
        <h2 class="bottom-cta-title">
          今天，正式开启你的一人公司之旅
        </h2>
        <p class="bottom-cta-desc">
          无论你是一名全栈工程师、产品设计师、内容专家还是独立顾问，「晨昏线外」为你提供全方位的商业后盾与成长生态。
        </p>
        <div class="bottom-cta-actions">
          <button
            v-if="!userSession"
            class="btn-liquid bottom-btn-primary"
            @click="$emit('open-register')"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="8.5" cy="7" r="4"/>
              <line x1="20" y1="8" x2="20" y2="14"/>
              <line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
            <span>免费注册入驻平台</span>
          </button>
          <button
            v-if="!userSession"
            class="btn-liquid-outline bottom-btn-secondary"
            @click="$emit('open-login')"
          >
            <span>已有账号？立即登录</span>
          </button>
          <button
            v-else
            class="btn-liquid bottom-btn-primary"
            @click="$emit('switch-tab', 'forum')"
          >
            <span>进入创客工作台 ›</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { trackCardSpotlight } from './spotlight';

defineProps({
  userSession: {
    type: Object,
    default: null,
  },
});

defineEmits(['open-login', 'open-register', 'switch-tab']);
</script>

<style scoped>
.section-container {
  margin-bottom: 72px;
}

.bottom-cta-box {
  padding: 56px 40px;
  text-align: center;
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-lg);
  margin-top: 32px;
}

.bottom-cta-orb {
  position: absolute;
  top: -50%;
  left: 30%;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
  pointer-events: none;
  filter: blur(40px);
}

.bottom-cta-inner {
  position: relative;
  z-index: 1;
  max-width: 640px;
  margin: 0 auto;
}

.bottom-cta-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin-bottom: 14px;
}

.bottom-cta-desc {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 28px;
}

.bottom-cta-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
}

.bottom-btn-primary {
  padding: 12px 28px;
  font-size: 14px;
  font-weight: 600;
}

.bottom-btn-secondary {
  padding: 12px 24px;
  font-size: 14px;
}
</style>
