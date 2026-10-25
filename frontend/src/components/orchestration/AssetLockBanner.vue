<template>
  <div class="lockbanner" :class="{ mine: heldByMe, other: heldByOther }">
    <template v-if="heldByMe">
      <span class="lockbadge mine">🔒 我持有编辑权</span>
      <span class="locktext">编辑权已锁定 {{ remainingMinutes }} 分钟，其他人暂无法修改。</span>
      <button class="btn-liquid-outline lockbtn" :disabled="busy" @click="$emit('release')">{{ busy ? '处理中...' : '释放锁' }}</button>
    </template>
    <template v-else-if="heldByOther">
      <span class="lockbadge other">🔒 已被锁定</span>
      <span class="locktext">
        <strong>{{ holderLabel }}</strong> 正在编辑此资产，剩余约 {{ remainingMinutes }} 分钟自动释放；期间仅可查看。
      </span>
      <button class="btn-liquid-outline lockbtn" :disabled="busy" @click="$emit('acquire')">{{ busy ? '获取中...' : '尝试获取锁' }}</button>
    </template>
    <template v-else>
      <span class="lockbadge free">空闲</span>
      <span class="locktext">当前无人编辑。修改前请先锁定编辑权，避免多人同时操作。</span>
      <button class="btn-liquid lockbtn" :disabled="busy" @click="$emit('acquire')">{{ busy ? '获取中...' : '锁定并编辑' }}</button>
    </template>
  </div>
</template>

<script setup>
/**
 * 排他锁状态条：展示 锁定状态 + 锁定人，并提供 获取/释放 操作入口。
 */
import { computed } from 'vue';

const props = defineProps({
  heldByMe: { type: Boolean, default: false },
  heldByOther: { type: Boolean, default: false },
  holderLabel: { type: String, default: '' },
  remainingSeconds: { type: Number, default: 0 },
  busy: { type: Boolean, default: false },
});

defineEmits(['acquire', 'release']);

const remainingMinutes = computed(() => Math.max(1, Math.round(props.remainingSeconds / 60)));
</script>

<style scoped>
.lockbanner { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 14px; border-radius: var(--radius-md); border: 1px solid var(--glass-border-subtle); background: var(--glass-surface-subtle); }
.lockbanner.mine { border-color: var(--status-success-soft); background: var(--status-success-soft); }
.lockbanner.other { border-color: var(--status-warning-soft); background: var(--status-warning-soft); }
.lockbadge { font-family: var(--font-mono); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: var(--glass-surface); color: var(--text-secondary); flex-shrink: 0; }
.lockbadge.mine { color: var(--status-success); }
.lockbadge.other { color: var(--status-warning); }
.locktext { font-size: 12.5px; color: var(--text-secondary); flex: 1; min-width: 200px; }
.lockbtn { padding: 6px 14px; font-size: 12px; flex-shrink: 0; }
.lockbtn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
