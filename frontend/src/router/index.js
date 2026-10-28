import { createRouter, createWebHistory } from 'vue-router';
import { authState, ensureSession, isAuthenticated, isPlatformAdmin, mustChangePassword } from '@/stores/auth';
import { notify } from '@/api/notification';

const HomeView = () => import('@/views/HomeView.vue');
const ForumView = () => import('@/views/ForumView.vue');
const ShowcaseView = () => import('@/views/ShowcaseView.vue');
const PolicyView = () => import('@/views/PolicyView.vue');
const DemandsView = () => import('@/views/DemandsView.vue');
const SopView = () => import('@/views/SopView.vue');
const PerksView = () => import('@/views/PerksView.vue');
const MembershipView = () => import('@/views/MembershipView.vue');
const ComplianceView = () => import('@/views/ComplianceView.vue');
const ProfileView = () => import('@/views/ProfileView.vue');
const ChangePasswordView = () => import('@/views/ChangePasswordView.vue');
const ConsoleView = () => import('@/views/ConsoleView.vue');
const FrontendOrchView = () => import('@/views/FrontendOrchView.vue');
const OpsView = () => import('@/views/OpsView.vue');

const makerMeta = { requiresAuth: true, roles: ['MAKER', 'ADMIN'] };
const adminMeta = { requiresAuth: true, roles: ['ADMIN'] };

export const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { tab: 'home', public: true, title: '首页', passSession: true },
  },
  {
    path: '/forum/:id?',
    name: 'forum',
    component: ForumView,
    meta: { ...makerMeta, tab: 'forum', title: '头脑风暴', passSession: true },
  },
  {
    path: '/products/:id?',
    name: 'products',
    component: ShowcaseView,
    meta: { ...makerMeta, tab: 'product', title: '产品橱窗', passSession: true },
  },
  {
    path: '/policies/:id?',
    name: 'policies',
    component: PolicyView,
    meta: { ...makerMeta, tab: 'policy', title: '政策中心', passSession: true },
  },
  {
    path: '/demands/:id?',
    name: 'demands',
    component: DemandsView,
    meta: { ...makerMeta, tab: 'demand', title: '需求集市' },
  },
  {
    path: '/sop/docs/:id?',
    name: 'sop-docs',
    component: SopView,
    meta: { ...makerMeta, tab: 'sop', title: '流程文书' },
  },
  {
    path: '/sop/flows/:id?',
    name: 'sop-flows',
    component: SopView,
    meta: { ...makerMeta, tab: 'sop', title: '流程文书' },
  },
  {
    path: '/sop/my-docs/:id',
    name: 'sop-my-doc',
    component: SopView,
    meta: { ...makerMeta, tab: 'sop', title: '我的文书' },
  },
  {
    path: '/sop/my-flows/:id',
    name: 'sop-my-flow',
    component: SopView,
    meta: { ...makerMeta, tab: 'sop', title: '我的流程' },
  },
  {
    path: '/sop/flow-builder',
    name: 'sop-flow-builder',
    component: SopView,
    meta: { ...makerMeta, tab: 'sop', title: '编排流程' },
  },
  {
    path: '/sop/:view?',
    name: 'sop',
    component: SopView,
    meta: { ...makerMeta, tab: 'sop', title: '流程文书' },
  },
  {
    path: '/perks/:id?',
    name: 'perks',
    component: PerksView,
    meta: { ...makerMeta, tab: 'perks', title: '生态特权', passSession: true },
  },
  {
    path: '/compliance/:id?',
    name: 'compliance',
    component: ComplianceView,
    meta: { ...makerMeta, tab: 'compliance', title: '合规指南', passSession: true },
  },
  {
    path: '/membership',
    name: 'membership',
    component: MembershipView,
    meta: { ...makerMeta, tab: 'membership', title: '会员中心' },
  },
  {
    path: '/profile',
    name: 'profile',
    component: ProfileView,
    meta: { ...makerMeta, tab: 'profile', title: '创客档案' },
  },
  {
    path: '/change-password',
    name: 'change-password',
    component: ChangePasswordView,
    meta: { ...makerMeta, tab: 'change-password', title: '账号安全', passSession: true },
  },
  {
    path: '/admin/orchestration',
    name: 'admin-orchestration',
    component: ConsoleView,
    meta: { ...adminMeta, tab: 'backend-orch', title: '后端编排', passSession: true },
  },
  {
    path: '/admin/layout',
    name: 'admin-layout',
    component: FrontendOrchView,
    meta: { ...adminMeta, tab: 'frontend-orch', title: '前端编排' },
  },
  {
    path: '/admin/ops',
    name: 'admin-ops',
    component: OpsView,
    meta: { ...adminMeta, tab: 'ops', title: '运营大盘' },
  },
  {
    path: '/admin/moderation',
    name: 'admin-moderation',
    component: OpsView,
    meta: { ...adminMeta, tab: 'moderation', title: '内容治理' },
  },

  // Legacy hash-era paths → current routes. Keeps old bookmarks working.
  { path: '/policy', redirect: '/policies' },
  { path: '/product', redirect: '/products' },
  { path: '/demand', redirect: '/demands' },
  { path: '/perk', redirect: '/perks' },
  { path: '/backend-orch', redirect: '/admin/orchestration' },
  { path: '/console', redirect: '/admin/orchestration' },
  { path: '/frontend-orch', redirect: '/admin/layout' },
  { path: '/ops', redirect: '/admin/ops' },
  { path: '/moderation', redirect: '/admin/moderation' },
  { path: '/:pathMatch(.*)*', redirect: '/' },
];

export const TAB_TO_PATH = {
  home: '/',
  forum: '/forum',
  product: '/products',
  policy: '/policies',
  demand: '/demands',
  sop: '/sop',
  perks: '/perks',
  membership: '/membership',
  compliance: '/compliance',
  profile: '/profile',
  'change-password': '/change-password',
  'backend-orch': '/admin/orchestration',
  console: '/admin/orchestration',
  'frontend-orch': '/admin/layout',
  ops: '/admin/ops',
  moderation: '/admin/moderation',
};

export function pathForTab(tab) {
  return TAB_TO_PATH[tab] || '/';
}

export function tabForRoute(route) {
  return route?.meta?.tab || 'home';
}

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (to.name === from.name && to.params.id && !from.params.id) return { top: 0 };
    return { top: 0 };
  },
});

const LEGACY_HASH_PATHS = {
  home: '/',
  forum: '/forum',
  product: '/products',
  policy: '/policies',
  demand: '/demands',
  sop: '/sop',
  perks: '/perks',
  membership: '/membership',
  compliance: '/compliance',
  profile: '/profile',
  'change-password': '/change-password',
  'backend-orch': '/admin/orchestration',
  console: '/admin/orchestration',
  'frontend-orch': '/admin/layout',
  ops: '/admin/ops',
  moderation: '/admin/moderation',
};

/**
 * Old hash links (`/#forum?post_id=xxx`) still exist in bookmarks and shared
 * chats. Convert them on the first navigation, then clear the hash.
 */
function legacyHashTarget() {
  if (typeof window === 'undefined') return null;
  const raw = window.location.hash.replace(/^#\/?/, '').trim();
  if (!raw) return null;
  const [segment, queryString = ''] = raw.split('?');
  const base = LEGACY_HASH_PATHS[segment];
  if (!base) return null;
  const params = new URLSearchParams(queryString);
  let path = base;
  if (segment === 'forum' && params.get('post_id')) {
    path = `/forum/${encodeURIComponent(params.get('post_id'))}`;
    params.delete('post_id');
  }
  const query = Object.fromEntries(params.entries());
  return { path, query };
}

router.beforeEach(async (to) => {
  // Old hash URLs must be converted before the auth guard so the redirect
  // target is the real detail route, not the home page.
  const legacy = legacyHashTarget();
  if (legacy) {
    window.history.replaceState(null, '', `${legacy.path}${Object.keys(legacy.query).length ? `?${new URLSearchParams(legacy.query).toString()}` : ''}`);
    if (to.path !== legacy.path) return legacy;
  }

  // Verify the token once per boot. Deep links must not flash an empty shell.
  await ensureSession();

  const requiresAuth = Boolean(to.meta.requiresAuth);
  if (requiresAuth && !isAuthenticated.value) {
    return {
      name: 'home',
      query: { login: '1', redirect: to.fullPath },
    };
  }

  if (to.meta.roles && !to.meta.roles.includes(authState.role) && !isPlatformAdmin.value) {
    notify({
      title: '权限不足',
      message: '该页面仅对平台管理员开放。',
      type: 'WARN',
    });
    return { name: 'home' };
  }

  if (to.meta.roles?.includes('ADMIN') && !isPlatformAdmin.value) {
    notify({
      title: '权限不足',
      message: '该页面仅对平台管理员开放。',
      type: 'WARN',
    });
    return { name: 'home' };
  }

  if (mustChangePassword.value && to.name !== 'change-password' && to.name !== 'home') {
    return { name: 'change-password' };
  }

  return true;
});

router.afterEach((to) => {
  const title = to.meta?.title ? `${to.meta.title} · 晨昏线外` : '晨昏线外 · 超级个体与一人公司商业操作系统';
  if (typeof document !== 'undefined') document.title = title;
});

export default router;
