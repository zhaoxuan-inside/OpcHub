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

    <div class="grid-3 exhibition-grid">
      <div
        v-for="item in filteredContentList"
        :key="item.id"
        class="glass-card exhibition-card"
        @mousemove="trackCardSpotlight"
        @click="$emit('exhibit-click', item)"
      >
        <div>
          <div class="exhibit-header">
            <span class="mono-tag" :style="{ color: item.badgeColor || 'var(--text-secondary)' }">
              {{ item.categoryTag }}
            </span>
            <span class="exhibit-metric">{{ item.metricLabel }}</span>
          </div>

          <h3 class="exhibit-title">{{ item.title }}</h3>
          <p class="exhibit-summary">{{ item.summary }}</p>
        </div>

        <div class="exhibit-footer">
          <div class="exhibit-author">
            <div class="author-dot"></div>
            <span>{{ item.authorOrSource }}</span>
          </div>
          <div class="exhibit-cta">
            <span>{{ item.actionLabel }}</span>
            <span class="cta-arrow">›</span>
          </div>
        </div>
      </div>
    </div>
    <div v-if="filteredContentList.length === 0" class="exhibition-empty">
      该分类内容正在收录中，切换其他筛选查看更多精选。
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue';
import { trackCardSpotlight } from './spotlight';

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
  margin-bottom: 72px;
}

.section-header {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 36px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.section-desc {
  font-size: 14.5px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Filter Tabs Bar */
.filter-tabs-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 24px;
}

.filter-tab-pill {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-liquid);
  user-select: none;
}

.filter-tab-pill:hover {
  color: var(--text-primary);
  background: var(--glass-surface-hover);
}

.filter-tab-pill.active {
  color: #fff;
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 2px 10px rgba(0, 113, 227, 0.35);
}

/* Exhibition Cards */
.exhibition-grid {
  margin-top: 20px;
}

.exhibition-card {
  min-height: 220px;
}

.exhibit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.exhibit-metric {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
}

.exhibit-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  line-height: 1.35;
}

.exhibit-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.55;
  margin-bottom: 18px;
}

.exhibit-footer {
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.exhibit-author {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-tertiary);
}

.author-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

.exhibit-cta {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--accent);
  font-weight: 600;
}

.cta-arrow {
  font-size: 14px;
  transition: transform 0.2s ease;
}

.exhibition-card:hover .cta-arrow {
  transform: translateX(3px);
}

.exhibition-empty {
  text-align: center;
  padding: 36px 0;
  color: var(--text-tertiary);
  font-size: 13px;
}
</style>
