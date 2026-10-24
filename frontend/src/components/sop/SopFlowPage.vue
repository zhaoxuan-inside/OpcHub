<template>
  <!--
    Full-page flow reader (replaces the workspace, not a modal).

    Mirrors the standard document page's visual language: the same glass header
    with breadcrumb, the same pane structure, and the same ordered child list —
    except each row is one document step of the flow.
  -->
  <div class="sop-doc-page">
    <div class="glass-box sop-doc-header">
      <div class="sop-doc-header-left">
        <button class="sop-doc-back" @click="$emit('back')" title="返回流程向导">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
        </button>
        <div class="sop-doc-heading">
          <div class="sop-doc-breadcrumb">
            <span class="sop-doc-crumb-link" @click="$emit('back')">流程文书</span>
            <span class="sop-doc-crumb-sep">/</span>
            <span class="sop-doc-crumb-current">{{ flow.name }}</span>
          </div>
          <div class="sop-doc-meta">
            <span v-if="flow.is_official" class="sop-doc-category-pill">官方认证</span>
            <span v-if="owner" class="sop-doc-category-pill owner">我的流程</span>
            <span class="sop-doc-category-pill">{{ categoryLabel(flow.category) }}</span>
            <span class="sop-doc-stage">阶段 {{ stageRange }}</span>
            <span class="sop-doc-dot">·</span>
            <span>{{ (steps || []).length }} 个步骤</span>
            <span class="sop-doc-dot">·</span>
            <span>{{ flow.publisher_org || 'OpcHub 平台' }}</span>
          </div>
        </div>
      </div>

      <div v-if="owner" class="sop-doc-header-actions">
        <button type="button" class="btn-liquid-outline sop-doc-action" @click="$emit('edit', flow)" title="编辑这份流程">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
          <span>编辑</span>
        </button>
        <button type="button" class="btn-liquid-outline sop-doc-action danger" @click="$emit('delete', flow)" title="删除这份流程">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          <span>删除</span>
        </button>
      </div>
    </div>

    <div class="sop-doc-body sop-doc-body-single">
      <section class="sop-doc-form-pane">
        <div class="sop-doc-pane-label">流程步骤</div>

        <div v-if="flow.description" class="sop-doc-intro">{{ flow.description }}</div>

        <ContentInteractionBar
          v-if="!owner && flow.id"
          target-type="SOP_FLOW"
          :target-id="flow.id"
          :target-title="flow.name"
          auto-load
          :authenticated="authenticated"
          @require-login="$emit('require-login')"
          @toast="$emit('toast', $event)"
        />

        <div v-if="flow.outcome" class="sop-doc-outcome">
          <span class="sop-doc-outcome-label">完成整个流程，你会得到</span>
          <span>{{ flow.outcome }}</span>
        </div>

        <div v-if="(flow.unlocks || []).length" class="sop-doc-next-hint">
          <span class="sop-doc-outcome-label">解锁能力</span>
          <span>{{ (flow.unlocks || []).join('；') }}</span>
        </div>

        <div class="sop-doc-child-list">
          <button
            v-for="step in (steps || [])"
            :key="step.node_id"
            type="button"
            class="sop-doc-child"
            @click="$emit('open-step', step)"
          >
            <span class="sop-doc-child-order">{{ step.order }}</span>
            <div class="sop-doc-child-body">
              <div class="sop-doc-child-name">{{ step.name }}</div>
              <div class="sop-doc-child-meta">
                阶段 {{ String(step.stage || 0).padStart(2, '0') }}
                <span class="sop-doc-dot">·</span>
                {{ (step.required_fields || []).length }} 个待填要素
                <template v-if="step.note">
                  <span class="sop-doc-dot">·</span>
                  {{ step.note }}
                </template>
              </div>
            </div>
            <span class="sop-doc-child-go">去填写 ›</span>
          </button>
        </div>

        <!-- 展示页面免责声明 -->
        <ContentDisclaimer type="sop" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
import ContentDisclaimer from '@/components/ContentDisclaimer.vue';

const props = defineProps({
  detail: { type: Object, default: null },
  owner: { type: Boolean, default: false },
  authenticated: { type: Boolean, default: false },
});

defineEmits(['back', 'open-step', 'edit', 'delete', 'require-login', 'toast']);

const FLOW_CATEGORY_LABELS = {
  ENTITY: '主体设立',
  IP: '科技资质',
  CROSS_BORDER: '跨境出海',
  COMPLIANCE: '全生命周期',
  MY: '私有流程',
};

const flow = computed(() => props.detail?.template || {});
const steps = computed(() => props.detail?.steps || []);

const stageRange = computed(() => {
  const list = [...(flow.value.stages || [])].sort((a, b) => a - b);
  if (!list.length) return '--';
  if (list.length === 1) return String(list[0]).padStart(2, '0');
  return `${String(list[0]).padStart(2, '0')}-${String(list[list.length - 1]).padStart(2, '0')}`;
});

function categoryLabel(category) {
  return FLOW_CATEGORY_LABELS[category] || category || '标准流程';
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

.sop-doc-action.danger:hover {
  border-color: var(--status-danger-soft);
  color: var(--status-danger);
}

.sop-doc-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.sop-doc-stage {
  font-family: var(--font-mono, monospace);
}

.sop-doc-dot {
  opacity: 0.6;
}

.sop-doc-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  overflow: hidden;
}

.sop-doc-body-single {
  grid-template-columns: 1fr;
}

.sop-doc-form-pane {
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

.sop-doc-form-pane::-webkit-scrollbar {
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

.sop-doc-intro {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-secondary);
  padding: 11px 13px;
  border-radius: 9px;
  background: var(--glass-surface-subtle);
}

.sop-doc-outcome,
.sop-doc-next-hint {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px 13px;
  border-radius: 9px;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-primary);
  flex-shrink: 0;
}

.sop-doc-outcome {
  background: var(--status-success-soft);
  border: 1px solid var(--status-success-soft);
}

.sop-doc-next-hint {
  background: var(--status-warning-soft);
  border: 1px solid var(--status-warning-soft);
}

.sop-doc-outcome-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

/* Ordered document steps — same list idiom as the subgraph composition page */
.sop-doc-child-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sop-doc-child {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.sop-doc-child:hover {
  border-color: rgba(0, 113, 227, 0.35);
  transform: translateY(-1px);
}

.sop-doc-child-order {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono, monospace);
  background: rgba(0, 113, 227, 0.12);
  color: var(--accent);
  border: 1px solid rgba(0, 113, 227, 0.25);
}

.sop-doc-child-body {
  flex: 1;
  min-width: 0;
}

.sop-doc-child-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.sop-doc-child-meta {
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sop-doc-child-go {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  flex-shrink: 0;
}
</style>
