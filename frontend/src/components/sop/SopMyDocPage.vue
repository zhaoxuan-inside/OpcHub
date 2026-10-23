<template>
  <!--
    Full-page private-document reader (replaces the workspace, not a modal).

    Mirrors the standard document page's visual language: the same glass header
    with breadcrumb, the same paper surface — except the content is the maker's
    own rendered document and the actions are delete instead of export.
  -->
  <div class="sop-doc-page">
    <div class="glass-box sop-doc-header">
      <div class="sop-doc-header-left">
        <button class="sop-doc-back" @click="$emit('back')" title="返回我的文书">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
        </button>
        <div class="sop-doc-heading">
          <div class="sop-doc-breadcrumb">
            <span class="sop-doc-crumb-link" @click="$emit('back')">流程文书</span>
            <span class="sop-doc-crumb-sep">/</span>
            <span class="sop-doc-crumb-current">{{ doc.document_title }}</span>
          </div>
          <div class="sop-doc-meta">
            <span class="sop-doc-category-pill owner">私有文书</span>
            <span class="sop-doc-stage">{{ (doc.status || 'READY') }}</span>
            <span class="sop-doc-dot">·</span>
            <span>{{ templateName }}</span>
            <span class="sop-doc-dot">·</span>
            <span>生成于 {{ formatDate(doc.created_at) }}</span>
          </div>
        </div>
      </div>

      <div class="sop-doc-header-actions">
        <button type="button" class="btn-liquid-outline sop-doc-action danger" @click="$emit('delete', doc)" title="删除这份文书">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          <span>删除</span>
        </button>
      </div>
    </div>

    <div class="sop-doc-body sop-doc-body-single">
      <section class="sop-doc-preview-pane">
        <div class="sop-doc-pane-label">文书正文</div>

        <div class="sop-doc-paper">
          <pre class="sop-doc-paper-content">{{ doc.rendered_content || '该文书暂无正文内容。' }}</pre>
        </div>

        <div class="sop-doc-outcome">
          <span class="sop-doc-outcome-label">合规状态</span>
          <span>{{ doc.compliance_passed ? '要素齐备，已通过合规校验。' : '存在缺失要素，建议回到对应标准文书补齐后重新生成。' }}</span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  doc: { type: Object, default: null },
  templateNameOf: { type: Function, default: null },
});

defineEmits(['back', 'delete']);

const templateName = computed(
  () => props.templateNameOf?.(props.doc?.template_id) || props.doc?.template_id || '标准文书'
);

function formatDate(isoStr) {
  if (!isoStr) return '未标注';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  } catch {
    return '未标注';
  }
}
</script>

<style scoped>
.sop-doc-page {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.sop-doc-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 22px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.sop-doc-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.sop-doc-back {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.sop-doc-back:hover {
  border-color: rgba(0, 113, 227, 0.35);
  color: var(--accent);
}

.sop-doc-heading {
  min-width: 0;
}

.sop-doc-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  margin-bottom: 3px;
}

.sop-doc-crumb-link {
  color: var(--text-secondary);
  cursor: pointer;
}

.sop-doc-crumb-link:hover {
  color: var(--accent);
}

.sop-doc-crumb-sep {
  color: var(--text-tertiary);
}

.sop-doc-crumb-current {
  color: var(--text-primary);
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-doc-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  color: var(--text-tertiary);
  flex-wrap: wrap;
}

.sop-doc-category-pill {
  font-size: 11px;
  font-weight: 500;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent, #0071e3);
  border: 1px solid rgba(0, 113, 227, 0.18);
}

.sop-doc-category-pill.owner {
  background: var(--status-warning-soft);
  color: var(--status-warning);
  border-color: var(--status-warning-soft);
}

.sop-doc-stage {
  font-family: var(--font-mono, monospace);
}

.sop-doc-dot {
  opacity: 0.6;
}

.sop-doc-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.sop-doc-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: var(--radius-full);
}

.sop-doc-action.danger:hover {
  border-color: var(--status-danger-soft);
  color: var(--status-danger);
}

.sop-doc-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  overflow: hidden;
}

.sop-doc-preview-pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 22px;
  border-radius: var(--radius-lg, 16px);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  scrollbar-width: none;
}

.sop-doc-preview-pane::-webkit-scrollbar {
  display: none;
}

.sop-doc-pane-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-shrink: 0;
}

.sop-doc-paper {
  flex: 1;
  min-height: 240px;
  overflow-y: auto;
  background: var(--glass-surface-solid);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  padding: 24px;
  box-shadow: var(--glass-shadow);
}

.sop-doc-paper-content {
  margin: 0;
  font-family: var(--font-mono, monospace);
  font-size: 12.5px;
  line-height: 1.95;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.sop-doc-outcome {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px 13px;
  border-radius: 9px;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-primary);
  flex-shrink: 0;
  background: var(--status-success-soft);
  border: 1px solid var(--status-success-soft);
}

.sop-doc-outcome-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}
</style>
