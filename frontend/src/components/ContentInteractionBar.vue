<template>
  <div class="ci-wrap">
    <!-- 1-5 Star Rating (only shown in detail contexts, not on cards) -->
    <div v-if="enableRating && variant === 'pill' && !compact" class="ci-rating-row" :class="ratingToneClass" @click.stop>
      <span class="ci-rating-label">评分</span>
      <button
        v-for="n in 5"
        :key="n"
        type="button"
        class="ci-star"
        :class="{ on: displayRating >= n }"
        @mouseenter="hoverRating = n"
        @mouseleave="hoverRating = 0"
        @click="rate(n)"
        :title="`${n} 分`"
        :aria-label="`${n} 分`"
      >
        <OpcIcon :name="displayRating >= n ? 'star-filled' : 'star'" :size="14" />
      </button>
      <span class="ci-rating-meta">
        <template v-if="ratingCount > 0">{{ ratingAvg }} · {{ ratingCount }}人</template>
        <template v-else>暂无人评分</template>
      </span>
      <span v-if="viewer.rating > 0" class="ci-rating-mine">我的 {{ viewer.rating }}<OpcIcon name="star-filled" :size="12" /></span>
    </div>

    <div class="ci-bar" :class="{ 'ci-bar-compact': compact, 'ci-bar-band': variant === 'band' }">
      <!-- 点赞 -->
      <button
        type="button"
        class="ci-btn ci-like"
        :class="{ active: viewer.liked }"
        @click.stop="toggle('LIKE')"
        :title="viewer.liked ? '取消点赞' : '点赞'"
        :aria-pressed="viewer.liked"
      >
        <InteractionIcon name="like" :filled="viewer.liked" :size="iconSize" />
        <span v-if="showLabels && variant !== 'band'" class="ci-label">{{ viewer.liked ? '已点赞' : '点赞' }}</span>
        <span class="ci-count">{{ counts.like }}</span>
      </button>

      <!-- 点踩：用户互动维护信息的有效性（内容失实/无帮助的直接信号） -->
      <button
        type="button"
        class="ci-btn ci-dislike"
        :class="{ active: viewer.disliked }"
        @click.stop="toggle('DISLIKE')"
        :title="viewer.disliked ? '取消点踩' : '点踩（信息失实或无帮助）'"
        :aria-pressed="viewer.disliked"
      >
        <InteractionIcon name="dislike" :filled="viewer.disliked" :size="iconSize" />
        <span v-if="showLabels && variant !== 'band'" class="ci-label">{{ viewer.disliked ? '已点踩' : '点踩' }}</span>
        <span class="ci-count">{{ counts.dislike }}</span>
      </button>

      <!-- 评论 -->
      <button
        type="button"
        class="ci-btn ci-comment"
        :class="{ active: viewer.commented }"
        @click.stop="handleCommentClick"
        :title="commentMode === 'disabled' ? '暂不支持评论' : '查看评论'"
        :disabled="commentMode === 'disabled'"
      >
        <InteractionIcon name="comment" :filled="viewer.commented" :size="iconSize" />
        <span v-if="showLabels && variant !== 'band'" class="ci-label">评论</span>
        <span class="ci-count">{{ counts.comment }}</span>
      </button>

      <!-- 喜欢 -->
      <button
        type="button"
        class="ci-btn ci-love"
        :class="{ active: viewer.loved }"
        @click.stop="toggle('LOVE')"
        :title="viewer.loved ? '取消喜欢' : '喜欢'"
        :aria-pressed="viewer.loved"
      >
        <InteractionIcon name="love" :filled="viewer.loved" :size="iconSize" />
        <span v-if="showLabels && variant !== 'band'" class="ci-label">{{ viewer.loved ? '已喜欢' : '喜欢' }}</span>
        <span class="ci-count">{{ counts.love }}</span>
      </button>

      <!-- 收藏 -->
      <button
        type="button"
        class="ci-btn ci-favorite"
        :class="{ active: viewer.favorited }"
        @click.stop="toggle('FAVORITE')"
        :title="viewer.favorited ? '取消收藏' : '收藏'"
        :aria-pressed="viewer.favorited"
      >
        <InteractionIcon name="favorite" :filled="viewer.favorited" :size="iconSize" />
        <span v-if="showLabels && variant !== 'band'" class="ci-label">{{ viewer.favorited ? '已收藏' : '收藏' }}</span>
        <span class="ci-count">{{ counts.favorite }}</span>
      </button>

      <!-- 举报：用户互动维护内容有效性，举报进入平台审核队列 -->
      <button
        type="button"
        class="ci-btn ci-report"
        :disabled="reporting"
        @click.stop="submitReport"
        title="举报违规或失实内容"
        aria-label="举报该内容"
      >
        <OpcIcon name="alert" :size="iconSize" />
        <span v-if="showLabels && variant !== 'band'" class="ci-label">举报</span>
      </button>

      <!-- 评分 (read-only score display on cards; 5-star rating lives in detail) -->
      <div
        v-if="variant === 'band'"
        class="ci-btn ci-score"
        :class="[scoreToneClass, { active: ratingCount > 0 }]"
        :title="ratingCount > 0 ? `平均评分 ${ratingAvg}，共 ${ratingCount} 人评分` : '暂无人评分，进入详情可打分'"
      >
        <InteractionIcon name="star" :filled="ratingCount > 0" :size="iconSize" />
        <span class="ci-label">评分</span>
        <span class="ci-count">{{ ratingCount > 0 ? ratingAvg : '暂无' }}</span>
      </div>

      <ContentCommentDrawer
        v-if="commentMode === 'drawer'"
        :visible="drawerVisible"
        :target-type="targetType"
        :target-id="String(targetId)"
        :title="targetTitle"
        :authenticated="authenticated"
        @close="drawerVisible = false"
        @count-change="handleCommentCount"
        @require-login="requireLogin"
        @toast="(payload) => emit('toast', payload)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import InteractionIcon from '@/components/InteractionIcon.vue';
import ContentCommentDrawer from '@/components/ContentCommentDrawer.vue';

const props = defineProps({
  targetType: { type: String, required: true },
  targetId: { type: [String, Number], required: true },
  targetTitle: { type: String, default: '' },
  likeCount: { type: [Number, String], default: 0 },
  favoriteCount: { type: [Number, String], default: 0 },
  loveCount: { type: [Number, String], default: 0 },
  commentCount: { type: [Number, String], default: 0 },
  dislikeCount: { type: [Number, String], default: 0 },
  ratingAvg: { type: [Number, String], default: 0 },
  ratingCount: { type: [Number, String], default: 0 },
  myRating: { type: [Number, String], default: 0 },
  liked: { type: Boolean, default: false },
  favorited: { type: Boolean, default: false },
  loved: { type: Boolean, default: false },
  commented: { type: Boolean, default: false },
  disliked: { type: Boolean, default: false },
  authenticated: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  showLabels: { type: Boolean, default: false },
  commentMode: { type: String, default: 'drawer' }, // drawer | emit | disabled
  autoLoad: { type: Boolean, default: false },
  variant: { type: String, default: 'pill' }, // pill | band
  enableRating: { type: Boolean, default: true },
});

const emit = defineEmits(['changed', 'open-comments', 'require-login', 'toast']);

const counts = reactive({
  like: toCount(props.likeCount),
  favorite: toCount(props.favoriteCount),
  love: toCount(props.loveCount),
  comment: toCount(props.commentCount),
  dislike: toCount(props.dislikeCount),
});

const viewer = reactive({
  liked: Boolean(props.liked),
  favorited: Boolean(props.favorited),
  loved: Boolean(props.loved),
  commented: Boolean(props.commented),
  disliked: Boolean(props.disliked),
  rating: toCount(props.myRating),
});

const rating = reactive({
  avg: toNum(props.ratingAvg),
  count: toCount(props.ratingCount),
});

const drawerVisible = ref(false);
const pendingKind = ref('');
const hoverRating = ref(0);
const ratingSaving = ref(false);
const reporting = ref(false);

const iconSize = computed(() => {
  if (props.variant === 'band') return 17;
  return props.compact ? 13 : 16;
});

const displayRating = computed(() => hoverRating.value || viewer.rating || Math.round(rating.avg) || 0);

function toneOf(value) {
  const v = Number(value) || 0;
  if (v >= 4) return 'high';
  if (v >= 3) return 'mid';
  if (v >= 1) return 'low';
  return '';
}

const ratingToneClass = computed(() => {
  const tone = toneOf(displayRating.value);
  return tone ? `tone-${tone}` : '';
});

const scoreToneClass = computed(() => {
  const tone = toneOf(rating.avg);
  return tone ? `tone-${tone}` : '';
});

watch(
  () => [
    props.likeCount, props.favoriteCount, props.loveCount, props.commentCount, props.dislikeCount,
  ],
  ([like, favorite, love, comment, dislike]) => {
    counts.like = toCount(like);
    counts.favorite = toCount(favorite);
    counts.love = toCount(love);
    counts.comment = toCount(comment);
    counts.dislike = toCount(dislike);
  }
);

watch(
  () => [props.liked, props.favorited, props.loved, props.commented, props.disliked],
  ([liked, favorited, loved, commented, disliked]) => {
    viewer.liked = Boolean(liked);
    viewer.favorited = Boolean(favorited);
    viewer.loved = Boolean(loved);
    viewer.commented = Boolean(commented);
    viewer.disliked = Boolean(disliked);
  }
);

watch(
  () => [props.ratingAvg, props.ratingCount, props.myRating],
  ([avg, count, mine]) => {
    rating.avg = toNum(avg);
    rating.count = toCount(count);
    viewer.rating = toCount(mine);
  }
);

function toCount(value) {
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? num : 0;
}

function toNum(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
}

function requireLogin() {
  emit('require-login');
}

// 举报（用户互动维护内容有效性）：提交到平台审核队列，由运营复核后下架/恢复。
async function submitReport() {
  if (!props.authenticated) {
    requireLogin();
    return;
  }
  if (reporting.value) return;
  reporting.value = true;
  try {
    const res = await dispatchGateway('moderation.report', {
      target_type: props.targetType,
      target_id: String(props.targetId),
      target_title: props.targetTitle || '',
      snippet_content: props.targetTitle || '',
    });
    if (res.ok && res.data) {
      emit('toast', {
        title: '举报已提交',
        message: '感谢反馈：该内容已进入平台审核队列，运营复核后将作下架或恢复处理。',
        type: 'SUCCESS',
      });
    } else {
      emit('toast', { title: '举报未提交', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '举报异常', message: '举报服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    reporting.value = false;
  }
}

function emitChanged() {
  emit('changed', {
    targetType: props.targetType,
    targetId: String(props.targetId),
    like_count: counts.like,
    favorite_count: counts.favorite,
    love_count: counts.love,
    comment_count: counts.comment,
    dislike_count: counts.dislike,
    rating_avg: rating.avg,
    rating_count: rating.count,
    viewer: {
      liked: viewer.liked,
      favorited: viewer.favorited,
      loved: viewer.loved,
      commented: viewer.commented,
      disliked: viewer.disliked,
      rating: viewer.rating,
    },
  });
}

function applyState(data) {
  if (!data) return;
  if (data.like_count !== undefined) counts.like = toCount(data.like_count);
  if (data.favorite_count !== undefined) counts.favorite = toCount(data.favorite_count);
  if (data.love_count !== undefined) counts.love = toCount(data.love_count);
  if (data.comment_count !== undefined) counts.comment = toCount(data.comment_count);
  if (data.dislike_count !== undefined) counts.dislike = toCount(data.dislike_count);
  if (data.rating_avg !== undefined) rating.avg = toNum(data.rating_avg);
  if (data.rating_count !== undefined) rating.count = toCount(data.rating_count);
  if (data.viewer) {
    viewer.liked = Boolean(data.viewer.liked);
    viewer.favorited = Boolean(data.viewer.favorited);
    viewer.loved = Boolean(data.viewer.loved);
    viewer.commented = Boolean(data.viewer.commented);
    viewer.disliked = Boolean(data.viewer.disliked);
    viewer.rating = toCount(data.viewer.rating);
  }
}

const KIND_META = {
  LIKE: { activeKey: 'liked', countKey: 'like' },
  FAVORITE: { activeKey: 'favorited', countKey: 'favorite' },
  LOVE: { activeKey: 'loved', countKey: 'love' },
  DISLIKE: { activeKey: 'disliked', countKey: 'dislike' },
};

async function toggle(kind) {
  if (!props.authenticated) {
    requireLogin();
    return;
  }
  if (pendingKind.value) return;

  const meta = KIND_META[kind];
  const activeKey = meta.activeKey;
  const countKey = meta.countKey;
  const wasActive = viewer[activeKey];
  const previousCount = counts[countKey];

  viewer[activeKey] = !wasActive;
  counts[countKey] = Math.max(0, previousCount + (wasActive ? -1 : 1));
  pendingKind.value = kind;
  emitChanged();

  try {
    const res = await dispatchGateway('content.interaction.toggle', {
      target_type: props.targetType,
      target_id: String(props.targetId),
      kind,
      target_title: props.targetTitle || '',
    });
    if (res.ok && res.data) {
      applyState(res.data);
      emitChanged();
    } else {
      viewer[activeKey] = wasActive;
      counts[countKey] = previousCount;
      emitChanged();
      emit('toast', { title: '互动未完成', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    viewer[activeKey] = wasActive;
    counts[countKey] = previousCount;
    emitChanged();
    emit('toast', { title: '互动异常', message: '互动服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    pendingKind.value = '';
  }
}

async function rate(score) {
  if (!props.authenticated) {
    requireLogin();
    return;
  }
  if (ratingSaving.value) return;
  ratingSaving.value = true;
  const previousMine = viewer.rating;
  const previousAvg = rating.avg;
  const previousCount = rating.count;
  viewer.rating = score; // optimistic
  hoverRating.value = 0;
  try {
    const res = await dispatchGateway('content.interaction.rate', {
      target_type: props.targetType,
      target_id: String(props.targetId),
      score,
    });
    if (res.ok && res.data) {
      applyState(res.data);
      emitChanged();
      emit('toast', {
        title: previousMine ? '评分已更新' : '评分成功',
        message: previousMine ? `已将评分更新为 ${score} 分。` : `感谢你为该内容打出 ${score} 分。`,
        type: 'SUCCESS',
      });
    } else {
      viewer.rating = previousMine;
      rating.avg = previousAvg;
      rating.count = previousCount;
      emitChanged();
      emit('toast', { title: '评分未完成', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    viewer.rating = previousMine;
    rating.avg = previousAvg;
    rating.count = previousCount;
    emitChanged();
    emit('toast', { title: '评分异常', message: '评分服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    ratingSaving.value = false;
  }
}

function handleCommentClick() {
  if (props.commentMode === 'disabled') return;
  if (props.commentMode === 'emit') {
    emit('open-comments');
    return;
  }
  drawerVisible.value = true;
}

function handleCommentCount(nextTotal) {
  counts.comment = toCount(nextTotal);
  emitChanged();
}

async function loadState() {
  if (!props.targetId) return;
  try {
    const res = await dispatchGateway(
      'content.interactions.state',
      {
        targets: [{ target_type: props.targetType, target_id: String(props.targetId) }],
      },
      { silent: true }
    );
    const state = res.ok && res.data && Array.isArray(res.data.items) ? res.data.items[0] : null;
    if (state) {
      applyState(state);
      emitChanged();
    }
  } catch (e) {
    // Detail pages must never fail to render because the counter call failed.
  }
}

watch(
  () => [props.targetType, props.targetId, props.autoLoad],
  ([, , autoLoad]) => {
    if (autoLoad) loadState();
  },
  { immediate: true }
);
</script>

<style scoped>
.ci-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

/* ===== 1-5 Star Rating Row ===== */
.ci-rating-row {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  font-size: 11.5px;
}

.ci-rating-label {
  color: var(--text-tertiary, #8b93a1);
  margin-right: 2px;
}

.ci-star {
  border: none;
  background: transparent;
  color: var(--text-tertiary, #cfd3da);
  font-size: 15px;
  line-height: 1;
  padding: 0 1px;
  cursor: pointer;
  transition: color 0.15s ease, transform 0.15s ease;
}

.ci-star.on {
  color: var(--accent);
}

.ci-star:hover {
  transform: scale(1.18);
  color: var(--accent);
}

/* Star fill color by score: 4-5 success / 3 warning / 1-2 danger */
.ci-rating-row.tone-high .ci-star.on,
.ci-rating-row.tone-high .ci-star:hover {
  color: var(--status-success);
}

.ci-rating-row.tone-mid .ci-star.on,
.ci-rating-row.tone-mid .ci-star:hover {
  color: var(--status-warning);
}

.ci-rating-row.tone-low .ci-star.on,
.ci-rating-row.tone-low .ci-star:hover {
  color: var(--status-danger);
}

.ci-rating-meta {
  color: var(--text-tertiary, #8b93a1);
  font-size: 10.5px;
  margin-left: 4px;
}

.ci-rating-mine {
  color: var(--accent);
  font-size: 10.5px;
  font-weight: 700;
}

/* ===== Interaction buttons ===== */
.ci-bar {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.ci-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 30px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--glass-border, rgba(120, 130, 150, 0.22));
  background: transparent;
  color: var(--text-secondary, #5b6472);
  font-size: 11.5px;
  font-weight: 650;
  line-height: 1;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
  white-space: nowrap;
}

.ci-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.ci-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ci-label {
  font-size: 11px;
}

.ci-count {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}

.ci-like.active {
  color: var(--accent);
}

.ci-favorite.active {
  color: var(--accent);
}

.ci-love.active {
  color: var(--accent);
}

/* 举报：默认弱化展示，悬停提示风险语义色 */
.ci-report {
  opacity: 0.75;
}

.ci-report:hover:not(:disabled) {
  color: var(--warning, #b25000);
  opacity: 1;
}

.ci-comment.active {
  color: var(--accent);
}

.ci-dislike.active {
  color: var(--accent);
}

/* Read-only 评分 score display (cards) */
.ci-score {
  cursor: default;
}

.ci-score:hover {
  transform: none;
  background: transparent;
}

.ci-score .ci-label {
  color: var(--text-tertiary, #8b93a1);
}

.ci-bar-compact {
  gap: 4px;
}

.ci-bar-compact .ci-btn {
  min-height: 26px;
  padding: 4px 8px;
  font-size: 11px;
  gap: 4px;
}

.ci-bar-compact .ci-count {
  font-size: 10.5px;
}

/* ===== Band variant: icon-only evenly-spread social action strip ===== */
.ci-bar-band {
  display: flex;
  width: 100%;
  gap: 0;
  padding: 0;
  background: transparent;
  border: none;
}

.ci-bar-band .ci-btn {
  flex: 1;
  justify-content: center;
  min-height: 32px;
  padding: 4px 6px;
  gap: 6px;
  border: none;
  border-radius: 0;
  background: transparent;
  color: var(--text-secondary, #5b6472);
  font-size: 12.5px;
}

.ci-bar-band .ci-btn:hover:not(:disabled) {
  transform: none;
}

.ci-bar-band .ci-count {
  font-size: 12.5px;
  font-weight: 700;
}

.ci-bar-band .ci-like.active {
  color: var(--accent);
}

.ci-bar-band .ci-favorite.active {
  color: var(--accent);
}

.ci-bar-band .ci-love.active {
  color: var(--accent);
}

.ci-bar-band .ci-comment.active {
  color: var(--accent);
}

.ci-bar-band .ci-dislike.active {
  color: var(--accent);
}

.ci-bar-band .ci-score.tone-high {
  color: var(--status-success);
}

.ci-bar-band .ci-score.tone-mid {
  color: var(--status-warning);
}

.ci-bar-band .ci-score.tone-low {
  color: var(--status-danger);
}

.ci-bar-band .ci-score:hover {
  background: transparent;
}

@media (max-width: 640px) {
  .ci-btn {
    padding: 4px 8px;
  }
}
</style>
