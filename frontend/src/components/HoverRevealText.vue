<template>
  <!--
    Fixed-size clamped summary + hover liquid-glass reveal overlay.

    The card itself NEVER resizes: `.hr-text` stays clamped at a fixed line range
    (uniform card footprint). On hover a fully-styled liquid-glass overlay is shown
    above the same card (absolutely positioned, pointer-events: none), so no other
    card in the grid is ever pushed around — zero layout jitter.
  -->
  <div
    class="hr"
    :class="`hr-l${lines}`"
    @mousemove="onMove"
    @mouseleave="onLeave"
  >
    <p class="hr-text" :title="text">{{ text }}</p>
    <div class="hr-pop">
      <p class="hr-pop-text">{{ text }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  text: { type: String, default: '' },
  lines: { type: Number, default: 2 },
});

const mx = ref(50);
const my = ref(50);

function onMove(e) {
  const rect = e.currentTarget.getBoundingClientRect();
  mx.value = rect.width
    ? Math.round(((e.clientX - rect.left) / rect.width) * 100)
    : 50;
  my.value = rect.height
    ? Math.round(((e.clientY - rect.top) / rect.height) * 100)
    : 50;
}

function onLeave() {
  mx.value = 50;
  my.value = 50;
}
</script>

<style scoped>
.hr {
  position: relative;
}

/* Fixed-size clamped summary (uniform card footprint) */
.hr-text {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.45;
  color: var(--text-secondary, #5b6472);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
}

.hr-l1 .hr-text {
  -webkit-line-clamp: 1;
  line-clamp: 1;
  min-height: 1.5em;
  max-height: 1.5em;
}

.hr-l2 .hr-text {
  -webkit-line-clamp: 2;
  line-clamp: 2;
  min-height: 2.9em;
  max-height: 2.9em;
}

.hr-l3 .hr-text {
  -webkit-line-clamp: 3;
  line-clamp: 3;
  min-height: 4.35em;
  max-height: 4.35em;
}

/* Hover reveal overlay (liquid glass + mouse-follow light) */
.hr-pop {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  z-index: 60;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.96));
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.65));
  box-shadow: var(--glass-shadow-hover, 0 18px 40px rgba(0, 0, 0, 0.2));
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px) scale(0.99);
  transition: opacity 0.2s ease, transform 0.2s ease, visibility 0.2s;
  pointer-events: none;
  overflow: hidden;
}

.hr-pop::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(
    240px circle at var(--mx, 50%) var(--my, 50%),
    rgba(0, 113, 227, 0.16),
    transparent 70%
  );
  pointer-events: none;
}

.hr-pop-text {
  position: relative;
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-primary, #1a1c1e);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow-y: auto;
}

.hr:hover .hr-pop {
  opacity: 1;
  visibility: visible;
  transform: none;
}

.hr:hover .hr-text {
  visibility: hidden; /* keep the reserved box so the card never collapses */
}
</style>
