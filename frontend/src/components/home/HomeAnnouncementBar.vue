<template>
  <div class="announcement-wrapper">
    <div class="announcement-pill" @click="$emit('explore')">
      <span class="pulse-dot"></span>
      <span class="announcement-tag">OPC 2.0 正式上线</span>
      <span class="announcement-text">专为一人公司打造的商业操作系统 · 首月入驻立享全域政策研判与生态特权</span>
      <span class="announcement-arrow">›</span>
    </div>
  </div>
</template>

<script setup>
defineEmits(['explore']);
</script>

<style scoped>
.announcement-wrapper {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 30px;
  padding: 0 4px;
}

.announcement-pill {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  padding: 0 0 11px;
  border-radius: 0;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--glass-border-subtle);
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.18s ease, border-color 0.18s ease;
  user-select: none;
}

.announcement-pill:hover {
  background: transparent;
  border-color: var(--text-primary);
  box-shadow: none;
  color: var(--text-primary);
  transform: none;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-success);
  box-shadow: 0 0 8px var(--status-success-soft);
  flex-shrink: 0;
  animation: pulse 2s infinite ease-in-out;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.announcement-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.announcement-text {
  font-weight: 500;
}

.announcement-arrow {
  margin-left: auto;
  font-size: 14px;
  color: var(--text-tertiary);
  transition: transform 0.2s ease;
}

.announcement-pill:hover .announcement-arrow {
  transform: translateX(3px);
  color: var(--accent);
}
</style>
