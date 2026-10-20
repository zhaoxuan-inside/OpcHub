<template>
  <div style="min-height: 100vh; position: relative; display: flex; flex-direction: column;">
    <!-- Ambient Fluid Background Orbs -->
    <div class="ambient-container">
      <div class="ambient-orb orb-1"></div>
      <div class="ambient-orb orb-2"></div>
      <div class="ambient-orb orb-3"></div>
    </div>

    <!-- Sticky Liquid Navigation -->
    <Navbar
      :active-tab="activeTab"
      :user-session="userSession"
      :current-role="currentRole"
      :is-dark="isDark"
      @switch-tab="handleSwitchTab"
      @toggle-role="handleToggleRole"
      @toggle-theme="handleToggleTheme"
      @open-login="showLoginModal = true"
      @open-profile="handleSwitchTab('profile')"
    />

    <!-- Main View Container -->
    <main>
      <!-- 1. Home View: Accessible to all; STRICTLY the ONLY view for unauthenticated visitors -->
      <HomeView
        v-if="!userSession || activeTab === 'home'"
        :user-session="userSession"
        @open-login="showLoginModal = true"
        @open-register="showRegisterModal = true"
        @switch-tab="handleSwitchTab"
        @toast="showToast"
      />

      <!-- 2. Authenticated Maker / User Views -->
      <template v-else-if="userSession && currentRole !== 'ADMIN'">
        <ForumView
          v-if="activeTab === 'forum'"
          :user-session="userSession"
          @open-register="showRegisterModal = true"
          @toast="showToast"
        />
        <ShowcaseView
          v-else-if="activeTab === 'product'"
          @open-register="showRegisterModal = true"
          @toast="showToast"
        />
        <PolicyView
          v-else-if="activeTab === 'policy'"
          @toast="showToast"
        />
        <DemandsView
          v-else-if="activeTab === 'demand'"
          @open-register="showRegisterModal = true"
          @toast="showToast"
        />
        <SopView
          v-else-if="activeTab === 'sop'"
          @toast="showToast"
        />
        <PerksView
          v-else-if="activeTab === 'perks'"
          @open-register="showRegisterModal = true"
          @toast="showToast"
        />
        <ComplianceView
          v-else-if="activeTab === 'compliance'"
          @switch-tab="handleSwitchTab"
        />
        <ProfileView
          v-else-if="activeTab === 'profile'"
          @logout="handleLogout"
          @toast="showToast"
        />
      </template>

      <!-- 3. Authenticated Admin / Governance Views -->
      <template v-else-if="userSession && currentRole === 'ADMIN'">
        <ConsoleView
          v-if="activeTab === 'backend-orch' || activeTab === 'console' || activeTab === 'frontend-orch'"
          @toast="showToast"
        />
        <OpsView
          v-else-if="activeTab === 'ops' || activeTab === 'moderation'"
        />
        <ProfileView
          v-else-if="activeTab === 'profile'"
          @logout="handleLogout"
          @toast="showToast"
        />
      </template>
    </main>

    <!-- Modals -->
    <RegisterModal
      :visible="showRegisterModal"
      @close="showRegisterModal = false"
      @switch-to-login="switchToLogin"
      @open-legal="openLegalModal"
      @register-success="onRegisterSuccess"
    />

    <LoginModal
      :visible="showLoginModal"
      @close="showLoginModal = false"
      @switch-to-register="switchToRegister"
      @login-success="onLoginSuccess"
    />

    <LegalModal
      :visible="showLegalModal"
      :initial-tab="legalTab"
      @close="showLegalModal = false"
      @agree="onLegalAgreed"
    />

    <!-- Liquid Specular Notice Capsule -->
    <transition name="toast-slide">
      <div
        v-if="notice"
        :class="['notice-capsule', `notice-${notice.type ? notice.type.toLowerCase() : 'info'}`]"
        style="position: fixed; bottom: 32px; right: 32px; z-index: 999999; padding: 14px 18px; border-radius: var(--radius-md); background: var(--glass-surface-solid); border: 1px solid var(--glass-border); box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22), var(--glass-specular); backdrop-filter: var(--blur-strength); -webkit-backdrop-filter: var(--blur-strength); max-width: 440px; min-width: 320px; display: flex; align-items: flex-start; gap: 12px;"
      >
        <!-- Icon Badge -->
        <div
          :style="{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            background: notice.type === 'SUCCESS' ? 'rgba(52, 199, 89, 0.14)' : (notice.type === 'DANGER' || notice.type === 'ERROR' ? 'rgba(255, 59, 48, 0.14)' : (notice.type === 'WARN' ? 'rgba(255, 149, 0, 0.14)' : 'rgba(0, 113, 227, 0.14)')),
            color: notice.type === 'SUCCESS' ? '#34C759' : (notice.type === 'DANGER' || notice.type === 'ERROR' ? '#FF3B30' : (notice.type === 'WARN' ? '#FF9500' : 'var(--accent)')),
            fontWeight: '700',
            fontSize: '14px',
          }"
        >
          <span v-if="notice.type === 'SUCCESS'">✓</span>
          <span v-else-if="notice.type === 'DANGER' || notice.type === 'ERROR'">✕</span>
          <span v-else-if="notice.type === 'WARN'">⚠</span>
          <span v-else>ℹ</span>
        </div>

        <div style="flex: 1; min-width: 0;">
          <div style="font-weight: 600; font-size: 13.5px; color: var(--text-primary); margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center;">
            <span>{{ notice.title }}</span>
            <button
              @click="dismissNotice"
              style="border: none; background: transparent; cursor: pointer; color: var(--text-tertiary); font-size: 14px; line-height: 1; padding: 2px 4px; border-radius: 4px; transition: color 0.15s ease;"
              title="关闭通知"
            >
              ✕
            </button>
          </div>
          <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; word-break: break-word;">
            {{ notice.message }}
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import Navbar from '@/components/Navbar.vue';
import RegisterModal from '@/components/RegisterModal.vue';
import LoginModal from '@/components/LoginModal.vue';
import LegalModal from '@/components/LegalModal.vue';
import HomeView from '@/views/HomeView.vue';
import ForumView from '@/views/ForumView.vue';
import ShowcaseView from '@/views/ShowcaseView.vue';
import PolicyView from '@/views/PolicyView.vue';
import DemandsView from '@/views/DemandsView.vue';
import SopView from '@/views/SopView.vue';
import PerksView from '@/views/PerksView.vue';
import ComplianceView from '@/views/ComplianceView.vue';
import ConsoleView from '@/views/ConsoleView.vue';
import OpsView from '@/views/OpsView.vue';
import ProfileView from '@/views/ProfileView.vue';
import { dispatchGateway } from '@/api/gateway';
import { activeNotice, notify, dismissNotice } from '@/api/notification';

const MAKER_TABS = ['home', 'forum', 'product', 'policy', 'demand', 'sop', 'perks', 'compliance', 'profile'];
const ADMIN_TABS = ['home', 'backend-orch', 'console', 'frontend-orch', 'ops', 'moderation', 'profile'];

function getInitialRole() {
  const saved = localStorage.getItem('opchub_current_role');
  if (saved === 'ADMIN' || saved === 'MAKER') return saved;
  return 'MAKER';
}

function getInitialTab() {
  const rawHash = window.location.hash.replace(/^#\/?/, '').trim();
  const hash = rawHash.split('?')[0];
  if (hash && (MAKER_TABS.includes(hash) || ADMIN_TABS.includes(hash))) {
    return hash;
  }
  const saved = localStorage.getItem('opchub_active_tab');
  if (saved && (MAKER_TABS.includes(saved) || ADMIN_TABS.includes(saved))) {
    return saved;
  }
  return 'home';
}

function getInitialUserSession() {
  try {
    const token = localStorage.getItem('opchub_session_token');
    if (!token) return null;
    const raw = localStorage.getItem('opchub_user_session');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

const activeTab = ref('home');
const initialTab = getInitialTab();
if (initialTab && initialTab !== 'home') {
  activeTab.value = initialTab;
}
const currentRole = ref(getInitialRole());
const isDark = ref(false);
const userSession = ref(getInitialUserSession());

const showRegisterModal = ref(false);
const showLoginModal = ref(false);
const showLegalModal = ref(false);
const legalTab = ref('terms');

const notice = activeNotice;

function handleSwitchTab(tab) {
  if (!userSession.value && tab !== 'home') {
    showToast({
      title: '需登录创客账号',
      message: '未登录用户仅限浏览平台宣传首页。请登录或入驻后进入创客工作台。',
      type: 'INFO',
    });
    showLoginModal.value = true;
    return;
  }
  activeTab.value = tab;
  localStorage.setItem('opchub_active_tab', tab);
  if (window.location.hash.replace(/^#\/?/, '') !== tab) {
    window.location.hash = tab;
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleToggleRole() {
  if (!userSession.value) {
    showToast({
      title: '需管理员登录',
      message: '管理治理视角仅限授权管理员登录后进入。',
      type: 'INFO',
    });
    showLoginModal.value = true;
    return;
  }
  if (userSession.value.role !== 'ADMIN' && currentRole.value === 'MAKER') {
    showToast({
      title: '权限不足',
      message: '管理治理视角仅限授权管理员登录后进入。',
      type: 'WARN',
    });
    return;
  }
  if (currentRole.value === 'MAKER') {
    currentRole.value = 'ADMIN';
    localStorage.setItem('opchub_current_role', 'ADMIN');
    handleSwitchTab('ops');
    showToast({
      title: '视角已切换',
      message: '当前已切换至【管理治理视角 (Admin Governance)】，展示后端微内核编排与全域运营大盘。',
      type: 'INFO',
    });
  } else {
    currentRole.value = 'MAKER';
    localStorage.setItem('opchub_current_role', 'MAKER');
    handleSwitchTab('home');
    showToast({
      title: '视角已切换',
      message: '当前已切换回【创客工作台视角 (Maker OS)】。',
      type: 'INFO',
    });
  }
}

function handleLogout() {
  localStorage.removeItem('opchub_session_token');
  localStorage.removeItem('opchub_user_session');
  localStorage.removeItem('opchub_active_tab');
  localStorage.removeItem('opchub_current_role');
  userSession.value = null;
  activeTab.value = 'home';
  currentRole.value = 'MAKER';
  if (window.location.hash) {
    history.replaceState(null, '', window.location.pathname);
  }
  showToast({
    title: '已退出登录',
    message: '您已安全退出创客登录，已返回平台宣传首页。',
    type: 'INFO',
  });
}

function handleToggleTheme() {
  isDark.value = !isDark.value;
  if (isDark.value) {
    document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('opchub_theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
    localStorage.setItem('opchub_theme', 'light');
  }
}

function switchToLogin() {
  showRegisterModal.value = false;
  showLoginModal.value = true;
}

function switchToRegister() {
  showLoginModal.value = false;
  showRegisterModal.value = true;
}

function openLegalModal(tab) {
  legalTab.value = tab;
  showLegalModal.value = true;
}

function onLegalAgreed() {
  showToast({
    title: '协议已确认',
    message: '您已完整阅读并同意《用户服务协议》与《隐私政策》！',
    type: 'INFO',
  });
}

function onRegisterSuccess(data) {
  showRegisterModal.value = false;
  userSession.value = data;
  localStorage.setItem('opchub_user_session', JSON.stringify(data));
  currentRole.value = 'MAKER';
  localStorage.setItem('opchub_current_role', 'MAKER');
  handleSwitchTab('profile');
  showToast({
    title: '商用入驻成功',
    message: `恭喜创客 ${data.email}，已完成商用认证并持久化落库 PostgreSQL 18！`,
    type: 'SUCCESS',
  });
}

function onLoginSuccess(data) {
  showLoginModal.value = false;
  userSession.value = data;
  localStorage.setItem('opchub_user_session', JSON.stringify(data));
  const role = data.role || (data.user && data.user.role) || 'MAKER';
  if (role === 'ADMIN') {
    const savedRole = localStorage.getItem('opchub_current_role');
    currentRole.value = (savedRole === 'MAKER' || savedRole === 'ADMIN') ? savedRole : 'ADMIN';
  } else {
    currentRole.value = 'MAKER';
  }
  localStorage.setItem('opchub_current_role', currentRole.value);

  // 登录后若在 home 默认推荐主入口，若已经在其他页面则保持当前页面
  if (activeTab.value === 'home') {
    const defaultTab = currentRole.value === 'ADMIN' ? 'ops' : 'forum';
    handleSwitchTab(defaultTab);
  } else {
    handleSwitchTab(activeTab.value);
  }
  showToast({
    title: '登录成功',
    message: `欢迎回来，${data.nickname || data.email}！`,
    type: 'SUCCESS',
  });
}

function showToast({ title, message, type = 'INFO', duration = 4500 }) {
  notify({ title, message, type, duration });
}

async function checkSession() {
  const token = localStorage.getItem('opchub_session_token');
  if (token) {
    try {
      const res = await dispatchGateway('auth.session', {}, { silent: true });
      if (res.ok && res.data && (res.data.authenticated || res.data.valid)) {
        const u = res.data.user || res.data;
        userSession.value = u;
        localStorage.setItem('opchub_user_session', JSON.stringify(u));

        // 维持当前页面模式，禁止刷新自动改切视角模式
        const savedRole = localStorage.getItem('opchub_current_role');
        if (u.role === 'ADMIN') {
          if (savedRole === 'MAKER' || savedRole === 'ADMIN') {
            currentRole.value = savedRole;
          } else {
            currentRole.value = 'ADMIN';
            localStorage.setItem('opchub_current_role', 'ADMIN');
          }
        } else {
          currentRole.value = 'MAKER';
          localStorage.setItem('opchub_current_role', 'MAKER');
        }

        // 保持当前页面：检查当前 tab 是否与模式兼容，保持所在页面
        const currentTab = activeTab.value;
        if (currentRole.value === 'ADMIN' && !ADMIN_TABS.includes(currentTab)) {
          if (MAKER_TABS.includes(currentTab) && currentTab !== 'home') {
            currentRole.value = 'MAKER';
            localStorage.setItem('opchub_current_role', 'MAKER');
          }
        } else if (currentRole.value !== 'ADMIN' && !MAKER_TABS.includes(currentTab)) {
          if (ADMIN_TABS.includes(currentTab)) {
            if (u.role === 'ADMIN') {
              currentRole.value = 'ADMIN';
              localStorage.setItem('opchub_current_role', 'ADMIN');
            } else {
              activeTab.value = 'home';
              localStorage.setItem('opchub_active_tab', 'home');
              if (window.location.hash) {
                history.replaceState(null, '', window.location.pathname);
              }
            }
          }
        }
      } else if (res.statusCode === 401 || (res.data && res.data.valid === false)) {
        localStorage.removeItem('opchub_session_token');
        localStorage.removeItem('opchub_user_session');
        localStorage.removeItem('opchub_active_tab');
        localStorage.removeItem('opchub_current_role');
        userSession.value = null;
        activeTab.value = 'home';
        currentRole.value = 'MAKER';
        if (window.location.hash) {
          history.replaceState(null, '', window.location.pathname);
        }
      }
    } catch (e) {
      console.warn('Session check fallback', e);
    }
  } else {
    userSession.value = null;
    activeTab.value = 'home';
    currentRole.value = 'MAKER';
    if (window.location.hash) {
      history.replaceState(null, '', window.location.pathname);
    }
  }
}

function onHashChange() {
  const rawHash = window.location.hash.replace(/^#\/?/, '').trim();
  const hash = rawHash.split('?')[0];
  if (hash && (MAKER_TABS.includes(hash) || ADMIN_TABS.includes(hash))) {
    if (activeTab.value !== hash) {
      if (!userSession.value && hash !== 'home') {
        activeTab.value = 'home';
        if (window.location.hash) {
          history.replaceState(null, '', window.location.pathname);
        }
        showLoginModal.value = true;
      } else {
        activeTab.value = hash;
        localStorage.setItem('opchub_active_tab', hash);
      }
    }
  }
}

onMounted(() => {
  const savedTheme = localStorage.getItem('opchub_theme');
  if (savedTheme === 'dark') {
    isDark.value = true;
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  window.addEventListener('hashchange', onHashChange);
  if (activeTab.value && activeTab.value !== 'home' && !window.location.hash) {
    window.location.hash = activeTab.value;
  }
  checkSession();
});

onUnmounted(() => {
  window.removeEventListener('hashchange', onHashChange);
});
</script>

<style scoped>
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-slide-enter-from {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
}

.toast-slide-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.97);
}

.notice-capsule {
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

.notice-error {
  border-left: 4px solid #FF3B30 !important;
}

.notice-success {
  border-left: 4px solid #34C759 !important;
}

.notice-warn {
  border-left: 4px solid #FF9500 !important;
}

.notice-info {
  border-left: 4px solid var(--accent) !important;
}
</style>
