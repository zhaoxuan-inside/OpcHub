<template>
  <!--
    A maker's own saved document rendered as a card.

    Mirrors the standard document card so both workspaces share one visual
    idiom; the "私有文书" badge replaces the official one, and the footer
    carries state + delete instead of community counters.
  -->
  <div
    class="glass-card sop-doc-card sop-mydoc-card opc-card-shell opc-card"
    @mousemove="handleMouseMove"
    @click="$emit('open', doc)"
  >
    <!-- Card head: title + private badge -->
    <div class="sop-doc-card-head">
      <h3 class="sop-doc-card-title" :title="doc.document_title">{{ doc.document_title }}</h3>
      <span class="sop-mydoc-badge" title="仅自己可见的私有文书">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
        私有文书
      </span>
    </div>

    <!-- Provenance: template + status -->
    <div class="sop-doc-card-provenance">
      <div class="sop-doc-author">
        <div class="sop-doc-author-avatar sop-mydoc-avatar">{{ initials }}</div>
        <div class="sop-doc-author-text">
          <span class="sop-doc-author-name">我</span>
          <span class="sop-doc-author-title">文书起草人</span>
        </div>
      </div>
      <div class="sop-doc-org">
        <span class="sop-doc-org-label">使用模板</span>
        <span class="sop-doc-org-name">{{ templateName }}</span>
      </div>
    </div>

    <!-- Summary: first lines of the rendered content -->
    <p class="sop-doc-card-summary" :title="summaryText">{{ summaryText }}</p>

    <!-- Created date -->
    <div class="sop-doc-card-date">
      <span class="sop-doc-date-label">生成时间</span>
      <span class="sop-doc-date-value">{{ formatDate(doc.created_at) }}</span>
    </div>

    <!-- Card footer: state + publish + delete -->
    <div class="sop-doc-card-footer" @click.stop>
      <span class="sop-mydoc-state" :class="statusClass" :title="statusHint">
        {{ statusLabel }}
      </span>
      <span
        class="sop-mydoc-compliance"
        :title="doc.compliance_passed ? '要素齐备，已通过合规校验' : '存在缺失要素'"
      >
        {{ doc.compliance_passed ? '合规校验通过' : '要素缺失' }}
      </span>

      <div class="sop-doc-card-actions">
        <button
          type="button"
          class="sop-doc-action sop-mydoc-publish"
          :class="{ disabled: !canPublish }"
          :disabled="!canPublish"
          @click="$emit('publish', doc)"
          :title="publishTitle"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
          <span>{{ publishLabel }}</span>
        </button>

        <button
          type="button"
          class="sop-doc-action sop-mydoc-delete"
          @click="$emit('delete', doc)"
          title="删除这份文书"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          <span>删除</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  doc: { type: Object, required: true },
  templateNameOf: { type: Function, default: null },
});

defineEmits(['open', 'delete', 'publish']);

const DOC_STATUS_LABELS = {
  READY: '待发布',
  PENDING_REVIEW: '审核中',
  PUBLISHED: '已发布',
  REJECTED: '未通过',
};

const statusKey = computed(() => props.doc.status || 'READY');
const statusLabel = computed(() => DOC_STATUS_LABELS[statusKey.value] || statusKey.value);

/** A private document can be published while READY (or re-published after a rejection). */
const canPublish = computed(() => ['READY', 'REJECTED'].includes(statusKey.value));

const publishLabel = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return '审核中';
  if (statusKey.value === 'PUBLISHED') return '已发布';
  return '发布';
});

const publishTitle = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return '该文书正在平台审核中，通过后将发布至标准文书库';
  if (statusKey.value === 'PUBLISHED') return '该文书已发布至标准文书库';
  return '发布至标准文书库（提交后进入待审核状态）';
});

const statusHint = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return '已提交审核，等待平台合规审核';
  if (statusKey.value === 'PUBLISHED') return '审核通过，已发布至标准文书库';
  if (statusKey.value === 'REJECTED') return '审核未通过，可修改后重新发布';
  return '私有文书，可发布至标准文书库';
});

const statusClass = computed(() => {
  if (statusKey.value === 'PENDING_REVIEW') return 'pending';
  if (statusKey.value === 'PUBLISHED') return 'published';
  if (statusKey.value === 'REJECTED') return 'rejected';
  return 'ready';
});

const templateName = computed(
  () => props.templateNameOf?.(props.doc.template_id) || props.doc.template_id || '标准文书'
);

const summaryText = computed(() => {
  const content = props.doc.rendered_content || '';
  const flat = content.replace(/\s+/g, ' ').trim();
  return flat || '已保存的私有文书，点击查看全文。';
});

const initials = computed(() => '我');

function formatDate(isoStr) {
  if (!isoStr) return '未标注';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
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
.sop-doc-card {
  gap: 10px;
}

.sop-doc-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.sop-doc-card-title {
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

.sop-doc-card-provenance {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sop-doc-author {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.sop-doc-author-avatar {
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

.sop-doc-author-text {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.sop-doc-author-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.sop-doc-author-title {
  font-size: 10.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-doc-org {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.sop-doc-org-label {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.sop-doc-org-name {
  font-size: 11.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-doc-card-summary {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sop-doc-card-date {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.sop-doc-date-label {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

.sop-doc-date-value {
  font-size: 11px;
  color: var(--text-secondary);
  font-family: var(--font-mono, monospace);
}

.sop-doc-card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--glass-border-subtle);
  flex-wrap: wrap;
}

.sop-doc-action {
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

[data-theme="dark"] .sop-doc-card {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}

.sop-mydoc-badge {
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

.sop-mydoc-avatar {
  background: linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
  border: 1px solid var(--glass-border-subtle);
}

.sop-mydoc-state {
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

.sop-mydoc-state.ready {
  background: var(--status-success-soft);
  border-color: var(--status-success-soft);
  color: var(--status-success);
}

.sop-mydoc-state.pending {
  background: var(--status-warning-soft);
  border-color: var(--status-warning-soft);
  color: var(--status-warning);
}

.sop-mydoc-state.published {
  background: var(--accent-glass);
  border-color: var(--accent-glow);
  color: var(--accent);
}

.sop-mydoc-state.rejected {
  background: var(--status-danger-soft);
  border-color: var(--status-danger-soft);
  color: var(--status-danger);
}

.sop-doc-card-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}

.sop-mydoc-publish {
  color: var(--accent, #0071e3);
  border-color: rgba(0, 113, 227, 0.25);
}

.sop-mydoc-publish:hover:not(:disabled) {
  background: rgba(0, 113, 227, 0.1);
  border-color: rgba(0, 113, 227, 0.45);
}

.sop-doc-action.disabled {
  opacity: 0.55;
  cursor: not-allowed;
  color: var(--text-tertiary);
  border-color: var(--glass-border-subtle);
}

.sop-mydoc-compliance {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  background: var(--status-success-soft);
  border: 1px solid var(--status-success-soft);
  color: var(--status-success);
}

.sop-mydoc-delete:hover {
  border-color: var(--status-danger-soft);
  color: var(--status-danger);
}
</style>
