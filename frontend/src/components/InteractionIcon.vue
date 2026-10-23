<template>
  <svg
    class="interaction-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- LIKE / 点赞 -->
    <path
      v-if="name === 'like'"
      d="M7 10v11H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1h3Zm0 0 4.2-7.2A2 2 0 0 1 14.9 4l-.7 4.3h5.1a2 2 0 0 1 2 2.4l-1.6 8A2 2 0 0 1 17.8 20H7"
    />
    <!-- FAVORITE / 收藏（书签） -->
    <path
      v-else-if="name === 'favorite'"
      d="M7 3h10a1 1 0 0 1 1 1v17l-6-3.5L6 21V4a1 1 0 0 1 1-1Z"
    />
    <!-- LOVE / 喜欢 -->
    <path
      v-else-if="name === 'love'"
      d="M20.8 5.6a5.2 5.2 0 0 0-7.4 0L12 7l-1.4-1.4a5.2 5.2 0 1 0-7.4 7.4L12 21l8.8-7.9a5.2 5.2 0 0 0 0-7.5Z"
    />
    <!-- COMMENT / 评论 -->
    <path
      v-else-if="name === 'comment'"
      d="M21 11.5a8.4 8.4 0 0 1-8.5 8.3 9 9 0 0 1-3.6-.8L3 21l1.9-5.4a8 8 0 0 1-1.4-4.5A8.4 8.4 0 0 1 12 2.8a8.4 8.4 0 0 1 9 8.7Z"
    />
    <!-- DISLIKE / 踩 -->
    <path
      v-else-if="name === 'dislike'"
      d="M7 10v11H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1h3Zm0 0 4.2 7.2A2 2 0 0 0 14.9 20l-.7-4.3h5.1a2 2 0 0 0 2-2.4l-1.6-8A2 2 0 0 0 17.8 4H7"
    />
    <!-- STAR / 评分 -->
    <path
      v-else-if="name === 'star'"
      d="m12 2.5 2.9 6.2 6.9.9-5 4.8 1.2 6.8L12 18.8l-6 3.4 1.2-6.8-5-4.8 6.9-.9L12 2.5Z"
    />
  </svg>
</template>

<script setup>
defineProps({
  name: { type: String, default: 'like' },
  filled: { type: Boolean, default: false },
  size: { type: [Number, String], default: 15 },
  strokeWidth: { type: [Number, String], default: 1.9 },
});
</script>

<style scoped>
.interaction-icon {
  display: block;
  flex-shrink: 0;
  transition: transform 0.18s ease;
}
</style>
