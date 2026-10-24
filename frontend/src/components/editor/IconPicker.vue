<template>
  <div class="icon-picker" ref="rootRef">
    <!-- Trigger tile: shows the selected built-in icon or a placeholder -->
    <button
      type="button"
      class="ip-trigger"
      :class="{ active: !!resolvedName, open }"
      :title="resolvedName ? `内置图标：${resolvedName}（点击更换）` : '选择内置图标'"
      @click="open = !open"
    >
      <span v-if="resolvedName" class="ip-tile ip-tile-selected">
        <OpcIcon :name="resolvedName" :size="20" />
      </span>
      <span v-else class="ip-placeholder">
        <OpcIcon name="modules" :size="16" />
        <span>选择图标</span>
      </span>
      <svg v-if="resolvedName" class="ip-clear" viewBox="0 0 24 24" title="清除图标" @click.stop="clear">
        <line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>
      </svg>
    </button>

    <!-- Dropdown grid of the built-in redrawn line-icon library -->
    <div v-if="open" class="ip-panel">
      <div class="ip-panel-head">
        <span>内置图标</span>
        <span class="ip-panel-hint">平台重绘线性图标库 · 不支持外部上传</span>
      </div>
      <div class="ip-grid">
        <button
          v-for="name in BUILTIN_ICON_NAMES"
          :key="name"
          type="button"
          class="ip-tile"
          :class="{ selected: name === resolvedName }"
          :title="ICON_LABELS[name] || name"
          @click="pick(name)"
        >
          <OpcIcon :name="name" :size="18" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { BUILTIN_ICON_NAMES, ICON_LABELS } from '@/utils/builtinIcons';

/**
 * IconPicker —— 平台内置图标选择器。
 *
 * 约束：素材只允许从平台重绘线性图标库（OpcIcon）中选择，不提供任何
 * 上传或外链入口。值统一存储为 `icon:<name>`（空串表示未选择），
 * 与既有 icon_url 字段契约兼容。
 */

const props = defineProps({
  modelValue: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue']);

const open = ref(false);
const rootRef = ref(null);

const resolvedName = computed(() => {
  const v = props.modelValue || '';
  return v.startsWith('icon:') ? v.slice(5) : '';
});

function pick(name) {
  emit('update:modelValue', `icon:${name}`);
  open.value = false;
}

function clear() {
  emit('update:modelValue', '');
  open.value = false;
}

function onGlobalClick(e) {
  if (!rootRef.value?.contains(e.target)) open.value = false;
}

onMounted(() => document.addEventListener('click', onGlobalClick));
onBeforeUnmount(() => document.removeEventListener('click', onGlobalClick));
</script>

<style scoped>
.icon-picker {
  position: relative;
  display: inline-block;
}

.ip-trigger {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px;
  border-radius: var(--radius-sm, 10px);
  border: 1px solid var(--glass-border);
  background: var(--glass-surface-subtle);
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.ip-trigger:hover,
.ip-trigger.open {
  border-color: rgba(0, 113, 227, 0.45);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.08);
}

.ip-tile {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  border: 1px solid var(--glass-border-subtle);
  background: linear-gradient(135deg, var(--accent-glass, rgba(0, 113, 227, 0.1)) 0%, var(--glass-surface-hover, rgba(0, 0, 0, 0.03)) 100%);
  color: var(--accent);
}

.ip-tile:hover {
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-1px);
}

.ip-tile.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-glass, rgba(0, 113, 227, 0.18));
  color: var(--accent);
}

.ip-placeholder {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  height: 34px;
  font-size: 12.5px;
  color: var(--text-tertiary);
}

.ip-clear {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 16px;
  height: 16px;
  padding: 2px;
  border-radius: 50%;
  background: var(--glass-surface-solid, #fff);
  border: 1px solid var(--glass-border);
  color: var(--text-tertiary);
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
}

.ip-clear:hover {
  color: var(--status-danger, #ff3b30);
  border-color: currentColor;
}

/* Dropdown panel */

.ip-panel {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 70;
  width: 296px;
  padding: 12px;
  border-radius: var(--radius-md, 14px);
  border: 1px solid var(--glass-border);
  background: var(--glass-surface-solid, #fff);
  box-shadow: var(--glass-shadow-hover, 0 16px 40px rgba(0, 0, 0, 0.16));
  animation: ip-panel-in 0.16s ease;
}

@keyframes ip-panel-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.ip-panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 0 2px 8px;
}

.ip-panel-head > span:first-child {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.ip-panel-hint {
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.ip-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  max-height: 240px;
  overflow-y: auto;
}
</style>
