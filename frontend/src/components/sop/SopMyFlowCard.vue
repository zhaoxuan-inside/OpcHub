<template>
  <!--
    A maker's own flow rendered as a card.

    Mirrors the platform flow card so both workspaces share one visual idiom;
    the "我的流程" badge replaces the official one, and the footer carries
    edit / delete instead of community counters.
  -->
  <div
    class="glass-card sop-flow-card sop-myflow-card opc-card-shell opc-card"
    @mousemove="handleMouseMove"
    @click="$emit('open', flow)"
  >
    <!-- Card head: name + private badge -->
    <div class="sop-flow-card-head">
      <h3 class="sop-flow-card-title" :title="flow.name">{{ flow.name }}</h3>
      <span class="sop-myflow-badge" title="仅自己可见的私有流程">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
        我的流程
      </span>
    </div>

    <!-- Provenance: owner + visibility -->
    <div class="sop-flow-card-provenance">
      <div class="sop-flow-author">
        <div class="sop-flow-author-avatar sop-myflow-avatar">我</div>
        <div class="sop-flow-author-text">
          <span class="sop-flow-author-name">我</span>
          <span class="sop-flow-author-title">流程编排人</span>
        </div>
      </div>
      <div class="sop-flow-org">
        <span class="sop-flow-org-label">可见范围</span>
        <span class="sop-flow-org-name">私有 · 仅自己可见</span>
      </div>
    </div>

    <!-- Summary -->
    <p class="sop-flow-card-summary" :title="flow.description">
      {{ flow.description || '暂无说明，点击查看流程步骤。' }}
    </p>

    <!-- Composition -->
    <div class="sop-flow-card-meta">
      <span class="sop-flow-chip">{{ flow.step_count }} 个步骤</span>
      <span v-for="stage in flow.stages" :key="stage" class="sop-flow-chip sop-flow-chip-stage">
        阶段 {{ String(stage).padStart(2, '0') }}
      </span>
    </div>

    <!-- Created date -->
    <div class="sop-flow-card-date">
      <span class="sop-flow-date-label">创建时间</span>
      <span class="sop-flow-date-value">{{ formatDate(flow.published_at) }}</span>
    </div>

    <!-- Footer: state + actions -->
    <div class="sop-flow-card-footer" @click.stop>
      <span class="sop-myflow-state" :class="statusClass" :title="statusHint">{{ statusLabel }}</span>

      <button
        type="button"
        class="sop-flow-action"
        @click="$emit('edit', flow)"
        title="编辑这份流程"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
        <span>编辑</span>
      </button>

      <button
        type="button"
        class="sop-flow-action sop-myflow-publish"
        :class="{ disabled: !canPublish }"
        :disabled="!canPublish"
        @click="$emit('publish', flow)"
        :title="publishTitle"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
        </svg>
        <span>{{ publishLabel }}</span>
      </button>

      <button
        type="button"
        class="sop-flow-action sop-myflow-delete"
        @click="$emit('delete', flow)"
        title="删除这份流程"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
        <span>删除</span>
      </button>

      <span class="sop-flow-card-fields">{{ flow.step_count }} 个步骤</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  flow: { type: Object, required: true },
});

defineEmits(['open', 'edit', 'delete', 'publish']);

const FLOW_STATUS_LABELS = {
  DRAFT: '草稿',
  ACTIVE: '待发布',
  PENDING_REVIEW: '审核中',
  PUBLISHED: '已发布',
  REJECTED: '未通过',
};

const statusKey = computed(() => props.flow.status || 'ACTIVE');
const statusLabel = computed(() => FLOW_STATUS_LABELS[statusKey.value] || statusKey.value);

/** A private flow can be published while DRAFT/ACTIVE (or re-published after rejection/editing). */
const canPublish = computed(() => ['DRAFT', 'ACTIVE', 'REJECTED'].includes(statusKey.value));

const publishLabel = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return '审核中';
  if (statusKey.value === 'PUBLISHED') return '已发布';
  return '发布';
});

const publishTitle = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return '该流程正在平台审核中，通过后将发布至流程向导';
  if (statusKey.value === 'PUBLISHED') return '该流程已发布至流程向导';
  return '发布至流程向导（提交后进入待审核状态）';
});

const statusHint = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return '已提交审核，等待平台合法性与敏感词检查';
  if (statusKey.value === 'PUBLISHED') return '审核通过，已发布至流程向导';
  if (statusKey.value === 'REJECTED') return '审核未通过，可编辑修改后重新发布';
  return '私有流程，可发布至流程向导';
});

const statusClass = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return 'pending';
  if (statusKey.value === 'PUBLISHED') return 'published';
  if (statusKey.value === 'REJECTED') return 'rejected';
  if (statusKey.value === 'DRAFT') return 'draft';
  return 'ready';
});

function formatDate(isoStr) {
  if (!isoStr) return '未标注';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return '未标注';
  }
}

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  card.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`);
  card.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`);
}
</script>

<style scoped>
/* 卡片外壳由全局 .opc-card-shell 承载（统一 18px 20px / radius / glass / hover） */
.sop-flow-card {
  gap: 10px;
}

.sop-flow-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.sop-flow-card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sop-flow-card-provenance {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sop-flow-author {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.sop-flow-author-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.sop-flow-author-text {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.sop-flow-author-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.sop-flow-author-title {
  font-size: 10.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-flow-org {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.sop-flow-org-label {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.sop-flow-org-name {
  font-size: 11.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-flow-card-summary {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sop-flow-card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.sop-flow-chip {
  font-size: 10.5px;
  font-weight: 500;
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-secondary);
}

.sop-flow-chip-stage {
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

.sop-flow-card-date {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.sop-flow-date-label {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

.sop-flow-date-value {
  font-size: 11px;
  color: var(--text-secondary);
  font-family: var(--font-mono, monospace);
}

.sop-flow-card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--glass-border-subtle);
  flex-wrap: wrap;
}

.sop-flow-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s ease;
}

.sop-flow-action:hover {
  border-color: rgba(0, 113, 227, 0.3);
  color: var(--accent);
}

.sop-flow-card-fields {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.sop-myflow-state {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.sop-myflow-state.ready {
  background: var(--status-success-soft);
  border-color: var(--status-success-soft);
  color: var(--status-success);
}

.sop-myflow-state.draft {
  background: var(--glass-surface-subtle);
  border-color: var(--glass-border-subtle);
  color: var(--text-tertiary);
}

.sop-myflow-state.pending {
  background: var(--status-warning-soft);
  border-color: var(--status-warning-soft);
  color: var(--status-warning);
}

.sop-myflow-state.published {
  background: var(--accent-glass);
  border-color: var(--accent-glow);
  color: var(--accent);
}

.sop-myflow-state.rejected {
  background: var(--status-danger-soft);
  border-color: var(--status-danger-soft);
  color: var(--status-danger);
}

.sop-myflow-publish {
  color: var(--accent, #0071e3);
  border-color: rgba(0, 113, 227, 0.25);
}

.sop-myflow-publish:hover:not(:disabled) {
  background: rgba(0, 113, 227, 0.1);
  border-color: rgba(0, 113, 227, 0.45);
}

.sop-flow-action.disabled {
  opacity: 0.55;
  cursor: not-allowed;
  color: var(--text-tertiary);
  border-color: var(--glass-border-subtle);
}

[data-theme="dark"] .sop-flow-card {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}

.sop-myflow-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: var(--status-warning-soft);
  color: var(--status-warning);
  border: 1px solid var(--status-warning-soft);
  flex-shrink: 0;
  white-space: nowrap;
}

.sop-myflow-avatar {
  background: linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
  border: 1px solid var(--glass-border-subtle);
}

.sop-myflow-delete:hover {
  border-color: var(--status-danger-soft);
  color: var(--status-danger);
}
</style>
