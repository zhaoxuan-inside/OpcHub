<template>
  <Teleport to="body">
    <Transition name="inbox-fade">
      <div v-if="visible" class="inbox-backdrop" @click.self="$emit('close')">
        <section class="inbox-window glass-box" role="dialog" aria-modal="true" aria-label="消息箱">
          <header class="inbox-head">
            <div class="inbox-head-text">
              <h2 class="inbox-title">消息箱</h2>
              <p class="inbox-subtitle">发布内容的审核结果与平台通知</p>
            </div>
            <div class="inbox-head-actions">
              <button
                v-if="unread > 0"
                type="button"
                class="inbox-text-btn"
                :disabled="marking"
                @click="markAllRead"
              >
                全部已读
              </button>
              <button type="button" class="inbox-close-btn" title="关闭消息箱" @click="$emit('close')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </header>

          <div class="inbox-filter-row">
            <button
              v-for="tab in filters"
              :key="tab.key"
              type="button"
              class="inbox-filter-pill"
              :class="{ active: filter === tab.key }"
              @click="selectFilter(tab.key)"
            >
              {{ tab.label }}
              <span v-if="tab.key === 'UNREAD' && unread > 0" class="inbox-filter-count">{{ unread }}</span>
            </button>
          </div>

          <div class="inbox-list-wrap">
            <div v-if="loading" class="inbox-empty">正在加载消息…</div>
            <div v-else-if="items.length === 0" class="inbox-empty">
              <div class="inbox-empty-title">暂无消息</div>
              <p class="inbox-empty-desc">发布内容后，审核结果会在这里通知你。</p>
            </div>
            <ul v-else class="inbox-list">
              <li
                v-for="item in items"
                :key="item.id"
                class="inbox-item"
                :class="[`level-${(item.level || 'INFO').toLowerCase()}`, { unread: item.status === 'UNREAD' }]"
                @click="openItem(item)"
              >
                <span class="inbox-dot" aria-hidden="true"></span>
                <div class="inbox-item-main">
                  <div class="inbox-item-title-row">
                    <span class="inbox-item-title">{{ item.title }}</span>
                    <span v-if="item.verdict" class="inbox-verdict" :class="`verdict-${item.verdict.toLowerCase()}`">
                      {{ verdictLabel(item.verdict) }}
                    </span>
                  </div>
                  <p class="inbox-item-content">{{ item.content }}</p>
                  <div class="inbox-item-meta">
                    <span>{{ formatTime(item.created_at) }}</span>
                    <span v-if="item.scene" class="inbox-meta-divider">·</span>
                    <span v-if="item.scene">{{ item.scene }}</span>
                  </div>
                </div>
                <button
                  type="button"
                  class="inbox-delete-btn"
                  title="删除该消息"
                  @click.stop="removeItem(item)"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6l-1 14H6L5 6"></path>
                    <path d="M10 11v6M14 11v6"></path>
                  </svg>
                </button>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  visible: { type: Boolean, default: false },
  userSession: { type: Object, default: null },
});

const emit = defineEmits(['close', 'toast', 'unread-change']);

const filters = [
  { key: 'ALL', label: '全部' },
  { key: 'UNREAD', label: '未读' },
];

const items = ref([]);
const unread = ref(0);
const loading = ref(false);
const marking = ref(false);
const filter = ref('ALL');

function verdictLabel(verdict) {
  return {
    PASSED: '校验通过',
    PASSED_DEGRADED: '已放行',
    BLOCKED: '未通过',
  }[verdict] || verdict;
}

function formatTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

async function load() {
  if (!props.userSession) return;
  loading.value = true;
  try {
    const res = await dispatchGateway('notifications.list', {
      status: filter.value === 'UNREAD' ? 'UNREAD' : undefined,
      limit: 100,
    }, { silent: true });
    if (res.ok && res.data) {
      items.value = res.data.items || [];
      unread.value = Number(res.data.unread || 0);
      emit('unread-change', unread.value);
    }
  } finally {
    loading.value = false;
  }
}

function selectFilter(key) {
  if (filter.value === key) return;
  filter.value = key;
  load();
}

async function markAllRead() {
  if (marking.value) return;
  marking.value = true;
  try {
    const res = await dispatchGateway('notifications.mark_all_read', {}, { silent: true });
    if (res.ok && res.data) {
      unread.value = Number(res.data.unread || 0);
      items.value = items.value.map((it) => ({ ...it, status: 'READ' }));
      emit('unread-change', unread.value);
      emit('toast', { title: '消息箱', message: '全部消息已标记为已读', type: 'SUCCESS' });
      if (filter.value === 'UNREAD') load();
    }
  } finally {
    marking.value = false;
  }
}

async function openItem(item) {
  if (item.status !== 'UNREAD') return;
  const res = await dispatchGateway('notifications.mark_read', { ids: [item.id] }, { silent: true });
  if (res.ok) {
    item.status = 'READ';
    unread.value = Math.max(0, unread.value - (res.data?.updated || 1));
    emit('unread-change', unread.value);
    if (filter.value === 'UNREAD') {
      items.value = items.value.filter((it) => it.id !== item.id);
    }
  }
}

async function removeItem(item) {
  const res = await dispatchGateway('notifications.delete', { id: item.id }, { silent: true });
  if (!res.ok) return;
  items.value = items.value.filter((it) => it.id !== item.id);
  unread.value = Number(res.data?.unread ?? unread.value);
  emit('unread-change', unread.value);
}

watch(() => props.visible, (open) => {
  if (open) load();
});
</script>

<style scoped>
.inbox-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(10, 12, 18, 0.28);
  backdrop-filter: blur(6px);
}

.inbox-window {
  width: min(620px, 100%);
  max-height: min(78vh, 760px);
  display: flex;
  flex-direction: column;
  border-radius: 20px;
  overflow: hidden;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.9));
  box-shadow: 0 28px 80px rgba(10, 16, 30, 0.28), var(--glass-specular);
  padding: 0;
  margin: 0;
}

.inbox-head {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px 14px;
}

.inbox-title {
  margin: 0;
  font-size: 20px;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.inbox-subtitle {
  margin: 5px 0 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.inbox-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.inbox-text-btn {
  border: none;
  background: transparent;
  color: var(--accent);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  padding: 4px 6px;
}

.inbox-text-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.inbox-close-btn {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid var(--glass-border);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}

.inbox-filter-row {
  display: flex;
  gap: 8px;
  padding: 0 24px 14px;
  border-bottom: 1px solid var(--glass-border);
}

.inbox-filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
}

.inbox-filter-pill.active {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.08);
  border-color: rgba(0, 113, 227, 0.2);
}

.inbox-filter-count {
  min-width: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  line-height: 18px;
  text-align: center;
}

.inbox-list-wrap {
  overflow-y: auto;
  padding: 10px 14px 18px;
}

.inbox-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inbox-item {
  position: relative;
  display: flex;
  gap: 12px;
  padding: 13px 14px;
  border-radius: 14px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease;
}

.inbox-item:hover {
  background: rgba(120, 130, 150, 0.07);
  border-color: var(--glass-border);
}

.inbox-item.unread {
  background: rgba(0, 113, 227, 0.045);
}

.inbox-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: var(--text-tertiary);
}

.inbox-item.unread .inbox-dot {
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12);
}

.inbox-item.level-success .inbox-dot { background: var(--status-success, #2e9e5b); }
.inbox-item.level-warning .inbox-dot { background: var(--status-warning, #b25000); }
.inbox-item.level-error .inbox-dot { background: var(--status-danger, #c0392b); }

.inbox-item-main {
  flex: 1;
  min-width: 0;
}

.inbox-item-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.inbox-item-title {
  font-size: 13.5px;
  font-weight: 650;
  color: var(--text-primary);
}

.inbox-verdict {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
}

.inbox-verdict.verdict-passed {
  color: var(--status-success, #2e9e5b);
  border-color: rgba(46, 158, 91, 0.3);
  background: rgba(46, 158, 91, 0.08);
}

.inbox-verdict.verdict-blocked {
  color: var(--status-danger, #c0392b);
  border-color: rgba(192, 57, 43, 0.3);
  background: rgba(192, 57, 43, 0.08);
}

.inbox-verdict.verdict-passed_degraded {
  color: var(--status-warning, #b25000);
  border-color: rgba(178, 80, 0, 0.3);
  background: rgba(178, 80, 0, 0.08);
}

.inbox-item-content {
  margin: 5px 0 6px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-secondary);
  word-break: break-word;
}

.inbox-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.inbox-delete-btn {
  align-self: flex-start;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  opacity: 0;
  transition: opacity 0.18s ease, color 0.18s ease;
}

.inbox-item:hover .inbox-delete-btn {
  opacity: 1;
}

.inbox-delete-btn:hover {
  color: var(--status-danger, #c0392b);
}

.inbox-empty {
  padding: 42px 20px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 12.5px;
}

.inbox-empty-title {
  font-size: 14px;
  font-weight: 650;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.inbox-empty-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
}

.inbox-fade-enter-active,
.inbox-fade-leave-active {
  transition: opacity 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.inbox-fade-enter-from,
.inbox-fade-leave-to {
  opacity: 0;
}

[data-theme='dark'] .inbox-window {
  background: rgba(18, 20, 29, 0.94);
}

@media (max-width: 640px) {
  .inbox-backdrop { padding: 12px; }
  .inbox-window { max-height: 86vh; }
  .inbox-head { padding: 18px 18px 12px; }
  .inbox-filter-row { padding: 0 18px 12px; }
  .inbox-list-wrap { padding: 8px 8px 14px; }
}
</style>
