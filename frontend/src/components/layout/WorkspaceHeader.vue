<template>
  <header class="workspace-header">
    <div class="ws-line">
      <span class="ws-eyebrow">{{ eyebrow }}</span>
      <span class="ws-rule" aria-hidden="true"></span>
      <span class="ws-meta">{{ meta }}</span>
    </div>

    <div class="ws-body">
      <div class="ws-copy">
        <h1 class="ws-title">{{ title }}</h1>
        <p v-if="description" class="ws-desc">{{ description }}</p>
      </div>

      <div v-if="stats && stats.length" class="ws-stats">
        <div v-for="stat in stats" :key="stat.label" class="ws-stat">
          <strong>{{ stat.value }}</strong>
          <span>{{ stat.label }}</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
  eyebrow: { type: String, default: '' },
  meta: { type: String, default: '' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  stats: { type: Array, default: () => [] },
});
</script>

<style scoped>
.workspace-header {
  flex-shrink: 0;
  padding: 2px 2px 18px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.ws-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  overflow: hidden;
}

.ws-eyebrow {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  color: var(--accent);
  white-space: nowrap;
}

.ws-rule {
  flex: 1;
  height: 1px;
  background: var(--glass-border-subtle);
  min-width: 20px;
}

.ws-meta {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.ws-body {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
}

.ws-copy {
  min-width: 0;
}

.ws-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 34px;
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.05em;
  color: var(--text-primary);
}

.ws-desc {
  max-width: 640px;
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-secondary);
}

.ws-stats {
  display: flex;
  align-items: flex-end;
  gap: 26px;
  flex-shrink: 0;
  padding-bottom: 3px;
}

.ws-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 54px;
}

.ws-stat strong {
  font-family: var(--font-mono);
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.04em;
  color: var(--text-primary);
  line-height: 1.2;
}

.ws-stat span {
  font-size: 9.5px;
  letter-spacing: 0.03em;
  color: var(--text-tertiary);
  white-space: nowrap;
}

@media (max-width: 760px) {
  .ws-body {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
  }

  .ws-title {
    font-size: 28px;
  }

  .ws-stats {
    width: 100%;
    justify-content: space-between;
    gap: 12px;
  }
}
</style>
