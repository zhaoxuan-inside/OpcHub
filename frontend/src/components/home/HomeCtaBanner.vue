<template>
  <section class="section-container">
    <div class="cta-block">
      <div class="cta-copy">
        <div class="cta-eyebrow mono-tag">JOIN THE OPC REVOLUTION</div>
        <h2 class="cta-title">今天，正式开启<br />你的一人公司之旅</h2>
        <p class="cta-desc">
          无论你是一名全栈工程师、产品设计师、内容专家还是独立顾问，
          「晨昏线外」为你提供政策、文书、曝光与撮合的商业底座。
        </p>
      </div>

      <div class="cta-actions">
        <button
          v-if="!userSession"
          class="btn-liquid cta-btn-primary"
          @click="$emit('open-register')"
        >
          <span>免费注册入驻平台</span>
          <span class="cta-arrow">→</span>
        </button>
        <button
          v-if="!userSession"
          class="cta-btn-secondary"
          @click="$emit('open-login')"
        >
          <span>已有账号？立即登录</span>
        </button>
        <button
          v-else
          class="btn-liquid cta-btn-primary"
          @click="$emit('switch-tab', 'forum')"
        >
          <span>进入创客工作台</span>
          <span class="cta-arrow">→</span>
        </button>
        <span class="cta-note">ONE PERSON COMPANY / COMMERCIAL OS</span>
      </div>
    </div>
  </section>
</template>

<script setup>
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

.cta-block {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  gap: 48px;
  align-items: end;
  padding: 48px 50px;
  border-radius: 22px;
  background: var(--text-primary);
  color: var(--bg-canvas);
}

.cta-eyebrow {
  display: inline-flex;
  margin-bottom: 18px;
  background: transparent !important;
  border-color: rgba(255, 255, 255, 0.24) !important;
  color: rgba(255, 255, 255, 0.62) !important;
}

.cta-title {
  font-family: var(--font-display);
  font-size: clamp(30px, 3.4vw, 44px);
  font-weight: 680;
  line-height: 1.08;
  letter-spacing: -0.055em;
  margin-bottom: 16px;
}

.cta-desc {
  max-width: 620px;
  font-size: 13px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.62);
}

.cta-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.cta-btn-primary {
  width: 100%;
  justify-content: space-between;
  background: var(--bg-canvas) !important;
  color: var(--text-primary) !important;
  border-color: var(--bg-canvas) !important;
  padding: 13px 18px;
  font-size: 13px;
}

.cta-arrow {
  font-family: var(--font-mono);
  font-size: 13px;
}

.cta-btn-secondary {
  width: 100%;
  text-align: left;
  padding: 10px 2px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  cursor: pointer;
}

.cta-btn-secondary:hover {
  color: #fff;
}

.cta-note {
  margin-top: 8px;
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.07em;
  color: rgba(255, 255, 255, 0.38);
}

[data-theme="dark"] .cta-block {
  background: #F4F5F7;
  color: #0A0B0D;
}

[data-theme="dark"] .cta-title {
  color: #0A0B0D;
}

[data-theme="dark"] .cta-desc {
  color: rgba(10, 11, 13, 0.62);
}

[data-theme="dark"] .cta-eyebrow {
  color: rgba(10, 11, 13, 0.55) !important;
  border-color: rgba(10, 11, 13, 0.18) !important;
}

[data-theme="dark"] .cta-btn-primary {
  background: #0A0B0D !important;
  color: #F4F5F7 !important;
  border-color: #0A0B0D !important;
}

[data-theme="dark"] .cta-btn-secondary {
  color: rgba(10, 11, 13, 0.62);
}

@media (max-width: 860px) {
  .cta-block {
    grid-template-columns: 1fr;
    gap: 28px;
    padding: 34px 26px;
  }
}
</style>
