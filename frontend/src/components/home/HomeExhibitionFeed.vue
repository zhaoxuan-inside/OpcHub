<template>
  <section class="section-container">
    <div class="section-header">
      <h2 class="section-title">精选展厅 · 浏览创客作品与扶持精粹</h2>
      <p class="section-desc">
        探索「晨昏线外」实时沉淀的真实作品、深度政策与经验手记。
      </p>

      <div class="filter-tabs-bar">
        <button
          class="filter-tab-pill"
          :class="{ active: currentContentFilter === 'all' }"
          @click="currentContentFilter = 'all'"
        >
          全部精选推荐
        </button>
        <button
          class="filter-tab-pill"
          :class="{ active: currentContentFilter === 'product' }"
          @click="currentContentFilter = 'product'"
        >
          <OpcIcon name="flame" :size="13" /> 卓越商业作品
        </button>
        <button
          class="filter-tab-pill"
          :class="{ active: currentContentFilter === 'policy' }"
          @click="currentContentFilter = 'policy'"
        >
          <OpcIcon name="landmark" :size="13" /> 重点扶持政策
        </button>
        <button
          class="filter-tab-pill"
          :class="{ active: currentContentFilter === 'forum' }"
          @click="currentContentFilter = 'forum'"
        >
          <OpcIcon name="bulb" :size="13" /> 创客思想手记
        </button>
        <button
          class="filter-tab-pill"
          :class="{ active: currentContentFilter === 'perk' }"
          @click="currentContentFilter = 'perk'"
        >
          <OpcIcon name="gift" :size="13" /> 独家生态特权
        </button>
      </div>
    </div>

    <div class="exhibition-list">
      <button
        v-for="(item, idx) in filteredContentList"
        :key="item.id"
        type="button"
        class="exhibit-row"
        @click="$emit('exhibit-click', item)"
      >
        <span class="exhibit-index">{{ String(idx + 1).padStart(2, '0') }}</span>

        <span class="exhibit-main">
          <span class="exhibit-meta">
            <span class="exhibit-category" :style="{ color: item.badgeColor || 'var(--text-secondary)' }">{{ item.categoryTag }}</span>
            <span class="exhibit-metric">{{ item.metricLabel }}</span>
          </span>
          <span class="exhibit-title">{{ item.title }}</span>
          <span class="exhibit-summary">{{ item.summary }}</span>
        </span>

        <span class="exhibit-side">
          <span class="exhibit-author">
            <span class="author-dot"></span>
            {{ item.authorOrSource }}
          </span>
          <span class="exhibit-cta">
            {{ item.actionLabel }}
            <span class="cta-arrow">↗</span>
          </span>
        </span>
      </button>
    </div>
    <div v-if="filteredContentList.length === 0" class="exhibition-empty">
      该分类内容正在收录中，切换其他筛选查看更多精选。
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});

defineEmits(['exhibit-click']);

const currentContentFilter = ref('all');

const filteredContentList = computed(() => {
  const list = props.items || [];
  if (currentContentFilter.value === 'all') {
    return list;
  }
  return list.filter((item) => item.type === currentContentFilter.value);
});
</script>

<style scoped>
.section-container {
  margin-bottom: 80px;
}

.section-header {
  text-align: left;
  max-width: none;
  margin: 0 0 24px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 680;
  letter-spacing: -0.045em;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.section-desc {
  max-width: 680px;
  font-size: 13.5px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.filter-tabs-bar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.filter-tab-pill {
  padding: 6px 12px;
  border-radius: 999px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease;
  user-select: none;
}

.filter-tab-pill:hover {
  color: var(--text-primary);
  background: var(--glass-surface-subtle);
}

.filter-tab-pill.active {
  color: var(--bg-canvas);
  background: var(--text-primary);
  border-color: var(--text-primary);
  box-shadow: none;
}

[data-theme="dark"] .filter-tab-pill.active {
  color: #0A0B0D;
}

.exhibition-list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--glass-border);
}

.exhibit-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 220px;
  gap: 22px;
  align-items: start;
  width: 100%;
  padding: 22px 6px;
  border: none;
  border-bottom: 1px solid var(--glass-border-subtle);
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: background 0.18s ease;
}

.exhibit-row:hover {
  background: var(--glass-surface-subtle);
}

.exhibit-index {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  padding-top: 4px;
}

.exhibit-main {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.exhibit-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.exhibit-category {
  color: var(--text-tertiary);
}

.exhibit-metric {
  color: var(--accent);
}

.exhibit-title {
  font-family: var(--font-display);
  font-size: 19px;
  font-weight: 640;
  line-height: 1.35;
  letter-spacing: -0.025em;
  color: var(--text-primary);
}

.exhibit-summary {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.exhibit-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  padding-top: 2px;
  text-align: right;
}

.exhibit-author {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.author-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.exhibit-cta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.04em;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.cta-arrow {
  transition: transform 0.2s ease, color 0.2s ease;
}

.exhibit-row:hover .cta-arrow {
  color: var(--accent);
  transform: translate(2px, -2px);
}

.exhibition-empty {
  padding: 36px 0;
  color: var(--text-tertiary);
  font-size: 12.5px;
}

@media (max-width: 760px) {
  .exhibit-row {
    grid-template-columns: 30px minmax(0, 1fr);
    gap: 12px;
  }

  .exhibit-side {
    grid-column: 2;
    align-items: flex-start;
    text-align: left;
  }

  .exhibit-title {
    font-size: 17px;
  }
}
</style>
