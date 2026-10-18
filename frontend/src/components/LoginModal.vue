<template>
  <div v-if="visible" class="sheet-modal" @click.self="$emit('close')">
    <div class="sheet-body" style="max-width: 440px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: var(--accent-glass); color: var(--accent);">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
              <polyline points="10 17 15 12 10 7"/>
              <line x1="15" y1="12" x2="3" y2="12"/>
            </svg>
          </div>
          <div>
            <h3 style="font-size: 17px; font-weight: 600;">创客登录 · OpcHub</h3>
            <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary);">
              MAKER SESSION AUTHENTICATION
            </div>
          </div>
        </div>
        <button class="btn-liquid-outline" style="padding: 4px 8px;" @click="$emit('close')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Segmented Auth Mode Switcher -->
      <div style="display: flex; background: var(--glass-surface-subtle); padding: 3px; border-radius: var(--radius-sm); border: 1px solid var(--glass-border-subtle); margin-bottom: 16px;">
        <button class="auth-tab-btn active" type="button">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>
          </svg>
          创客登录
        </button>
        <button class="auth-tab-btn" type="button" @click="$emit('switch-to-register')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
          </svg>
          免费注册
        </button>
      </div>

      <div style="display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px;">
        <div>
          <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
            登录邮箱
          </label>
          <input
            v-model="email"
            type="email"
            class="glass-input"
            placeholder="maker@opchub.cn 或 您的注册邮箱"
            style="width: 100%; box-sizing: border-box;"
          />
        </div>

        <div>
          <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
            登录密码
          </label>
          <input
            v-model="password"
            type="password"
            class="glass-input"
            placeholder="输入密码"
            style="width: 100%; box-sizing: border-box;"
            @keyup.enter="handleLogin"
          />
        </div>

        <div
          v-if="errorMessage"
          style="color: #ff453a; font-size: 12px; padding: 6px 10px; background: rgba(255, 69, 58, 0.1); border-radius: var(--radius-sm);"
        >
          {{ errorMessage }}
        </div>
      </div>

      <div style="display: flex; gap: 10px; margin-bottom: 16px;">
        <button class="btn-liquid-outline" style="flex: 1; justify-content: center;" @click="$emit('close')">
          取消
        </button>
        <button class="btn-liquid" style="flex: 1; justify-content: center;" :disabled="loading" @click="handleLogin">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </div>

      <div style="text-align: center; font-size: 12.5px; color: var(--text-tertiary); border-top: 1px solid var(--glass-border-subtle); padding-top: 12px;">
        还没有创客账号？
        <a href="javascript:void(0)" @click="$emit('switch-to-register')" style="color: var(--accent); font-weight: 500; text-decoration: none;">
          立即免费注册邮箱账号
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';

defineProps({
  visible: Boolean,
});

const emit = defineEmits(['close', 'switch-to-register', 'login-success']);

const email = ref('');
const password = ref('');
const errorMessage = ref('');
const loading = ref(false);

async function handleLogin() {
  errorMessage.value = '';
  if (!email.value || !password.value) {
    errorMessage.value = '请输入邮箱和密码';
    return;
  }

  loading.value = true;
  try {
    const res = await dispatchGateway('auth.login', {
      email: email.value.trim().toLowerCase(),
      password: password.value,
    });

    if (!res.ok) {
      errorMessage.value = res.error || '登录鉴权失败，请检查账号密码';
      return;
    }

    const authData = res.data;
    localStorage.setItem('opchub_session_token', authData.token);
    emit('login-success', authData);
  } catch (e) {
    errorMessage.value = '网络请求异常，请稍后再试';
  } finally {
    loading.value = false;
  }
}
</script>
