<template>
  <div class="create-page-layout">
    <header class="glass-box create-page-head">
      <div class="create-page-head-left">
        <button type="button" class="create-back-btn" :title="`返回${backLabel}`" @click="$emit('back')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          <span>返回</span>
        </button>
        <h1 class="create-page-title">{{ title }}</h1>
      </div>

      <div v-if="$slots.meta" class="create-page-meta">
        <slot name="meta" />
      </div>

      <div v-if="$slots.actions" class="create-page-actions">
        <slot name="actions" />
      </div>
    </header>

    <div :class="plainBody ? 'create-page-body-plain' : 'glass-box create-page-body'">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  backLabel: { type: String, default: '返回' },
  // Use when the page body already owns its glass surface (e.g. forum editor).
  plainBody: { type: Boolean, default: false },
});

defineEmits(['back']);
</script>

<style scoped>
.create-page-layout {
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 0 0 48px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  box-sizing: border-box;
  scrollbar-width: none;
  /* Header height (14px padding × 2 + 32px button + borders): sticky children such as the
     RichEditor toolbar dock flush below it so scrolled content never peeks through a gap. */
  --create-sticky-top: 62px;
}

.create-page-layout::-webkit-scrollbar {
  display: none;
}

.create-page-head {
  position: sticky;
  top: 0;
  z-index: 20;
  flex-shrink: 0;
  margin-bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-radius: 16px;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.92));
  backdrop-filter: var(--blur-strength);
  -webkit-backdrop-filter: var(--blur-strength);
}

.create-page-head-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.create-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  height: 32px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid var(--glass-border);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.create-back-btn:hover {
  color: var(--accent);
  border-color: rgba(0, 113, 227, 0.35);
  background: rgba(0, 113, 227, 0.05);
}

.create-page-title {
  margin: 0;
  min-width: 0;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.2;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.create-page-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.create-page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* The body is a flex item of the scroll container: it must keep its content
   height (flex-shrink: 0), otherwise `overflow: hidden` from .glass-box lets it
   collapse to the viewport and the bottom of the form becomes unreachable.
   `clip` keeps the rounded corners without creating a scroll container, so
   sticky descendants still dock against the page scroller. */
.create-page-body {
  flex-shrink: 0;
  margin-bottom: 0;
  padding: 24px 28px 30px;
  border-radius: 16px;
  overflow: hidden;
  overflow: clip;
}

.create-page-body-plain {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

@media (max-width: 720px) {
  .create-page-layout {
    padding-bottom: 36px;
  }

  .create-page-head {
    flex-wrap: wrap;
  }

  .create-page-body {
    padding: 18px 16px 22px;
  }

  .create-page-meta {
    order: 3;
    width: 100%;
  }

  .create-page-actions {
    width: 100%;
  }

  .create-page-actions :deep(.btn-liquid) {
    flex: 1;
  }
}
</style>
