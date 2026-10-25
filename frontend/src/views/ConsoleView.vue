<template>
  <div class="view-panel active">
    <div class="glass-box">
      <!-- Header -->
      <div class="cw-header">
        <div>
          <div class="cw-title-row">
            <h1 class="page-title cw-title">后端编排工作台 · 资产目录</h1>
            <span class="mono-tag cw-live-tag">算子 / 子图 / 场景</span>
          </div>
          <p class="cw-desc">
            统一管理算子、子图与场景三层编排资产；多人同时编排时由系统自动加锁，避免相互覆盖。
          </p>
        </div>
      </div>

      <!-- 全局锁看板：展示锁定状态与锁定人 -->
      <div class="cw-locks" v-if="activeLocks.length > 0">
        <span class="cw-locks-label mono-tag">🔒 编辑锁 {{ activeLocks.length }}</span>
        <div class="cw-locks-scroll">
          <span
            v-for="lk in activeLocks"
            :key="lk.entity_type + ':' + lk.entity_key"
            class="cw-lock-chip"
            :title="`持有至 ${lk.expires_at}`"
          >
            <em>{{ entityTypeName(lk.entity_type) }}</em>
            <strong>{{ lk.entity_key }}</strong>
            <span>{{ holderDisplay(lk) }}</span>
          </span>
        </div>
      </div>

      <!-- 三层页签 -->
      <div class="cw-tabs">
        <button
          v-for="t in tabs"
          :key="t.key"
          class="cw-tab"
          :class="{ active: activeTab === t.key }"
          @click="activeTab = t.key"
        >
          {{ t.label }}
          <span class="cw-tab-count">{{ counts[t.key] ?? '…' }}</span>
        </button>
      </div>

      <!-- 面板 -->
      <OperatorPanel v-show="activeTab === 'operators'" :user-session="userSession" @toast="(t) => emit('toast', t)" @count="onCount" />
      <SubgraphPanel v-show="activeTab === 'subgraphs'" :user-session="userSession" @toast="(t) => emit('toast', t)" @count="onCount" />
      <ScenarioPanel v-show="activeTab === 'scenarios'" :user-session="userSession" @toast="(t) => emit('toast', t)" @count="onCount" />
    </div>
  </div>
</template>

<script setup>
/**
 * 后端编排工作台外壳：算子 / 子图 / 场景 三层资产管理 + 全局排他锁看板。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import OperatorPanel from '@/components/orchestration/OperatorPanel.vue';
import SubgraphPanel from '@/components/orchestration/SubgraphPanel.vue';
import ScenarioPanel from '@/components/orchestration/ScenarioPanel.vue';

const props = defineProps({
  userSession: { type: Object, default: null },
});
const emit = defineEmits(['toast']);

const tabs = [
  { key: 'operators', label: '算子' },
  { key: 'subgraphs', label: '子图' },
  { key: 'scenarios', label: '场景' },
];
const activeTab = ref('operators');
const counts = ref({});
const activeLocks = ref([]);
let locksTimer = null;

function onCount(key, value) {
  counts.value[key] = value;
}

function entityTypeName(type) {
  return { operator: '算子', subgraph: '子图', scenario: '场景' }[type] || type;
}

function holderDisplay(lk) {
  const name = lk.holder_name || lk.holder_id;
  const mins = Math.max(1, Math.round((new Date(lk.expires_at).getTime() - Date.now()) / 60000));
  return `${name} · 剩 ${mins} 分`;
}

async function loadLocks() {
  const res = await dispatchGateway('orchestration.catalog.locks', {}, { silent: true });
  activeLocks.value = res.ok && Array.isArray(res.data?.locks) ? res.data.locks : [];
}

onMounted(() => {
  loadLocks();
  locksTimer = setInterval(loadLocks, 15000);
});

onBeforeUnmount(() => {
  if (locksTimer) clearInterval(locksTimer);
});
</script>

<style scoped>
.cw-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
.cw-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.cw-title { font-size: 26px; margin: 0; }
.cw-live-tag { background: var(--status-success-soft); color: var(--status-success); border-color: var(--status-success-soft); }
.cw-desc { font-size: 13px; color: var(--text-secondary); max-width: 720px; }

.cw-locks { display: flex; align-items: center; gap: 10px; margin-top: 14px; padding: 8px 12px; background: var(--status-warning-soft); border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); }
.cw-locks-label { background: var(--glass-surface); color: var(--status-warning); flex-shrink: 0; }
.cw-locks-scroll { display: flex; gap: 8px; overflow-x: auto; min-width: 0; }
.cw-lock-chip { display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; padding: 3px 10px; border-radius: 12px; background: var(--glass-surface); color: var(--text-secondary); white-space: nowrap; flex-shrink: 0; }
.cw-lock-chip em { font-style: normal; color: var(--status-warning); font-size: 10.5px; }
.cw-lock-chip strong { font-family: var(--font-mono); font-weight: 600; }

.cw-tabs { display: flex; gap: 6px; margin-top: 16px; border-bottom: 1px solid var(--glass-border-subtle); }
.cw-tab { background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-secondary); font-size: 14px; padding: 8px 18px; cursor: pointer; display: flex; align-items: center; gap: 6px; }
.cw-tab:hover { color: var(--accent); }
.cw-tab.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.cw-tab-count { font-family: var(--font-mono); font-size: 11px; padding: 1px 7px; border-radius: 9px; background: var(--glass-surface-subtle); color: var(--text-tertiary); }
.cw-tab.active .cw-tab-count { background: var(--accent-glass); color: var(--accent); }
</style>
