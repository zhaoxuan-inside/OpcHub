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
      <!-- Maker / User Views -->
      <HomeView
        v-if="activeTab === 'home'"
        @switch-tab="handleSwitchTab"
        @open-profile="handleSwitchTab('profile')"
      />
      <ForumView
        v-else-if="activeTab === 'forum'"
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

      <!-- Admin / Governance Views -->
      <ConsoleView
        v-else-if="activeTab === 'backend-orch' || activeTab === 'console'"
        @toast="showToast"
      />
      <OpsView
        v-else-if="activeTab === 'ops'"
      />
      <ProfileView
        v-else-if="activeTab === 'profile'"
        @toast="showToast"
      />
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
    <div
      v-if="notice"
      style="position: fixed; bottom: 32px; right: 32px; z-index: 99999; padding: 14px 20px; border-radius: var(--radius-md); background: var(--glass-surface-solid); border: 1px solid var(--glass-border); box-shadow: 0 16px 40px rgba(0, 0, 0, 0.25), var(--glass-specular); backdrop-filter: var(--blur-strength); -webkit-backdrop-filter: var(--blur-strength); max-width: 420px; animation: fadeInView 0.28s ease;"
    >
      <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;">
        <span v-if="notice.type === 'SUCCESS'" style="color: #34C759; font-weight: 800;">✓</span>
        <span v-else-if="notice.type === 'DANGER'" style="color: #FF3B30; font-weight: 800;">✕</span>
        <span v-else style="color: var(--accent); font-weight: 800;">ℹ</span>
        <span>{{ notice.title }}</span>
      </div>
      <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.55;">
        {{ notice.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
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

const activeTab = ref('home');
const currentRole = ref('MAKER');
const isDark = ref(false);
const userSession = ref(null);

const showRegisterModal = ref(false);
const showLoginModal = ref(false);
const showLegalModal = ref(false);
const legalTab = ref('terms');

const notice = ref(null);
let noticeTimer = null;

function handleSwitchTab(tab) {
  activeTab.value = tab;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleToggleRole() {
  if (currentRole.value === 'MAKER') {
    currentRole.value = 'ADMIN';
    activeTab.value = 'ops';
    showToast({
      title: '视角已切换',
      message: '当前已切换至【管理治理视角 (Admin Governance)】，展示后端微内核编排与全域运营大盘。',
      type: 'INFO',
    });
  } else {
    currentRole.value = 'MAKER';
    activeTab.value = 'home';
    showToast({
      title: '视角已切换',
      message: '当前已切换回【创客工作台视角 (Maker OS)】，为您呈现赋能服务地图。',
      type: 'INFO',
    });
  }
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
  activeTab.value = 'profile';
  showToast({
    title: '商用入驻成功',
    message: `恭喜创客 ${data.email}，已完成商用认证并持久化落库 PostgreSQL 18！`,
    type: 'SUCCESS',
  });
}

function onLoginSuccess(data) {
  showLoginModal.value = false;
  userSession.value = data;
  showToast({
    title: '登录成功',
    message: `欢迎回来，${data.nickname || data.email}！`,
    type: 'SUCCESS',
  });
}

function showToast({ title, message, type = 'INFO' }) {
  notice.value = { title, message, type };
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    notice.value = null;
  }, 4000);
}

async function checkSession() {
  const token = localStorage.getItem('opchub_session_token');
  if (token) {
    try {
      const res = await dispatchGateway('auth.session', {});
      if (res.ok && res.data && res.data.authenticated) {
        userSession.value = res.data.user || res.data;
      } else {
        localStorage.removeItem('opchub_session_token');
      }
    } catch (e) {
      console.warn('Session check fallback', e);
    }
  }
}

onMounted(() => {
  const savedTheme = localStorage.getItem('opchub_theme');
  if (savedTheme === 'dark') {
    isDark.value = true;
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  checkSession();
});
</script>
