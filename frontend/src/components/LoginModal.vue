<template>
  <div v-if="visible" class="sheet-modal" @click.self="$emit('close')">
    <div class="sheet-body" style="max-width: 440px;">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <BrandLogo :size="32" />
          <div>
            <h3 style="font-size: 17px; font-weight: 600;">创客登录 · 晨昏线外</h3>
            <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary);">
              BEYOND TERMINATOR // AUTH
            </div>
          </div>
        </div>
        <button class="btn-liquid-outline" style="padding: 4px 8px;" @click="$emit('close')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Segmented Auth Mode Switcher (Login vs Register) -->
      <div style="display: flex; background: var(--glass-surface-subtle); padding: 3px; border-radius: var(--radius-sm); border: 1px solid var(--glass-border-subtle); margin-bottom: 14px;">
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

      <!-- Login Method Switcher (Account+Pwd / Email+Code / Email+Pwd) -->
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; background: var(--glass-surface-subtle); padding: 3px; border-radius: var(--radius-sm); border: 1px solid var(--glass-border-subtle); margin-bottom: 16px; gap: 4px;">
        <button
          type="button"
          :class="['login-mode-tab', { active: loginMode === 'account_password' }]"
          @click="switchLoginMode('account_password')"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
          账号密码
        </button>
        <button
          type="button"
          :class="['login-mode-tab', { active: loginMode === 'email_code' }]"
          @click="switchLoginMode('email_code')"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
          </svg>
          邮箱验证码
        </button>
        <button
          type="button"
          :class="['login-mode-tab', { active: loginMode === 'email_password' }]"
          @click="switchLoginMode('email_password')"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          邮箱密码
        </button>
      </div>

      <!-- Form Fields -->
      <div style="display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px;">
        <!-- Mode 1: 账号+密码 -->
        <template v-if="loginMode === 'account_password'">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
              创客账号
            </label>
            <input
              v-model="account"
              type="text"
              class="glass-input"
              placeholder="请输入用户名、账号或注册邮箱"
              style="width: 100%; box-sizing: border-box;"
              @keyup.enter="handleLogin"
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
              placeholder="请输入密码"
              style="width: 100%; box-sizing: border-box;"
              @keyup.enter="handleLogin"
            />
          </div>
        </template>

        <!-- Mode 2: 邮箱+验证码 -->
        <template v-else-if="loginMode === 'email_code'">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
              创客邮箱
            </label>
            <input
              v-model="email"
              type="email"
              class="glass-input"
              placeholder="请输入您的注册邮箱"
              style="width: 100%; box-sizing: border-box;"
            />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 130px; gap: 10px; align-items: end;">
            <div>
              <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
                邮箱验证码
              </label>
              <input
                v-model="verificationCode"
                type="text"
                maxlength="6"
                class="glass-input"
                placeholder="6 位验证码"
                style="width: 100%; box-sizing: border-box; letter-spacing: 2px; font-weight: 600;"
                @keyup.enter="handleLogin"
              />
            </div>
            <div>
              <button
                type="button"
                class="btn-liquid-outline"
                :disabled="sendingCode || cooldownSeconds > 0"
                @click="handleSendCode"
                style="width: 100%; height: 38px; justify-content: center; font-size: 12px; white-space: nowrap;"
              >
                {{ sendingCode ? '发送中...' : (cooldownSeconds > 0 ? `${cooldownSeconds}s 后重发` : '获取验证码') }}
              </button>
            </div>
          </div>

          <div
            v-if="codeTip"
            style="color: var(--accent); font-size: 12px; padding: 6px 10px; background: var(--accent-glass); border-radius: var(--radius-sm); border: 1px solid rgba(0, 113, 227, 0.15);"
          >
            {{ codeTip }}
            <a
              v-if="mockCode"
              href="javascript:void(0)"
              @click="verificationCode = mockCode"
              style="margin-left: 8px; color: var(--accent); font-weight: 600; text-decoration: underline;"
            >
              一键填入
            </a>
          </div>
        </template>

        <!-- Mode 3: 邮箱+密码 -->
        <template v-else-if="loginMode === 'email_password'">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
              创客邮箱
            </label>
            <input
              v-model="email"
              type="email"
              class="glass-input"
              placeholder="请输入您的注册邮箱"
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
              placeholder="请输入密码"
              style="width: 100%; box-sizing: border-box;"
              @keyup.enter="handleLogin"
            />
          </div>
        </template>

        <!-- Error Feedback -->
        <div
          v-if="errorMessage"
          style="color: #ff453a; font-size: 12px; padding: 6px 10px; background: rgba(255, 69, 58, 0.1); border-radius: var(--radius-sm);"
        >
          {{ errorMessage }}
        </div>
      </div>

      <!-- Action Buttons -->
      <div style="display: flex; gap: 10px; margin-bottom: 16px;">
        <button class="btn-liquid-outline" style="flex: 1; justify-content: center;" @click="$emit('close')">
          取消
        </button>
        <button class="btn-liquid" style="flex: 1; justify-content: center;" :disabled="loading" @click="handleLogin">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </div>

      <!-- Switch to Register Link -->
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
import { ref, onUnmounted } from 'vue';
import BrandLogo from './BrandLogo.vue';
import { dispatchGateway } from '@/api/gateway';

defineProps({
  visible: Boolean,
});

const emit = defineEmits(['close', 'switch-to-register', 'login-success']);

// Login modes: 'account_password' | 'email_code' | 'email_password'
const loginMode = ref('account_password');

// Input fields
const account = ref('');
const email = ref('');
const password = ref('');
const verificationCode = ref('');

// Statuses
const errorMessage = ref('');
const codeTip = ref('');
const mockCode = ref('');
const loading = ref(false);
const sendingCode = ref(false);
const cooldownSeconds = ref(0);
let cooldownTimer = null;

function switchLoginMode(mode) {
  loginMode.value = mode;
  errorMessage.value = '';
}

async function handleSendCode() {
  errorMessage.value = '';
  codeTip.value = '';
  mockCode.value = '';

  const cleanEmail = email.value.trim().toLowerCase();
  if (!cleanEmail) {
    errorMessage.value = '请输入用于登录的创客邮箱';
    return;
  }
  if (!cleanEmail.includes('@') || !cleanEmail.includes('.')) {
    errorMessage.value = '邮箱格式不正确，请输入有效的邮箱地址';
    return;
  }

  sendingCode.value = true;
  try {
    const res = await dispatchGateway('auth.send-code', {
      email: cleanEmail,
    });

    if (!res.ok) {
      errorMessage.value = res.error || '验证码发送失败，请稍后再试';
      return;
    }

    const payload = res.data || {};
    codeTip.value = payload.message || '验证码已发送至您的邮箱，5分钟内有效';
    if (payload.mock_code) {
      mockCode.value = payload.mock_code;
    }

    // Start 60s cooldown timer
    cooldownSeconds.value = payload.cooldown_seconds || 60;
    if (cooldownTimer) clearInterval(cooldownTimer);
    cooldownTimer = setInterval(() => {
      cooldownSeconds.value--;
      if (cooldownSeconds.value <= 0) {
        clearInterval(cooldownTimer);
        cooldownTimer = null;
      }
    }, 1000);
  } catch (e) {
    errorMessage.value = '网络请求异常，无法发送验证码';
  } finally {
    sendingCode.value = false;
  }
}

async function handleLogin() {
  errorMessage.value = '';

  const payload = {
    login_type: loginMode.value,
  };

  if (loginMode.value === 'account_password') {
    if (!account.value.trim()) {
      errorMessage.value = '请输入创客账号、用户名或邮箱';
      return;
    }
    if (!password.value) {
      errorMessage.value = '请输入登录密码';
      return;
    }
    payload.account = account.value.trim();
    payload.password = password.value;
  } else if (loginMode.value === 'email_code') {
    if (!email.value.trim()) {
      errorMessage.value = '请输入登录邮箱';
      return;
    }
    if (!verificationCode.value.trim()) {
      errorMessage.value = '请输入 6 位邮箱验证码';
      return;
    }
    payload.email = email.value.trim().toLowerCase();
    payload.code = verificationCode.value.trim();
  } else {
    // email_password
    if (!email.value.trim()) {
      errorMessage.value = '请输入登录邮箱';
      return;
    }
    if (!password.value) {
      errorMessage.value = '请输入登录密码';
      return;
    }
    payload.email = email.value.trim().toLowerCase();
    payload.password = password.value;
  }

  loading.value = true;
  try {
    const res = await dispatchGateway('auth.login', payload);

    if (!res.ok) {
      errorMessage.value = res.error || '登录鉴权失败，请检查登录信息';
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

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer);
  }
});
</script>

<style scoped>
.login-mode-tab {
  padding: 6px 8px;
  font-size: 11.5px;
  font-weight: 500;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  white-space: nowrap;
}

.login-mode-tab.active {
  background: var(--glass-surface);
  color: var(--accent);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.login-mode-tab:hover:not(.active) {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.35);
}
</style>
