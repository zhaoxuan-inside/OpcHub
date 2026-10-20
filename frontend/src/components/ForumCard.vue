<template>
  <!-- 1. High-Density Compact Mode (极速高密模式) -->
  <article
    v-if="density === 'compact'"
    class="compact-post-row glass-box"
    @click="$emit('select', post)"
  >
    <div class="compact-main-col">
      <div class="compact-title-row">
        <span v-if="post.pinned" class="badge-pinned-sm">
          <ForumIcon name="pinned" size="10" />
          <span>{{ post.pinned }}</span>
        </span>
        <span class="badge-category-sm" :style="pillStyle">
          {{ categoryLabel }}
        </span>
        <h4 class="compact-title" :title="post.title">
          {{ post.title }}
        </h4>
      </div>

      <div class="compact-meta-row">
        <div class="author-micro">
          <span class="author-micro-avatar" :style="{ background: avatarBg }">
            {{ authorInitial }}
          </span>
          <span class="compact-author-name">{{ post.author || '平台创客' }}</span>
        </div>
        <span class="dot-sep">·</span>
        <span class="compact-time">{{ post.updated_at || '刚刚' }}</span>
        <span class="dot-sep">·</span>
        <span class="compact-ip">{{ post.ip_location || '来自 浙江' }}</span>

        <!-- Primary Highlight Metric in Compact View -->
        <template v-if="computedMetrics.length > 0">
          <span class="dot-sep">·</span>
          <span class="compact-metric-pill" :class="`metric-${computedMetrics[0].type || 'info'}`">
            <span class="metric-icon">{{ computedMetrics[0].icon }}</span>
            <span class="metric-label">{{ computedMetrics[0].label }}:</span>
            <strong class="metric-val">{{ computedMetrics[0].val }}</strong>
          </span>
        </template>
      </div>
    </div>

    <!-- Compact Actions Group -->
    <div class="compact-actions-col" @click.stop>
      <button
        type="button"
        class="compact-btn-upvote"
        :class="{ active: isUpvoted }"
        @click="handleToggleUpvote"
        :title="isUpvoted ? '已赞同 (点击取消)' : '赞同实战经验'"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M12 4.5L19 14H5L12 4.5Z" :fill="isUpvoted ? 'currentColor' : 'none'"></path>
        </svg>
        <span>{{ currentUpvotes }}</span>
      </button>

      <button
        type="button"
        class="compact-btn-action"
        @click="$emit('select', post)"
        title="查看探讨见解"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <span>{{ post.replies || post.comment_count || 0 }}</span>
      </button>

      <button
        type="button"
        class="compact-btn-icon"
        :class="{ active: isBookmarked }"
        @click="handleToggleBookmark"
        :title="isBookmarked ? '已收藏' : '收藏归档'"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" :fill="isBookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
        </svg>
      </button>

      <button
        type="button"
        class="compact-btn-icon"
        :class="{ active: isCopied }"
        @click="handleShare"
        :title="isCopied ? '已复制链接' : '分享经验帖'"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="18" cy="5" r="3"></circle>
          <circle cx="6" cy="12" r="3"></circle>
          <circle cx="18" cy="19" r="3"></circle>
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
        </svg>
      </button>

      <button
        v-if="canDelete"
        type="button"
        class="compact-btn-icon compact-btn-delete"
        @click="$emit('delete', post)"
        title="删除此实战帖"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
      </button>
    </div>
  </article>

  <!-- 2. Standard Zhihu Feed Stream Mode (知乎文章流深度模式) -->
  <article
    v-else
    class="zhihu-post-card glass-box"
    :class="{ 'card-expanded': isExpanded }"
    @click="$emit('select', post)"
  >
    <!-- 2.1 Ultra-Compact Single-Row Author Meta -->
    <div class="zhihu-author-header">
      <div class="author-left">
        <div class="author-avatar" :style="{ background: avatarBg }">
          {{ authorInitial }}
        </div>
        <div class="author-inline-info">
          <span class="author-name">{{ post.author || '平台创客' }}</span>
          <span class="author-badge">认证个体</span>
          <span class="dot-sep">·</span>
          <span class="post-time">{{ post.updated_at || '刚刚' }}</span>
          <span class="dot-sep">·</span>
          <span class="post-ip">{{ post.ip_location || '来自 浙江' }}</span>
          <span v-if="post.view_count" class="dot-sep">·</span>
          <span v-if="post.view_count" class="post-views">浏览 {{ post.view_count }}</span>
        </div>
      </div>

      <!-- Category & Pinned Badges -->
      <div class="badges-right">
        <span v-if="post.pinned" class="badge-pinned">
          <ForumIcon name="pinned" size="11" />
          <span>{{ post.pinned }}</span>
        </span>
        <span class="badge-category" :style="pillStyle">
          {{ categoryLabel }}
        </span>
      </div>
    </div>

    <!-- 2.2 Zhihu Headline Title -->
    <h3 class="zhihu-card-title">
      {{ post.title }}
    </h3>

    <!-- 2.3 Executive Practical Metric Chips (实战量化核心指标) -->
    <div v-if="computedMetrics.length > 0" class="zhihu-metrics-row">
      <div
        v-for="(m, idx) in computedMetrics"
        :key="idx"
        class="metric-chip"
        :class="`chip-${m.type || 'info'}`"
      >
        <span class="chip-icon">{{ m.icon }}</span>
        <span class="chip-label">{{ m.label }}</span>
        <strong class="chip-val">{{ m.val }}</strong>
      </div>
    </div>

    <!-- 2.4 Excerpt with Inline Markdown Expand/Collapse (知乎核心体验：卡片内原地阅读全文) -->
    <div class="zhihu-card-content" @click.stop>
      <!-- Collapsed: 3-line rich excerpt -->
      <div v-if="!isExpanded" class="snippet-wrapper">
        <p class="snippet-text">
          {{ post.snippet || post.content }}
        </p>
        <button type="button" class="btn-read-full" @click="toggleExpand">
          <span>阅读全文</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      </div>

      <!-- Expanded: In-Place High-Density Markdown Rendering -->
      <div v-else class="expanded-full-body">
        <div
          class="markdown-rendered-content expanded-markdown"
          v-html="renderedFullContent"
        ></div>
        <div class="inline-collapse-bar">
          <button type="button" class="btn-collapse-inline" @click="toggleExpand">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
            <span>收起全文</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 2.5 Keyword Tags -->
    <div v-if="computedTags.length > 0 && !isExpanded" class="zhihu-keywords-row">
      <span
        v-for="tag in computedTags"
        :key="tag"
        class="keyword-tag"
        @click.stop
      >
        #{{ tag }}
      </span>
    </div>

    <!-- 2.6 Zhihu Signature Action Toolbar -->
    <div class="zhihu-action-bar">
      <div class="action-buttons-group">
        <!-- Upvote (知乎经典赞同块) -->
        <button
          type="button"
          class="btn-zhihu-upvote"
          :class="{ active: isUpvoted }"
          @click.stop="handleToggleUpvote"
          :title="isUpvoted ? '取消赞同' : '赞同此实战经验'"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 4.5L19 14H5L12 4.5Z" :fill="isUpvoted ? 'currentColor' : 'none'"></path>
          </svg>
          <span class="upvote-label">{{ isUpvoted ? '已赞同' : '赞同' }}</span>
          <span class="upvote-count">{{ currentUpvotes }}</span>
        </button>

        <!-- Comments -->
        <button
          type="button"
          class="btn-zhihu-action"
          @click.stop="$emit('select', post)"
          title="进入深度交流与评论树"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span>{{ post.replies || post.comment_count || 0 }} 条探讨</span>
        </button>

        <!-- Bookmark -->
        <button
          type="button"
          class="btn-zhihu-action"
          :class="{ active: isBookmarked }"
          @click.stop="handleToggleBookmark"
          title="收藏归档至知识库"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" :fill="isBookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
          <span>{{ isBookmarked ? '已收藏' : '收藏' }}</span>
        </button>

        <!-- Share -->
        <button
          type="button"
          class="btn-zhihu-action"
          :class="{ active: isCopied }"
          @click.stop="handleShare"
          title="分享实战帖"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="18" cy="5" r="3"></circle>
            <circle cx="6" cy="12" r="3"></circle>
            <circle cx="18" cy="19" r="3"></circle>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
          </svg>
          <span>{{ isCopied ? '已复制' : '分享' }}</span>
        </button>

        <!-- Delete Button for Author or Admin -->
        <button
          v-if="canDelete"
          type="button"
          class="btn-zhihu-action btn-zhihu-delete"
          @click.stop="$emit('delete', post)"
          title="删除此实战帖"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          <span>删除</span>
        </button>

        <!-- Deep Dive Action Link -->
        <button
          type="button"
          class="btn-zhihu-deep"
          @click.stop="$emit('select', post)"
          title="查看完整评论与探讨方案"
        >
          <span>深入探讨 →</span>
        </button>
      </div>

      <!-- Right Discussion Info or Collapse Button -->
      <div class="action-right-wrap">
        <button
          v-if="isExpanded"
          type="button"
          class="btn-collapse-corner"
          @click.stop="toggleExpand"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <polyline points="18 15 12 9 6 15"></polyline>
          </svg>
          <span>收起全文</span>
        </button>
        <div v-else class="discuss-heat-tag">
          <span class="heat-flame">🔥</span>
          <span>{{ Math.max(3, Math.floor((post.replies || post.comment_count || 8) * 1.5)) }} 人热议中</span>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import ForumIcon from '@/components/ForumIcon.vue';
import { renderMarkdown } from '@/utils/markdown';

const props = defineProps({
  post: {
    type: Object,
    required: true,
  },
  userSession: {
    type: Object,
    default: null,
  },
  density: {
    type: String,
    default: 'comfortable', // 'comfortable' | 'compact'
  },
});

const emit = defineEmits(['select', 'upvote', 'bookmark', 'delete', 'toast']);

const currentUserId = computed(() => {
  return props.userSession?.uid || props.userSession?.id || props.userSession?.user?.id || props.userSession?.user?.uid || '';
});

const currentUserRole = computed(() => {
  return (props.userSession?.role || props.userSession?.user?.role || localStorage.getItem('opchub_current_role') || 'MAKER').toUpperCase();
});

const canDelete = computed(() => {
  if (currentUserRole.value === 'ADMIN') return true;
  if (currentUserId.value && props.post?.author_id && String(props.post.author_id) === String(currentUserId.value)) {
    return true;
  }
  return false;
});

const isUpvoted = ref(Boolean(props.post.is_upvoted));
const currentUpvotes = ref(props.post.upvotes ?? props.post.upvote_count ?? 0);
const isBookmarked = ref(Boolean(props.post.is_bookmarked));
const isCopied = ref(false);
const isExpanded = ref(false);
let copyTimer = null;

watch(
  () => props.post,
  (newP) => {
    if (newP) {
      isUpvoted.value = Boolean(newP.is_upvoted);
      currentUpvotes.value = newP.upvotes ?? newP.upvote_count ?? 0;
      isBookmarked.value = Boolean(newP.is_bookmarked);
    }
  },
  { deep: true }
);

function toggleExpand(e) {
  if (e) e.stopPropagation();
  isExpanded.value = !isExpanded.value;
}

const renderedFullContent = computed(() => {
  const text = props.post.content || props.post.snippet || '';
  return renderMarkdown(text);
});

const authorInitial = computed(() => {
  const name = props.post.author || '创客';
  return name[0].toUpperCase();
});

const avatarBg = computed(() => {
  const code = (props.post.author || 'M').charCodeAt(0);
  const gradients = [
    'linear-gradient(135deg, #0071E3, #42B883)',
    'linear-gradient(135deg, #FF6B6B, #FFE66D)',
    'linear-gradient(135deg, #4E65FF, #92EFFD)',
    'linear-gradient(135deg, #7F00FF, #E100FF)',
    'linear-gradient(135deg, #F97316, #FB7185)',
  ];
  return gradients[code % gradients.length];
});

// Category metadata
const categoryMeta = {
  DEV: { label: '技术踩坑', color: '#0071e3', bg: 'rgba(0, 113, 227, 0.1)' },
  BIZ: { label: '独立出海', color: '#00a3ff', bg: 'rgba(0, 163, 255, 0.1)' },
  TAX: { label: '工商财税', color: '#e67e22', bg: 'rgba(230, 126, 34, 0.12)' },
  AGENTS: { label: 'AI智能体', color: '#a855f7', bg: 'rgba(168, 85, 247, 0.12)' },
  POLICY: { label: '政策申报', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)' },
};

const normalizedCategory = computed(() => {
  const cat = (props.post.category_code || props.post.category || '').toUpperCase();
  if (cat.includes('DEV') || cat.includes('技术')) return 'DEV';
  if (cat.includes('BIZ') || cat.includes('出海')) return 'BIZ';
  if (cat.includes('TAX') || cat.includes('财税')) return 'TAX';
  if (cat.includes('AGENT') || cat.includes('智能体')) return 'AGENTS';
  if (cat.includes('POLICY') || cat.includes('政策')) return 'POLICY';
  return 'DEV';
});

const categoryLabel = computed(() => {
  return props.post.category || categoryMeta[normalizedCategory.value]?.label || '实战讨论';
});

const pillStyle = computed(() => {
  const meta = categoryMeta[normalizedCategory.value] || categoryMeta.DEV;
  return {
    color: meta.color,
    background: meta.bg,
  };
});

// High-Density Metric Badges Resolution
const computedMetrics = computed(() => {
  if (props.post.metrics && Array.isArray(props.post.metrics) && props.post.metrics.length > 0) {
    return props.post.metrics;
  }
  const list = [];
  const t = props.post.title || '';
  const c = props.post.snippet || props.post.content || '';

  if (t.includes('免征') || t.includes('年报') || c.includes('30 万')) {
    list.push({ label: '季度免征额', val: '¥300,000', icon: '💰', type: 'success' });
    list.push({ label: '申报耗时', val: '15分钟', icon: '⏱️', type: 'info' });
    list.push({ label: '综合税负', val: '0%', icon: '📊', type: 'accent' });
  } else if (t.includes('算力') || c.includes('算力券')) {
    list.push({ label: '财政直拨', val: '¥120,000', icon: '🎁', type: 'success' });
    list.push({ label: '审批周期', val: '45天', icon: '📅', type: 'info' });
    list.push({ label: '资质要件', val: '软著+科技型', icon: '📝', type: 'warning' });
  } else if (t.includes('Stripe') || t.includes('对公户') || c.includes('结汇')) {
    list.push({ label: '结汇时效', val: 'T+1 自动到账', icon: '⚡', type: 'success' });
    list.push({ label: '综合费率', val: '4.8% → 1.9%', icon: '💵', type: 'accent' });
    list.push({ label: '合规阻断', val: '0% 拦截', icon: '🛡️', type: 'info' });
  } else if (t.includes('pgvector') || t.includes('PostgreSQL')) {
    list.push({ label: '检索延迟', val: '120ms → 18ms', icon: '⚡', type: 'success' });
    list.push({ label: '节点容量', val: '200万向量', icon: '💾', type: 'info' });
    list.push({ label: '基础设施', val: '$42/月', icon: '📉', type: 'accent' });
  } else if (t.includes('FastAPI') || t.includes('SQLite') || t.includes('全栈')) {
    list.push({ label: '承载峰值', val: '100,000 MAU', icon: '👥', type: 'success' });
    list.push({ label: '硬件规格', val: '2核4G 单机', icon: '🖥️', type: 'info' });
    list.push({ label: '运维精力', val: '< 5% 时长', icon: '🚀', type: 'accent' });
  } else if (t.includes('定价') || t.includes('Freemium') || c.includes('留存')) {
    list.push({ label: '跟踪样本', val: '1,200 付费创客', icon: '📊', type: 'info' });
    list.push({ label: 'LTV提升', val: '3.2 倍', icon: '💰', type: 'success' });
    list.push({ label: '年度留存', val: '68.4%', icon: '📈', type: 'accent' });
  }
  return list;
});

const computedTags = computed(() => {
  if (props.post.tags && Array.isArray(props.post.tags) && props.post.tags.length > 0) {
    return props.post.tags;
  }
  const list = [];
  const t = props.post.title || '';
  if (t.includes('Stripe')) list.push('Stripe跨境', '万里汇对公户');
  if (t.includes('pgvector') || t.includes('PostgreSQL')) list.push('pgvector', 'PostgreSQL', 'HNSW');
  if (t.includes('年报') || t.includes('免征')) list.push('合规免税', '税务年报', '小微优惠');
  if (t.includes('算力')) list.push('算力券补贴', '科技入库', '软著申报');
  if (t.includes('Agent')) list.push('AI智能体', 'RAG架构');
  if (t.includes('出海')) list.push('出海定价', 'SaaS留存');
  if (list.length === 0) list.push('实战落地', '避坑指南');
  return list.slice(0, 4);
});

function handleToggleUpvote() {
  if (isUpvoted.value) {
    isUpvoted.value = false;
    currentUpvotes.value = Math.max(0, currentUpvotes.value - 1);
  } else {
    isUpvoted.value = true;
    currentUpvotes.value += 1;
  }
  emit('upvote', { post: props.post, isUpvoted: isUpvoted.value, count: currentUpvotes.value });
}

function handleToggleBookmark() {
  isBookmarked.value = !isBookmarked.value;
  props.post.is_bookmarked = isBookmarked.value;

  try {
    const raw = localStorage.getItem('opchub_forum_bookmarks');
    let bookmarks = raw ? JSON.parse(raw) : [];
    const sid = String(props.post.id);
    if (isBookmarked.value) {
      if (!bookmarks.some((b) => (typeof b === 'object' ? String(b.id) === sid : String(b) === sid))) {
        bookmarks.push({
          id: props.post.id,
          title: props.post.title,
          category: categoryLabel.value,
          author: props.post.author,
          created_at: new Date().toISOString(),
        });
      }
    } else {
      bookmarks = bookmarks.filter((b) => (typeof b === 'object' ? String(b.id) !== sid : String(b) !== sid));
    }
    localStorage.setItem('opchub_forum_bookmarks', JSON.stringify(bookmarks));
  } catch (e) {}

  emit('bookmark', { post: props.post, isBookmarked: isBookmarked.value });
}

async function handleShare() {
  const origin = window.location.origin || '';
  const pathname = window.location.pathname || '/';
  const shareUrl = `${origin}${pathname}#forum?post_id=${encodeURIComponent(props.post?.id || '')}`;
  const shareText = `【OpcHub 头脑风暴实战经验分享】\n《${props.post?.title}》\n作者：${props.post?.author || '创客'}\n链接：${shareUrl}`;

  let ok = false;
  if (navigator?.clipboard?.writeText && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(shareText);
      ok = true;
    } catch (e) {}
  }
  if (!ok) {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = shareText;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '-9999px';
      textarea.setAttribute('readonly', '');
      document.body.appendChild(textarea);
      textarea.select();
      ok = document.execCommand('copy');
      document.body.removeChild(textarea);
    } catch (e) {}
  }

  if (ok) {
    isCopied.value = true;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      isCopied.value = false;
    }, 2000);
  }

  emit('toast', {
    title: ok ? '实战经验已复制' : '分享链接已就绪',
    message: ok ? '实战帖标题与深度链接已存入剪贴板，可随时发给同行创客交流！' : `链接：${shareUrl}`,
    type: ok ? 'SUCCESS' : 'INFO',
  });
}
</script>

<style scoped>
/* ========================================================
   1. Compact High-Density Row Mode (紧凑模式样式)
   ======================================================== */
.compact-post-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: var(--radius-sm, 8px);
  background: var(--glass-surface, rgba(255, 255, 255, 0.7));
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.85));
  cursor: pointer;
  transition: all 0.16s ease;
  gap: 16px;
}

.compact-post-row:hover {
  transform: translateY(-1px);
  border-color: rgba(0, 113, 227, 0.3);
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.08);
}

.compact-main-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.compact-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.badge-pinned-sm {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 700;
  color: #ff3b30;
  background: rgba(255, 59, 48, 0.1);
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
}

.badge-category-sm {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.compact-title {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text-primary, #121316);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.15s ease;
}

.compact-post-row:hover .compact-title {
  color: var(--accent, #0071E3);
}

.compact-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-tertiary, #7D828D);
  white-space: nowrap;
  overflow: hidden;
}

.author-micro {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.author-micro-avatar {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
}

.compact-author-name {
  font-weight: 500;
  color: var(--text-secondary, #4B4E56);
}

.compact-metric-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent, #0071E3);
}

.compact-metric-pill.metric-success {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.compact-metric-pill.metric-warning {
  background: rgba(245, 158, 11, 0.1);
  color: #d97706;
}

.compact-actions-col {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.compact-btn-upvote {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 4px;
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent, #0071E3);
  border: none;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.compact-btn-upvote.active {
  background: var(--accent, #0071E3);
  color: #fff;
}

.compact-btn-action,
.compact-btn-icon {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  background: transparent;
  color: var(--text-tertiary, #7D828D);
  border: none;
  font-size: 11.5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.compact-btn-action:hover,
.compact-btn-icon:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--accent, #0071E3);
}

.compact-btn-icon.active {
  color: var(--accent, #0071E3);
}

/* ========================================================
   2. Standard Comfortable Zhihu Post Card (深度文章流)
   ======================================================== */
.zhihu-post-card {
  display: flex;
  flex-direction: column;
  padding: 15px 20px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface, rgba(255, 255, 255, 0.72));
  backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.85));
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-sizing: border-box;
  width: 100%;
}

.zhihu-post-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 113, 227, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
  border-color: rgba(0, 113, 227, 0.25);
}

/* 2.1 Ultra-Compact Single-Row Author Meta */
.zhihu-author-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.author-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.author-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 11px;
  flex-shrink: 0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}

.author-inline-info {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-tertiary, #7D828D);
  line-height: 1;
}

.author-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #121316);
}

.author-badge {
  font-size: 10px;
  font-weight: 500;
  color: var(--accent, #0071E3);
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  border: 1px solid rgba(0, 113, 227, 0.16);
  padding: 1px 5px;
  border-radius: 3px;
}

.dot-sep {
  opacity: 0.5;
}

.badges-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge-pinned {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10.5px;
  font-weight: 600;
  color: #ff3b30;
  background: rgba(255, 59, 48, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-category {
  font-size: 10.5px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 5px;
}

/* 2.2 Headline Title */
.zhihu-card-title {
  font-size: 16.5px;
  font-weight: 700;
  color: var(--text-primary, #121316);
  line-height: 1.42;
  margin: 0 0 8px 0;
  letter-spacing: -0.2px;
  transition: color 0.16s ease;
}

.zhihu-post-card:hover .zhihu-card-title {
  color: var(--accent, #0071E3);
}

/* 2.3 Executive Practical Metric Chips */
.zhihu-metrics-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 9px;
}

.metric-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 5px;
  background: rgba(0, 113, 227, 0.06);
  border: 1px solid rgba(0, 113, 227, 0.12);
  color: var(--text-secondary, #333);
}

.metric-chip strong {
  color: var(--accent, #0071E3);
  font-weight: 600;
}

.metric-chip.chip-success {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.18);
}
.metric-chip.chip-success strong {
  color: #059669;
}

.metric-chip.chip-warning {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.18);
}
.metric-chip.chip-warning strong {
  color: #d97706;
}

.metric-chip.chip-accent {
  background: rgba(127, 0, 255, 0.06);
  border-color: rgba(127, 0, 255, 0.14);
}
.metric-chip.chip-accent strong {
  color: #7c3aed;
}

/* 2.4 Excerpt & In-Place Expand */
.zhihu-card-content {
  margin-bottom: 10px;
}

.snippet-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.snippet-text {
  font-size: 13.5px;
  line-height: 1.62;
  color: var(--text-secondary, #44474E);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-read-full {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--accent, #0071E3);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 2px 0;
  width: fit-content;
  transition: opacity 0.16s ease;
}

.btn-read-full:hover {
  opacity: 0.8;
  text-decoration: underline;
}

/* In-Place Markdown Expanded Container */
.expanded-full-body {
  margin-top: 8px;
  padding: 14px 16px;
  background: rgba(0, 0, 0, 0.015);
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.05));
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.expanded-markdown {
  font-size: 14px;
  line-height: 1.68;
}

.inline-collapse-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed rgba(0, 0, 0, 0.06);
}

.btn-collapse-inline {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent, #0071E3);
  background: rgba(0, 113, 227, 0.08);
  border: 1px solid rgba(0, 113, 227, 0.16);
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-collapse-inline:hover {
  background: rgba(0, 113, 227, 0.15);
}

/* 2.5 Keywords */
.zhihu-keywords-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 11px;
}

.keyword-tag {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary, #7D828D);
  background: var(--glass-surface-subtle, rgba(0, 0, 0, 0.025));
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.05));
  padding: 2px 7px;
  border-radius: 4px;
  transition: all 0.16s ease;
}

.keyword-tag:hover {
  color: var(--accent, #0071E3);
  border-color: rgba(0, 113, 227, 0.2);
}

/* 2.6 Signature Action Bar */
.zhihu-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.04));
  flex-wrap: wrap;
  gap: 8px;
}

.action-buttons-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.btn-zhihu-upvote {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: var(--radius-sm, 6px);
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent, #0071E3);
  border: 1px solid transparent;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-zhihu-upvote:hover {
  background: rgba(0, 113, 227, 0.14);
}

.btn-zhihu-upvote.active {
  background: var(--accent, #0071E3);
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(0, 113, 227, 0.25);
}

.btn-zhihu-upvote.active svg path {
  fill: #ffffff;
}

.btn-zhihu-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 9px;
  border-radius: var(--radius-sm, 6px);
  background: transparent;
  color: var(--text-secondary, #4B4E56);
  border: none;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-zhihu-action:hover {
  color: var(--accent, #0071E3);
  background: var(--glass-surface-subtle, rgba(0, 0, 0, 0.035));
}

.btn-zhihu-action.active {
  color: var(--accent, #0071E3);
  font-weight: 600;
}

.btn-zhihu-deep {
  display: inline-flex;
  align-items: center;
  padding: 5px 8px;
  border-radius: var(--radius-sm, 6px);
  background: transparent;
  color: var(--accent, #0071E3);
  border: none;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-zhihu-deep:hover {
  text-decoration: underline;
}

.action-right-wrap {
  display: flex;
  align-items: center;
}

.discuss-heat-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
}

.btn-collapse-corner {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11.5px;
  color: var(--accent, #0071E3);
  background: transparent;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.btn-collapse-corner:hover {
  text-decoration: underline;
}

/* Dark mode adjustments */
[data-theme="dark"] .zhihu-post-card,
[data-theme="dark"] .compact-post-row {
  background: rgba(26, 29, 36, 0.72);
  border-color: rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .compact-btn-upvote,
[data-theme="dark"] .btn-zhihu-upvote {
  background: rgba(0, 113, 227, 0.15);
}

[data-theme="dark"] .compact-btn-action:hover,
[data-theme="dark"] .compact-btn-icon:hover,
[data-theme="dark"] .btn-zhihu-action:hover {
  background: rgba(255, 255, 255, 0.06);
}

[data-theme="dark"] .expanded-full-body {
  background: rgba(0, 0, 0, 0.25);
  border-color: rgba(255, 255, 255, 0.08);
}

.btn-zhihu-delete:hover,
.compact-btn-delete:hover {
  color: #ff3b30 !important;
  background: rgba(255, 59, 48, 0.1) !important;
}

[data-theme="dark"] .btn-zhihu-delete:hover,
[data-theme="dark"] .compact-btn-delete:hover {
  color: #ff453a !important;
  background: rgba(255, 69, 58, 0.18) !important;
}
</style>
