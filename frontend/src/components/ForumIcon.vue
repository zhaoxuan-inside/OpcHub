<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :class="['opc-icon', `opc-icon-${name}`]"
    style="display: inline-block; vertical-align: middle; flex-shrink: 0;"
  >
    <!-- 1. Spark: 四芒流光灵感星 (用于新风暴、灵感碰撞) -->
    <g v-if="name === 'spark'">
      <path
        d="M12 2C12 7.5 7.5 12 2 12C7.5 12 12 16.5 12 22C12 16.5 16.5 12 22 12C16.5 12 12 7.5 12 2Z"
        fill="currentColor"
        fill-opacity="0.16"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <!-- Companion micro spark -->
      <circle cx="19" cy="5" r="1.5" fill="currentColor" />
      <circle cx="5" cy="19" r="1" fill="currentColor" fill-opacity="0.7" />
      <!-- Center Core -->
      <circle cx="12" cy="12" r="1.8" fill="currentColor" />
    </g>

    <!-- 2. AI Brain / Quantum Neural: 量子智脑环 (用于 RAG AI 创客顾问) -->
    <g v-else-if="name === 'ai-brain'">
      <!-- Dual overlapping orbital rings with refraction depth -->
      <ellipse
        cx="12"
        cy="12"
        rx="9"
        ry="4.2"
        transform="rotate(-25 12 12)"
        fill="currentColor"
        fill-opacity="0.1"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-dasharray="1 1.2"
      />
      <ellipse
        cx="12"
        cy="12"
        rx="9"
        ry="4.2"
        transform="rotate(35 12 12)"
        stroke="currentColor"
        stroke-width="1.6"
      />
      <!-- Glowing Center Core with Pulsing Spark -->
      <circle cx="12" cy="12" r="3.2" fill="currentColor" fill-opacity="0.25" stroke="currentColor" stroke-width="1.6" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" />
      <!-- Orbital Nodes -->
      <circle cx="5.2" cy="8.5" r="1.2" fill="currentColor" />
      <circle cx="18.8" cy="15.5" r="1.2" fill="currentColor" />
    </g>

    <!-- 3. Upvote: 能量共鸣赞同晶体 (用于主帖与评论点赞) -->
    <g v-else-if="name === 'upvote'">
      <!-- Bottom pedestal -->
      <rect
        x="6"
        y="19"
        width="12"
        height="2.5"
        rx="1.25"
        fill="currentColor"
        fill-opacity="0.2"
        stroke="currentColor"
        stroke-width="1.4"
      />
      <!-- Upward Kinetic Prism -->
      <path
        d="M12 2.8L19.2 11.2C19.8 11.9 19.3 13 18.3 13H15.2V16.2C15.2 16.7 14.8 17.2 14.2 17.2H9.8C9.2 17.2 8.8 16.7 8.8 16.2V13H5.7C4.7 13 4.2 11.9 4.8 11.2L12 2.8Z"
        fill="currentColor"
        fill-opacity="0.18"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linejoin="round"
      />
      <!-- Inner Specular Glare -->
      <path
        d="M12 5.5L16.2 10.8H13.8"
        stroke="currentColor"
        stroke-width="1.2"
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-opacity="0.6"
      />
    </g>

    <!-- 4. Chat: 共鸣探讨双波纹气泡 (用于回帖与见解数) -->
    <g v-else-if="name === 'chat'">
      <!-- Secondary background echo bubble -->
      <path
        d="M17.5 12.5C18.8 11.4 19.8 9.9 19.8 8.2C19.8 4.8 16.1 2 11.5 2C8.6 2 6 3.1 4.5 4.8"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-dasharray="2 1.5"
        stroke-opacity="0.6"
      />
      <!-- Primary rounded front bubble -->
      <path
        d="M4 8C4 5.8 6.2 4 9 4H15C17.8 4 20 5.8 20 8V12C20 14.2 17.8 16 15 16H10.5L6.5 19.5C5.8 20.1 4.8 19.6 4.8 18.7V16C4.3 16 4 15.6 4 15V8Z"
        fill="currentColor"
        fill-opacity="0.14"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linejoin="round"
      />
      <!-- 3 Discussion Pulse Dots -->
      <circle cx="8.5" cy="10" r="1.2" fill="currentColor" />
      <circle cx="12" cy="10" r="1.2" fill="currentColor" />
      <circle cx="15.5" cy="10" r="1.2" fill="currentColor" />
    </g>

    <!-- 5. Accepted: 翡翠解题印章 (用于已采纳方案、验证通过) -->
    <g v-else-if="name === 'accepted'">
      <!-- Octagonal soft shield -->
      <path
        d="M12 2L15.5 3.5L19 2.5L20 6.2L23 8.5L21.8 12L23 15.5L20 17.8L19 21.5L15.5 20.5L12 22L8.5 20.5L5 21.5L4 17.8L1 15.5L2.2 12L1 8.5L4 6.2L5 2.5L8.5 3.5L12 2Z"
        fill="currentColor"
        fill-opacity="0.15"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linejoin="round"
      />
      <!-- Bold checkmark -->
      <path
        d="M8 12.2L10.8 15L16.2 9"
        fill="none"
        stroke="currentColor"
        stroke-width="2.2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </g>

    <!-- 6. Pinned: 晶钻锚定徽标 (用于置顶与精选) -->
    <g v-else-if="name === 'pinned'">
      <!-- Diamond Gem Top -->
      <path
        d="M12 2L17.5 5.5L14.5 11.5L16 13.5H8L9.5 11.5L6.5 5.5L12 2Z"
        fill="currentColor"
        fill-opacity="0.2"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linejoin="round"
      />
      <!-- Needle Pin Tip with Gradient Line -->
      <path
        d="M12 13.5V21.5"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      />
      <!-- Surface Ripple -->
      <ellipse
        cx="12"
        cy="21.5"
        rx="3.5"
        ry="1.2"
        fill="none"
        stroke="currentColor"
        stroke-width="1.2"
        stroke-opacity="0.5"
      />
    </g>

    <!-- 7. Bookmark: 极客典藏缎带 (用于收藏归档) -->
    <g v-else-if="name === 'bookmark'">
      <path
        d="M6 3.5C6 2.67 6.67 2 7.5 2H16.5C17.33 2 18 2.67 18 3.5V21L12 16.8L6 21V3.5Z"
        fill="currentColor"
        fill-opacity="0.14"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linejoin="round"
      />
      <!-- Internal Star Spark Gem -->
      <circle cx="12" cy="7.5" r="1.6" fill="currentColor" />
      <path
        d="M12 5V10M9.5 7.5H14.5"
        stroke="currentColor"
        stroke-width="1.2"
        stroke-linecap="round"
      />
    </g>

    <!-- 8. Share / Teleport: 晶格超链跃迁 (用于复制分享) -->
    <g v-else-if="name === 'share'">
      <circle cx="17.5" cy="6.5" r="3.2" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="1.8" />
      <circle cx="6.5" cy="12" r="3.2" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="1.8" />
      <circle cx="17.5" cy="17.5" r="3.2" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="1.8" />
      <!-- Dynamic Connection Rays -->
      <path
        d="M9.2 10.6L14.8 7.8M9.2 13.4L14.8 16.2"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
      />
    </g>

    <!-- 9. Shield / Compliance: 创客哨兵护盾 (用于合规自律与言论举报) -->
    <g v-else-if="name === 'shield'">
      <path
        d="M12 2.5L20 5.8V11.5C20 16.5 16.6 20.8 12 22C7.4 20.8 4 16.5 4 11.5V5.8L12 2.5Z"
        fill="currentColor"
        fill-opacity="0.15"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linejoin="round"
      />
      <!-- Central Sentinel Eye & Core -->
      <ellipse cx="12" cy="11.5" rx="3.5" ry="2" fill="none" stroke="currentColor" stroke-width="1.4" />
      <circle cx="12" cy="11.5" r="1.2" fill="currentColor" />
    </g>

    <!-- 10. Topology: 物化路径树 (用于递归问答树标题) -->
    <g v-else-if="name === 'topology'">
      <!-- Root Node -->
      <circle cx="4.5" cy="6" r="2.5" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="1.6" />
      <!-- Branch 1 (Answer) -->
      <circle cx="12" cy="12" r="2.5" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="1.6" />
      <!-- Branch 2 (Deep reply) -->
      <circle cx="19.5" cy="18" r="2.5" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="1.6" />
      <!-- Curved Branching Fibers -->
      <path
        d="M7 6C9.5 6 9.5 12 12 12M14.5 12C17 12 17 18 19.5 18"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
      />
    </g>

    <!-- 11. Send: 离子推进光矢 (用于快捷回复提交) -->
    <g v-else-if="name === 'send'">
      <path
        d="M21.5 2.5L10 14M21.5 2.5L14.5 21.5C14.2 22.3 13.1 22.3 12.8 21.4L9.8 14.2L2.6 11.2C1.7 10.9 1.7 9.8 2.5 9.5L21.5 2.5Z"
        fill="currentColor"
        fill-opacity="0.16"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linejoin="round"
      />
      <circle cx="21" cy="3" r="1.2" fill="currentColor" />
    </g>

    <!-- 12. Lens: 晶核透镜 (用于搜索检索) -->
    <g v-else-if="name === 'lens'">
      <!-- Lens Circle -->
      <circle
        cx="10.5"
        cy="10.5"
        r="7"
        fill="currentColor"
        fill-opacity="0.12"
        stroke="currentColor"
        stroke-width="1.8"
      />
      <!-- Specular Refraction Glare on Glass -->
      <path
        d="M7.5 7.5C8.5 6.5 9.8 6 11.2 6"
        fill="none"
        stroke="currentColor"
        stroke-width="1.4"
        stroke-linecap="round"
        stroke-opacity="0.8"
      />
      <!-- Ergonomic Handle -->
      <path
        d="M15.5 15.5L20.5 20.5"
        stroke="currentColor"
        stroke-width="2.2"
        stroke-linecap="round"
      />
    </g>

    <!-- 13. Plus: 晶格聚能十字 (用于发起新风暴) -->
    <g v-else-if="name === 'plus'">
      <circle cx="12" cy="12" r="9.2" fill="currentColor" fill-opacity="0.14" stroke="currentColor" stroke-width="1.6" />
      <path
        d="M12 7.5V16.5M7.5 12H16.5"
        stroke="currentColor"
        stroke-width="2.2"
        stroke-linecap="round"
      />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </g>

    <!-- 14. Chevron: 柔和胶囊箭头 (用于折叠展开) -->
    <g v-else-if="name === 'chevron'">
      <path
        d="M6.5 9.5L12 15L17.5 9.5"
        fill="none"
        stroke="currentColor"
        stroke-width="2.2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </g>

    <!-- 15. Close: 晶面取消叉号 -->
    <g v-else-if="name === 'close'">
      <circle cx="12" cy="12" r="9" fill="currentColor" fill-opacity="0.1" />
      <path
        d="M15.5 8.5L8.5 15.5M8.5 8.5L15.5 15.5"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      />
    </g>

    <!-- 16. Empty Galaxy: 引力星尘透镜 (用于空状态) -->
    <g v-else-if="name === 'empty-galaxy'">
      <circle cx="12" cy="12" r="9" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-width="1.4" stroke-dasharray="3 2" />
      <ellipse cx="12" cy="12" rx="10" ry="3.5" transform="rotate(-30 12 12)" fill="none" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.4" />
      <!-- Central floating gem cube -->
      <path
        d="M12 7.5L16 9.8V14.2L12 16.5L8 14.2V9.8L12 7.5Z"
        fill="currentColor"
        fill-opacity="0.18"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linejoin="round"
      />
      <path d="M12 7.5V16.5M12 12L16 9.8M12 12L8 9.8" stroke="currentColor" stroke-width="1.2" />
      <!-- Orbiting dust points -->
      <circle cx="5" cy="7" r="1.2" fill="currentColor" />
      <circle cx="19" cy="16" r="1" fill="currentColor" />
      <circle cx="18" cy="8" r="1.5" fill="currentColor" />
    </g>

    <!-- Fallback default spark -->
    <g v-else>
      <circle cx="12" cy="12" r="8" fill="currentColor" fill-opacity="0.15" stroke="currentColor" stroke-width="1.8" />
    </g>
  </svg>
</template>

<script setup>
defineProps({
  name: {
    type: String,
    required: true,
  },
  size: {
    type: [Number, String],
    default: 16,
  },
});
</script>

<style scoped>
.opc-icon {
  display: inline-block;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), color 0.2s ease;
}
</style>
