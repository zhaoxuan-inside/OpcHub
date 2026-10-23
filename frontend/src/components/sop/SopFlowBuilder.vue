<template>
  <!--
    Flow builder: compose a personal document flow.
    The maker picks nodes from the catalog (documents or subgraphs), orders them,
    and optionally anchors the flow to a business goal.
  -->
  <div class="sop-builder">
    <!-- Flow meta -->
    <div class="sop-builder-meta">
      <div class="sop-builder-field">
        <label class="sop-builder-label">流程名称 <span class="sop-req">*</span></label>
        <input
          v-model="form.name"
          type="text"
          class="sop-builder-input"
          placeholder="如：我的出海 SaaS 落地流程"
        />
      </div>
      <div class="sop-builder-field">
        <label class="sop-builder-label">流程说明</label>
        <input
          v-model="form.description"
          type="text"
          class="sop-builder-input"
          placeholder="这份流程要达成什么"
        />
      </div>
      <div class="sop-builder-field">
        <label class="sop-builder-label">关联目标（可选）</label>
        <select v-model="form.goal_id" class="sop-builder-input">
          <option value="">不关联目标</option>
          <option v-for="g in goals" :key="g.id" :value="g.id">{{ g.title }}</option>
        </select>
      </div>
    </div>

    <!-- Selected nodes -->
    <div class="sop-builder-section">
      <div class="sop-builder-section-head">
        <span class="sop-builder-section-title">流程节点（{{ form.node_refs.length }}）</span>
        <span class="sop-builder-section-hint">按顺序执行，可拖动调整</span>
      </div>

      <div v-if="!form.node_refs.length" class="sop-builder-empty">
        还没有选择节点。从下方节点库中挑选文书或子图。
      </div>

      <ul v-else class="sop-builder-list">
        <li v-for="(ref, idx) in form.node_refs" :key="ref.node_id" class="sop-builder-item">
          <span class="sop-builder-item-order">{{ idx + 1 }}</span>
          <span class="sop-builder-item-name">{{ nodeName(ref.node_id) }}</span>
          <span class="sop-builder-item-kind">{{ nodeKind(ref.node_id) }}</span>
          <label class="sop-builder-required">
            <input v-model="ref.required" type="checkbox" />
            <span>必办</span>
          </label>
          <span class="sop-builder-item-actions">
            <button type="button" class="sop-builder-move" :disabled="idx === 0" @click="move(idx, -1)" title="上移"><OpcIcon name="arrow-up" :size="13" /></button>
            <button type="button" class="sop-builder-move" :disabled="idx === form.node_refs.length - 1" @click="move(idx, 1)" title="下移"><OpcIcon name="arrow-down" :size="13" /></button>
            <button type="button" class="sop-builder-remove" @click="remove(idx)" title="移除"><OpcIcon name="close" :size="13" /></button>
          </span>
        </li>
      </ul>
    </div>

    <!-- Node catalog -->
    <div class="sop-builder-section">
      <div class="sop-builder-section-head">
        <span class="sop-builder-section-title">节点库</span>
        <div class="sop-builder-catalog-filter">
          <button
            v-for="cat in categories"
            :key="cat.key"
            type="button"
            :class="['sop-builder-cat', { active: catalogCategory === cat.key }]"
            @click="catalogCategory = cat.key"
          >
            {{ cat.label }}
          </button>
        </div>
      </div>

      <div class="sop-builder-catalog">
        <button
          v-for="node in catalogNodes"
          :key="node.id"
          type="button"
          class="sop-builder-catalog-item"
          :class="{ added: isSelected(node.id) }"
          :disabled="isSelected(node.id)"
          @click="add(node)"
        >
          <span class="sop-builder-catalog-name">{{ node.name }}</span>
          <span class="sop-builder-catalog-meta">
            {{ node.kind === 'subgraph' ? `子图 · ${(node.children || []).length} 份` : `${(node.required_fields || []).length} 个待填项` }}
          </span>
        </button>
      </div>
    </div>

    <!-- Actions -->
    <div class="sop-builder-actions">
      <button type="button" class="btn-liquid-outline submit-btn" @click="$emit('cancel')">取消</button>
      <button type="button" class="btn-liquid submit-btn" :disabled="submitting" @click="submit">
        {{ submitting ? '保存中...' : '保存流程' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';

const props = defineProps({
  goals: { type: Array, default: () => [] },
  nodes: { type: Array, default: () => [] },
  initial: { type: Object, default: null },
  submitting: { type: Boolean, default: false },
});

const emit = defineEmits(['submit', 'cancel']);

const CATEGORY_LABELS = {
  ENTITY: '主体登记',
  TAX: '税务合规',
  LEGAL: '法律文书',
  BANK: '银行账户',
  IP: '知识产权',
  CROSS_BORDER: '跨境出海',
  FINANCE: '财务票据',
};

const form = reactive({
  name: '',
  description: '',
  goal_id: '',
  node_refs: [],
});

const catalogCategory = ref('ALL');

watch(
  () => props.initial,
  (init) => {
    form.name = init?.name || '';
    form.description = init?.description || '';
    form.goal_id = init?.goal_id || '';
    form.node_refs = (init?.node_refs || []).map((r) => ({ ...r }));
  },
  { immediate: true }
);

const categories = computed(() => {
  const used = new Set(props.nodes.map((n) => n.category));
  const list = [{ key: 'ALL', label: '全部' }];
  for (const [key, label] of Object.entries(CATEGORY_LABELS)) {
    if (used.has(key)) list.push({ key, label });
  }
  return list;
});

const catalogNodes = computed(() =>
  props.nodes.filter(
    (n) => catalogCategory.value === 'ALL' || n.category === catalogCategory.value
  )
);

function nodeName(nodeId) {
  const node = props.nodes.find((n) => n.id === nodeId);
  return node ? node.name : nodeId;
}

function nodeKind(nodeId) {
  const node = props.nodes.find((n) => n.id === nodeId);
  return node && node.kind === 'subgraph' ? '子图' : '文书';
}

function isSelected(nodeId) {
  return form.node_refs.some((r) => r.node_id === nodeId);
}

function add(node) {
  if (isSelected(node.id)) return;
  form.node_refs.push({ node_id: node.id, required: true, note: '' });
}

function remove(index) {
  form.node_refs.splice(index, 1);
}

function move(index, delta) {
  const target = index + delta;
  if (target < 0 || target >= form.node_refs.length) return;
  const [item] = form.node_refs.splice(index, 1);
  form.node_refs.splice(target, 0, item);
}

function submit() {
  emit('submit', {
    name: form.name.trim(),
    description: form.description.trim(),
    goal_id: form.goal_id || null,
    node_refs: form.node_refs.map((r) => ({ ...r })),
  });
}
</script>

<style scoped>
.sop-builder {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sop-builder-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.sop-builder-field {
  flex: 1;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sop-builder-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.sop-req {
  color: var(--status-danger);
}

.sop-builder-input {
  width: 100%;
  padding: 8px 11px;
  border-radius: var(--radius-sm, 10px);
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  color: var(--text-primary);
  font-size: 12.5px;
  box-sizing: border-box;
  outline: none;
  transition: all 0.2s ease;
}

.sop-builder-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 8px var(--accent-glow);
  background: var(--glass-surface);
}

.sop-builder-section {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.sop-builder-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.sop-builder-section-title {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.sop-builder-section-hint {
  font-size: 11px;
  color: var(--text-tertiary);
}

.sop-builder-empty {
  padding: 18px 14px;
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  border-radius: 10px;
  background: var(--glass-surface-subtle);
  border: 1px dashed var(--glass-border-subtle);
}

.sop-builder-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.sop-builder-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 9px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.sop-builder-item-order {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10.5px;
  font-weight: 700;
  font-family: var(--font-mono, monospace);
  background: rgba(0, 113, 227, 0.12);
  color: var(--accent);
  border: 1px solid rgba(0, 113, 227, 0.25);
}

.sop-builder-item-name {
  flex: 1;
  min-width: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-builder-item-kind {
  font-size: 10.5px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
  flex-shrink: 0;
}

.sop-builder-required {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  flex-shrink: 0;
  cursor: pointer;
}

.sop-builder-item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.sop-builder-move,
.sop-builder-remove {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.16s ease;
}

.sop-builder-move:hover:not(:disabled),
.sop-builder-remove:hover {
  border-color: rgba(0, 113, 227, 0.35);
  color: var(--accent);
}

.sop-builder-move:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.sop-builder-remove:hover {
  border-color: var(--status-danger-soft);
  color: var(--status-danger);
}

.sop-builder-catalog-filter {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.sop-builder-cat {
  padding: 3px 10px;
  font-size: 11px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.16s ease;
}

.sop-builder-cat.active {
  background: rgba(0, 113, 227, 0.1);
  border-color: rgba(0, 113, 227, 0.25);
  color: var(--accent);
  font-weight: 600;
}

.sop-builder-catalog {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
  scrollbar-width: thin;
  padding-right: 4px;
}

.sop-builder-catalog-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px 11px;
  border-radius: 9px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
}

.sop-builder-catalog-item:hover:not(:disabled) {
  border-color: rgba(0, 113, 227, 0.35);
  transform: translateY(-1px);
}

.sop-builder-catalog-item.added {
  opacity: 0.45;
  cursor: not-allowed;
}

.sop-builder-catalog-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.35;
}

.sop-builder-catalog-meta {
  font-size: 10.5px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.sop-builder-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 4px;
}

.submit-btn {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-full);
}
</style>
