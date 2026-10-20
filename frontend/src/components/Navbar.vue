<template>
  <header>
    <div class="nav-glass-bar">
      <!-- 1. Left VisionOS Island: 晨昏线外 Beyond the Line -->
      <div
        class="brand-island"
        id="brandIsland"
        @click="$emit('switch-tab', currentRole === 'ADMIN' ? 'ops' : 'home')"
        title="晨昏线外 · Beyond the Line · 点击返回首页"
      >
        <div class="brand-mark-wrapper">
          <BrandLogo :size="22" />
        </div>
        <span class="brand-name">晨昏线外</span>
        <div class="brand-island-divider"></div>
        <span class="brand-tag">{{ currentRole === 'ADMIN' ? 'ADMIN' : 'Beyond the Line' }}</span>
      </div>

      <!-- 2. Middle Scrollable Nav Tabs Wrapper (Displayed ONLY after login) -->
      <div v-if="userSession" class="nav-tabs-wrapper">
        <nav class="nav-tabs" id="mainNavTabs">
          <!-- Maker / User Tabs -->
          <template v-if="currentRole !== 'ADMIN'">
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'home' }"
              @click="$emit('switch-tab', 'home')"
            >
              首页
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'forum' }"
              @click="$emit('switch-tab', 'forum')"
            >
              头脑风暴
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'product' }"
              @click="$emit('switch-tab', 'product')"
            >
              产品橱窗
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'policy' }"
              @click="$emit('switch-tab', 'policy')"
            >
              政策雷达
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'demand' }"
              @click="$emit('switch-tab', 'demand')"
            >
              需求集市
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'sop' }"
              @click="$emit('switch-tab', 'sop')"
            >
              流程文书
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'perks' }"
              @click="$emit('switch-tab', 'perks')"
            >
              生态特权
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'compliance' }"
              @click="$emit('switch-tab', 'compliance')"
            >
              合规指南
            </button>
          </template>

          <!-- Administrator Only Tabs -->
          <template v-else>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'home' }"
              @click="$emit('switch-tab', 'home')"
            >
              平台首页
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'backend-orch' }"
              @click="$emit('switch-tab', 'backend-orch')"
            >
              后端编排
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'frontend-orch' }"
              @click="$emit('switch-tab', 'frontend-orch')"
            >
              前端编排
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'ops' }"
              @click="$emit('switch-tab', 'ops')"
            >
              运营大盘
            </button>
            <button
              class="nav-tab-btn"
              :class="{ active: activeTab === 'moderation' }"
              @click="$emit('switch-tab', 'moderation')"
            >
              内容治理
            </button>
          </template>
        </nav>
      </div>

      <!-- 3. Right Action Island -->
      <div class="nav-right-actions">
        <!-- Quick Login / Register pill for unauthenticated visitors -->
        <button
          v-if="!userSession"
          class="btn-liquid nav-login-pill"
          @click="$emit('open-login')"
          title="点击登录创客工作台或入驻平台"
        >
          <span>登录 / 入驻</span>
        </button>

        <div class="nav-actions-island">
          <!-- Role Switcher (Maker vs Admin, only for logged in users) -->
          <button
            v-if="userSession"
            class="nav-icon-btn"
            :class="{ 'admin-active': currentRole === 'ADMIN' }"
            @click="toggleRole"
            :title="currentRole === 'ADMIN' ? '切换回创客视角' : '切换至管理治理视角'"
          >
            <!-- Maker Icon: 3D Layers -->
            <svg v-if="currentRole !== 'ADMIN'" viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            <!-- Admin Icon: Security Governance Shield -->
            <svg v-else viewBox="0 0 24 24">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span class="nav-role-dot"></span>
          </button>

          <div v-if="userSession" class="nav-island-divider"></div>

          <!-- Theme Switcher (Dark vs Light) -->
          <button
            class="nav-icon-btn"
            @click="toggleTheme"
            :title="isDark ? '切换至明亮模式' : '切换至暗黑模式'"
          >
            <svg v-if="isDark" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="5"></circle>
              <line x1="12" y1="1" x2="12" y2="3"></line>
              <line x1="12" y1="21" x2="12" y2="23"></line>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
              <line x1="1" y1="12" x2="3" y2="12"></line>
              <line x1="21" y1="12" x2="23" y2="12"></line>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>
            <svg v-else viewBox="0 0 24 24">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
          </button>

          <div v-if="userSession" class="nav-island-divider"></div>

          <!-- User Profile & Entitlements (Logged in only) -->
          <button
            v-if="userSession"
            class="nav-icon-btn logged-in"
            @click="handleUserClick"
            :title="`${userSession.nickname || userSession.email} · 查看创客档案`"
          >
            <div
              style="width: 22px; height: 22px; border-radius: 50%; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; color: #fff; background: linear-gradient(135deg, var(--accent), #5856D6); box-shadow: 0 2px 8px rgba(0, 113, 227, 0.4);"
            >
              {{ (userSession.nickname || userSession.email || 'M')[0].toUpperCase() }}
            </div>
            <span class="nav-user-badge online"></span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue';
import BrandLogo from './BrandLogo.vue';

const props = defineProps({
  activeTab: {
    type: String,
    default: 'forum',
  },
  userSession: {
    type: Object,
    default: null,
  },
  currentRole: {
    type: String,
    default: 'MAKER',
  },
  isDark: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits([
  'switch-tab',
  'toggle-role',
  'toggle-theme',
  'open-login',
  'open-profile',
]);

function toggleRole() {
  if (!props.userSession) {
    emit('open-login');
    return;
  }
  emit('toggle-role');
}

function toggleTheme() {
  emit('toggle-theme');
}

function handleUserClick() {
  if (props.userSession) {
    emit('switch-tab', 'profile');
  } else {
    emit('open-login');
  }
}
</script>

<style scoped>
.nav-login-pill {
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 600;
  height: 32px;
  box-shadow: 0 2px 10px rgba(0, 113, 227, 0.25);
}
</style>
