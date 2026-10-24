<template>
  <span v-if="visible" class="official-badge" :title="title">
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
    {{ label }}
  </span>
</template>

<script setup>
// 统一「官方发布」徽章：所有内容卡片共用一套视觉语言，
// 与 SOP 卡片的官方认证徽章保持一致（is_official 由服务端按发布者角色判定）。
defineProps({
  visible: { type: Boolean, default: false },
  label: { type: String, default: '官方' },
  title: { type: String, default: '官方发布：由平台官方账号发布并认证' },
})
</script>
