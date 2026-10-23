<template>
  <!--
    A platform flow template rendered as a card.

    Structurally identical to the standard document card: the card carries the
    flow's identity and provenance — who published it, when it was published,
    whether it is officially certified, its summary, and how the community has
    engaged with it (likes / favourites / real usage).
  -->
  <div
    class="glass-card sop-flow-card opc-card-shell opc-card opc-reveal-host"
    :class="{ 'sop-flow-card-official': flow.is_official }"
    @mousemove="handleMouseMove"
    @click="$emit('open', flow)"
  >
    <!-- Card head: name + official certification badge -->
    <div class="sop-flow-card-head">
      <h3 class="sop-flow-card-title opc-clamp opc-clamp-2" :title="flow.name">{{ flow.name }}</h3>
      <span v-if="flow.is_official" class="sop-flow-official-badge" title="官方认证流程">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        官方认证
      </span>
    </div>

    <!-- Publisher -->
    <div class="sop-flow-card-provenance">
      <div class="sop-flow-author">
        <div class="sop-flow-author-avatar" :style="authorStyle">{{ initials }}</div>
        <div class="sop-flow-author-text">
          <span class="sop-flow-author-name">{{ flow.author_name || '平台编辑部' }}</span>
        </div>
      </div>
    </div>

    <!-- Summary (hover reveals full) -->
    <HoverRevealText :text="flow.summary || flow.description" :lines="2" />

    <!-- Card footer: functional metadata (usage / steps) -->
    <div class="sop-flow-card-footer" @click.stop>
      <!-- Verified-in-use: real usage proves the flow is effective -->
      <span
        class="sop-flow-action sop-flow-action-verified"
        :class="{ used: (flow.usage_count || 0) > 0 }"
        :title="(flow.usage_count || 0) > 0 ? `已有 ${flow.usage_count} 位创客使用该流程` : '暂无创客使用记录'"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M9 11l3 3L22 4"></path>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
        </svg>
        <span>{{ flow.usage_count || 0 }} 人使用</span>
      </span>

      <span class="sop-flow-card-fields">{{ flow.step_count }} 个步骤</span>
    </div>

    <!-- Unified interaction band lives at the very bottom -->
    <div class="sop-flow-interaction-row" @click.stop>
      <ContentInteractionBar
        target-type="SOP_FLOW"
        :target-id="flow.id"
        :target-title="flow.name"
        :like-count="flow.like_count ?? 0"
        :favorite-count="flow.favorite_count ?? 0"
        :love-count="flow.love_count ?? 0"
        :comment-count="flow.comment_count ?? 0"
        :dislike-count="flow.dislike_count ?? 0"
        :rating-avg="flow.rating_avg ?? 0"
        :rating-count="flow.rating_count ?? 0"
        :my-rating="flow.viewer?.rating ?? 0"
        :liked="flow.viewer ? flow.viewer.liked : false"
        :favorited="flow.viewer ? flow.viewer.favorited : Boolean(flow.favorited)"
        :loved="flow.viewer ? flow.viewer.loved : Boolean(flow.liked)"
        :commented="flow.viewer ? flow.viewer.commented : false"
        :disliked="flow.viewer?.disliked ?? false"
        :authenticated="authenticated"
        variant="band"
        @changed="handleInteractionChanged"
        @require-login="$emit('require-login')"
        @toast="$emit('toast', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
import HoverRevealText from '@/components/HoverRevealText.vue';
import { applyBarChange } from '@/utils/contentInteractions';

const props = defineProps({
  flow: { type: Object, required: true },
  authenticated: { type: Boolean, default: false },
});

defineEmits(['open', 'like', 'favorite', 'require-login', 'toast']);

function handleInteractionChanged(payload) {
  applyBarChange(props.flow, payload);
  props.flow.liked = Boolean(payload.viewer?.loved);
  props.flow.favorited = Boolean(payload.viewer?.favorited);
}

const initials = computed(() => {
  const name = props.flow.author_name || '编';
  const clean = String(name).replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
  return clean.slice(0, 1) || '编';
});

const authorStyle = computed(() => ({
  background: 'linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%)',
  color: 'var(--text-secondary)',
  border: '1px solid var(--glass-border-subtle)',
}));

function formatDate(isoStr) {
  if (!isoStr) return '未标注';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return '未标注';
  }
}

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  card.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`);
  card.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`);
}
</script>

<style scoped>
/* 卡片外壳由全局 .opc-card-shell 承载（统一 18px 20px / radius / glass / hover） */
.sop-flow-card {
  gap: 10px;
}

/* Officially certified flows are marked by the badge, not an edge stripe. */
.sop-flow-card-official {
  border-color: var(--glass-border-hover, rgba(0, 113, 227, 0.22));
}

/* Head: title + certification */
.sop-flow-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.sop-flow-card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sop-flow-official-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent, #0071e3);
  border: 1px solid rgba(0, 113, 227, 0.25);
  flex-shrink: 0;
  white-space: nowrap;
}

/* Provenance: publisher + organisation */
.sop-flow-card-provenance {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sop-flow-author {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.sop-flow-author-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.sop-flow-author-text {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.sop-flow-author-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.sop-flow-author-title {
  font-size: 10.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sop-flow-org {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.sop-flow-org-label {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.sop-flow-org-name {
  font-size: 11.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Summary */
.sop-flow-card-summary {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Publish date */
.sop-flow-card-date {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.sop-flow-date-label {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

.sop-flow-date-value {
  font-size: 11px;
  color: var(--text-secondary);
  font-family: var(--font-mono, monospace);
}

/* Footer: interactions */
.sop-flow-card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--glass-border-subtle);
  flex-wrap: wrap;
}

.sop-flow-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s ease;
}

.sop-flow-action:hover {
  border-color: rgba(0, 113, 227, 0.3);
  color: var(--accent);
}

.sop-flow-action.active {
  background: var(--accent-glass);
  border-color: var(--accent-glow);
  color: var(--accent);
}

.sop-flow-action-verified {
  cursor: default;
  color: var(--text-tertiary);
}

.sop-flow-action-verified.used {
  background: var(--status-success-soft);
  border-color: var(--status-success-soft);
  color: var(--status-success);
}

.sop-flow-action-verified:hover {
  border-color: var(--glass-border-subtle);
  color: inherit;
}

.sop-flow-card-fields {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

/* Unified interaction band at the bottom of the card */
.sop-flow-interaction-row {
  padding-top: 10px;
  margin-top: 2px;
}

[data-theme="dark"] .sop-flow-card {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}
</style>
