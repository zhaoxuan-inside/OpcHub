<template>
  <Teleport to="body">
    <transition name="cp-fade">
      <div v-if="visible" class="cp-overlay" @click.self="close">
        <section class="cp-panel" role="dialog" aria-modal="true" aria-label="全局搜索与快捷跳转">
          <div class="cp-search-row">
            <OpcIcon name="search" :size="17" />
            <input
              ref="inputRef"
              v-model="query"
              class="cp-input"
              type="text"
              autocomplete="off"
              spellcheck="false"
              placeholder="搜索政策、帖子、作品、需求、文书，或输入功能名…"
              aria-label="全局搜索"
              @keydown="onKeydown"
            />
            <kbd class="cp-kbd">ESC</kbd>
          </div>

          <div ref="panelRef" class="cp-body">
            <div v-if="loading" class="cp-state">
              <span class="cp-spinner"></span>
              正在汇总全站内容…
            </div>

            <template v-else>
              <template v-for="group in groups" :key="group.key">
                <div class="cp-group-title">
                  <span>{{ group.label }}</span>
                  <span class="cp-group-count">{{ group.items.length }}</span>
                </div>
                <button
                  v-for="item in group.items"
                  :key="item.key"
                  type="button"
                  class="cp-item"
                  :class="{ 'is-active': activeKey === item.key }"
                  @mouseenter="activeKey = item.key"
                  @click="choose(item)"
                >
                  <span class="cp-item-icon">
                    <OpcIcon :name="item.icon || 'compass'" :size="15" />
                  </span>
                  <span class="cp-item-main">
                    <span class="cp-item-title">{{ item.title }}</span>
                    <span v-if="item.subtitle" class="cp-item-sub">{{ item.subtitle }}</span>
                  </span>
                  <span class="cp-item-type">{{ item.typeLabel }}</span>
                </button>
              </template>

              <div v-if="!groups.length" class="cp-state">
                <OpcIcon name="search" :size="18" />
                没有找到与「{{ query }}」相关的内容
              </div>
            </template>
          </div>

          <footer class="cp-footer">
            <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
            <span><kbd>↵</kbd> 打开</span>
            <span><kbd>ESC</kbd> 关闭</span>
            <span class="cp-footer-hint">⌘K / Ctrl+K 随时唤起</span>
          </footer>
        </section>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  visible: { type: Boolean, default: false },
  userSession: { type: Object, default: null },
  currentRole: { type: String, default: 'MAKER' },
});

const emit = defineEmits(['close', 'navigate']);

const inputRef = ref(null);
const panelRef = ref(null);
const query = ref('');
const loading = ref(false);
const activeKey = ref('');
const contentItems = ref([]);
const recentItems = ref([]);
const loaded = ref(false);
const RECENT_KEY = 'opchub_recent_commands';

const STATIC_MAKER = [
  { key: 'nav-home', title: '首页', subtitle: '平台总览与今日推荐', tab: 'home', icon: 'compass', typeLabel: '页面' },
  { key: 'nav-forum', title: '头脑风暴', subtitle: '发帖、提问、回答与实战复盘', tab: 'forum', icon: 'users', typeLabel: '页面' },
  { key: 'nav-products', title: '产品橱窗', subtitle: '独立作品与微 SaaS 展示', tab: 'product', icon: 'box', typeLabel: '页面' },
  { key: 'nav-policies', title: '政策中心', subtitle: '政策检索、资格自测与免税测算', tab: 'policy', icon: 'landmark', typeLabel: '页面' },
  { key: 'nav-demands', title: '需求集市', subtitle: '需求委托、竞标与撮合', tab: 'demand', icon: 'briefcase', typeLabel: '页面' },
  { key: 'nav-sop', title: '流程文书', subtitle: '标准文书、引导填写与流程向导', tab: 'sop', icon: 'file', typeLabel: '页面' },
  { key: 'nav-perks', title: '生态特权', subtitle: '生态伙伴优惠与领取', tab: 'perks', icon: 'gift', typeLabel: '页面' },
  { key: 'nav-compliance', title: '合规指南', subtitle: '法条、案例与合规阅读', tab: 'compliance', icon: 'shield', typeLabel: '页面' },
  { key: 'nav-membership', title: '会员中心', subtitle: '积分、会员与权益', tab: 'membership', icon: 'gem', typeLabel: '页面' },
  { key: 'nav-profile', title: '创客档案', subtitle: '身份、互动足迹与账号安全', tab: 'profile', icon: 'users', typeLabel: '页面' },
];

const STATIC_ADMIN = [
  { key: 'nav-admin-orch', title: '后端编排', subtitle: '算子、子图、场景与 DAG 试跑', path: '/admin/orchestration', icon: 'modules', typeLabel: '管理' },
  { key: 'nav-admin-layout', title: '前端布局', subtitle: '页面栅格与组件编排', path: '/admin/layout', icon: 'monitor', typeLabel: '管理' },
  { key: 'nav-admin-ops', title: '运营大盘', subtitle: '流量、互动与模块热力', path: '/admin/ops', icon: 'chart-up', typeLabel: '管理' },
  { key: 'nav-admin-moderation', title: '内容治理', subtitle: '审核队列与风险内容', path: '/admin/moderation', icon: 'shield', typeLabel: '管理' },
];

const staticItems = computed(() => {
  const base = props.currentRole === 'ADMIN' ? [...STATIC_ADMIN, ...STATIC_MAKER] : STATIC_MAKER;
  return base;
});

function normalizeList(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return Array.isArray(data.items) ? data.items : [];
}

function pickId(item) {
  return item?.id || item?.code || item?.thread_id || '';
}

function loadContent() {
  if (loaded.value || !props.userSession) return;
  loaded.value = true;
  loading.value = true;

  const calls = [
    ['policies.list', {}, (d) => normalizeList(d).slice(0, 8).map((p) => ({
      key: `policy-${pickId(p)}`,
      title: p.title,
      subtitle: [p.region, p.policy_level, p.category].filter(Boolean).join(' · '),
      path: `/policies/${encodeURIComponent(pickId(p))}`,
      icon: 'landmark',
      typeLabel: '政策',
    }))],
    ['products.list', {}, (d) => normalizeList(d).slice(0, 8).map((p) => ({
      key: `product-${pickId(p)}`,
      title: p.title,
      subtitle: [p.tagline || p.description, p.author_name].filter(Boolean).join(' · ').slice(0, 70),
      path: `/products/${encodeURIComponent(pickId(p))}`,
      icon: 'box',
      typeLabel: '作品',
    }))],
    ['forum.feed.stream', { category_code: 'ALL', cursor: 0, limit: 16, sort_by: 'hot' }, (d) => normalizeList(d).slice(0, 8).map((p) => ({
      key: `forum-${pickId(p)}`,
      title: p.title,
      subtitle: [p.author_name, `${p.reply_count ?? p.replies ?? 0} 回答`, `${p.upvote_count ?? p.upvotes ?? 0} 赞同`].filter(Boolean).join(' · '),
      path: `/forum/${encodeURIComponent(pickId(p))}`,
      icon: 'comment',
      typeLabel: '帖子',
    }))],
    ['demands.list', {}, (d) => normalizeList(d).slice(0, 8).map((p) => ({
      key: `demand-${pickId(p)}`,
      title: p.title,
      subtitle: [p.category, p.budget ? `预算 ¥${Number(p.budget).toLocaleString()}` : '', p.status].filter(Boolean).join(' · '),
      path: `/demands/${encodeURIComponent(pickId(p))}`,
      icon: 'briefcase',
      typeLabel: '需求',
    }))],
    ['sop.documents', { user_id: props.userSession?.uid || props.userSession?.id || '' }, (d) => normalizeList(d).slice(0, 8).map((p) => ({
      key: `sop-doc-${pickId(p)}`,
      title: p.name || p.document_title || p.title,
      subtitle: [p.category, `${(p.required_fields || []).length} 个待填要素`].filter(Boolean).join(' · '),
      path: `/sop/docs/${encodeURIComponent(pickId(p))}`,
      icon: 'file',
      typeLabel: '文书',
    }))],
    ['sop.flow.templates', { user_id: props.userSession?.uid || props.userSession?.id || '' }, (d) => normalizeList(d).slice(0, 8).map((p) => ({
      key: `sop-flow-${pickId(p)}`,
      title: p.name || p.title,
      subtitle: [p.category, `${(p.node_refs || []).length || (p.nodes || []).length} 个节点`].filter(Boolean).join(' · '),
      path: `/sop/flows/${encodeURIComponent(pickId(p))}`,
      icon: 'clipboard',
      typeLabel: '流程',
    }))],
    ['perks.list', {}, (d) => normalizeList(d).slice(0, 6).map((p) => ({
      key: `perk-${pickId(p)}`,
      title: p.name || p.title,
      subtitle: [p.provider, p.value_cny ? `价值 ¥${Number(p.value_cny).toLocaleString()}` : ''].filter(Boolean).join(' · '),
      path: `/perks/${encodeURIComponent(pickId(p))}`,
      icon: 'gift',
      typeLabel: '特权',
    }))],
  ];

  Promise.allSettled(calls.map(([scenario, payload]) => dispatchGateway(scenario, payload, { silent: true })))
    .then((results) => {
      const collected = [];
      results.forEach((result, index) => {
        if (result.status !== 'fulfilled' || !result.value?.ok) return;
        const mapper = calls[index][2];
        collected.push(...mapper(result.value.data));
      });
      contentItems.value = collected.filter((item) => item.title && item.path);
    })
    .finally(() => {
      loading.value = false;
    });
}

function readRecent() {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    recentItems.value = raw ? JSON.parse(raw) : [];
  } catch (error) {
    recentItems.value = [];
  }
}

function remember(item) {
  try {
    const next = [item, ...recentItems.value.filter((entry) => entry.key !== item.key)].slice(0, 5);
    recentItems.value = next;
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch (error) {
    // localStorage may be unavailable in private mode; the palette still works.
  }
}

const groups = computed(() => {
  const q = query.value.trim().toLowerCase();

  if (!q) {
    const result = [];
    if (recentItems.value.length) result.push({ key: 'recent', label: '最近访问', items: recentItems.value });
    result.push({ key: 'nav', label: '快捷跳转', items: staticItems.value });
    result.push({
      key: 'content',
      label: '最近内容',
      items: contentItems.value.slice(0, 8),
    });
    return result.filter((group) => group.items.length);
  }

  const pool = [...staticItems.value, ...contentItems.value];
  const scored = pool
    .map((item) => {
      const title = String(item.title || '').toLowerCase();
      const subtitle = String(item.subtitle || '').toLowerCase();
      let score = 0;
      if (title.startsWith(q)) score = 100;
      else if (title.includes(q)) score = 70;
      else if (subtitle.includes(q)) score = 35;
      return { item, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((entry) => entry.item);

  const grouped = new Map();
  for (const item of scored) {
    const label = item.typeLabel === '页面' ? '页面与功能' : `${item.typeLabel}`;
    if (!grouped.has(label)) grouped.set(label, []);
    grouped.get(label).push(item);
  }
  return [...grouped.entries()].map(([label, items]) => ({ key: label, label, items }));
});

const flatItems = computed(() => groups.value.flatMap((group) => group.items));

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      query.value = '';
      activeKey.value = '';
      return;
    }
    readRecent();
    loadContent();
    nextTick(() => {
      inputRef.value?.focus();
      activeKey.value = flatItems.value[0]?.key || '';
    });
  }
);

watch(
  () => query.value,
  () => {
    nextTick(() => {
      activeKey.value = flatItems.value[0]?.key || '';
    });
  }
);

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault();
    close();
    return;
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    const list = flatItems.value;
    if (!list.length) return;
    const current = list.findIndex((item) => item.key === activeKey.value);
    const delta = event.key === 'ArrowDown' ? 1 : -1;
    const next = (current + delta + list.length) % list.length;
    activeKey.value = list[next].key;
    nextTick(() => {
      panelRef.value?.querySelector('.cp-item.is-active')?.scrollIntoView({ block: 'nearest' });
    });
    return;
  }
  if (event.key === 'Enter') {
    event.preventDefault();
    const item = flatItems.value.find((entry) => entry.key === activeKey.value) || flatItems.value[0];
    if (item) choose(item);
  }
}

function choose(item) {
  if (!item) return;
  remember(item);
  emit('navigate', item.tab ? { tab: item.tab } : { path: item.path });
  emit('close');
}

function close() {
  emit('close');
}
</script>

<style scoped>
.cp-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 10vh 20px 20px;
  background: rgba(8, 10, 16, 0.34);
  backdrop-filter: blur(10px) saturate(140%);
  -webkit-backdrop-filter: blur(10px) saturate(140%);
}

.cp-panel {
  width: min(640px, 100%);
  max-height: min(72vh, 640px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 20px;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.96));
  border: 1px solid var(--glass-border);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.28), var(--glass-specular);
}

.cp-search-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--glass-border-subtle);
  color: var(--text-tertiary);
}

.cp-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 15px;
  font-family: inherit;
}

.cp-input::placeholder {
  color: var(--text-tertiary);
}

.cp-kbd,
.cp-footer kbd {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 6px;
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-tertiary);
  background: var(--glass-surface);
}

.cp-body {
  flex: 1;
  min-height: 120px;
  overflow-y: auto;
  padding: 10px 10px 14px;
}

.cp-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 10px 6px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.cp-group-count {
  font-weight: 500;
  letter-spacing: 0;
}

.cp-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: background 0.16s ease, border-color 0.16s ease;
}

.cp-item.is-active,
.cp-item:hover {
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  border-color: rgba(0, 113, 227, 0.16);
}

.cp-item-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border-subtle);
  color: var(--accent);
}

.cp-item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cp-item-title {
  font-size: 13.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cp-item-sub {
  font-size: 11.5px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cp-item-type {
  flex-shrink: 0;
  font-size: 10px;
  color: var(--text-tertiary);
  border: 1px solid var(--glass-border-subtle);
  border-radius: 999px;
  padding: 2px 8px;
}

.cp-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 44px 16px;
  font-size: 12.5px;
  color: var(--text-secondary);
}

.cp-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--glass-border-subtle);
  border-top-color: var(--accent);
  animation: cpSpin 0.8s linear infinite;
}

@keyframes cpSpin {
  to { transform: rotate(360deg); }
}

.cp-footer {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 18px;
  border-top: 1px solid var(--glass-border-subtle);
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.cp-footer span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.cp-footer-hint {
  margin-left: auto;
}

.cp-fade-enter-active,
.cp-fade-leave-active {
  transition: opacity 0.18s ease;
}

.cp-fade-enter-from,
.cp-fade-leave-to {
  opacity: 0;
}

.cp-fade-enter-active .cp-panel,
.cp-fade-leave-active .cp-panel {
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.cp-fade-enter-from .cp-panel,
.cp-fade-leave-to .cp-panel {
  transform: translateY(-8px) scale(0.98);
}

@media (max-width: 640px) {
  .cp-overlay {
    padding: 0;
    align-items: stretch;
  }

  .cp-panel {
    max-height: 100vh;
    height: 100vh;
    border-radius: 0;
    border: none;
  }

  .cp-footer-hint {
    display: none;
  }
}
</style>
