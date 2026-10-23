<template>
  <!--
    A workflow node rendered as a card.
    A node is either a single document ("文书") or a composite subgraph ("子图") that
    groups several documents to accomplish one business outcome.
  -->
  <div
    class="glass-card sop-node-card opc-card-shell opc-card"
    :class="{ 'sop-node-card-subgraph': node.kind === 'subgraph' }"
    @mousemove="handleMouseMove"
    @click="$emit('select', node)"
    @keydown.enter="$emit('open', node)"
  >
    <!-- Card Top: Icon & Basic Info -->
    <div class="card-header-row">
      <div class="app-icon-wrapper opc-card-icon">
        <div class="app-icon-fallback" :style="iconStyle">
          {{ node.kind === 'subgraph' ? '⊞' : '§' }}
        </div>
      </div>

      <div class="card-title-group">
        <div class="card-title-line">
          <h3 class="sop-node-title" :title="node.name">{{ node.name }}</h3>
          <span v-if="node.kind === 'subgraph'" class="sop-node-kind-badge">
            子图 · {{ childCount }} 份文书
          </span>
        </div>
        <div class="card-badges-line">
          <span class="badge-cat">{{ categoryLabel }}</span>
          <span class="sop-node-stage">阶段 {{ String(node.stage).padStart(2, '0') }}</span>
          <span v-if="node.kind === 'document'" class="badge-field-count">
            {{ (node.required_fields || []).length }} 个待填项
          </span>
        </div>
      </div>
    </div>

    <!-- Card Body -->
    <div class="card-body">
      <p class="sop-node-desc">{{ node.description }}</p>
    </div>

    <!-- Outcome: what you get after finishing this node -->
    <div v-if="node.outcome" class="sop-node-outcome">
      <span class="sop-node-outcome-label">完成后你会得到</span>
      <span class="sop-node-outcome-text">{{ node.outcome }}</span>
    </div>

    <!-- Card Footer -->
    <div class="card-footer-row" @click.stop>
      <div class="author-cell">
        <div class="author-avatar" :style="avatarStyle">{{ initials }}</div>
        <div class="author-text">
          <span class="author-name">{{ stageName }}</span>
          <span class="publish-time">{{ node.kind === 'subgraph' ? '复合子图' : '标准文书' }}</span>
        </div>
      </div>

      <div class="card-actions-cell">
        <span v-if="node.kind === 'subgraph'" class="sop-node-child-pill">
          {{ childCount }} 份
        </span>
        <button
          type="button"
          class="btn-liquid-outline btn-detail-sm"
          @click.stop="$emit('open', node)"
        >
          {{ node.kind === 'subgraph' ? '展开子图' : '去填写' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  node: { type: Object, required: true },
  stages: { type: Array, default: () => [] },
});

// `select` = highlight the node in the sidebar (read-only preview)
// `open`   = the explicit action: open the fill studio (or expand a subgraph)
defineEmits(['select', 'open']);

const CATEGORY_LABELS = {
  ENTITY: '主体登记',
  TAX: '税务合规',
  LEGAL: '法律文书',
  BANK: '银行账户',
  IP: '知识产权',
  CROSS_BORDER: '跨境出海',
  FINANCE: '财务票据',
};

const categoryLabel = computed(() => CATEGORY_LABELS[props.node.category] || props.node.category);

const childCount = computed(() => (props.node.children || []).length);

const stageName = computed(() => {
  const stage = props.stages.find((s) => s.stage === props.node.stage);
  if (!stage) return `阶段 ${props.node.stage}`;
  return stage.name.replace(/^阶段\s*\d+[:：]\s*/, '');
});

const initials = computed(() => {
  const name = props.node.name || '';
  const clean = name.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
  return clean.slice(0, 2) || '文';
});

const iconStyle = computed(() => ({
  background: 'linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%)',
  color: 'var(--text-secondary)',
  border: '1px solid var(--glass-border-subtle)',
}));

const avatarStyle = computed(() => ({
  background: 'linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%)',
  color: 'var(--text-secondary)',
  border: '1px solid var(--glass-border-subtle)',
}));

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  card.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`);
  card.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`);
}
</script>

<style scoped>
/* 卡片外壳由全局 .opc-card-shell 承载（统一 18px 20px / radius / glass / hover） */

.sop-node-card-subgraph {
  border-style: solid;
  border-color: var(--accent-glow);
  background: linear-gradient(150deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
}

/* 图标 tile：尺寸由全局 .opc-card-icon 承载 */
.app-icon-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 19px;
}

.sop-node-title {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-node-kind-badge {
  font-size: 10.5px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: var(--accent-glass);
  color: var(--accent);
  border: 1px solid var(--accent-glow);
  flex-shrink: 0;
}

.sop-node-stage {
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  padding: 1px 7px;
  border-radius: 6px;
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
  border: 1px solid var(--glass-border-subtle);
}

.badge-field-count {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--status-success-soft);
  color: var(--status-success);
  border: 1px solid var(--status-success-soft);
}

.sop-node-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.55;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-node-outcome {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px 11px;
  border-radius: 8px;
  background: var(--status-success-soft);
  border: 1px solid var(--status-success-soft);
}

.sop-node-outcome-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--status-success);
  letter-spacing: 0.02em;
}

.sop-node-outcome-text {
  font-size: 12px;
  line-height: 1.55;
  color: var(--text-primary);
}

/* Card Footer: 全局统一 (.card-footer-row / .author-* / .card-actions-cell) */
.author-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10.5px;
  font-weight: 700;
  flex-shrink: 0;
}

.sop-node-child-pill {
  font-size: 11.5px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--accent-glass);
  color: var(--accent);
  border: 1px solid var(--accent-glow);
}

.btn-detail-sm {
  padding: 4px 12px;
  font-size: 11.5px;
  font-weight: 500;
  border-radius: var(--radius-full);
}

[data-theme="dark"] .sop-node-card {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .sop-node-card-subgraph {
  background: linear-gradient(150deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
  border-color: var(--accent-glow);
}
</style>
