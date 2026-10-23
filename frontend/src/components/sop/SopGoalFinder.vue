<template>
  <!--
    Goal reverse-lookup view: for makers who know the outcome they want but not
    which documents it takes. Selecting a goal resolves the required documents
    (subgraphs expanded) in executable order.
  -->
  <div class="sop-goal-finder">
    <!-- Goal list -->
    <div class="sop-goal-list">
      <button
        v-for="goal in goals"
        :key="goal.id"
        type="button"
        class="sop-goal-card"
        :class="{ active: goal.id === selectedGoalId }"
        @click="selectGoal(goal)"
      >
        <span class="sop-goal-card-title">{{ goal.title }}</span>
        <span class="sop-goal-card-desc">{{ goal.description }}</span>
        <span class="sop-goal-card-hint">{{ goal.audience_hint }}</span>
      </button>
    </div>

    <!-- Resolved plan -->
    <div v-if="plan" class="sop-goal-plan">
      <div class="sop-goal-plan-head">
        <div>
          <div class="sop-goal-plan-label">达成目标所需文书</div>
          <h4 class="sop-goal-plan-title">{{ plan.goal.title }}</h4>
        </div>
        <div class="sop-goal-plan-head-right">
          <span class="sop-goal-plan-count">
            {{ requiredCount }} 份必办 · {{ recommendedCount }} 份建议
          </span>
          <button type="button" class="btn-liquid-outline sop-goal-save-flow" @click="$emit('save-as-flow', plan)">
            存为我的流程
          </button>
        </div>
      </div>

      <p v-if="plan.goal.outcome" class="sop-goal-plan-outcome">
        达成后：{{ plan.goal.outcome }}
      </p>

      <!-- Flow graph: click a node to open its document page -->
      <div class="sop-goal-graph">
        <SopFlowGraph
          :nodes="plan.items"
          :edges="plan.edges || []"
          :selected-id="selectedNodeId"
          @select-node="$emit('open-node', $event)"
          @open-node="$emit('open-node', $event)"
        />
      </div>

      <!-- Ordered checklist -->
      <details class="sop-goal-details">
        <summary class="sop-goal-details-summary">按顺序查看文书清单（{{ plan.items.length }} 项）</summary>
        <ol class="sop-goal-steps">
        <li
          v-for="item in plan.items"
          :key="item.node_id"
          class="sop-goal-step"
          :class="{ optional: !item.required }"
        >
          <span class="sop-goal-step-order">{{ item.order }}</span>
          <div class="sop-goal-step-body">
            <div class="sop-goal-step-title-row">
              <span class="sop-goal-step-title">{{ item.name }}</span>
              <span class="sop-goal-step-badge" :class="item.required ? 'req' : 'rec'">
                {{ item.required ? '必办' : '建议' }}
              </span>
            </div>
            <div class="sop-goal-step-meta">
              <span v-if="item.parent_id" class="sop-goal-step-group">
                属于子图：{{ groupName(item.parent_id) }}
              </span>
              <span>阶段 {{ String(item.stage).padStart(2, '0') }}</span>
              <span class="dot-sep">·</span>
              <span>{{ (item.required_fields || []).length }} 个待填项</span>
            </div>
            <p v-if="item.outcome" class="sop-goal-step-outcome">{{ item.outcome }}</p>
            <button type="button" class="sop-goal-step-cta" @click="$emit('open-node', item)">
              去填写 ›
            </button>
          </div>
        </li>
      </ol>
      </details>

      <p v-if="(plan.missing_nodes || []).length" class="sop-goal-missing">
        有 {{ plan.missing_nodes.length }} 个节点数据缺失，请联系平台补充。
      </p>
    </div>

    <div v-else class="sop-goal-empty">
      选择你想要的最终目的，平台会反向推导出需要编写的全部文书与先后顺序。
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import SopFlowGraph from '@/components/sop/SopFlowGraph.vue';

const props = defineProps({
  goals: { type: Array, default: () => [] },
  plan: { type: Object, default: null },
  selectedGoalId: { type: String, default: '' },
  selectedNodeId: { type: String, default: '' },
  nodes: { type: Array, default: () => [] },
});

const emit = defineEmits(['select-goal', 'open-node', 'select-node', 'save-as-flow']);

const requiredCount = computed(() => (props.plan?.items || []).filter((i) => i.required).length);
const recommendedCount = computed(() => (props.plan?.items || []).filter((i) => !i.required).length);

function selectGoal(goal) {
  emit('select-goal', goal);
}

function groupName(parentId) {
  const node = props.nodes.find((n) => n.id === parentId);
  return node ? node.name : parentId;
}
</script>

<style scoped>
.sop-goal-finder {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.sop-goal-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.sop-goal-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 14px 16px;
  border-radius: var(--radius-md, 12px);
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.sop-goal-card:hover {
  border-color: rgba(0, 113, 227, 0.3);
  transform: translateY(-2px);
}

.sop-goal-card.active {
  background: rgba(0, 113, 227, 0.08);
  border-color: rgba(0, 113, 227, 0.4);
}

.sop-goal-card-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
}

.sop-goal-card-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.sop-goal-card-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.sop-goal-plan {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px 22px;
  border-radius: var(--radius-lg, 16px);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
}

.sop-goal-plan-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.sop-goal-plan-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  margin-bottom: 3px;
}

.sop-goal-plan-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.sop-goal-plan-count {
  font-size: 11.5px;
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  flex-shrink: 0;
}

.sop-goal-plan-outcome {
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-primary);
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.05));
}

.sop-goal-plan-head-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.sop-goal-save-flow {
  padding: 5px 12px;
  font-size: 11.5px;
  font-weight: 500;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.sop-goal-graph {
  padding: 14px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.sop-goal-details {
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 10px;
}

.sop-goal-details-summary {
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  list-style: none;
}

.sop-goal-details-summary::-webkit-details-marker {
  display: none;
}

.sop-goal-details-summary::before {
  content: '▸ ';
  color: var(--text-tertiary);
}

.sop-goal-details[open] .sop-goal-details-summary::before {
  content: '▾ ';
}

.sop-goal-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  counter-reset: none;
}

.sop-goal-step {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.sop-goal-step.optional {
  opacity: 0.82;
  border-style: dashed;
}

.sop-goal-step-order {
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

.sop-goal-step-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sop-goal-step-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sop-goal-step-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.sop-goal-step-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.sop-goal-step-badge.req {
  background: rgba(0, 113, 227, 0.12);
  color: #0071e3;
  border: 1px solid rgba(0, 113, 227, 0.25);
}

.sop-goal-step-badge.rec {
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
  border: 1px solid var(--glass-border-subtle);
}

.sop-goal-step-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-tertiary);
  flex-wrap: wrap;
}

.sop-goal-step-group {
  color: var(--accent);
}

.dot-sep {
  opacity: 0.5;
}

.sop-goal-step-outcome {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0;
}

.sop-goal-step-cta {
  align-self: flex-start;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  color: var(--accent);
  font-size: 12px;
  font-weight: 500;
}

.sop-goal-step-cta:hover {
  text-decoration: underline;
}

.sop-goal-missing {
  font-size: 12px;
  color: var(--status-danger);
  margin: 0;
}

.sop-goal-empty {
  padding: 40px 20px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-tertiary);
  line-height: 1.7;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
}
</style>
