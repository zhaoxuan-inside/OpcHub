<template>
  <div class="publish-notice" role="note">
    <span class="publish-notice-mark">发布公约</span>
    <p class="publish-notice-text">
      所有注册用户均可发布。平台仅进行敏感词校验，不对信息真实性背书；内容的有效性由
      点赞、点踩、评分与举报等社区互动共同维护。官方账号发布的内容会显示「官方」标签。
    </p>
  </div>
</template>

<script setup>
// 统一发布公约：政策 / 文书 / 流程 / 头脑风暴 / 产品橱窗 / 需求集市 / 生态特权
// 共用同一套创建发布入口说明，避免各页面口径不一致。
</script>

<style scoped>
.publish-notice {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 0 0 18px;
  padding: 10px 14px;
  border: 1px solid var(--glass-border, rgba(120, 130, 150, 0.22));
  border-radius: 12px;
  background: rgba(0, 113, 227, 0.045);
}

.publish-notice-mark {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent, #0071e3);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1.6;
}

.publish-notice-text {
  margin: 0;
  color: var(--text-secondary, #5b6472);
  font-size: 12px;
  line-height: 1.6;
}

[data-theme='dark'] .publish-notice {
  background: rgba(41, 151, 255, 0.08);
}
</style>
