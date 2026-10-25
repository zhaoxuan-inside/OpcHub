<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box ops-header-card">
      <div class="ops-header-row">
        <div>
          <div class="ops-title-row">
            <h1 class="page-title">运营数据大盘</h1>
            <span class="mono-tag ops-live-tag" :class="{ live: dashboard?.is_live }">
              {{ dashboard?.is_live ? 'TELEMETRY · LIVE' : 'TELEMETRY · OFFLINE' }}
            </span>
          </div>
          <p class="ops-desc">
            指标聚合自各业务域的实时记录；未接入埋点的指标显式标注，不使用模拟数据。
          </p>
        </div>
        <button
          type="button"
          class="btn-liquid-outline ops-refresh-btn"
          :disabled="isLoading"
          @click="loadDashboard"
        >
          {{ isLoading ? '聚合中...' : '刷新大盘' }}
        </button>
      </div>

      <!-- KPI Grid -->
      <div v-if="kpiList.length > 0" class="kpi-grid-6">
        <div v-for="kpi in kpiList" :key="kpi.label" class="kpi-card">
          <div class="kpi-label"><span>{{ kpi.label }}</span></div>
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-delta" :class="kpi.delta_percent > 0 ? 'up' : ''">
            {{ kpi.delta_percent > 0 ? `↑ ${kpi.delta_percent}%` : kpi.sub_text }}
          </div>
        </div>
      </div>
      <div v-else-if="!isLoading" class="ops-empty-hint">暂无大盘数据，请点击「刷新大盘」拉取。</div>
    </div>

    <!-- Module Heatmap (real domain record counts) -->
    <div class="glass-box ops-section-card">
      <div class="ops-section-header">
        <h2 class="ops-section-title">全域模块内容量分布</h2>
        <span class="mono-tag">SOURCE: DOMAIN RECORD COUNTS</span>
      </div>
      <div v-if="heatmaps.length > 0" class="heatmap-list">
        <div v-for="m in heatmaps" :key="m.code" class="heatmap-row">
          <span class="heatmap-name">{{ m.module_name }}</span>
          <div class="heatmap-bar-wrap">
            <div class="heatmap-bar" :style="{ width: `${m.percentage}%` }"></div>
          </div>
          <span class="heatmap-count">{{ m.pv_count }} 条 · {{ m.percentage }}%</span>
        </div>
      </div>
      <div v-else class="ops-empty-hint">各业务模块暂无内容记录。</div>
    </div>

    <!-- Recent Gateway Logs -->
    <div class="glass-box ops-section-card">
      <div class="ops-section-header">
        <h2 class="ops-section-title">最近网关调用</h2>
        <span class="mono-tag">GATEWAY LOG TAIL</span>
      </div>
      <div v-if="gatewayLogs.length > 0" class="log-table">
        <div class="log-row log-head">
          <span>路由</span><span>终端</span><span>延迟</span><span>状态</span>
        </div>
        <div v-for="log in gatewayLogs" :key="log.id" class="log-row">
          <span class="log-route">{{ log.route }}</span>
          <span>{{ log.terminal }}</span>
          <span>{{ log.latency_ms }} ms</span>
          <span class="log-status">{{ log.status }}</span>
        </div>
      </div>
      <div v-else class="ops-empty-hint">暂无网关调用记录（网关审计日志未产生或未接入）。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const emit = defineEmits(['toast']);

const dashboard = ref(null);
const isLoading = ref(false);

const kpiList = computed(() => {
  const d = dashboard.value;
  if (!d) return [];
  return [d.dau, d.uv, d.pv, d.mau, d.retention, d.api_throughput].filter(Boolean);
});

const heatmaps = computed(() => dashboard.value?.module_heatmaps || []);
const gatewayLogs = computed(() => dashboard.value?.recent_gateway_logs || []);

async function loadDashboard() {
  if (isLoading.value) return;
  isLoading.value = true;
  try {
    const res = await dispatchGateway('ops.dashboard', {});
    if (res.ok && res.data) {
      dashboard.value = res.data;
    } else {
      emit('toast', { title: '大盘拉取失败', message: res.error || '请稍后重试', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '大盘拉取异常', message: '遥测服务暂时不可用，请稍后重试', type: 'ERROR' });
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  loadDashboard();
});
</script>

<style scoped>
.ops-header-card {
  padding: 24px 32px 18px;
  margin-bottom: 20px;
}

.ops-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.ops-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.ops-title-row .page-title {
  font-size: 26px;
  margin: 0;
}

.ops-live-tag {
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
}

.ops-live-tag.live {
  background: var(--status-success-soft);
  color: var(--status-success);
}

.ops-desc {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 640px;
}

.ops-refresh-btn {
  padding: 8px 16px;
  font-size: 12.5px;
}

.ops-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ops-section-card {
  padding: 18px 24px;
  margin-bottom: 20px;
}

.ops-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.ops-section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.ops-empty-hint {
  padding: 24px 12px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

.heatmap-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.heatmap-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.heatmap-name {
  width: 110px;
  font-size: 12.5px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.heatmap-bar-wrap {
  flex: 1;
  height: 10px;
  border-radius: 5px;
  background: var(--glass-surface-subtle);
  overflow: hidden;
}

.heatmap-bar {
  height: 100%;
  border-radius: 5px;
  background: var(--accent);
  transition: width 0.4s ease;
}

.heatmap-count {
  width: 120px;
  text-align: right;
  font-size: 12px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.log-table {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-row {
  display: grid;
  grid-template-columns: 1fr 90px 80px 110px;
  gap: 8px;
  padding: 7px 10px;
  border-radius: var(--radius-sm, 6px);
  font-size: 12.5px;
  color: var(--text-secondary);
}

.log-row.log-head {
  color: var(--text-tertiary);
  font-size: 11.5px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.log-row:nth-child(2n) {
  background: var(--glass-surface-subtle);
}

.log-route {
  font-family: var(--font-mono, monospace);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-status {
  color: var(--status-success);
}
</style>
