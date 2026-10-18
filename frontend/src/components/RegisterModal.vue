<template>
  <div v-if="visible" class="sheet-modal" @click.self="$emit('close')">
    <div class="sheet-body" style="max-width: 530px; max-height: 90vh; overflow-y: auto;">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: var(--accent-glass); color: var(--accent);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
          </div>
          <div>
            <h3 style="font-size: 17px; font-weight: 600;">创客注册 · 开启超级个体商业之旅</h3>
            <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary);">
              COMMERCIAL ONBOARDING · OPC HUB
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
      <div style="display: flex; background: var(--glass-surface-subtle); padding: 3px; border-radius: var(--radius-sm); border: 1px solid var(--glass-border-subtle); margin-bottom: 14px;">
        <button class="auth-tab-btn" type="button" @click="$emit('switch-to-login')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>
          </svg>
          创客登录
        </button>
        <button class="auth-tab-btn active" type="button">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
          </svg>
          商用入驻注册
        </button>
      </div>

      <!-- Commercial Account Identity Selector -->
      <div style="margin-bottom: 14px;">
        <label style="display: block; font-size: 11.5px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
          入驻身份类型 <span style="color: #ff453a;">*</span>
        </label>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;">
          <div
            class="account-type-card"
            :style="form.account_type === 'MAKER' ? { border: '1px solid var(--accent)', background: 'var(--accent-glass)' } : { border: '1px solid var(--glass-border-subtle)', background: 'var(--glass-surface-subtle)' }"
            style="padding: 8px 6px; border-radius: 8px; cursor: pointer; text-align: center;"
            @click="form.account_type = 'MAKER'"
          >
            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary);">个人创客</div>
            <div style="font-size: 9.5px; color: var(--text-tertiary); margin-top: 2px;">独立开发者/顾问</div>
          </div>
          <div
            class="account-type-card"
            :style="form.account_type === 'OPC' ? { border: '1px solid var(--accent)', background: 'var(--accent-glass)' } : { border: '1px solid var(--glass-border-subtle)', background: 'var(--glass-surface-subtle)' }"
            style="padding: 8px 6px; border-radius: 8px; cursor: pointer; text-align: center;"
            @click="form.account_type = 'OPC'"
          >
            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary);">一人公司 (OPC)</div>
            <div style="font-size: 9.5px; color: var(--text-tertiary); margin-top: 2px;">个体户/工作室</div>
          </div>
          <div
            class="account-type-card"
            :style="form.account_type === 'ENTERPRISE' ? { border: '1px solid var(--accent)', background: 'var(--accent-glass)' } : { border: '1px solid var(--glass-border-subtle)', background: 'var(--glass-surface-subtle)' }"
            style="padding: 8px 6px; border-radius: 8px; cursor: pointer; text-align: center;"
            @click="form.account_type = 'ENTERPRISE'"
          >
            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary);">企业机构</div>
            <div style="font-size: 9.5px; color: var(--text-tertiary); margin-top: 2px;">生态伙伴/企业</div>
          </div>
        </div>
      </div>

      <div style="display: flex; flex-direction: column; gap: 11px; margin-bottom: 16px;">
        <!-- Email Row -->
        <div>
          <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
            创客商用邮箱 <span style="color: #ff453a;">*</span>
          </label>
          <input
            v-model="form.email"
            type="email"
            class="glass-input"
            placeholder="例如: yourname@opchub.cn 或 常用邮箱"
            style="width: 100%; box-sizing: border-box;"
          />
        </div>

        <!-- Anti-Bot Captcha Row -->
        <div style="display: grid; grid-template-columns: 1fr 140px; gap: 10px; align-items: end;">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              人机防刷安全验证 <span style="color: #ff453a;">*</span>
            </label>
            <input
              v-model="form.captcha_code"
              :disabled="captchaVerified"
              class="glass-input"
              :placeholder="captchaVerified ? '✓ 人机验证已通过' : '输入计算结果或字符'"
              style="width: 100%; box-sizing: border-box;"
            />
          </div>
          <div>
            <div
              @click="onCaptchaClick"
              style="height: 38px; border-radius: 8px; overflow: hidden; cursor: pointer; display: flex; align-items: center; justify-content: center; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle);"
              :title="captchaVerified ? '人机验证已通过' : '点击更换验证码'"
            >
              <div v-if="captchaSvg" v-html="captchaSvg" style="display: flex; height: 100%; width: 100%;"></div>
              <span v-else style="font-size: 11px; color: var(--text-tertiary);">加载中...</span>
            </div>
          </div>
        </div>

        <!-- Verification Code Row -->
        <div style="display: grid; grid-template-columns: 1fr 140px; gap: 10px; align-items: end;">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              邮箱验证码 <span style="color: #ff453a;">*</span>
            </label>
            <input
              v-model="form.verification_code"
              class="glass-input"
              placeholder="6 位数字验证码"
              maxlength="6"
              style="width: 100%; box-sizing: border-box; letter-spacing: 2px; font-weight: 600;"
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
              {{ sendingCode ? '发送中...' : (cooldownSeconds > 0 ? `${cooldownSeconds}s 后可重发` : (captchaVerified ? '重新获取' : '获取验证码')) }}
            </button>
          </div>
        </div>

        <!-- Passwords & Strength Meter -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              登录密码 <span style="color: #ff453a;">*</span>
            </label>
            <input
              v-model="form.password"
              type="password"
              class="glass-input"
              placeholder="至少8位字母+数字"
              style="width: 100%; box-sizing: border-box;"
            />
          </div>
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              确认密码 <span style="color: #ff453a;">*</span>
            </label>
            <input
              v-model="form.confirm_password"
              type="password"
              class="glass-input"
              placeholder="再次输入密码"
              style="width: 100%; box-sizing: border-box;"
            />
          </div>
        </div>

        <!-- Dynamic Password Strength Indicator -->
        <div style="margin-top: -2px;">
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; margin-bottom: 4px;">
            <span style="color: var(--text-tertiary);">安全策略：需8位以上包含字母与数字</span>
            <span :style="{ color: pwdStrengthColor, fontWeight: 600 }">{{ pwdStrengthLabel }}</span>
          </div>
          <div style="height: 4px; background: rgba(142, 142, 147, 0.2); border-radius: 2px; overflow: hidden; display: flex; gap: 2px;">
            <div :style="{ flex: 1, background: pwdScore >= 1 ? pwdStrengthColor : 'transparent', transition: 'background 0.3s' }"></div>
            <div :style="{ flex: 1, background: pwdScore >= 2 ? pwdStrengthColor : 'transparent', transition: 'background 0.3s' }"></div>
            <div :style="{ flex: 1, background: pwdScore >= 3 ? pwdStrengthColor : 'transparent', transition: 'background 0.3s' }"></div>
            <div :style="{ flex: 1, background: pwdScore >= 4 ? pwdStrengthColor : 'transparent', transition: 'background 0.3s' }"></div>
          </div>
        </div>

        <!-- Identity Profile Information -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              创客昵称 (选填)
            </label>
            <input
              v-model="form.nickname"
              type="text"
              class="glass-input"
              placeholder="默认取邮箱前缀"
              style="width: 100%; box-sizing: border-box;"
            />
          </div>
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              联系手机 (选填)
            </label>
            <input
              v-model="form.phone"
              type="text"
              class="glass-input"
              placeholder="用于商机与履约通知"
              style="width: 100%; box-sizing: border-box;"
            />
          </div>
        </div>

        <!-- Company Name and Credit Code (when OPC or Enterprise) -->
        <div v-if="form.account_type !== 'MAKER'" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              企业/工作室全称 <span style="color: #ff453a;">*</span>
            </label>
            <input
              v-model="form.company_name"
              type="text"
              class="glass-input"
              placeholder="如：极客视界一人公司"
              style="width: 100%; box-sizing: border-box;"
            />
          </div>
          <div>
            <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary);">
              统一社会信用代码 (选填)
            </label>
            <input
              v-model="form.credit_code"
              type="text"
              class="glass-input"
              placeholder="18位法人/个体工商代码"
              maxlength="18"
              style="width: 100%; box-sizing: border-box; text-transform: uppercase;"
            />
          </div>
        </div>

        <!-- Industry Track Selection -->
        <div>
          <label style="display: block; font-size: 12px; font-weight: 500; margin-bottom: 6px; color: var(--text-secondary);">
            意向业务赛道 (有助于定制工作台)
          </label>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            <span
              v-for="track in tracks"
              :key="track"
              class="track-pill"
              :style="form.industry_track === track ? { background: 'var(--accent-glass)', border: '1px solid var(--accent)', color: 'var(--text-primary)' } : { background: 'var(--glass-surface-subtle)', border: '1px solid var(--glass-border-subtle)', color: 'var(--text-secondary)' }"
              style="font-size: 11px; padding: 3px 9px; border-radius: 12px; cursor: pointer;"
              @click="form.industry_track = track"
            >
              {{ track }}
            </span>
          </div>
        </div>

        <!-- Statutory Compliance Checkbox (Default Unchecked) -->
        <div
          :style="{ border: agreeError ? '1px solid #ff453a' : '1px solid var(--glass-border-subtle)' }"
          style="margin-top: 2px; padding: 8px 10px; border-radius: var(--radius-sm); background: var(--glass-surface-subtle); transition: border 0.3s;"
        >
          <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer; user-select: none;">
            <input
              v-model="form.agreed_terms"
              type="checkbox"
              style="margin-top: 2px; cursor: pointer; accent-color: var(--accent);"
            />
            <span style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.45;">
              我已阅读并完全同意
              <a href="javascript:void(0)" @click.prevent="$emit('open-legal', 'terms')" style="color: var(--accent); text-decoration: none; font-weight: 500;">《用户服务协议》</a>
              与
              <a href="javascript:void(0)" @click.prevent="$emit('open-legal', 'privacy')" style="color: var(--accent); text-decoration: none; font-weight: 500;">《隐私政策与个人信息保护指引》</a>
              ，承诺严格遵循国家法律法规及一人公司合规经营守则。
            </span>
          </label>
        </div>

        <!-- Error Alert -->
        <div
          v-if="errorMessage"
          style="color: #ff453a; font-size: 12px; padding: 6px 10px; background: rgba(255, 69, 58, 0.1); border-radius: var(--radius-sm);"
        >
          {{ errorMessage }}
        </div>
      </div>

      <!-- Submit Actions -->
      <div style="display: flex; gap: 10px; margin-bottom: 14px;">
        <button class="btn-liquid-outline" style="flex: 1; justify-content: center;" @click="$emit('close')">
          取消
        </button>
        <button
          class="btn-liquid"
          style="flex: 1; justify-content: center;"
          :disabled="submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '商用入驻审核与事务落库中...' : '完成商用入驻注册' }}
        </button>
      </div>

      <div style="text-align: center; font-size: 12.5px; color: var(--text-tertiary); border-top: 1px solid var(--glass-border-subtle); padding-top: 12px;">
        已有创客账号？
        <a href="javascript:void(0)" @click="$emit('switch-to-login')" style="color: var(--accent); font-weight: 500; text-decoration: none;">
          直接登录
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  visible: Boolean,
});

const emit = defineEmits(['close', 'switch-to-login', 'open-legal', 'register-success']);

const tracks = [
  'AI 原生应用与智能体',
  '出海 SaaS 与独立开发',
  '跨境电商与数字贸易',
  '智能软硬件与 IoT',
  '咨询与数字创意服务',
];

const form = reactive({
  account_type: 'MAKER',
  company_name: '',
  credit_code: '',
  email: '',
  captcha_code: '',
  verification_code: '',
  password: '',
  confirm_password: '',
  nickname: '',
  phone: '',
  industry_track: 'AI 原生应用与智能体',
  agreed_terms: false,
});

const captchaId = ref('');
const captchaSvg = ref('');
const captchaVerified = ref(false);
const verifiedCaptchaId = ref('');
const sendingCode = ref(false);
const submitting = ref(false);
const errorMessage = ref('');
const agreeError = ref(false);

const cooldownSeconds = ref(0);
let cooldownTimer = null;

// Password strength calculation
const pwdScore = computed(() => {
  const p = form.password;
  if (!p) return 0;
  let score = 0;
  if (p.length >= 8) score++;
  if (/[a-zA-Z]/.test(p) && /\d/.test(p)) score++;
  if (/[^a-zA-Z0-9]/.test(p)) score++;
  if (p.length >= 12) score++;
  return score;
});

const pwdStrengthLabel = computed(() => {
  switch (pwdScore.value) {
    case 0:
      return '未输入';
    case 1:
      return '极弱';
    case 2:
      return '中等';
    case 3:
      return '良好';
    case 4:
      return '强';
    default:
      return '';
  }
});

const pwdStrengthColor = computed(() => {
  switch (pwdScore.value) {
    case 1:
      return '#ff453a';
    case 2:
      return '#ff9f0a';
    case 3:
      return '#30d158';
    case 4:
      return '#0071E3';
    default:
      return '#8e8e93';
  }
});

async function refreshCaptcha() {
  captchaVerified.value = false;
  verifiedCaptchaId.value = '';
  try {
    const res = await dispatchGateway('auth.captcha', {});
    if (res.ok && res.data) {
      captchaId.value = res.data.captcha_id;
      captchaSvg.value = res.data.captcha_svg || res.data.svg;
    }
  } catch (e) {
    console.error('Fetch captcha error', e);
  }
}

function onCaptchaClick() {
  if (captchaVerified.value) return;
  refreshCaptcha();
}

async function handleSendCode() {
  errorMessage.value = '';
  if (!form.email || !form.email.includes('@')) {
    errorMessage.value = '请先输入有效的创客商用邮箱';
    return;
  }

  if (!captchaVerified.value) {
    if (!form.captcha_code) {
      errorMessage.value = '请先输入人机防刷图形验证码';
      return;
    }
    if (!captchaId.value) {
      errorMessage.value = '图形验证码已失效，请点击刷新';
      return;
    }
  }

  sendingCode.value = true;
  try {
    const payload = {
      email: form.email.trim().toLowerCase(),
    };
    if (captchaVerified.value && verifiedCaptchaId.value) {
      payload.captcha_verified = true;
      payload.captcha_id = verifiedCaptchaId.value;
    } else {
      payload.captcha_id = captchaId.value;
      payload.captcha_code = form.captcha_code.trim();
    }

    const res = await dispatchGateway('auth.send-code', payload);
    if (!res.ok) {
      errorMessage.value = res.error || '验证码发送失败';
      if (!captchaVerified.value) {
        refreshCaptcha();
      }
      return;
    }

    captchaVerified.value = true;
    verifiedCaptchaId.value = captchaId.value;

    startCooldown(60);
  } catch (e) {
    errorMessage.value = '网络异常，验证码发送失败';
  } finally {
    sendingCode.value = false;
  }
}

function startCooldown(sec) {
  cooldownSeconds.value = sec;
  clearInterval(cooldownTimer);
  cooldownTimer = setInterval(() => {
    cooldownSeconds.value--;
    if (cooldownSeconds.value <= 0) {
      clearInterval(cooldownTimer);
    }
  }, 1000);
}

async function handleSubmit() {
  errorMessage.value = '';
  agreeError.value = false;

  if (!form.email || !form.email.includes('@')) {
    errorMessage.value = '请输入有效的商用邮箱';
    return;
  }
  if (!form.verification_code || form.verification_code.length !== 6) {
    errorMessage.value = '请输入 6 位邮箱验证码';
    return;
  }
  if (!form.password || form.password.length < 8) {
    errorMessage.value = '密码长度至少需 8 位';
    return;
  }
  if (!/[a-zA-Z]/.test(form.password) || !/\d/.test(form.password)) {
    errorMessage.value = '密码必须同时包含字母与数字';
    return;
  }
  if (form.password !== form.confirm_password) {
    errorMessage.value = '两次输入的密码不一致';
    return;
  }
  if (form.account_type !== 'MAKER' && !form.company_name.trim()) {
    errorMessage.value = '一人公司或企业主体必须填写主体名称';
    return;
  }
  if (!form.agreed_terms) {
    errorMessage.value = '请勾选同意《用户服务协议》与《隐私政策》后继续';
    agreeError.value = true;
    return;
  }

  submitting.value = true;
  try {
    const res = await dispatchGateway('auth.register', {
      email: form.email.trim().toLowerCase(),
      verification_code: form.verification_code.trim(),
      password: form.password,
      account_type: form.account_type,
      company_name: form.company_name ? form.company_name.trim() : null,
      credit_code: form.credit_code ? form.credit_code.trim().toUpperCase() : null,
      nickname: form.nickname ? form.nickname.trim() : null,
      phone: form.phone ? form.phone.trim() : null,
      industry_track: form.industry_track,
      agreed_terms: true,
    });

    if (!res.ok) {
      errorMessage.value = res.error || '入驻注册失败，请检查填写内容';
      return;
    }

    const regData = res.data;
    if (regData && regData.token) {
      localStorage.setItem('opchub_session_token', regData.token);
    }
    emit('register-success', regData);
  } catch (e) {
    errorMessage.value = '网络请求异常，请检查服务可用性';
  } finally {
    submitting.value = false;
  }
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      errorMessage.value = '';
      agreeError.value = false;
      refreshCaptcha();
    }
  }
);

onMounted(() => {
  if (props.visible) {
    refreshCaptcha();
  }
});
</script>
