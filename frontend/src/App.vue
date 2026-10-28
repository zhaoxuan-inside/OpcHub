<template>
  <div style="min-height: 100vh; position: relative; display: flex; flex-direction: column;">
    <!-- Ambient Fluid Background Orbs -->
    <div class="ambient-container">
      <div class="ambient-orb orb-1"></div>
      <div class="ambient-orb orb-2"></div>
      <div class="ambient-orb orb-3"></div>
    </div>

    <!-- Fixed Liquid Navigation -->
    <Navbar
      :active-tab="activeTab"
      :user-session="userSession"
      :current-role="currentRole"
      :is-dark="isDark"
      :unread-count="unreadCount"
      @switch-tab="handleSwitchTab"
      @toggle-role="handleToggleRole"
      @toggle-theme="handleToggleTheme"
      @open-login="showLoginModal = true"
      @open-profile="handleSwitchTab('profile')"
      @open-inbox="openInbox"
      @open-command="openCommandPalette"
    />

    <!-- Routed workspace. Every list/detail has a real URL now. -->
    <main>
      <RouterView v-slot="{ Component }">
        <component
          :is="Component"
          v-bind="viewProps"
          @toast="showToast"
          @open-login="showLoginModal = true"
          @open-register="showRegisterModal = true"
          @switch-tab="handleSwitchTab"
          @navigate="handleNavigate"
          @logout="handleLogout"
          @session-updated="onSessionUpdated"
          @require-login="showLoginModal = true"
        />
      </RouterView>
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

    <!-- 消息箱：发布审核结果通知 -->
    <NotificationInbox
      :visible="showInbox"
      :user-session="userSession"
      @close="showInbox = false"
      @unread-change="unreadCount = $event"
      @toast="showToast"
    />

    <!-- Global command palette (⌘K / Ctrl+K) -->
    <CommandPalette
      :visible="showCommandPalette"
      :user-session="userSession"
      :current-role="currentRole"
      @close="showCommandPalette = false"
      @navigate="handleCommandNavigate"
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
            background: notice.type === 'SUCCESS' ? 'var(--status-success-soft)' : (notice.type === 'DANGER' || notice.type === 'ERROR' ? 'var(--status-danger-soft)' : (notice.type === 'WARN' ? 'var(--status-warning-soft)' : 'var(--accent-glass)')),
            color: notice.type === 'SUCCESS' ? 'var(--status-success)' : (notice.type === 'DANGER' || notice.type === 'ERROR' ? 'var(--status-danger)' : (notice.type === 'WARN' ? 'var(--status-warning)' : 'var(--accent)')),
            fontWeight: '700',
            fontSize: '14px',
          }"
        >
          <OpcIcon v-if="notice.type === 'SUCCESS'" name="check" :size="15" />
          <OpcIcon v-else-if="notice.type === 'DANGER' || notice.type === 'ERROR'" name="close" :size="15" />
          <OpcIcon v-else-if="notice.type === 'WARN'" name="alert" :size="15" />
          <OpcIcon v-else name="info" :size="15" />
        </div>

        <div style="flex: 1; min-width: 0;">
          <div style="font-weight: 600; font-size: 13.5px; color: var(--text-primary); margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center;">
            <span>{{ notice.title }}</span>
            <button
              @click="dismissNotice"
              style="border: none; background: transparent; cursor: pointer; color: var(--text-tertiary); font-size: 14px; line-height: 1; padding: 2px 4px; border-radius: 4px; transition: color 0.15s ease;"
              title="关闭通知"
            >
              <OpcIcon name="close" :size="14" />
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Navbar from '@/components/Navbar.vue';
import RegisterModal from '@/components/RegisterModal.vue';
import LoginModal from '@/components/LoginModal.vue';
import LegalModal from '@/components/LegalModal.vue';
import NotificationInbox from '@/components/NotificationInbox.vue';
import CommandPalette from '@/components/CommandPalette.vue';
import { dispatchGateway } from '@/api/gateway';
import { activeNotice, notify, dismissNotice } from '@/api/notification';
import {
  authState,
  clearSession,
  ensureSession,
  isAuthenticated,
  isPlatformAdmin,
  rememberTab,
  setSession,
  toggleRole,
  updateSessionUser,
} from '@/stores/auth';
import { pathForTab, tabForRoute } from '@/router';

const route = useRoute();
const router = useRouter();

const userSession = computed(() => authState.user);
const currentRole = computed(() => authState.role);
const activeTab = computed(() => tabForRoute(route));

const isDark = ref(false);
const showRegisterModal = ref(false);
const showLoginModal = ref(false);
const showLegalModal = ref(false);
const legalTab = ref('terms');
const showCommandPalette = ref(false);

// 消息箱：审核结果的持久通知
const showInbox = ref(false);
const unreadCount = ref(0);
let unreadTimer = null;

const notice = activeNotice;

const viewProps = computed(() => (route.meta?.passSession ? { userSession: authState.user } : {}));

async function refreshUnread(announceNew = false) {
  if (!authState.user) {
    unreadCount.value = 0;
    return;
  }
  const res = await dispatchGateway('notifications.unread_count', {}, { silent: true });
  if (!res.ok) return;
  const next = Number(res.data?.unread || 0);
  if (announceNew && next > unreadCount.value) {
    showToast({
      title: '消息箱',
      message: `收到 ${next - unreadCount.value} 条新的平台审核结果`,
      type: 'INFO',
    });
  }
  unreadCount.value = next;
}

function openInbox() {
  showInbox.value = true;
  refreshUnread(false);
}

function openCommandPalette() {
  showCommandPalette.value = true;
}

function onGlobalPointerDown(event) {
  document.querySelectorAll('details.ci-more[open]').forEach((details) => {
    if (!details.contains(event.target)) details.open = false;
  });
}

function onGlobalKeydown(event) {
  const key = String(event.key || '').toLowerCase();
  if (key === 'escape') {
    document.querySelectorAll('details.ci-more[open]').forEach((details) => {
      details.open = false;
    });
  }
  if ((event.metaKey || event.ctrlKey) && key === 'k') {
    event.preventDefault();
    if (!isAuthenticated.value) {
      showLoginModal.value = true;
      return;
    }
    showCommandPalette.value = !showCommandPalette.value;
    return;
  }
  if (key === 'escape' && showCommandPalette.value) {
    showCommandPalette.value = false;
  }
}

watch(
  () => authState.user,
  (session) => {
    if (session) refreshUnread(false);
    else {
      unreadCount.value = 0;
      showInbox.value = false;
    }
  }
);

watch(
  () => route.fullPath,
  () => {
    if (authState.user) refreshUnread(true);
  }
);

watch(
  () => route.query.login,
  (value) => {
    if (value === '1' && !isAuthenticated.value) showLoginModal.value = true;
  },
  { immediate: true }
);

function handleSwitchTab(tab) {
  if (!isAuthenticated.value && tab !== 'home') {
    showToast({
      title: '需登录创客账号',
      message: '未登录用户仅限浏览平台宣传首页。请登录或入驻后进入创客工作台。',
      type: 'INFO',
    });
    showLoginModal.value = true;
    return;
  }
  const path = pathForTab(tab);
  rememberTab(tab);
  if (route.path === path) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }
  router.push(path);
}

function handleNavigate(target) {
  if (!target) return;
  if (String(target).startsWith('/')) {
    router.push(String(target));
    return;
  }
  handleSwitchTab(target);
}

function handleCommandNavigate(target) {
  showCommandPalette.value = false;
  if (!target) return;
  if (target.tab) {
    handleSwitchTab(target.tab);
    return;
  }
  if (target.path) router.push(target.path);
}

function handleToggleRole() {
  if (!authState.user) {
    showToast({
      title: '需管理员登录',
      message: '管理治理视角仅限授权管理员登录后进入。',
      type: 'INFO',
    });
    showLoginModal.value = true;
    return;
  }
  if (!isPlatformAdmin.value) {
    showToast({
      title: '权限不足',
      message: '管理治理视角仅限授权管理员登录后进入。',
      type: 'WARN',
    });
    return;
  }
  const next = toggleRole();
  if (next === 'ADMIN') {
    router.push('/admin/ops');
    showToast({
      title: '视角已切换',
      message: '当前已切换至【管理治理视角】，可查看后端编排与全域运营大盘。',
      type: 'INFO',
    });
  } else {
    router.push('/');
    showToast({
      title: '视角已切换',
      message: '当前已切换回【创客工作台视角】。',
      type: 'INFO',
    });
  }
}

function handleLogout() {
  clearSession();
  router.replace('/');
  showToast({
    title: '已退出登录',
    message: '您已安全退出创客登录，已返回平台宣传首页。',
    type: 'INFO',
  });
}

function onSessionUpdated(updated) {
  updateSessionUser(updated);
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
  setSession(data, { preferAdmin: false });
  router.replace('/profile');
  showToast({
    title: '商用入驻成功',
    message: data.message || `恭喜创客 ${data.email}，已完成商用认证，欢迎入驻！`,
    type: 'SUCCESS',
  });
}

function onLoginSuccess(data) {
  showLoginModal.value = false;
  setSession(data, { preferAdmin: true });

  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '';
  if (redirect) {
    router.replace(redirect);
  } else if (isPlatformAdmin.value && authState.role === 'ADMIN') {
    router.replace('/admin/ops');
  } else if (route.path === '/') {
    router.replace('/forum');
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

onMounted(async () => {
  const savedTheme = localStorage.getItem('opchub_theme');
  if (savedTheme === 'dark') {
    isDark.value = true;
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  await ensureSession(true);
  refreshUnread(false);

  window.addEventListener('keydown', onGlobalKeydown);
  window.addEventListener('pointerdown', onGlobalPointerDown);
  unreadTimer = setInterval(() => {
    if (authState.user) refreshUnread(true);
  }, 60000);
});

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown);
  window.removeEventListener('pointerdown', onGlobalPointerDown);
  if (unreadTimer) {
    clearInterval(unreadTimer);
    unreadTimer = null;
  }
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

/*
 * Message blocks carry no left accent bar. The circular icon badge already
 * conveys the severity through its own colour, so a second coloured stripe
 * on the edge is redundant.
 */
</style>
