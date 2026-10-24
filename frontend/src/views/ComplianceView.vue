<template>
  <div class="view-panel active compliance-view-wrapper">
    <!-- Mode 1: Full-page create view (统一发布体验：分区下拉 + 富文本正文) -->
    <CreatePageLayout
      v-if="currentViewMode === 'create'"
      title="发布法条 / 案例"
      back-label="合规指南"
      @back="closePublishModal"
    >
      <template #actions>
        <button
          type="submit"
          form="compliance-publish-form"
          class="btn-liquid"
          :disabled="isPublishing"
        >
          {{ isPublishing ? '发布中…' : '发布' }}
        </button>
      </template>

      <PublishForm
        id="compliance-publish-form"
        :model="publishForm"
        :fields="COMPLIANCE_FIELDS"
        @submit="submitPublish"
      />
    </CreatePageLayout>

    <!-- Mode 2: List View (双栏知识库流) -->
    <div v-else class="compliance-main-content">
      <!-- Dual-column Layout matching PolicyView (政策中心) -->
      <div class="compliance-feed-layout">
        <!-- Main Compliance Stream (左侧法条/案例流) -->
        <section class="compliance-feed-stream">
          <!-- Category Filter Bar (分类选项卡 + 搜索 + 排序 + 发布) -->
          <div class="glass-box feed-filter-bar">
            <div class="category-tabs-scroll">
              <button
                v-for="cat in categoryList"
                :key="cat.key"
                type="button"
                :class="['category-tab-pill', { active: currentCategory === cat.key }]"
                @click="selectCategory(cat.key)"
              >
                <span><OpcIcon :name="cat.icon" :size="13" /> {{ cat.label }}</span>
                <span v-if="getCategoryCount(cat.key) > 0" class="cat-pill-count">
                  {{ getCategoryCount(cat.key) }}
                </span>
              </button>
            </div>

            <div class="feed-filter-right">
              <!-- Search Box -->
              <div class="semantic-search-box">
                <div class="search-input-wrap">
                  <input
                    v-model="searchQuery"
                    type="text"
                    class="semantic-search-input"
                    placeholder="搜索法条 / 案例..."
                    @keydown.enter="handleSearch"
                  />
                  <button v-if="searchQuery" type="button" class="clear-search-btn" @click="resetSearch" title="清空搜索">×</button>
                </div>
                <button
                  type="button"
                  class="btn-liquid semantic-search-btn"
                  @click="handleSearch"
                  title="关键词检索"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  <span>检索</span>
                </button>
              </div>

              <!-- Sort Segmented (热门打榜默认) -->
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

              <!-- Publish Button (右上角发布法条/案例) -->
              <button class="btn-liquid publish-mini-btn" @click="openPublishModal" title="发布法条或避坑案例">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                </svg>
                <span>发布</span>
              </button>

              <!-- Refresh Button (同步数据库) -->
              <button class="btn-liquid-outline refresh-mini-btn" @click="handleManualRefresh" title="刷新并同步合规数据库">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                </svg>
                <span>刷新</span>
              </button>
            </div>
          </div>

          <!-- Semantic Search Status Banner -->
          <div v-if="isSearchActive" class="semantic-search-banner glass-box">
            <div class="banner-left">
              <span class="sparkle-badge"><OpcIcon name="search" :size="13" /> 检索结果</span>
              <span class="banner-text">
                已为您找到与「<strong>{{ activeSearchQuery }}</strong>」相关的 <strong>{{ sortedDisplayItems.length }}</strong> 条法条/案例
              </span>
            </div>
            <button class="btn-liquid-outline btn-reset-search" @click="resetSearch">
              <span>恢复全部</span>
            </button>
          </div>

          <!-- Knowledge Cards Scroll Container -->
          <div class="opc-cards-scroll">
            <!-- Loading State Indicator -->
            <div v-if="isLoading && displayItems.length === 0" class="posts-loading-banner glass-box">
              <span class="loading-spinner"></span>
              <span>正在从数据库检索并加载「{{ currentCategoryLabel }}」合规知识库...</span>
            </div>

            <!-- Knowledge Cards Grid (法条 / 案例 卡片流) -->
            <div
              v-if="sortedDisplayItems.length > 0"
              class="compliance-cards-container opc-cards-grid"
            >
              <div
                v-for="item in sortedDisplayItems"
                :key="item.id"
                class="glass-card compliance-card opc-card-shell opc-card"
                @click="openDetail(item)"
              >
                <!-- Card Header: Law Emblem / Case Badge + 热门标记 -->
                <div class="card-header-row">
                  <div class="compliance-icon-wrapper opc-card-icon" :style="itemIconStyle(item)">
                    <span class="compliance-emblem-icon"><OpcIcon :name="itemIcon(item)" :size="20" /></span>
                  </div>
                  <div class="card-title-group">
                    <div class="card-title-line">
                      <h3 class="compliance-title" :title="item.title">{{ item.title }}</h3>
                      <span v-if="item.hot_score >= 90" class="hot-flame-badge"><OpcIcon name="flame" :size="12" /> 热门</span>
                    </div>
                    <div class="card-badges-line">
                      <template v-if="isLaw(item)">
                        <span class="badge-law" :style="lawColorStyle(item)">{{ item.name || '法条' }}</span>
                        <span class="badge-level" :style="levelColorStyle(item)">{{ item.level || '国家级' }}</span>
                        <span class="mono-tag badge-code">{{ item.code || item.id }}</span>
                      </template>
                      <template v-else>
                        <span class="badge-case" :style="{ background: `${item.badge_color}18`, color: item.badge_color, border: `1px solid ${item.badge_color}40` }">
                          {{ item.badge || '避坑案例' }}
                        </span>
                        <span class="badge-industry"><OpcIcon name="factory" :size="12" /> {{ item.industry }}</span>
                      </template>
                      <OfficialBadge :visible="item.is_official" label="官方" title="官方发布：由平台官方账号发布并认证" />
                    </div>
                  </div>
                </div>

                <!-- Card Body -->
                <div class="card-body">
                  <template v-if="isLaw(item)">
                    <p class="compliance-summary" :title="item.summary">{{ item.summary }}</p>
                    <div class="compliance-issuer-row">
                      <span class="issuer-pill"><OpcIcon name="landmark" :size="12" /> {{ item.issuer || '发布机关' }}</span>
                      <span class="issuer-pill"><OpcIcon name="calendar" :size="12" /> {{ item.published_at || '—' }}</span>
                    </div>
                  </template>
                  <template v-else>
                    <p class="compliance-summary" :title="item.lesson">
                      <strong>【避坑经验】</strong> {{ item.lesson }}
                    </p>
                  </template>
                </div>

                <!-- Card Highlights -->
                <div class="card-highlights-row">
                  <template v-if="isLaw(item)">
                    <span class="highlight-chip chip-penalty"><OpcIcon name="alert" :size="12" /> {{ item.penalties }}</span>
                    <span class="highlight-chip chip-law"><OpcIcon name="scroll" :size="12" /> {{ item.law_ref }}</span>
                  </template>
                  <template v-else>
                    <span class="highlight-chip chip-violation"><OpcIcon name="bolt" :size="12" /> {{ item.violation }}</span>
                  </template>
                </div>

                <!-- Card Footer -->
                <div class="card-footer-row" @click.stop>
                  <div class="issuer-cell">
                    <div class="issuer-avatar"><OpcIcon :name="isLaw(item) ? 'scroll' : 'case'" :size="18" /></div>
                    <div class="issuer-text">
                      <span class="issuer-name">{{ isLaw(item) ? (item.issuer || '发布机关') : '典型踩坑案例' }}</span>
                      <span class="issuer-level-tag">{{ isLaw(item) ? (item.level || '国家级') : '监管处罚' }}</span>
                    </div>
                  </div>
                  <div class="card-actions-cell">
                    <span class="hot-score-chip"><OpcIcon name="flame" :size="12" /> {{ item.hot_score || 0 }}</span>
                    <button type="button" class="btn-liquid-outline btn-detail-sm" @click.stop="openDetail(item)">
                      <span>查看详情</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Inline Detail (content area, no modal) -->
            <div v-if="selectedItem" class="inline-detail-slot glass-box">
              <div class="inline-detail-head">
                <button type="button" class="btn-back-inline" @click="closeDetail">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                  </svg>
                  <span>返回合规知识库</span>
                </button>
                <span class="inline-detail-crumb">合规中心 / {{ selectedItem.title }}</span>
              </div>

              <div class="detail-header">
                <div class="detail-icon-wrap" :style="itemIconStyle(selectedItem)">
                  <span class="detail-emblem-icon"><OpcIcon :name="itemIcon(selectedItem)" :size="24" /></span>
                </div>
                <div class="detail-title-block">
                  <div class="detail-title-row">
                    <h2 class="detail-title">{{ selectedItem.title }}</h2>
                    <span class="mono-tag version-pill">{{ selectedItem.code || selectedItem.id }}</span>
                    <span v-if="selectedItem.hot_score >= 90" class="hot-flame-badge"><OpcIcon name="flame" :size="12" /> 热门</span>
                  </div>
                  <p class="detail-tagline">{{ isLaw(selectedItem) ? selectedItem.summary : `${selectedItem.industry} · ${selectedItem.badge}` }}</p>
                  <div class="detail-meta-pills">
                    <span class="detail-cat-pill">{{ isLaw(selectedItem) ? (selectedItem.name || '法条') : '避坑案例' }}</span>
                    <span class="detail-level-pill">{{ isLaw(selectedItem) ? (selectedItem.level || '国家级') : '监管处罚' }}</span>
                    <span class="detail-region-pill"><OpcIcon name="flame" :size="12" /> 热度 {{ selectedItem.hot_score || 0 }}</span>
                  </div>
                </div>
              </div>

              <div class="detail-action-bar">
                <button type="button" class="btn-liquid action-btn primary-action" @click="openPublishModal">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                  </svg>
                  <span>发布法条 / 案例</span>
                </button>
              </div>

              <div class="detail-body-scroll">
                <template v-if="isLaw(selectedItem)">
                  <div class="detail-section">
                    <h4 class="section-title">核心条文要点</h4>
                    <!-- 正文为富文本编辑器产出的 Markdown，渲染后展示 -->
                    <div class="detail-full-description markdown-rendered-content" v-html="renderedLawContent"></div>
                  </div>
                  <div class="detail-section">
                    <h4 class="section-title">违规罚则</h4>
                    <div class="detail-full-description"><OpcIcon name="alert" :size="13" /> {{ selectedItem.penalties }}</div>
                  </div>
                  <div class="detail-section">
                    <h4 class="section-title">发布信息</h4>
                    <div class="spec-grid">
                      <div class="spec-item">
                        <span class="spec-label">效力级别</span>
                        <span class="spec-value">{{ selectedItem.level || '国家级' }}</span>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">发布机关</span>
                        <span class="spec-value">{{ selectedItem.issuer || '—' }}</span>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">发布日期</span>
                        <span class="spec-value mono-val">{{ selectedItem.published_at || '—' }}</span>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">热度分</span>
                        <span class="spec-value"><OpcIcon name="flame" :size="12" /> {{ selectedItem.hot_score || 0 }}</span>
                      </div>
                      <div class="spec-item" style="grid-column: span 2;">
                        <span class="spec-label">官方法条依据</span>
                        <span class="spec-value">{{ selectedItem.law_ref }}</span>
                      </div>
                      <div class="spec-item" style="grid-column: span 2;">
                        <span class="spec-label">数据存储</span>
                        <span class="spec-value spec-success">PostgreSQL 合规库持久化</span>
                      </div>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div class="detail-section">
                    <h4 class="section-title">案情背景与违规事实</h4>
                    <div class="detail-full-description markdown-rendered-content" v-html="renderedCaseViolation"></div>
                  </div>
                  <div class="detail-section">
                    <h4 class="section-title">监管处罚结果</h4>
                    <div class="detail-full-description"><OpcIcon name="scale" :size="13" /> {{ selectedItem.consequence }}</div>
                  </div>
                  <div class="detail-section">
                    <h4 class="section-title">避坑经验</h4>
                    <div class="ai-summary-highlight-box">
                      <p class="ai-box-text"><OpcIcon name="bulb" :size="14" /> {{ selectedItem.lesson }}</p>
                    </div>
                  </div>
                </template>

                <!-- 展示页面免责声明 -->
                <ContentDisclaimer type="compliance" />
              </div>
            </div>

            <!-- Empty State -->
            <div v-else-if="!isLoading && sortedDisplayItems.length === 0" class="glass-box empty-state-box">
              <div class="empty-icon-wrap">
                <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
              </div>
              <h3 class="empty-title">当前筛选下暂无合规知识</h3>
              <p class="empty-desc">
                {{ searchQuery ? `没有检索到与 “${searchQuery}” 匹配的法条或案例。` : '当前分类下暂无已收录内容。' }}
              </p>
              <div class="empty-actions">
                <button v-if="searchQuery || currentCategory !== 'ALL'" class="btn-liquid-outline" @click="resetSearch">
                  重置筛选条件
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Right Auxiliary Sidebar (与政策中心同款辅助侧栏) -->
        <aside class="compliance-feed-sidebar">
          <!-- 1. Compliance Center Card (合规中心) -->
          <div class="glass-box sidebar-card compliance-center-card">
            <div class="creator-card-header">
              <div class="creator-icon-orb" style="background: var(--accent-glass); color: var(--accent);">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              </div>
              <div>
                <h4 class="creator-title">合规指南中心</h4>
                <p class="creator-desc">法条 · 案例 · 热门打榜</p>
              </div>
            </div>

            <button class="btn-liquid btn-creator-publish" @click="openPublishModal">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
              </svg>
              <span>发布法条 / 案例</span>
            </button>

            <div class="creator-quick-links">
              <span class="quick-pill" @click="selectCategory('LAW')">法条</span>
              <span class="quick-pill" @click="selectCategory('CASE')">案例</span>
              <span class="quick-pill" @click="selectCategory('HOT')">热门打榜</span>
              <span class="quick-pill" @click="quickSearchKeyword('隐私')">隐私合规</span>
              <span class="quick-pill" @click="quickSearchKeyword('二清')">防二清</span>
              <span class="quick-pill" @click="quickSearchKeyword('备案')">上线备案</span>
            </div>
          </div>

          <!-- 2. Today's Hot Compliance Rank (今日合规打榜) -->
          <div class="glass-box sidebar-card hot-ranking-card">
            <div class="sidebar-card-title-row">
              <div class="title-with-icon">
                <span class="hot-badge-fire"><OpcIcon name="flame" :size="14" /></span>
                <h4 class="sidebar-title">今日合规打榜</h4>
              </div>
              <span class="hot-subtitle">实时更新</span>
            </div>

            <div class="hot-ranking-list">
              <div
                v-for="(item, idx) in hotRankItems"
                :key="item.id"
                class="hot-rank-item"
                @click="openDetail(item)"
              >
                <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                <div class="hot-item-content">
                  <h5 class="hot-item-title">{{ item.title }}</h5>
                  <div class="hot-item-meta">
                    <span><OpcIcon name="flame" :size="12" /> {{ item.hot_score || 0 }} 热度</span>
                    <span class="dot-sep">·</span>
                    <span>{{ isLaw(item) ? (item.name || '法条') : '案例' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. Disclaimer Card (免责声明) -->
          <div class="glass-box sidebar-card disclaimer-card">
            <h4 class="sidebar-title-sm">免责声明</h4>
            <p class="guidelines-desc">
              本页法条与案例内容仅供学习参考，不构成法律意见。具体合规义务请以国家现行法律法规及主管机关正式文件为准。
            </p>
            <div class="guidelines-footer">
              <span>OpcHub 合规中心 v2.1</span>
              <span class="dot-sep">·</span>
              <span class="link-span" @click="openPublishModal">补充收录</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import OfficialBadge from '@/components/OfficialBadge.vue';
import ContentDisclaimer from '@/components/ContentDisclaimer.vue';
import PublishForm from '@/components/PublishForm.vue';
import CreatePageLayout from '@/components/CreatePageLayout.vue';
import { COMPLIANCE_FIELDS } from '@/config/publishForms';
import { renderMarkdown } from '@/utils/markdown';
import {
  COMPLIANCE_LAW_ICONS,
  COMPLIANCE_LEVEL_COLORS,
  COMPLIANCE_LAW_COLORS,
  COMPLIANCE_SORT_OPTIONS,
  COMPLIANCE_HOT_RANK_LIMIT,
} from '@/config/compliancePage';

const emit = defineEmits(['switch-tab', 'toast', 'open-login']);

// 当前登录会话（页面未接收 userSession prop，与 SopView 同样从本地存储读取）
function safeSession() {
  try {
    const raw = localStorage.getItem('opchub_user_session');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

// ---- Knowledge base (from PostgreSQL via gateway) ----
const laws = ref([]);
const cases = ref([]);
const isLoading = ref(false);
const isSearchActive = ref(false);
const activeSearchQuery = ref('');
const searchQuery = ref('');

// Category & Sorting
const currentCategory = ref('ALL');
const currentSort = ref('hot');
const selectedItem = ref(null);

// 详情正文渲染：发布侧为富文本（Markdown），详情侧统一渲染后展示
const renderedLawContent = computed(() =>
  selectedItem.value ? renderMarkdown(selectedItem.value.content || selectedItem.value.summary || '') : ''
);

const renderedCaseViolation = computed(() =>
  selectedItem.value ? renderMarkdown(selectedItem.value.violation || '') : ''
);

const categoryList = [
  { key: 'ALL', label: '全部', icon: 'shield' },
  { key: 'LAW', label: '法条', icon: 'scroll' },
  { key: 'CASE', label: '案例', icon: 'case' },
  { key: 'HOT', label: '热门', icon: 'flame' },
];

const sortOptions = COMPLIANCE_SORT_OPTIONS;

// Publish 视图模式（同论坛"发起新风暴话题"：内容区内联展开，非弹窗）
const currentViewMode = ref('list'); // 'list' | 'create'
const isPublishing = ref(false);
const publishForm = ref({
  kind: 'law',
  title: '',
  code: '',
  summary: '',
  content: '',
  level: '法律',
  issuer: '',
  published_at: '',
  penalties: '',
  law_ref: '',
  industry: '',
  violation: '',
  consequence: '',
  lesson: '',
  badge: '',
});

// Lifecycle: lock body scroll to feed like PolicyView
onMounted(() => {
  document.body.classList.add('fixed-screen-feed');
  loadAll();
});

watch(currentViewMode, (mode) => {
  if (mode === 'list') {
    document.body.classList.add('fixed-screen-feed');
  } else {
    document.body.classList.remove('fixed-screen-feed');
  }
});

onUnmounted(() => {
  document.body.classList.remove('fixed-screen-feed');
});

async function loadAll() {
  isLoading.value = true;
  try {
    const [lawRes, caseRes] = await Promise.all([
      dispatchGateway('compliance.laws', {}),
      dispatchGateway('compliance.cases', {}),
    ]);
    if (lawRes.ok && Array.isArray(lawRes.data)) laws.value = lawRes.data;
    if (caseRes.ok && Array.isArray(caseRes.data)) cases.value = caseRes.data;
  } catch (err) {
    console.error('Failed to load compliance knowledge base:', err);
    emit('toast', {
      title: '数据同步异常',
      message: '未能从数据库同步合规知识库，请稍后重试。',
      type: 'ERROR',
    });
  } finally {
    isLoading.value = false;
  }
}

async function handleManualRefresh() {
  await loadAll();
  emit('toast', {
    title: '合规库已更新',
    message: '已从 PostgreSQL 数据库同步最新法条与案例。',
    type: 'SUCCESS',
  });
}

function selectCategory(catKey) {
  currentCategory.value = catKey;
  selectedItem.value = null;
}

const currentCategoryLabel = computed(() => {
  const c = categoryList.find((item) => item.key === currentCategory.value);
  return c ? c.label : '全部';
});

function getCategoryCount(catKey) {
  if (catKey === 'LAW') return laws.value.length;
  if (catKey === 'CASE') return cases.value.length;
  if (catKey === 'HOT') return hotRankItems.value.length;
  return laws.value.length + cases.value.length;
}

function isLaw(item) {
  return item && ('law_ref' in item || 'content' in item);
}

// Display list with category filter
const displayItems = computed(() => {
  if (currentCategory.value === 'LAW') return [...laws.value];
  if (currentCategory.value === 'CASE') return [...cases.value];
  if (currentCategory.value === 'HOT') return [...hotRankItems.value];
  return [...laws.value, ...cases.value];
});

// Search
async function handleSearch() {
  const q = searchQuery.value.trim();
  if (!q) {
    resetSearch();
    return;
  }
  isSearchActive.value = true;
  activeSearchQuery.value = q;
}

function resetSearch() {
  searchQuery.value = '';
  isSearchActive.value = false;
  activeSearchQuery.value = '';
}

function quickSearchKeyword(keyword) {
  searchQuery.value = keyword;
  handleSearch();
}

// Sorted items (hot rank default, respecting search query)
const sortedDisplayItems = computed(() => {
  let list = [...displayItems.value];
  if (isSearchActive.value && searchQuery.value.trim()) {
    const qLower = searchQuery.value.trim().toLowerCase();
    list = list.filter((item) => {
      const text = `${item.title} ${item.summary || ''} ${item.content || ''} ${item.law_ref || ''} ${item.lesson || ''} ${item.violation || ''}`.toLowerCase();
      return text.includes(qLower);
    });
  }
  if (currentSort.value === 'hot') {
    list.sort((a, b) => (b.hot_score || 0) - (a.hot_score || 0));
  } else if (currentSort.value === 'new') {
    list.sort((a, b) => {
      const ta = a.published_at ? new Date(a.published_at).getTime() : 0;
      const tb = b.published_at ? new Date(b.published_at).getTime() : 0;
      return tb - ta;
    });
  } else if (currentSort.value === 'level') {
    const levelWeight = { '法律': 4, '行政法规': 3, '部门规章': 2, '地方性法规': 1 };
    list.sort((a, b) => (levelWeight[b.level] || 0) - (levelWeight[a.level] || 0));
  }
  return list;
});

// Top N Hot Rank for Right Auxiliary Sidebar (今日合规打榜)
const hotRankItems = computed(() => {
  return [...laws.value, ...cases.value]
    .sort((a, b) => (b.hot_score || 0) - (a.hot_score || 0))
    .slice(0, COMPLIANCE_HOT_RANK_LIMIT);
});

// ---- Detail ----
function openDetail(item) {
  selectedItem.value = item;
}

function closeDetail() {
  selectedItem.value = null;
}

// ---- Publish (内联视图模式，同论坛"发起新风暴话题") ----
// currentViewMode: 'list' | 'create'
function openPublishModal() {
  publishForm.value = {
    kind: 'law',
    title: '',
    code: `LAW-${Math.floor(10 + Math.random() * 90)}`,
    summary: '',
    content: '',
    level: '法律',
    issuer: '',
    published_at: '',
    penalties: '',
    law_ref: '',
    industry: '',
    violation: '',
    consequence: '',
    lesson: '',
    badge: '',
  };
  currentViewMode.value = 'create';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function closePublishModal() {
  currentViewMode.value = 'list';
}

async function submitPublish() {
  if (!safeSession()) {
    emit('open-login');
    emit('toast', {
      title: '需要登录',
      message: '请先登录创客账号后再发布法条或避坑案例。',
      type: 'WARNING',
    });
    return;
  }
  isPublishing.value = true;
  try {
    const res = await dispatchGateway('compliance.publish', { ...publishForm.value });
    if (res.ok) {
      const kindLabel = publishForm.value.kind === 'law' ? '法条' : '案例';
      emit('toast', {
        title: `${kindLabel}发布成功`,
        message: `《${publishForm.value.title}》已通过平台敏感词校验并收录至合规知识库。`,
        type: 'SUCCESS',
      });
      currentViewMode.value = 'list';
      await loadAll();
    } else {
      emit('toast', {
        title: '发布提示',
        message: res.error || '发布未通过平台内容校验，请调整后重试。',
        type: 'WARNING',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '发布失败',
      message: e.message || '网络或接口通信异常，请稍后重试。',
      type: 'ERROR',
    });
  } finally {
    isPublishing.value = false;
  }
}

// ---- Display helpers ----
function itemIcon(item) {
  if (isLaw(item)) return COMPLIANCE_LAW_ICONS[item.icon_name] || 'scroll';
  return 'case';
}

function itemIconStyle(item) {
  if (isLaw(item)) {
    const color = COMPLIANCE_LAW_COLORS[item.code] || '#0071E3';
    return { background: `${color}1E`, border: `1px solid ${color}40` };
  }
  const color = item.badge_color || '#5B6472';
  return { background: `${color}1E`, border: `1px solid ${color}40` };
}

function lawColorStyle(item) {
  const color = COMPLIANCE_LAW_COLORS[item.code] || '#0071E3';
  return { background: `${color}14`, color, border: `1px solid ${color}30` };
}

function levelColorStyle(item) {
  const color = COMPLIANCE_LEVEL_COLORS[item.level] || '#0071E3';
  return { background: `${color}12`, color, border: `1px solid ${color}30` };
}
</script>

<style scoped>
/* ---------------- 1. Overall Wrapper Layout matching PolicyView ---------------- */
.compliance-view-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.compliance-main-content {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

/* Dual-Column Feed Layout identical to PolicyView */
.compliance-feed-layout {
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

.compliance-feed-stream {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}

/* Category Filter Bar */
.feed-filter-bar {
  flex-shrink: 0;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  border-radius: var(--radius-md, 14px);
  gap: 12px;
  flex-wrap: wrap;
  background: var(--glass-surface);
  backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  border: 1px solid var(--glass-border);
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
  display: inline-flex;
  align-items: center;
  gap: 6px;
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

.cat-pill-count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(0, 113, 227, 0.15);
}

.feed-filter-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

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

.semantic-search-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-full, 9999px);
  background: var(--accent);
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
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
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;
}

.sort-pill.active {
  background: var(--glass-surface);
  color: var(--accent);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.publish-mini-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.refresh-mini-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: var(--radius-full);
}

.semantic-search-banner {
  flex-shrink: 0;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: var(--radius-md, 12px);
  background: rgba(0, 113, 227, 0.08);
  border: 1px solid rgba(0, 113, 227, 0.25);
  font-size: 12.5px;
  color: var(--text-primary);
  gap: 12px;
}

.banner-left {
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

/* ---------------- 2. Scrollable Cards Container ---------------- */
/* 卡片滚动容器、网格与外壳：由全局统一卡片体系 (.opc-cards-scroll / .opc-cards-grid / .opc-card-shell) 承载 */

/* Compliance 图标 tile：尺寸由全局 .opc-card-icon 承载 */
.compliance-emblem-icon {
  font-size: 22px;
}

.compliance-title {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hot-flame-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--status-warning);
  background: var(--status-warning-soft);
  border: 1px solid var(--status-warning-soft);
  padding: 1px 7px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.badge-law {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

.badge-level {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

.badge-code {
  font-size: 10.5px;
}

.badge-case {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

.badge-industry {
  font-size: 11px;
  color: var(--text-tertiary);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.compliance-summary {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.compliance-issuer-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  flex-wrap: wrap;
}

.issuer-pill {
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-secondary);
}

/* Highlights chips 专属色（基础 .highlight-chip 由全局承载） */
.chip-penalty {
  color: var(--status-danger);
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chip-law {
  color: var(--accent);
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chip-violation {
  color: var(--status-warning);
  max-width: 300px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Card Footer: 全局统一 (.card-footer-row / .issuer-* / .card-actions-cell) */

.hot-score-chip {
  font-size: 11px;
  font-weight: 700;
  color: var(--status-warning);
}

.btn-detail-sm {
  padding: 3px 10px;
  font-size: 11.5px;
  font-weight: 500;
  border-radius: var(--radius-full);
}

/* ---------------- Loading & Empty States ---------------- */
.posts-loading-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 20px;
  border-radius: var(--radius-md, 12px);
  font-size: 12.5px;
  color: var(--text-tertiary);
  text-align: center;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 113, 227, 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state-box {
  padding: 56px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  border-radius: var(--radius-lg, 16px);
}

.empty-icon-wrap {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--glass-surface-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.empty-title {
  font-size: 16.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 420px;
  line-height: 1.5;
  margin: 0;
}

.empty-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

/* ---------------- Right Auxiliary Sidebar (与政策中心同款) ---------------- */
.compliance-feed-sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-self: stretch;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: none;
  box-sizing: border-box;
}

.compliance-feed-sidebar::-webkit-scrollbar {
  display: none;
}

.sidebar-card {
  flex-shrink: 0;
  margin: 0;
  padding: 18px 20px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface);
  backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  border: 1px solid var(--glass-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  box-sizing: border-box;
  width: 100%;
}

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
  background: var(--accent-glass);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.creator-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.creator-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
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
  border-radius: var(--radius-full);
}

.creator-quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-pill {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  padding: 3px 9px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.quick-pill:hover {
  color: var(--accent);
  border-color: rgba(0, 113, 227, 0.25);
  background: rgba(0, 113, 227, 0.05);
}

.sidebar-card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--glass-border-subtle);
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
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.hot-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: var(--accent);
}

.hot-ranking-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hot-rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm, 10px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  cursor: pointer;
  transition: all 0.18s ease;
}

.hot-rank-item:hover {
  border-color: rgba(0, 113, 227, 0.25);
  background: rgba(0, 113, 227, 0.05);
}

.rank-num {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
  background: var(--glass-surface);
  color: var(--text-secondary);
}

.rank-1 {
  background: var(--glass-surface-subtle);
  color: var(--text-primary);
  font-weight: 700;
}

.rank-2 {
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
}

.rank-3 {
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
}

.hot-item-content {
  flex: 1;
  min-width: 0;
}

.hot-item-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 2px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hot-rank-item:hover .hot-item-title {
  color: var(--accent);
}

.hot-item-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.sidebar-title-sm {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.guidelines-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0 0 12px 0;
}

.guidelines-footer {
  display: flex;
  align-items: center;
  font-size: 11px;
  color: var(--text-tertiary);
  gap: 5px;
}

.dot-sep {
  opacity: 0.5;
}

.link-span {
  color: var(--accent);
  cursor: pointer;
}

.link-span:hover {
  text-decoration: underline;
}

/* ---------------- Inline Detail ---------------- */
.inline-detail-slot {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border-radius: var(--radius-lg, 16px);
}

.inline-detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--glass-border-subtle);
  padding-bottom: 12px;
}

.btn-back-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  white-space: nowrap;
}

.btn-back-inline:hover {
  background: rgba(120, 130, 150, 0.1);
  color: var(--text-primary);
}

.inline-detail-crumb {
  font-size: 11.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  position: relative;
}

.detail-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-emblem-icon {
  font-size: 30px;
}

.detail-title-block {
  flex: 1;
  min-width: 0;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.detail-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

.version-pill {
  font-size: 11px;
}

.detail-tagline {
  font-size: 13.5px;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.detail-meta-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-cat-pill,
.detail-level-pill,
.detail-region-pill {
  font-size: 11.5px;
  padding: 2px 9px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.detail-action-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-full);
  text-decoration: none;
}

.primary-action {
  box-shadow: 0 4px 14px rgba(0, 113, 227, 0.25);
}

.detail-body-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-right: 4px;
}

.inline-detail-slot .detail-body-scroll {
  flex: none;
  overflow: visible;
  max-height: none;
  padding-right: 0;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.detail-full-description {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0;
}

.ai-summary-highlight-box {
  padding: 14px 16px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.ai-box-text {
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-primary);
  margin: 0;
}

.spec-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  background: var(--glass-surface-subtle);
  padding: 14px;
  border-radius: var(--radius-md, 12px);
  border: 1px solid var(--glass-border-subtle);
}

.spec-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.spec-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.spec-value {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-primary);
}

.spec-success {
  color: var(--status-success);
  font-size: 11.5px;
}

/* ---------------- Inline Create View (内容区内联发布，同论坛"发起新风暴话题") ---------------- */
.compliance-create-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
  animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.compliance-create-page::-webkit-scrollbar {
  display: none;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Header Bar */
.create-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  gap: 16px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.header-left-cluster {
  display: flex;
  align-items: center;
  gap: 14px;
}

.btn-back-square {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-liquid, all 0.2s ease);
}

.btn-back-square:hover {
  background: var(--glass-surface-hover);
  color: var(--accent);
  transform: translateX(-2px);
}

.page-title-cluster {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.breadcrumb-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.crumb-link {
  cursor: pointer;
  transition: color 0.2s ease;
}

.crumb-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.crumb-separator {
  opacity: 0.5;
}

.crumb-current {
  color: var(--text-primary);
  font-weight: 500;
}

.page-main-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin: 0;
}

.header-actions-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-header-publish {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-full);
}

.btn-header-publish:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Main Workspace Box */
.create-workspace-box {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex-shrink: 0;
}

/* Form Rows */
.form-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.required-star {
  color: var(--status-danger);
}

/* Category Pills Row (法条 / 案例) */
.categories-pill-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.cat-select-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  cursor: pointer;
  transition: var(--transition-liquid, all 0.2s ease);
  text-align: left;
}

.cat-select-btn:hover {
  background: var(--glass-surface-hover);
  border-color: var(--accent);
}

.cat-select-btn.active {
  background: var(--glass-surface-solid);
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent), var(--glass-shadow, 0 4px 16px rgba(0, 0, 0, 0.08));
}

.cat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-bottom: 6px;
}

.cat-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.cat-desc {
  font-size: 11px;
  color: var(--text-tertiary);
}

/* Title Input */
.title-input-row {
  gap: 8px;
}

.title-input-wrapper {
  position: relative;
}

.title-large-input {
  font-size: 15px !important;
  padding: 12px 14px !important;
  border-radius: var(--radius-md) !important;
}

/* Two-column grid for form fields */
.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.glass-select {
  height: 38px;
}

/* Footer Actions */
.create-footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
  padding-top: 16px;
  border-top: 1px solid var(--glass-border-subtle);
}

/* Responsive */
@media (max-width: 960px) {
  .form-grid-2 {
    grid-template-columns: 1fr;
  }
  .compliance-feed-layout {
    flex-direction: column;
  }
  .compliance-feed-sidebar {
    width: 100%;
    height: auto;
  }
}
</style>
