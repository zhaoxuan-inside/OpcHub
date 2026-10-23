<template>
  <!--
    Flow guide view: for makers unfamiliar with the process.
    Shows the stage timeline, and for the selected node: what this step produces,
    what it unlocks, and what to do next.
  -->
  <div class="sop-guide">
    <!-- Stage timeline -->
    <div class="sop-guide-timeline">
      <button
        v-for="stage in stages"
        :key="stage.code"
        type="button"
        class="sop-guide-stage"
        :class="{ active: stage.stage === currentStage }"
        @click="currentStage = stage.stage"
      >
        <span class="sop-guide-stage-num">{{ String(stage.stage).padStart(2, '0') }}</span>
        <span class="sop-guide-stage-name">{{ shortStageName(stage) }}</span>
      </button>
    </div>

    <!-- Nodes of the current stage -->
    <div class="sop-guide-stage-desc">{{ currentStageMeta?.description }}</div>

    <div class="sop-guide-nodes">
      <button
        v-for="node in stageNodes"
        :key="node.id"
        type="button"
        class="sop-guide-node"
        :class="{
          active: node.id === selectedNodeId,
          subgraph: node.kind === 'subgraph',
        }"
        @click="selectNode(node)"
      >
        <span class="sop-guide-node-title">{{ node.name }}</span>
        <span class="sop-guide-node-kind">
          {{ node.kind === 'subgraph' ? `子图 · ${(node.children || []).length} 份文书` : '文书' }}
        </span>
      </button>
    </div>

    <!-- Selected node guidance -->
    <div v-if="selectedNode" class="sop-guide-detail">
      <h4 class="sop-guide-detail-title">{{ selectedNode.name }}</h4>
      <p class="sop-guide-detail-desc">{{ selectedNode.description }}</p>

      <!-- 1. What you get after this step -->
      <div v-if="selectedNode.outcome" class="sop-guide-block">
        <div class="sop-guide-block-label">这一步做完，你会得到</div>
        <div class="sop-guide-block-text">{{ selectedNode.outcome }}</div>
      </div>

      <!-- 2. What becomes possible afterwards -->
      <div v-if="(selectedNode.unlocks || []).length" class="sop-guide-block">
        <div class="sop-guide-block-label">完成后可以解锁</div>
        <ul class="sop-guide-unlocks">
          <li v-for="(item, idx) in selectedNode.unlocks" :key="idx">{{ item }}</li>
        </ul>
      </div>

      <!-- 3. What to do next -->
      <div v-if="selectedNode.next_hint" class="sop-guide-block">
        <div class="sop-guide-block-label">接下来建议</div>
        <div class="sop-guide-block-text">{{ selectedNode.next_hint }}</div>
      </div>

      <!-- 4. Prerequisites with the reason behind the order -->
      <div v-if="prerequisites.length" class="sop-guide-block">
        <div class="sop-guide-block-label">开始前需要先完成</div>
        <div v-for="pre in prerequisites" :key="pre.node_id" class="sop-guide-prereq">
          <span class="sop-guide-prereq-name">{{ pre.name }}</span>
          <span class="sop-guide-prereq-why">{{ pre.rationale }}</span>
        </div>
      </div>

      <!-- Subgraph composition -->
      <div v-if="selectedNode.kind === 'subgraph'" class="sop-guide-block">
        <div class="sop-guide-block-label">该子图由以下文书构成</div>
        <button
          v-for="child in children"
          :key="child.id"
          type="button"
          class="sop-guide-child"
          @click="$emit('open-node', child)"
        >
          <span class="sop-guide-child-name">{{ child.name }}</span>
          <span class="sop-guide-child-count">{{ (child.required_fields || []).length }} 个待填项</span>
        </button>
      </div>

      <button type="button" class="btn-liquid sop-guide-cta" @click="$emit('open-node', selectedNode)">
        {{ selectedNode.kind === 'subgraph' ? '展开子图逐份填写' : '去填写这份文书' }}
      </button>
    </div>

    <div v-else class="sop-guide-empty">
      选择左侧任一阶段与节点，平台会告诉你这一步做完能得到什么、下一步该做什么。
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
  stages: { type: Array, default: () => [] },
  nodes: { type: Array, default: () => [] },
  selectedNodeId: { type: String, default: '' },
  prerequisites: { type: Array, default: () => [] },
  children: { type: Array, default: () => [] },
});

const emit = defineEmits(['select-node', 'open-node']);

const currentStage = ref(props.stages.length ? props.stages[0].stage : 1);

watch(
  () => props.selectedNodeId,
  (id) => {
    const node = props.nodes.find((n) => n.id === id);
    if (node) currentStage.value = node.stage;
  },
  { immediate: true }
);

const currentStageMeta = computed(() => props.stages.find((s) => s.stage === currentStage.value));

const stageNodes = computed(() => props.nodes.filter((n) => n.stage === currentStage.value));

const selectedNode = computed(() => props.nodes.find((n) => n.id === props.selectedNodeId) || null);

function shortStageName(stage) {
  return stage.name.replace(/^阶段\s*\d+[:：]\s*/, '');
}

function selectNode(node) {
  emit('select-node', node);
}
</script>

<style scoped>
.sop-guide {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sop-guide-timeline {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-bottom: 2px;
}

.sop-guide-timeline::-webkit-scrollbar {
  display: none;
}

.sop-guide-stage {
  flex: 1;
  min-width: 150px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border-radius: var(--radius-md, 12px);
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.sop-guide-stage:hover {
  border-color: rgba(0, 113, 227, 0.3);
}

.sop-guide-stage.active {
  background: rgba(0, 113, 227, 0.08);
  border-color: rgba(0, 113, 227, 0.35);
}

.sop-guide-stage-num {
  font-family: var(--font-mono, monospace);
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.sop-guide-stage-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.35;
}

.sop-guide-stage-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--glass-surface-subtle);
}

.sop-guide-nodes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sop-guide-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
}

.sop-guide-node:hover {
  border-color: rgba(0, 113, 227, 0.3);
}

.sop-guide-node.active {
  background: rgba(0, 113, 227, 0.08);
  border-color: rgba(0, 113, 227, 0.35);
}

.sop-guide-node.subgraph {
  border-color: var(--accent-glow);
  background: linear-gradient(150deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
}

.sop-guide-node-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.sop-guide-node-kind {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
  flex-shrink: 0;
}

.sop-guide-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 20px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
}

.sop-guide-detail-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.sop-guide-detail-desc {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0;
}

.sop-guide-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sop-guide-block-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}

.sop-guide-block-text {
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-primary);
  padding: 9px 12px;
  border-radius: 8px;
  background: var(--glass-surface-subtle);
}

.sop-guide-unlocks {
  margin: 0;
  padding-left: 18px;
  font-size: 12.5px;
  line-height: 1.75;
  color: var(--text-primary);
}

.sop-guide-prereq {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 9px 12px;
  border-radius: 8px;
  background: var(--status-warning-soft);
  border: 1px solid var(--status-warning-soft);
}

.sop-guide-prereq-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.sop-guide-prereq-why {
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.sop-guide-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
}

.sop-guide-child:hover {
  border-color: rgba(0, 113, 227, 0.3);
}

.sop-guide-child-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.sop-guide-child-count {
  font-size: 11px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.sop-guide-cta {
  align-self: flex-start;
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-full);
}

.sop-guide-empty {
  padding: 32px 20px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-tertiary);
  line-height: 1.7;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
}
</style>
