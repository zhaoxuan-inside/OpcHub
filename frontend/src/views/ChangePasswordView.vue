<template>
  <div class="view-panel change-password-view">
    <header class="cp-header">
      <button type="button" class="btn-liquid-outline cp-back" @click="goBack">
        <OpcIcon name="arrow-right" :size="13" />
        <span>返回</span>
      </button>
      <p class="cp-eyebrow">ACCOUNT SECURITY</p>
      <h1 class="cp-title">修改登录密码</h1>
      <p class="cp-subtitle">
        定期轮换登录密码，保护你的创客账号、商业资料与积分资产。
      </p>
    </header>

    <div class="cp-layout">
      <section class="glass-panel cp-card">
        <div v-if="mustChangePassword" class="cp-banner">
          <OpcIcon name="alert" :size="15" />
          <span>首次登录需完成密码轮换，之后才能进入后端编排等高风险页面。</span>
        </div>

        <div v-if="success" class="cp-success">
          <span class="cp-success-icon"><OpcIcon name="check" :size="18" /></span>
          <div>
            <h3>密码已更新</h3>
            <p>当前会话已续期。其他设备上的旧会话需要重新登录。</p>
            <button type="button" class="btn-liquid cp-success-btn" @click="goBack">返回用户中心</button>
          </div>
        </div>

        <form v-else class="cp-form" @submit.prevent="submit">
          <div class="cp-field">
            <label for="cp-old">当前登录密码</label>
            <input
              id="cp-old"
              v-model="oldPassword"
              type="password"
              class="glass-input"
              autocomplete="current-password"
              placeholder="请输入当前密码"
            />
          </div>

          <div class="cp-field">
            <label for="cp-new">新密码</label>
            <input
              id="cp-new"
              v-model="newPassword"
              type="password"
              class="glass-input"
              autocomplete="new-password"
              placeholder="至少 8 位，建议包含字母、数字与符号"
            />
            <div class="cp-strength">
              <div class="cp-strength-track">
                <span
                  v-for="index in 4"
                  :key="index"
                  class="cp-strength-segment"
                  :class="{ active: index <= strength.score, [`level-${strength.score}`]: true }"
                ></span>
              </div>
              <span class="cp-strength-label">{{ strength.label }}</span>
            </div>
            <ul class="cp-rules">
              <li :class="{ passed: rules.length }">长度不少于 8 位</li>
              <li :class="{ passed: rules.letter }">包含字母</li>
              <li :class="{ passed: rules.digit }">包含数字</li>
              <li :class="{ passed: rules.symbol }">包含符号（建议）</li>
            </ul>
          </div>

          <div class="cp-field">
            <label for="cp-confirm">确认新密码</label>
            <input
              id="cp-confirm"
              v-model="confirmPassword"
              type="password"
              class="glass-input"
              autocomplete="new-password"
              placeholder="再次输入新密码"
            />
            <p v-if="mismatch" class="cp-error">两次输入的新密码不一致</p>
          </div>

          <p v-if="errorMessage" class="cp-error cp-error-block">{{ errorMessage }}</p>

          <div class="cp-actions">
            <button type="button" class="btn-liquid-outline" @click="goBack">取消</button>
            <button type="submit" class="btn-liquid" :disabled="!canSubmit || isSubmitting">
              {{ isSubmitting ? '提交中…' : '确认修改密码' }}
            </button>
          </div>
        </form>
      </section>

      <aside class="cp-aside">
        <h3>安全建议</h3>
        <ul>
          <li>不要与其他平台使用相同密码。</li>
          <li>不要将密码通过聊天工具或邮件发送给他人。</li>
          <li>修改成功后，建议在常用设备上重新登录一次。</li>
          <li>如怀疑账号泄露，请立即修改密码并联系平台运营。</li>
        </ul>
        <div class="cp-note">
          密码仅用于登录校验，平台不会以明文形式存储或展示你的密码。
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['toast', 'navigate', 'session-updated']);

const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const isSubmitting = ref(false);
const success = ref(false);
const errorMessage = ref('');

const mustChangePassword = computed(() => Boolean(props.userSession?.must_change_password));

const rules = computed(() => ({
  length: newPassword.value.length >= 8,
  letter: /[A-Za-z]/.test(newPassword.value),
  digit: /\d/.test(newPassword.value),
  symbol: /[^A-Za-z0-9]/.test(newPassword.value),
}));

const strength = computed(() => {
  const value = newPassword.value;
  if (!value) return { score: 0, label: '未输入' };
  let score = 0;
  if (value.length >= 8) score += 1;
  if (value.length >= 12) score += 1;
  if (/[A-Za-z]/.test(value) && /\d/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value)) score += 1;
  score = Math.min(4, score);
  return {
    score,
    label: ['过弱', '较弱', '一般', '较强', '很强'][score] || '未输入',
  };
});

const mismatch = computed(
  () => Boolean(confirmPassword.value) && confirmPassword.value !== newPassword.value
);

const canSubmit = computed(
  () =>
    Boolean(oldPassword.value)
    && newPassword.value.length >= 8
    && confirmPassword.value === newPassword.value
    && newPassword.value !== oldPassword.value
);

function goBack() {
  emit('navigate', 'profile');
}

async function submit() {
  if (!canSubmit.value || isSubmitting.value) return;
  errorMessage.value = '';
  isSubmitting.value = true;
  try {
    const res = await dispatchGateway('auth.change_password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    });
    if (!res.ok) {
      errorMessage.value = res.error || '密码修改失败，请核对当前密码后重试。';
      return;
    }
    if (res.data?.token) {
      try {
        localStorage.setItem('opchub_session_token', res.data.token);
      } catch (e) {
        // localStorage 不可用时不影响服务端已完成的密码轮换
      }
    }
    emit('session-updated', {
      ...(props.userSession || {}),
      ...(res.data || {}),
      must_change_password: false,
    });
    oldPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    success.value = true;
    emit('toast', {
      title: '密码已更新',
      message: '登录密码轮换成功，当前会话已续期。',
      type: 'SUCCESS',
    });
  } catch (e) {
    errorMessage.value = '账号服务暂时不可用，请稍后重试。';
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.change-password-view {
  width: 100%;
  max-width: 1040px;
  margin: 0 auto;
  padding-bottom: 64px;
}

.cp-header {
  margin-bottom: 28px;
}

.cp-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 6px 14px;
  margin-bottom: 22px;
}

.cp-back :deep(svg) {
  transform: rotate(180deg);
}

.cp-eyebrow {
  font-family: var(--font-mono, 'SF Mono', Menlo, monospace);
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--text-tertiary);
  margin: 0 0 8px;
}

.cp-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.cp-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

.cp-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(240px, 0.9fr);
  gap: 20px;
  align-items: start;
}

.cp-card {
  padding: 28px;
}

.cp-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  margin-bottom: 20px;
  border-radius: var(--radius-md);
  background: var(--status-warning-soft);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.cp-banner :deep(svg) {
  color: var(--status-warning);
  flex-shrink: 0;
  margin-top: 1px;
}

.cp-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.cp-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.cp-field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.cp-field .glass-input {
  font-size: 13px;
  padding: 10px 12px;
}

.cp-strength {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 2px;
}

.cp-strength-track {
  display: flex;
  gap: 4px;
  flex: 1;
}

.cp-strength-segment {
  height: 3px;
  flex: 1;
  border-radius: 999px;
  background: var(--glass-border-subtle);
  transition: background 0.2s ease;
}

.cp-strength-segment.active.level-1 {
  background: var(--status-danger);
}

.cp-strength-segment.active.level-2 {
  background: var(--status-warning);
}

.cp-strength-segment.active.level-3 {
  background: var(--accent);
}

.cp-strength-segment.active.level-4 {
  background: var(--status-success);
}

.cp-strength-label {
  font-size: 10.5px;
  color: var(--text-tertiary);
  flex-shrink: 0;
  min-width: 28px;
}

.cp-rules {
  list-style: none;
  padding: 0;
  margin: 2px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
}

.cp-rules li {
  font-size: 10.5px;
  color: var(--text-tertiary);
  position: relative;
  padding-left: 12px;
}

.cp-rules li::before {
  content: '·';
  position: absolute;
  left: 0;
  color: var(--text-tertiary);
}

.cp-rules li.passed {
  color: var(--text-secondary);
}

.cp-rules li.passed::before {
  content: '✓';
  color: var(--status-success);
}

.cp-error {
  font-size: 11px;
  color: var(--status-danger);
  margin: 0;
  line-height: 1.5;
}

.cp-error-block {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--status-danger-soft);
}

.cp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
}

.cp-actions .btn-liquid,
.cp-actions .btn-liquid-outline {
  font-size: 12.5px;
  padding: 7px 20px;
}

.cp-success {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 8px 0;
}

.cp-success-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--status-success-soft);
  color: var(--status-success);
  flex-shrink: 0;
}

.cp-success h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 2px 0 6px;
}

.cp-success p {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 16px;
}

.cp-success-btn {
  font-size: 12.5px;
  padding: 7px 18px;
}

.cp-aside {
  padding: 24px;
  border-radius: var(--radius-lg);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.cp-aside h3 {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 14px;
}

.cp-aside ul {
  list-style: none;
  padding: 0;
  margin: 0 0 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cp-aside li {
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-secondary);
  padding-left: 12px;
  position: relative;
}

.cp-aside li::before {
  content: '·';
  position: absolute;
  left: 0;
  color: var(--text-tertiary);
}

.cp-note {
  font-size: 10.5px;
  line-height: 1.7;
  color: var(--text-tertiary);
  padding-top: 16px;
  border-top: 1px solid var(--glass-border-subtle);
}

@media (max-width: 820px) {
  .cp-layout {
    grid-template-columns: 1fr;
  }
}
</style>
