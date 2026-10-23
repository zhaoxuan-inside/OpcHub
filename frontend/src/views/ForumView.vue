<template>
  <div class="view-panel active forum-view-wrapper">
    <!-- Mode 1: Full-Page Create Storm View (全页面发起新风暴，非弹窗) -->
    <ForumCreateView
      v-if="currentViewMode === 'create'"
      :user-session="currentUserSession"
      @back="currentViewMode = 'list'"
      @success="handleNewPostSuccess"
      @toast="$emit('toast', $event)"
    />

    <!-- Mode 2: Full-Page Article Detail View (全页面居中展示文章详情与见解，非弹窗/非侧栏) -->
    <ForumDetailView
      v-else-if="currentViewMode === 'detail' && activePost"
      :post="activePost"
      :user-session="currentUserSession"
      @back="handleBackToList"
      @upvote="handleDetailUpvote"
      @bookmark="handleDetailBookmark"
      @update-post="handlePostUpdated"
      @delete="handleDeletePost"
      @toast="$emit('toast', $event)"
    />

    <!-- Mode 3: Standard Forum List & Bento Board Mode -->
    <div v-else class="forum-main-content">
      <!-- Zhihu-style Two-Column Article Stream & Hot Sidebar Layout -->
      <div class="zhihu-feed-layout">
        <!-- Main Article Stream (左侧知乎文章流) -->
        <section class="zhihu-feed-stream">
          <!-- Category Filter Bar (风暴分区选项卡 + 排序选择) -->
          <div class="glass-box feed-filter-bar">
            <div class="category-tabs-scroll">
              <button
                v-for="cat in categories"
                :key="cat.code"
                type="button"
                :class="['category-tab-pill', { active: selectedCategoryCode === cat.code }]"
                @click="handleSelectCategory(cat.code)"
              >
                <span>{{ cat.name }}</span>
              </button>
            </div>
            <div class="feed-filter-right">
              <!-- Search Box -->
              <div class="semantic-search-box">
                <div class="search-input-wrap">
                  <input
                    v-model="searchKeyword"
                    type="text"
                    class="semantic-search-input"
                    placeholder="搜索..."
                    @keydown.enter="handleSemanticSearch"
                  />
                  <button v-if="searchKeyword" type="button" class="clear-search-btn" @click="handleClearSearch" title="清空搜索">×</button>
                </div>
                <button
                  type="button"
                  class="btn-liquid semantic-search-btn"
                  :disabled="isSearching"
                  @click="handleSemanticSearch"
                  title="搜索"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                  <span>{{ isSearching ? '搜索中...' : '搜索' }}</span>
                </button>
              </div>

              <div class="sort-segmented">
                <button
                  v-for="opt in sortOptions"
                  :key="opt.key"
                  type="button"
                  :class="['sort-pill', { active: currentSort === opt.key }]"
                  @click="currentSort = opt.key"
                >
                  <OpcIcon :name="opt.icon" :size="13" /> {{ opt.label }}
                </button>
              </div>
            </div>
          </div>

          <!-- Semantic Search Status Banner -->
          <div v-if="isSemanticSearchActive" class="semantic-search-banner glass-box">
            <div class="banner-left">
              <span class="sparkle-badge"><OpcIcon name="search" :size="13" /> 搜索结果</span>
              <span class="banner-text">
                已为您找到与「<strong>{{ activeSearchQuery }}</strong>」相关的 <strong>{{ filteredAndSortedPosts.length }}</strong> 篇讨论
              </span>
            </div>
            <button class="btn-liquid-outline btn-reset-search" @click="handleClearSearch">
              <span>恢复全部讨论</span>
            </button>
          </div>

          <!-- Posts Scroll Container (ONLY this container scrolls with mouse wheel) -->
          <div
            class="zhihu-posts-scroll-container"
            ref="postsScrollContainerRef"
            @scroll.passive="handlePostsScroll"
          >
            <!-- Loading State Indicator (Initial or Category Reset) -->
            <div v-if="isInitialLoading" class="posts-loading-banner glass-box">
              <span class="loading-spinner"></span>
              <span>正在检索「{{ currentCategoryName }}」实战风暴探讨...</span>
            </div>

            <div
              v-if="filteredAndSortedPosts.length > 0"
              class="zhihu-posts-list"
              :class="{ 'density-compact': viewDensity === 'compact' }"
            >
              <ForumCard
                v-for="post in filteredAndSortedPosts"
                :key="post.id"
                :post="post"
                :density="viewDensity"
                :user-session="currentUserSession"
                @select="handleSelectPost"
                @mouseenter="handlePostHover(post)"
                @upvote="handleCardUpvote"
                @bookmark="handleDetailBookmark"
                @interaction="handleCardInteraction"
                @delete="handleDeletePost"
                @require-login="$emit('open-register')"
                @toast="$emit('toast', $event)"
              />
            </div>

            <!-- Infinite Scroll Sentinel Anchor (仅在有帖子且仍有更多时挂载监听) -->
            <div v-if="filteredAndSortedPosts.length > 0 && hasMore" ref="infiniteScrollSentinel" class="feed-sentinel-anchor"></div>

            <!-- Loading Next Batch Spinner -->
            <div v-if="isLoadingMore" class="feed-stream-loading glass-box">
              <span class="loading-spinner"></span>
              <span>正在触底流式预加载后续风暴经验...</span>
            </div>

            <!-- Empty State -->
            <div v-if="!isInitialLoading && filteredAndSortedPosts.length === 0" class="glass-box empty-state-box">
              <div class="empty-icon-wrap">
                <ForumIcon name="empty-galaxy" size="38" />
              </div>
              <h3 class="empty-title">当前筛选下暂无风暴帖</h3>
              <p class="empty-desc">换个关键词试试，或点击下方按钮发起该领域的第一个实战话题！</p>
              <button class="btn-liquid" @click="handleOpenCreatePage">
                <span>发起新风暴</span>
              </button>
            </div>
          </div>
        </section>

        <!-- Right Auxiliary Sidebar (右侧知乎式辅助侧边栏) -->
        <aside class="zhihu-feed-sidebar">
          <!-- 1. Creator Center Card -->
          <div class="glass-box sidebar-card creator-center-card">
            <div class="creator-card-header">
              <div class="creator-icon-orb">
                <ForumIcon name="spark" size="18" />
              </div>
              <div>
                <h4 class="creator-title">创客创作中心</h4>
                <p class="creator-desc">超级个体经验变现实战枢纽</p>
              </div>
            </div>
            <button class="btn-liquid btn-creator-publish" @click="handleOpenCreatePage">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span>发起新风暴话题</span>
            </button>
            <div class="creator-quick-links">
              <span class="quick-pill" @click="handleSelectCategory('TAX')">财税年报</span>
              <span class="quick-pill" @click="handleSelectCategory('BIZ')">独立出海</span>
              <span class="quick-pill" @click="handleSelectCategory('AGENTS')">AI智能体</span>
              <span class="quick-pill" @click="handleSelectCategory('DEV')">技术避坑</span>
            </div>
          </div>

          <!-- 2. Today's Brainstorm Hot Rank (今日风暴热榜) -->
          <div class="glass-box sidebar-card hot-ranking-card">
            <div class="sidebar-card-title-row">
              <div class="title-with-icon">
                <span class="hot-badge-fire"><OpcIcon name="flame" :size="14" /></span>
                <h4 class="sidebar-title">今日风暴热榜</h4>
              </div>
              <span class="hot-subtitle">实时更新</span>
            </div>

            <div class="hot-ranking-list">
              <div
                v-for="(item, idx) in hotRankPosts"
                :key="item.id"
                class="hot-rank-item"
                @click="handleSelectPost(item)"
              >
                <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                <div class="hot-item-content">
                  <h5 class="hot-item-title">{{ item.title }}</h5>
                  <div class="hot-item-meta">
                    <span><OpcIcon name="flame" :size="12" /> {{ (item.upvotes || 0) * 3 + (item.replies || 0) * 5 + 42 }} 热度</span>
                    <span class="dot-sep">·</span>
                    <span>{{ item.upvotes || 0 }} 点赞</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. Maker Knowledge & Community Guidelines -->
          <div class="glass-box sidebar-card guidelines-card">
            <h4 class="sidebar-title-sm">超级个体实战指南</h4>
            <p class="guidelines-desc">
              头脑风暴社区倡导<strong>「真实代码落盘、真实财务申报、真实踩坑复盘」</strong>。所有涉及税收减免与出海合规方案均支持一键归档至个人知识库。
            </p>
            <div class="guidelines-footer">
              <span>OpcHub 创客治理协议 v1.0</span>
              <span class="dot-sep">·</span>
              <span class="link-span" @click="handleOpenCreatePage">提出探讨</span>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- VisionOS Secondary Confirmation Dialog for Deleting Posts -->
    <Teleport to="body">
      <div
        v-if="isDeleteModalVisible"
        class="sheet-modal forum-delete-modal-backdrop"
        @click.self="cancelDeletePost"
        @keydown.esc="cancelDeletePost"
      >
        <div class="sheet-body forum-delete-modal-card" role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title">
          <!-- Header -->
          <div class="delete-modal-header">
            <div class="delete-modal-header-left">
              <div class="delete-modal-icon-badge">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </div>
              <div>
                <h3 id="delete-dialog-title" class="delete-modal-title">删除风暴帖确认</h3>
                <div class="delete-modal-sub">IRREVERSIBLE ACTION // CONFIRM DELETION</div>
              </div>
            </div>
            <button class="btn-liquid-outline modal-close-btn" @click="cancelDeletePost" aria-label="关闭">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          <!-- Post Preview Box in Liquid Glass -->
          <div v-if="postToDelete" class="delete-modal-preview">
            <div class="preview-meta-row">
              <span class="preview-category-badge">{{ postToDelete.category || '风暴区' }}</span>
              <span class="preview-author-tag">作者: {{ postToDelete.author || '匿名创客' }}</span>
              <span v-if="postToDelete.created_at" class="preview-date-tag">{{ postToDelete.created_at.slice(0, 10) }}</span>
            </div>
            <div class="preview-title">{{ postToDelete.title }}</div>
            <div v-if="postToDelete.snippet" class="preview-snippet">{{ postToDelete.snippet }}</div>
          </div>

          <!-- Warning Notice -->
          <div class="delete-warning-banner">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; margin-top: 1px;">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div class="delete-warning-text">
              该操作将彻底从 OpcHub 知识库与网关节点中注销此帖，相关的点赞与创客回复将同步归档或清理，<strong>此操作不可逆</strong>。
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="delete-modal-actions">
            <button
              type="button"
              class="btn-liquid-outline btn-cancel"
              :disabled="isDeleting"
              @click="cancelDeletePost"
            >
              取消保留
            </button>
            <button
              type="button"
              class="btn-liquid btn-confirm-delete"
              :disabled="isDeleting"
              @click="confirmExecuteDelete"
            >
              <svg v-if="!isDeleting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                <line x1="10" y1="11" x2="10" y2="17"/>
                <line x1="14" y1="11" x2="14" y2="17"/>
              </svg>
              <span v-else class="delete-spinner"></span>
              {{ isDeleting ? '正在执行删除...' : '确定彻底删除' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import ForumIcon from '@/components/ForumIcon.vue';
import ForumCard from '@/components/ForumCard.vue';
import ForumDetailView from '@/components/ForumDetailView.vue';
import ForumCreateView from '@/components/ForumCreateView.vue';
import { dispatchGateway } from '@/api/gateway';
import { enrichForumInteractions } from '@/utils/contentInteractions';

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['open-register', 'toast']);

// User Session Resolution
const currentUserSession = computed(() => {
  if (props.userSession) return props.userSession;
  try {
    const raw = localStorage.getItem('opchub_user_session');
    if (raw) return JSON.parse(raw);
  } catch (e) {
    // ignore
  }
  return null;
});

// Categories
const categories = [
  { code: 'ALL', name: '全部风暴区' },
  { code: 'TAX', name: '工商财税' },
  { code: 'BIZ', name: '独立出海' },
  { code: 'AGENTS', name: 'AI智能体' },
  { code: 'POLICY', name: '政策申报' },
  { code: 'DEV', name: '技术踩坑' },
];

const selectedCategoryCode = ref('ALL');

// Sort Options
const sortOptions = [
  { key: 'hot', label: '最热讨论', icon: 'flame' },
  { key: 'new', label: '最新发表', icon: 'bolt' },
  { key: 'featured', label: '官方精选', icon: 'trophy' },
];
const currentSort = ref('hot');

// Search
const searchKeyword = ref('');
const isSearching = ref(false);
const isSemanticSearchActive = ref(false);
const activeSearchQuery = ref('');

// Drawer & Full-Page View States
const isDrawerVisible = ref(false);
const activePost = ref(null);
const currentViewMode = ref('list'); // 'list' | 'create'


// Density Mode Switch
const viewDensity = ref(localStorage.getItem('opchub_forum_density') || 'comfortable');
function setDensity(mode) {
  viewDensity.value = mode;
  try {
    localStorage.setItem('opchub_forum_density', mode);
  } catch (e) {}
}

// Relative time formatting helper
function formatTimeAgo(isoStr) {
  if (!isoStr) return '刚刚';
  try {
    const diff = Date.now() - new Date(isoStr).getTime();
    if (isNaN(diff)) return '刚刚';
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return `${mins} 分钟前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} 小时前`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} 天前`;
    return new Date(isoStr).toLocaleDateString('zh-CN');
  } catch (e) {
    return '刚刚';
  }
}

// Active Posts dataset (infinite scroll stream)
const postsList = ref([]);
const currentCursor = ref(0);
const feedLimit = ref(10);
const totalCount = ref(0);
const hasMore = ref(true);
const isInitialLoading = ref(false);
const isLoadingMore = ref(false);
const isPrefetching = ref(false);
const lastScrollY = ref(0);
const infiniteScrollSentinel = ref(null);
let scrollObserver = null;
let hoverTimer = null;

// L1 Client Feed Cache: Key: `${cat}:${sort}` -> { items: [], cursor, hasMore, total, timestamp }
const clientFeedCache = new Map();
// L1 Speculative Detail Cache: thread_id -> detailData
const detailCache = new Map();
// Prefetch Buffer: Key: `${cat}:${sort}:${cursor}` -> { items: [], next_cursor, has_more }
const prefetchBuffer = new Map();

const currentCategoryName = computed(() => {
  return categories.find((c) => c.code === selectedCategoryCode.value)?.name || '全部';
});

function transformThread(t) {
  let snippet = '';
  if (t.content) {
    snippet = t.content
      .replace(/^#+\s+/gm, '')
      .replace(/[*_`>]/g, '')
      .replace(/\[!.*?\]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    if (snippet.length > 150) {
      snippet = snippet.slice(0, 150) + '...';
    }
  }

  const catObj = categories.find((c) => c.code === (t.category_code || '').toUpperCase());
  const categoryName = catObj?.name || '实战探讨';

  return {
    id: t.id,
    pinned: t.is_pinned ? '置顶' : null,
    category_code: t.category_code || 'DEV',
    category: categoryName,
    title: t.title || '',
    snippet: snippet,
    content: t.content || '',
    metrics: Array.isArray(t.metrics) ? t.metrics : [],
    author: t.author_name || (t.author_id ? `创客_${t.author_id.slice(0, 6)}` : '实战创客'),
    author_id: t.author_id || '',
    ip_location: t.ip_location || '来自 浙江',
    replies: t.comment_count ?? 0,
    comment_count: t.comment_count ?? 0,
    upvotes: t.upvote_count ?? 0,
    upvote_count: t.upvote_count ?? 0,
    like_count: t.upvote_count ?? 0,
    bookmark_count: t.bookmark_count ?? 0,
    favorite_count: t.bookmark_count ?? 0,
    love_count: t.love_count ?? 0,
    is_loved: Boolean(t.is_loved),
    view_count: t.view_count ?? 0,
    is_upvoted: Boolean(t.is_upvoted),
    created_at: t.created_at || new Date().toISOString(),
    updated_at: formatTimeAgo(t.updated_at || t.created_at),
    tags: Array.isArray(t.tags) && t.tags.length ? t.tags : [categoryName],
  };
}

async function fetchFeedStream(reset = false, silent = false) {
  const cat = selectedCategoryCode.value || 'ALL';
  const sort = currentSort.value;
  const cacheKey = `${cat}:${sort}`;

  if (reset) {
    currentCursor.value = 0;
    hasMore.value = true;

    // SWR Cache Check: if cached, render immediately without layout shift
    const cached = clientFeedCache.get(cacheKey);
    if (cached) {
      postsList.value = [...cached.items];
      currentCursor.value = cached.cursor;
      hasMore.value = cached.hasMore;
      totalCount.value = cached.total;
      enrichForumInteractions(postsList.value);

      // Fresh cache (< 15s): complete fast return
      if (Date.now() - cached.timestamp < 15000) {
        speculativePrefetchNext();
        return;
      }
      silent = true; // Background revalidate
    } else {
      if (!silent) isInitialLoading.value = true;
    }
  } else {
    if (isLoadingMore.value || !hasMore.value) return;

    // Check prefetch buffer for instantaneous zero-latency append
    const bufferKey = `${cat}:${sort}:${currentCursor.value}`;
    if (prefetchBuffer.has(bufferKey)) {
      const prefetched = prefetchBuffer.get(bufferKey);
      prefetchBuffer.delete(bufferKey);
      const newItems = prefetched.items.filter((p) => !postsList.value.some((ex) => String(ex.id) === String(p.id)));
      postsList.value.push(...newItems);
      currentCursor.value = prefetched.next_cursor !== null && prefetched.next_cursor !== undefined
        ? prefetched.next_cursor
        : (currentCursor.value + newItems.length);
      hasMore.value = prefetched.has_more;
      await enrichForumInteractions(newItems);

      clientFeedCache.set(cacheKey, {
        items: [...postsList.value],
        cursor: currentCursor.value,
        hasMore: hasMore.value,
        total: totalCount.value,
        timestamp: Date.now(),
      });

      speculativePrefetchNext();
      return;
    }

    isLoadingMore.value = true;
  }

  try {
    const res = await dispatchGateway('forum.feed.stream', {
      category_code: cat,
      cursor: currentCursor.value,
      limit: feedLimit.value,
      sort_by: sort,
    }, { silent: true });

    if (res.ok && res.data) {
      const data = res.data;
      const rawItems = Array.isArray(data.items) ? data.items : [];
      totalCount.value = typeof data.total === 'number' ? data.total : rawItems.length;
      hasMore.value = Boolean(data.has_more);
      currentCursor.value = data.next_cursor !== null && data.next_cursor !== undefined
        ? data.next_cursor
        : (currentCursor.value + rawItems.length);

      const transformed = rawItems.map(transformThread);

      if (reset) {
        postsList.value = transformed;
      } else {
        const newItems = transformed.filter((p) => !postsList.value.some((ex) => String(ex.id) === String(p.id)));
        postsList.value.push(...newItems);
      }

      await enrichForumInteractions(postsList.value);

      clientFeedCache.set(cacheKey, {
        items: [...postsList.value],
        cursor: currentCursor.value,
        hasMore: hasMore.value,
        total: totalCount.value,
        timestamp: Date.now(),
      });

      speculativePrefetchNext();
    } else {
      if (reset && !clientFeedCache.has(cacheKey)) {
        postsList.value = [];
      }
    }
  } catch (e) {
    if (reset && !clientFeedCache.has(cacheKey)) {
      postsList.value = [];
    }
  } finally {
    isInitialLoading.value = false;
    isLoadingMore.value = false;
  }
}

async function speculativePrefetchNext() {
  if (!hasMore.value || isPrefetching.value) return;
  const cat = selectedCategoryCode.value || 'ALL';
  const sort = currentSort.value;
  const cur = currentCursor.value;
  const bufferKey = `${cat}:${sort}:${cur}`;
  if (prefetchBuffer.has(bufferKey)) return;

  isPrefetching.value = true;
  try {
    const res = await dispatchGateway('forum.feed.stream', {
      category_code: cat,
      cursor: cur,
      limit: feedLimit.value,
      sort_by: sort,
    }, { silent: true });
    if (res.ok && res.data) {
      const rawItems = Array.isArray(res.data.items) ? res.data.items : [];
      const transformed = rawItems.map(transformThread);
      prefetchBuffer.set(bufferKey, {
        items: transformed,
        next_cursor: res.data.next_cursor,
        has_more: Boolean(res.data.has_more),
      });
    }
  } catch (_) {} finally {
    isPrefetching.value = false;
  }
}

function handlePostHover(post) {
  if (!post || !post.id) return;
  const tid = String(post.id);
  if (detailCache.has(tid)) return;
  clearTimeout(hoverTimer);
  hoverTimer = setTimeout(async () => {
    try {
      const res = await dispatchGateway('forum.threads.get', { thread_id: tid }, { silent: true });
      if (res.ok && res.data) {
        detailCache.set(tid, res.data);
      }
    } catch (_) {}
  }, 120);
}

function computeTextSemanticScore(query, text) {
  if (!query || !text) return 0;
  const q = query.toLowerCase().trim();
  const t = text.toLowerCase().trim();
  let score = 0;
  if (t.includes(q)) score += 0.45;
  const tokens = q.split(/[\s,，.。!！?？、/\\;；]+/).filter((w) => w.length >= 2);
  let hits = 0;
  tokens.forEach((tok) => {
    if (t.includes(tok)) hits++;
  });
  if (tokens.length > 0) {
    score += (hits / tokens.length) * 0.45;
  }
  const getBigrams = (str) => {
    const s = new Set();
    for (let i = 0; i < str.length - 1; i++) s.add(str.slice(i, i + 2));
    return s;
  };
  const bq = getBigrams(q);
  const bt = getBigrams(t);
  let inter = 0;
  bq.forEach((bg) => { if (bt.has(bg)) inter++; });
  if (bq.size > 0) {
    score += (inter / (bq.size + bt.size - inter || 1)) * 0.25;
  }
  return Math.min(0.999, Math.max(0.15, score));
}

async function handleSemanticSearch() {
  const query = searchKeyword.value.trim();
  if (!query) {
    handleClearSearch();
    return;
  }

  isSearching.value = true;
  try {
    const res = await dispatchGateway('forum.search.semantic', {
      query: query,
      category_code: selectedCategoryCode.value,
      top_k: 25,
    });

    if (res.ok && res.data && Array.isArray(res.data.items) && res.data.items.length > 0) {
      const transformed = res.data.items.map(transformThread);
      await enrichForumInteractions(transformed);
      postsList.value = transformed;
      totalCount.value = transformed.length;
      isSemanticSearchActive.value = true;
      activeSearchQuery.value = query;
      hasMore.value = false;
      emit('toast', {
        title: '搜索完成',
        message: `已为您找到 ${transformed.length} 篇相关讨论。`,
        type: 'SUCCESS',
      });
    } else {
      // In-browser fallback scoring over current posts
      const scored = postsList.value.map((p) => {
        const fullText = `${p.title || ''} ${p.snippet || ''} ${p.content || ''} ${(p.tags || []).join(' ')}`;
        const sim = computeTextSemanticScore(query, fullText);
        return {
          ...p,
          similarity: Math.round(sim * 10000) / 10000,
          similarity_score: Math.round(sim * 10000) / 10000,
          semantic_score: Math.round(sim * 1000) / 10,
        };
      });
      scored.sort((a, b) => (b.semantic_score || 0) - (a.semantic_score || 0));
      postsList.value = scored;
      isSemanticSearchActive.value = true;
      activeSearchQuery.value = query;
      hasMore.value = false;
      emit('toast', {
        title: '搜索完成',
        message: `已为您匹配相关讨论内容。`,
        type: 'SUCCESS',
      });
    }
  } catch (e) {
    const scored = postsList.value.map((p) => {
      const fullText = `${p.title || ''} ${p.snippet || ''} ${p.content || ''}`;
      const sim = computeTextSemanticScore(query, fullText);
      return {
        ...p,
        similarity: Math.round(sim * 10000) / 10000,
        similarity_score: Math.round(sim * 10000) / 10000,
        semantic_score: Math.round(sim * 1000) / 10,
      };
    });
    scored.sort((a, b) => (b.semantic_score || 0) - (a.semantic_score || 0));
    postsList.value = scored;
    isSemanticSearchActive.value = true;
    activeSearchQuery.value = query;
    hasMore.value = false;
  } finally {
    isSearching.value = false;
  }
}

function handleClearSearch() {
  searchKeyword.value = '';
  activeSearchQuery.value = '';
  isSemanticSearchActive.value = false;
  clientFeedCache.clear();
  fetchFeedStream(true);
}

const postsScrollContainerRef = ref(null);

function handlePostsScroll(e) {
  const el = e.target;
  if (!el || !hasMore.value || isLoadingMore.value || isInitialLoading.value) return;
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 250) {
    fetchFeedStream(false);
  }
}

function handleSelectCategory(catCode) {
  if (selectedCategoryCode.value === catCode) return;
  selectedCategoryCode.value = catCode;
  if (postsScrollContainerRef.value) {
    postsScrollContainerRef.value.scrollTop = 0;
  }
  if (isSemanticSearchActive.value && searchKeyword.value.trim()) {
    handleSemanticSearch();
  } else {
    fetchFeedStream(true);
  }
}

function initScrollObserver() {
  if (scrollObserver) {
    scrollObserver.disconnect();
    scrollObserver = null;
  }
  if (!infiniteScrollSentinel.value) return;

  scrollObserver = new IntersectionObserver((entries) => {
    const [entry] = entries;
    if (
      entry &&
      entry.isIntersecting &&
      hasMore.value &&
      !isLoadingMore.value &&
      !isInitialLoading.value &&
      postsList.value.length > 0
    ) {
      fetchFeedStream(false);
    }
  }, {
    root: postsScrollContainerRef.value || null,
    rootMargin: '200px',
    threshold: 0.01,
  });

  scrollObserver.observe(infiniteScrollSentinel.value);
}

// Category counts
function getCategoryCount(code) {
  if (code === 'ALL') return totalCount.value || postsList.value.length;
  return postsList.value.filter((p) => (p.category_code || '').toUpperCase() === code).length;
}

// Filtered and Sorted list
const filteredAndSortedPosts = computed(() => {
  let list = [...postsList.value];

  // 1. Category Filter
  if (selectedCategoryCode.value !== 'ALL') {
    list = list.filter((p) => (p.category_code || '').toUpperCase() === selectedCategoryCode.value);
  }

  // 2. Keyword Filter (only when not in semantic search mode)
  if (!isSemanticSearchActive.value && searchKeyword.value.trim()) {
    const q = searchKeyword.value.trim().toLowerCase();
    list = list.filter((p) => {
      const matchTitle = (p.title || '').toLowerCase().includes(q);
      const matchSnippet = (p.snippet || '').toLowerCase().includes(q);
      const matchAuthor = (p.author || '').toLowerCase().includes(q);
      const matchTags = (p.tags || []).some((t) => t.toLowerCase().includes(q));
      return matchTitle || matchSnippet || matchAuthor || matchTags;
    });
  }

  // 3. Sorting
  if (isSemanticSearchActive.value && currentSort.value !== 'new' && currentSort.value !== 'featured') {
    list.sort((a, b) => (b.semantic_score || 0) - (a.semantic_score || 0));
  } else if (currentSort.value === 'hot') {
    list.sort((a, b) => {
      // Newly created posts in current session stay at the very top
      if (a.is_new && !b.is_new) return -1;
      if (!a.is_new && b.is_new) return 1;

      // Pinned always on top
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      const scoreA = (a.upvotes || 0) * 2 + (a.replies || 0) * 3;
      const scoreB = (b.upvotes || 0) * 2 + (b.replies || 0) * 3;
      return scoreB - scoreA;
    });
  } else if (currentSort.value === 'new') {
    list.sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      const timeA = new Date(a.created_at || a.updated_at || 0).getTime() || 0;
      const timeB = new Date(b.created_at || b.updated_at || 0).getTime() || 0;
      if (timeA !== timeB) return timeB - timeA;
      return String(b.id).localeCompare(String(a.id));
    });
  } else if (currentSort.value === 'featured') {
    list = list.filter((p) => p.pinned);
  }

  return list;
});

// Top 5 Hot Brainstorm Posts for Zhihu-style Sidebar
const hotRankPosts = computed(() => {
  return [...postsList.value]
    .sort((a, b) => {
      const scoreA = (a.upvotes || 0) * 2 + (a.replies || 0) * 3;
      const scoreB = (b.upvotes || 0) * 2 + (b.replies || 0) * 3;
      return scoreB - scoreA;
    })
    .slice(0, 5);
});

// Card Select Action (全页面打开文章详情与交流)
function handleSelectPost(post) {
  lastScrollY.value = window.scrollY;
  activePost.value = post;
  currentViewMode.value = 'detail';
  if (!window.location.hash.includes(`post_id=${post.id}`)) {
    try {
      window.history.replaceState(null, '', `${window.location.pathname}#forum?post_id=${encodeURIComponent(post.id)}`);
    } catch (e) {}
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleBackToList() {
  currentViewMode.value = 'list';
  if (window.location.hash.includes('post_id=')) {
    try {
      window.history.replaceState(null, '', `${window.location.pathname}#forum`);
    } catch (e) {}
  }
  nextTick(() => {
    window.scrollTo({ top: lastScrollY.value, behavior: 'auto' });
    initScrollObserver();
  });
}

function handleDetailUpvote({ post, isUpvoted, count }) {
  if (post) {
    post.is_upvoted = isUpvoted;
    post.upvotes = count;
    post.upvote_count = count;
  }
  const found = postsList.value.find((p) => String(p.id) === String(post?.id));
  if (found) {
    found.is_upvoted = isUpvoted;
    found.upvotes = count;
    found.upvote_count = count;
  }
}

function handleDetailBookmark({ post, isBookmarked }) {
  if (post) {
    post.is_bookmarked = isBookmarked;
  }
  const found = postsList.value.find((p) => String(p.id) === String(post?.id));
  if (found) {
    found.is_bookmarked = isBookmarked;
  }
}

function handlePostUpdated(updatedPost) {
  const idx = postsList.value.findIndex((p) => String(p.id) === String(updatedPost?.id));
  if (idx !== -1) {
    postsList.value[idx] = { ...postsList.value[idx], ...updatedPost };
  }
}

function handleCardInteraction(payload) {
  if (!payload?.post) return;
  const post = payload.post;
  const found = postsList.value.find((p) => String(p.id) === String(post.id));
  if (found) {
    Object.assign(found, {
      like_count: post.like_count,
      favorite_count: post.favorite_count,
      love_count: post.love_count,
      comment_count: post.comment_count,
      viewer: post.viewer,
      upvotes: post.upvotes,
      upvote_count: post.upvote_count,
      replies: post.replies,
      bookmark_count: post.bookmark_count,
      is_upvoted: post.is_upvoted,
      is_bookmarked: post.is_bookmarked,
      is_loved: post.is_loved,
      is_commented: post.is_commented,
    });
  }
  if (activePost.value && String(activePost.value.id) === String(post.id)) {
    Object.assign(activePost.value, post);
  }
  try {
    clientFeedCache.clear();
  } catch (e) {}
}

// Post Deletion Modal & Execution (Super Admin or Author)
const isDeleteModalVisible = ref(false);
const postToDelete = ref(null);
const isDeleting = ref(false);

function handleDeletePost(post) {
  if (!post || !post.id) return;
  postToDelete.value = post;
  isDeleteModalVisible.value = true;
}

function cancelDeletePost() {
  if (isDeleting.value) return;
  isDeleteModalVisible.value = false;
  postToDelete.value = null;
}

async function confirmExecuteDelete() {
  const post = postToDelete.value;
  if (!post || !post.id || isDeleting.value) return;

  isDeleting.value = true;
  try {
    const res = await dispatchGateway('forum.threads.delete', {
      thread_id: String(post.id),
    });
    if (res.ok) {
      clientFeedCache.clear();
      prefetchBuffer.clear();
      detailCache.delete(String(post.id));
      emit('toast', {
        title: '帖子已删除',
        message: `实战帖《${post.title}》已成功移除。`,
        type: 'SUCCESS',
      });
      postsList.value = postsList.value.filter((p) => String(p.id) !== String(post.id));
      if (activePost.value && String(activePost.value.id) === String(post.id)) {
        handleBackToList();
      }
      isDeleteModalVisible.value = false;
      postToDelete.value = null;
    } else {
      emit('toast', {
        title: '删除失败',
        message: res.error || '您无权删除此帖子或服务器异常',
        type: 'ERROR',
      });
    }
  } catch (err) {
    emit('toast', {
      title: '删除失败',
      message: err.message || '网络或网关响应异常',
      type: 'ERROR',
    });
  } finally {
    isDeleting.value = false;
  }
}

// Card Upvote Toggle
function handleCardUpvote({ post, isUpvoted, count }) {
  post.is_upvoted = isUpvoted;
  post.upvotes = count;
  post.upvote_count = count;

  try {
    const raw = localStorage.getItem('opchub_forum_upvotes');
    let upvotes = raw ? JSON.parse(raw) : [];
    const sid = String(post.id);
    if (isUpvoted) {
      if (!upvotes.includes(sid)) upvotes.push(sid);
    } else {
      upvotes = upvotes.filter((id) => id !== sid);
    }
    localStorage.setItem('opchub_forum_upvotes', JSON.stringify(upvotes));
  } catch (e) {}

  emit('toast', {
    title: isUpvoted ? '已点赞灵感' : '已取消点赞',
    message: isUpvoted ? `您为《${post.title}》投出了一票！` : '已更新您的投票状态',
    type: 'SUCCESS',
  });

  if (post.id) {
    dispatchGateway('forum.upvote', {
      target_type: 'THREAD',
      target_id: String(post.id),
    }, { silent: true });
  }
}

// Open Full-Page Create View (非弹窗全页面)
function handleOpenCreatePage() {
  const token = localStorage.getItem('opchub_session_token');
  if (!token) {
    emit('toast', {
      title: '需要登录',
      message: '请先登录创客账号后再在风暴区发帖交流！',
      type: 'INFO',
    });
    emit('open-register');
    return;
  }
  currentViewMode.value = 'create';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// New Post Created Callback (发布成功后，全页面居中展示该文章)
function handleNewPostSuccess(newThread) {
  clientFeedCache.clear();
  prefetchBuffer.clear();
  postsList.value.unshift(newThread);
  activePost.value = newThread;
  currentViewMode.value = 'detail';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function syncStoredInteractions(list) {
  try {
    const rawUpvotes = localStorage.getItem('opchub_forum_upvotes');
    const upvotedIds = rawUpvotes ? JSON.parse(rawUpvotes) : [];
    const rawBookmarks = localStorage.getItem('opchub_forum_bookmarks');
    const bookmarks = rawBookmarks ? JSON.parse(rawBookmarks) : [];
    const bookmarkedIds = bookmarks.map((b) => (typeof b === 'object' ? String(b.id) : String(b)));

    list.forEach((p) => {
      const sid = String(p.id);
      if (upvotedIds.includes(sid)) {
        p.is_upvoted = true;
      }
      if (bookmarkedIds.includes(sid)) {
        p.is_bookmarked = true;
      }
    });
  } catch (e) {}
}

function checkUrlForPost() {
  const hash = window.location.hash || '';
  const match = hash.match(/post_id=([^&]+)/);
  if (match && match[1]) {
    const postId = decodeURIComponent(match[1]);
    const found = postsList.value.find((p) => String(p.id) === String(postId));
    if (found) {
      activePost.value = found;
      currentViewMode.value = 'detail';
    }
  }
}

function onWindowHashChange() {
  checkUrlForPost();
}

watch(currentSort, () => {
  fetchFeedStream(true);
});

watch(currentViewMode, (mode) => {
  if (mode === 'list') {
    document.body.classList.add('fixed-screen-feed');
  } else {
    document.body.classList.remove('fixed-screen-feed');
  }
}, { immediate: true });

// Lifecycle: Infinite Scroll Feed stream initialization & intersection observer mounting
onMounted(async () => {
  if (currentViewMode.value === 'list') {
    document.body.classList.add('fixed-screen-feed');
  }
  try {
    localStorage.removeItem('opchub_forum_deleted_threads');
  } catch (e) {}
  window.addEventListener('hashchange', onWindowHashChange);
  await fetchFeedStream(true);
  nextTick(() => {
    initScrollObserver();
  });
  checkUrlForPost();
});

onUnmounted(() => {
  document.body.classList.remove('fixed-screen-feed');
  window.removeEventListener('hashchange', onWindowHashChange);
  if (scrollObserver) {
    scrollObserver.disconnect();
    scrollObserver = null;
  }
  if (hoverTimer) {
    clearTimeout(hoverTimer);
  }
});
</script>

<style scoped>
.forum-view-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.forum-main-content {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

/* Zhihu-style Feed Two-Column Layout */
.zhihu-feed-layout {
  display: flex;
  gap: 20px;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  align-items: stretch;
  overflow: hidden;
  box-sizing: border-box;
}

.zhihu-feed-stream {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}

.feed-filter-bar {
  flex-shrink: 0;
  margin-bottom: 12px;
}

.semantic-search-banner {
  flex-shrink: 0;
  margin-bottom: 12px;
}

/* Scrollable Container: ONLY posts list scrolls with mouse wheel, NO scrollbar displayed */
.zhihu-posts-scroll-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-right: 0;
  padding-bottom: 24px;
  box-sizing: border-box;
  overscroll-behavior: contain;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.zhihu-posts-scroll-container::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

.zhihu-posts-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  box-sizing: border-box;
}

.zhihu-posts-list.density-compact {
  gap: 8px;
}

/* Zhihu Feed Sidebar */
.zhihu-feed-sidebar {
  width: 320px;
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  scrollbar-width: none;
  box-sizing: border-box;
}

.zhihu-feed-sidebar::-webkit-scrollbar {
  display: none;
}

.sidebar-card {
  flex-shrink: 0;
  margin: 0;
  padding: 18px 20px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface, rgba(255, 255, 255, 0.7));
  backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.85));
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  box-sizing: border-box;
  width: 100%;
}

/* 1. Creator Card */
.creator-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.creator-icon-orb {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--accent-glass, rgba(0, 113, 227, 0.1));
  color: var(--accent, #0071E3);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.creator-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #121316);
  margin: 0;
}

.creator-desc {
  font-size: 11.5px;
  color: var(--text-secondary, #4B4E56);
  margin: 2px 0 0 0;
}

.btn-creator-publish {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13.5px;
  font-weight: 600;
  margin-bottom: 14px;
}

.creator-quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-pill {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary, #4B4E56);
  background: var(--glass-surface-subtle, rgba(0, 0, 0, 0.03));
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
  padding: 3px 9px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.quick-pill:hover {
  color: var(--accent, #0071E3);
  border-color: rgba(0, 113, 227, 0.25);
  background: rgba(0, 113, 227, 0.05);
}

/* 2. Hot Ranking Card */
.sidebar-card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 6px;
}

.hot-badge-fire {
  font-size: 15px;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #121316);
  margin: 0;
}

.hot-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary, #7D828D);
}

.hot-ranking-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hot-rank-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.18s ease;
}

.hot-rank-item:hover {
  background: var(--glass-surface-subtle, rgba(0, 113, 227, 0.05));
}

.rank-num {
  font-size: 14px;
  font-weight: 800;
  font-style: italic;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  color: var(--text-tertiary);
}

.rank-1 {
  color: var(--text-primary);
  font-weight: 700;
}

.rank-2 {
  color: var(--text-secondary);
}

.rank-3 {
  color: var(--text-tertiary);
}

.hot-item-content {
  flex: 1;
  min-width: 0;
}

.hot-item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #121316);
  line-height: 1.45;
  margin: 0 0 3px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.18s ease;
}

.hot-rank-item:hover .hot-item-title {
  color: var(--accent, #0071E3);
}

.hot-item-meta {
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 3. Guidelines Card */
.sidebar-title-sm {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary, #121316);
  margin: 0 0 8px 0;
}

.guidelines-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary, #4B4E56);
  margin: 0 0 12px 0;
}

.guidelines-footer {
  display: flex;
  align-items: center;
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
  gap: 5px;
}

.link-span {
  color: var(--accent, #0071E3);
  cursor: pointer;
}

.link-span:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 960px) {
  .zhihu-feed-layout {
    flex-direction: column;
  }
  .zhihu-feed-sidebar {
    width: 100%;
  }
}

/* Empty State */
.empty-state-box {
  padding: 56px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.empty-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--glass-surface-subtle, rgba(245, 247, 252, 0.5));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary, #7D828D);
  margin-bottom: 6px;
}

.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #121316);
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-secondary, #4B4E56);
  max-width: 400px;
  margin: 0 0 10px 0;
}

/* Dark mode sidebar adjustments */
[data-theme="dark"] .sidebar-card {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .quick-pill {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
}

[data-theme="dark"] .hot-rank-item:hover {
  background: rgba(0, 113, 227, 0.12);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ---------------- VisionOS Delete Confirmation Modal ---------------- */
.forum-delete-modal-backdrop {
  z-index: 9999;
  animation: modalBackdropFadeIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.forum-delete-modal-card {
  max-width: 480px;
  width: 100%;
  border-radius: var(--radius-lg, 24px);
  border: 1px solid var(--glass-border);
  background: var(--glass-surface-solid);
  box-shadow: 0 32px 72px rgba(0, 0, 0, 0.36), var(--glass-specular);
  animation: modalScaleIn 0.26s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 24px;
}

.delete-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.delete-modal-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.delete-modal-icon-badge {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--status-danger-soft);
  color: var(--status-danger);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--status-danger);
}

.delete-modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}

.delete-modal-sub {
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  margin-top: 2px;
  letter-spacing: 0.05em;
}

.modal-close-btn {
  padding: 6px 10px;
  border-radius: var(--radius-full);
}

.delete-modal-preview {
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-md, 16px);
  padding: 14px 16px;
  margin-bottom: 16px;
}

.preview-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.preview-category-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: rgba(0, 113, 227, 0.12);
  color: var(--theme-accent, #0071e3);
  border: 1px solid rgba(0, 113, 227, 0.2);
}

.preview-author-tag,
.preview-date-tag {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.preview-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.preview-snippet {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.delete-warning-banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: var(--status-danger-soft);
  border: 1px solid var(--status-danger);
  border-radius: var(--radius-sm, 10px);
  padding: 10px 14px;
  margin-bottom: 22px;
  color: var(--status-danger);
  font-size: 12.5px;
  line-height: 1.5;
}

.delete-warning-text strong {
  font-weight: 700;
  color: var(--status-danger);
}

.delete-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: center;
}

.btn-confirm-delete {
  background: var(--status-danger) !important;
  color: #ffffff !important;
  border: none !important;
  font-weight: 600;
  padding: 8px 18px;
}

.btn-confirm-delete:hover:not(:disabled) {
  background: var(--status-danger) !important;
  filter: brightness(0.92);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px var(--status-danger-soft);
}

.btn-confirm-delete:disabled {
  opacity: 0.55 !important;
  cursor: not-allowed;
}

.delete-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes modalBackdropFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes modalScaleIn {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Dark mode adjustments for delete dialog */
[data-theme="dark"] .forum-delete-modal-card {
  background: rgba(24, 27, 34, 0.88);
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .delete-modal-preview {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .delete-warning-banner {
  background: var(--status-danger-soft);
  border-color: var(--status-danger);
  color: var(--status-danger);
}

[data-theme="dark"] .delete-warning-text strong {
  color: var(--status-danger);
}

/* ---------------- Category Filter Bar ---------------- */
.feed-filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  border-radius: var(--radius-md, 14px);
  margin-bottom: 14px;
  gap: 12px;
  flex-wrap: wrap;
}

.category-tabs-scroll {
  display: flex;
  gap: 6px;
  align-items: center;
  overflow-x: auto;
  scrollbar-width: none;
}

.category-tabs-scroll::-webkit-scrollbar {
  display: none;
}

.category-tab-pill {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-full, 9999px);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  white-space: nowrap;
}

.category-tab-pill:hover {
  color: var(--text-primary);
  background: var(--glass-surface-subtle);
}

.category-tab-pill.active {
  color: var(--accent, #0071e3);
  background: rgba(0, 113, 227, 0.1);
  border-color: rgba(0, 113, 227, 0.25);
  font-weight: 600;
}

.feed-filter-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* NLP Semantic Search in Feed Filter Bar */
.semantic-search-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.search-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.semantic-search-input {
  width: 200px;
  padding: 6px 26px 6px 12px;
  font-size: 12.5px;
  border-radius: var(--radius-full, 9999px);
  background: var(--glass-surface-subtle, rgba(0, 0, 0, 0.04));
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.08));
  color: var(--text-primary);
  outline: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.semantic-search-input:focus {
  width: 250px;
  background: var(--glass-surface);
  border-color: var(--accent, #0071E3);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.15);
}

.clear-search-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: 14px;
  cursor: pointer;
  line-height: 1;
  padding: 2px 4px;
  border-radius: 50%;
}

.clear-search-btn:hover {
  color: var(--text-primary);
}

.semantic-search-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-full, 9999px);
  background: var(--accent, #0071E3);
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.semantic-search-btn:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--accent-glow);
}

.semantic-search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Semantic Search Status Banner */
.semantic-search-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: var(--radius-md, 12px);
  background: var(--accent-glass);
  border: 1px solid rgba(0, 113, 227, 0.25);
  font-size: 12.5px;
  color: var(--text-primary);
  gap: 12px;
  margin-bottom: 12px;
}

.semantic-search-banner .banner-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.sparkle-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--accent-glass);
  color: var(--accent);
  font-weight: 700;
  font-size: 11px;
  flex-shrink: 0;
}

.banner-text {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-reset-search {
  padding: 4px 12px;
  font-size: 11.5px;
  flex-shrink: 0;
}

.sort-segmented {
  display: flex;
  gap: 3px;
  background: var(--glass-surface-subtle);
  padding: 3px;
  border-radius: var(--radius-full);
  border: 1px solid var(--glass-border-subtle);
}

.sort-pill {
  padding: 4px 10px;
  font-size: 11.5px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.18s;
  white-space: nowrap;
}

.sort-pill.active {
  background: var(--glass-surface-solid);
  color: var(--text-primary);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  font-weight: 600;
}

/* ---------------- Loading Indicator ---------------- */
.posts-loading-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--glass-surface-subtle);
  border-radius: var(--radius-md);
  border: 1px dashed var(--glass-border);
  margin-bottom: 12px;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 113, 227, 0.2);
  border-top-color: var(--accent, #0071e3);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

/* ---------------- Stream Infinite Scroll Loading & End States ---------------- */
.feed-sentinel-anchor {
  width: 100%;
  height: 2px;
  pointer-events: none;
  opacity: 0;
}

.feed-stream-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px;
  font-size: 13px;
  color: var(--text-secondary);
  border-radius: var(--radius-md, 14px);
  margin-top: 14px;
}

.feed-stream-end {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px 20px;
  font-size: 12px;
  color: var(--text-tertiary);
  border-radius: var(--radius-md, 14px);
  margin-top: 20px;
  margin-bottom: 24px;
  letter-spacing: 0.02em;
}

.crystal-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent, #0071e3);
  box-shadow: 0 0 6px var(--accent, #0071e3);
  display: inline-block;
  opacity: 0.7;
}

/* Dark mode adjustments for stream */
[data-theme="dark"] .feed-filter-bar,
[data-theme="dark"] .feed-stream-loading,
[data-theme="dark"] .feed-stream-end {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}
</style>
