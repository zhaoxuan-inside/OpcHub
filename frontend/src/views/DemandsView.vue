<template>
  <div class="view-panel active demands-view-wrapper">
    <div class="demands-main-content">
      <!-- Dual-column Layout identical to Product Showcase (产品橱窗) -->
      <div class="demands-feed-layout">
        <!-- Main Demand Stream (左侧商机流) -->
        <section class="demands-feed-stream">
          <!-- Category Filter Bar (商机分区选项卡 + 搜索 + 排序选择) -->
          <div class="glass-box feed-filter-bar">
            <div class="category-tabs-scroll">
              <button
                v-for="cat in categoryList"
                :key="cat.key"
                type="button"
                :class="['category-tab-pill', { active: currentCategory === cat.key }]"
                @click="selectCategory(cat.key)"
              >
                <span>{{ cat.label }}</span>
                <span v-if="cat.key === 'ALL' && totalCount > 0" class="cat-pill-count">{{ totalCount }}</span>
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
                    placeholder="搜索商机..."
                    @keydown.enter="handleSearch"
                  />
                  <button v-if="searchQuery" type="button" class="clear-search-btn" @click="handleClearSearch" title="清空搜索">×</button>
                </div>
                <button
                  type="button"
                  class="btn-liquid semantic-search-btn"
                  :disabled="isSearching"
                  @click="handleSearch"
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

              <button class="btn-liquid-outline refresh-mini-btn" @click="handleManualRefresh" title="刷新并重置本地缓存">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                </svg>
                <span>刷新</span>
              </button>
            </div>
          </div>

          <!-- Search Status Banner -->
          <div v-if="isSearchActive" class="semantic-search-banner glass-box">
            <div class="banner-left">
              <span class="sparkle-badge"><OpcIcon name="search" :size="13" /> 搜索结果</span>
              <span class="banner-text">
                已为您找到与「<strong>{{ activeSearchQuery }}</strong>」相关的 <strong>{{ sortedDisplayDemands.length }}</strong> 条企业委托
              </span>
            </div>
            <button class="btn-liquid-outline btn-reset-search" @click="handleClearSearch">
              <span>恢复全部商机</span>
            </button>
          </div>

          <!-- Demand Cards Scroll Container (ONLY this container scrolls with mouse wheel) -->
          <div
            class="opc-cards-scroll"
            ref="demandsScrollContainerRef"
            @scroll.passive="handleDemandsScroll"
          >
            <!-- Loading State Indicator -->
            <div v-if="loading && displayDemands.length === 0" class="posts-loading-banner glass-box">
              <span class="loading-spinner"></span>
              <span>正在从数据库检索并加载「{{ currentCategoryLabel }}」优质企业商机...</span>
            </div>

            <!-- Demand Cards Stream (需求集市内容：以卡片为主！) -->
            <div
              v-if="sortedDisplayDemands.length > 0 && !selectedDemand"
              class="demands-cards-container opc-cards-grid"
              id="demandCardsGrid"
            >
              <div
                v-for="item in sortedDisplayDemands"
                :key="item.id"
                class="glass-card demands-demand-card opc-card-shell opc-card opc-reveal-host"
                @mousemove="handleMouseMove"
                @click="openDemandDetail(item)"
              >
                <!-- Card Top: Category Icon & Basic Info -->
                <div class="card-header-row">
                  <div class="app-icon-wrapper opc-card-icon">
                    <div class="app-icon-fallback" :style="getIconFallbackStyle(item)">
                      <OpcIcon :name="getCategoryIcon(item.category)" :size="22" />
                    </div>
                  </div>

                  <div class="card-title-group">
                    <div class="card-title-line">
                      <h3 class="demand-title opc-clamp opc-clamp-2" :title="item.title">{{ item.title }}</h3>
                      <span v-if="item.status" class="demand-status-badge" :class="getStatusClass(item.status)">
                        {{ getStatusLabel(item.status) }}
                      </span>
                    </div>
                    <div class="card-badges-line">
                      <span class="badge-cat">{{ getCategoryLabel(item.category) }}</span>
                      <span class="badge-pricing pricing-onetime">
                        ¥{{ formatBudget(item.budget_cny) }} 预算
                      </span>
                      <span v-if="item.bidders_count" class="badge-semantic-score">
                        <OpcIcon name="users" :size="12" /> {{ item.bidders_count }} 人已竞标
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Card Body: Description (hover reveals full) -->
                <div class="card-body">
                  <HoverRevealText :text="item.description" :lines="2" />
                </div>

                <!-- Card Highlights / Quick Spec Chips -->
                <div class="card-highlights-row">
                  <span class="highlight-chip chip-deadline">
                    <OpcIcon name="timer" :size="12" /> {{ formatDeadline(item.deadline_at) }} 截止
                  </span>
                </div>

                <!-- Card Footer: Publisher + Bidders + Actions -->
                <div class="card-footer-row" @click.stop>
                  <div class="author-cell">
                    <div class="author-avatar" :style="getAuthorAvatarStyle(item)">
                      {{ getInitials(item.creator_name || item.creator_id) }}
                    </div>
                    <div class="author-text">
                      <span class="author-name">{{ item.creator_name || item.creator_id || '@企业委托方' }}</span>
                      <span class="publish-time">{{ formatDateShort(item.created_at) }}</span>
                    </div>
                  </div>

                  <div class="card-actions-cell">
                    <span class="upvote-btn-pill demand-bidder-pill">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                      </svg>
                      <span>{{ item.bidders_count || 0 }}</span>
                    </span>

                    <button
                      type="button"
                      class="btn-liquid btn-bid-sm"
                      @click.stop="handleOpenBid(item)"
                    >
                      竞标
                    </button>
                  </div>
                </div>

                <!-- Card Interaction Band (unified like/comment/love/favorite) -->
                <div class="card-interaction-row" @click.stop>
                  <ContentInteractionBar
                    target-type="DEMAND"
                    :target-id="item.id"
                    :target-title="item.title"
                    :like-count="item.like_count ?? 0"
                    :favorite-count="item.favorite_count ?? 0"
                    :love-count="item.love_count ?? 0"
                    :comment-count="item.comment_count ?? 0"
                    :dislike-count="item.dislike_count ?? 0"
                    :rating-avg="item.rating_avg ?? 0"
                    :rating-count="item.rating_count ?? 0"
                    :my-rating="item.viewer?.rating ?? 0"
                    :liked="item.viewer?.liked ?? false"
                    :favorited="item.viewer?.favorited ?? false"
                    :loved="item.viewer?.loved ?? false"
                    :commented="item.viewer?.commented ?? false"
                    :disliked="item.viewer?.disliked ?? false"
                    :authenticated="Boolean(currentUserSession)"
                    variant="band"
                    @changed="handleInteractionChanged(item, $event)"
                    @require-login="$emit('open-login')"
                    @toast="$emit('toast', $event)"
                  />
                </div>
              </div>
            </div>

            <!-- Inline Demand Detail (content area, no modal) -->
            <div v-if="selectedDemand" class="inline-detail-slot glass-box">
              <div class="inline-detail-head">
                <button type="button" class="btn-back-inline" @click="closeDemandDetail" title="返回商机列表">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                  </svg>
                  <span>返回商机列表</span>
                </button>
                <span class="inline-detail-crumb">需求集市 / {{ selectedDemand.title }}</span>
              </div>

              <div class="detail-header">
                <div class="detail-icon-wrap">
                  <div class="app-icon-fallback detail-icon-fallback" :style="getIconFallbackStyle(selectedDemand)">
                    <OpcIcon :name="getCategoryIcon(selectedDemand.category)" :size="26" />
                  </div>
                </div>

                <div class="detail-title-block">
                  <div class="detail-title-row">
                    <h2 class="detail-title">{{ selectedDemand.title }}</h2>
                    <span class="mono-tag version-pill" :class="getStatusClass(selectedDemand.status)">
                      {{ getStatusLabel(selectedDemand.status) }}
                    </span>
                  </div>
                  <p class="detail-tagline">
                    {{ getCategoryLabel(selectedDemand.category) }} · 预算 ¥{{ formatBudget(selectedDemand.budget_cny) }} · {{ selectedDemand.bidders_count || 0 }} 人已竞标
                  </p>
                  <div class="detail-meta-pills">
                    <span class="detail-cat-pill">{{ selectedDemand.creator_name || selectedDemand.creator_id || '@企业委托方' }}</span>
                    <span class="detail-pricing-pill">¥{{ formatBudget(selectedDemand.budget_cny) }} 托管</span>
                  </div>
                </div>
              </div>

              <div class="detail-action-bar">
                <ContentInteractionBar
                  target-type="DEMAND"
                  :target-id="selectedDemand.id"
                  :target-title="selectedDemand.title"
                  :like-count="selectedDemand.like_count ?? 0"
                  :favorite-count="selectedDemand.favorite_count ?? 0"
                  :love-count="selectedDemand.love_count ?? 0"
                  :comment-count="selectedDemand.comment_count ?? 0"
                  :dislike-count="selectedDemand.dislike_count ?? 0"
                  :rating-avg="selectedDemand.rating_avg ?? 0"
                  :rating-count="selectedDemand.rating_count ?? 0"
                  :my-rating="selectedDemand.viewer?.rating ?? 0"
                  :liked="selectedDemand.viewer?.liked ?? false"
                  :favorited="selectedDemand.viewer?.favorited ?? false"
                  :loved="selectedDemand.viewer?.loved ?? false"
                  :commented="selectedDemand.viewer?.commented ?? false"
                  :disliked="selectedDemand.viewer?.disliked ?? false"
                  :authenticated="Boolean(currentUserSession)"
                  show-labels
                  @changed="handleInteractionChanged(selectedDemand, $event)"
                  @require-login="$emit('open-login')"
                  @toast="$emit('toast', $event)"
                />
                <button class="action-btn action-btn-primary" @click="handleOpenBid(selectedDemand)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                  提交竞标方案
                </button>
                <span class="action-btn action-btn-muted">
                  <OpcIcon name="timer" :size="12" /> {{ formatDeadline(selectedDemand.deadline_at) }} 截止
                </span>
              </div>

              <div class="detail-body-scroll">
                <div class="detail-section">
                  <h4 class="section-title">委托详情</h4>
                  <p class="detail-full-description">{{ selectedDemand.description }}</p>
                </div>

                <div class="detail-section">
                  <h4 class="section-title">委托信息与规格</h4>
                  <div class="spec-grid">
                    <div class="spec-item">
                      <span class="spec-label">委托企业</span>
                      <span class="spec-value">{{ selectedDemand.creator_name || selectedDemand.creator_id || '@企业委托方' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">商机类别</span>
                      <span class="spec-value">{{ getCategoryLabel(selectedDemand.category) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">托管预算</span>
                      <span class="spec-value mono-val">¥{{ formatBudget(selectedDemand.budget_cny) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">竞标人数</span>
                      <span class="spec-value">{{ selectedDemand.bidders_count || 0 }} 人</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">发布时刻</span>
                      <span class="spec-value mono-val">{{ formatDate(selectedDemand.created_at) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">数据与持久化</span>
                      <span class="spec-value spec-success">PostgreSQL 库表持久存储</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Sentinel Anchor & Infinite Scroll Status -->
            <div v-if="sortedDisplayDemands.length > 0 && hasMore && !selectedDemand" ref="sentinelRef" class="feed-sentinel-anchor"></div>

            <!-- Loading Next Batch Spinner -->
            <div v-if="loadingMore && !selectedDemand" class="feed-stream-loading glass-box">
              <span class="loading-spinner"></span>
              <span>正在滚动加载更多企业委托与外包商机...</span>
            </div>

            <!-- Empty State -->
            <div v-else-if="!loading && sortedDisplayDemands.length === 0" class="glass-box empty-state-box">
              <div class="empty-icon-wrap">
                <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                  <path d="M16 21v-2a4 4 0 0 0-4-4"/><path d="M19 8v6"/><path d="M22 11h-6"/>
                </svg>
              </div>
              <h3 class="empty-title">当前分类下暂无在招企业委托</h3>
              <p class="empty-desc">
                {{ searchQuery ? `没有找到与 “${searchQuery}” 匹配的商机。` : '平台坚持代码与数据严格分离，数据库中尚未录入该分类商机。' }}
              </p>
              <div class="empty-actions">
                <button v-if="searchQuery" class="btn-liquid-outline" @click="searchQuery = ''; handleClearSearch()">
                  清除搜索条件
                </button>
                <button class="btn-liquid" @click="handleOpenPublish">
                  发布首个委托
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Right Auxiliary Sidebar: Exactly matching Product Showcase -->
        <aside class="demands-feed-sidebar">
          <!-- 1. Demand Publisher Center Card -->
          <div class="glass-box sidebar-card creator-center-card">
            <div class="creator-card-header">
              <div class="creator-icon-orb">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                </svg>
              </div>
              <div>
                <h4 class="creator-title">企业委托中心</h4>
                <p class="creator-desc">超级个体接单撮合与托管资金枢纽</p>
              </div>
            </div>
            <button class="btn-liquid btn-creator-publish" @click="handleOpenPublish">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span>发布新委托</span>
            </button>
            <div class="creator-quick-links">
              <span class="quick-pill" @click="selectCategory('DEV')">技术开发</span>
              <span class="quick-pill" @click="selectCategory('AI')">AI 智能体</span>
              <span class="quick-pill" @click="selectCategory('TAX')">财税合规</span>
              <span class="quick-pill" @click="selectCategory('LEGAL')">法律求助</span>
            </div>
          </div>

          <!-- 2. Today's Hot Demand Rank (今日商机热榜) -->
          <div class="glass-box sidebar-card hot-ranking-card">
            <div class="sidebar-card-title-row">
              <div class="title-with-icon">
                <span class="hot-badge-fire"><OpcIcon name="flame" :size="14" /></span>
                <h4 class="sidebar-title">今日商机热榜</h4>
              </div>
              <span class="hot-subtitle">实时更新</span>
            </div>

            <div class="hot-ranking-list">
              <div
                v-for="(item, idx) in hotRankDemands"
                :key="item.id"
                class="hot-rank-item"
                @click="openDemandDetail(item)"
              >
                <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                <div class="hot-item-content">
                  <h5 class="hot-item-title">{{ item.title }}</h5>
                  <div class="hot-item-meta">
                    <span><OpcIcon name="flame" :size="12" /> {{ (item.bidders_count || 0) * 3 + 42 }} 热度</span>
                    <span class="dot-sep">·</span>
                    <span>¥{{ formatBudget(item.budget_cny) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. Marketplace Guidelines Card -->
          <div class="glass-box sidebar-card guidelines-card">
            <h4 class="sidebar-title-sm">超级个体接单规范</h4>
            <p class="guidelines-desc">
              需求集市倡导<strong>「真实企业委托、资金托管保障、方案直达委托方」</strong>。所有竞标方案均通过合规审查并由平台托管交易资金。
            </p>
            <div class="guidelines-footer">
              <span>OpcHub 商机撮合协议 v1.0</span>
              <span class="dot-sep">·</span>
              <span class="link-span" @click="handleOpenPublish">发布委托</span>
            </div>
          </div>
        </aside>
      </div>
    </div>


    <!-- Demand Publish Modal -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="showPublishModal" class="modal-backdrop" @click="closePublishModal">
          <div class="modal-window glass-box publish-modal" @click.stop>
            <div class="modal-header">
              <div>
                <h2 class="modal-title">发布企业外包委托</h2>
                <p class="modal-subtitle">发布真实寻源需求至超级个体需求集市，资金由平台托管保障</p>
              </div>
              <button class="modal-close-btn" @click="closePublishModal"><OpcIcon name="close" :size="16" /></button>
            </div>

            <form class="publish-form" @submit.prevent="submitPublishDemand">
              <div class="form-group">
                <label class="form-label">委托标题 <span class="req">*</span></label>
                <input
                  v-model="publishForm.title"
                  type="text"
                  required
                  class="glass-input"
                  placeholder="如：外贸 CRM 系统的垂直行业 Agent 工作流搭建"
                />
              </div>

              <div class="form-group">
                <label class="form-label">详细需求说明 <span class="req">*</span></label>
                <textarea
                  v-model="publishForm.description"
                  required
                  rows="4"
                  class="glass-input"
                  placeholder="详细描述技术栈、交付物、验收标准与期望周期..."
                ></textarea>
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">商机类别</label>
                  <select v-model="publishForm.category" class="glass-input glass-select">
                    <option value="DEV">技术开发</option>
                    <option value="AI">AI 智能体</option>
                    <option value="TAX">财税合规</option>
                    <option value="LEGAL">法律求助</option>
                    <option value="BIZ">商业运营</option>
                  </select>
                </div>

                <div class="form-group flex-1">
                  <label class="form-label">托管预算 (¥)</label>
                  <input
                    v-model.number="publishForm.budget_cny"
                    type="number"
                    min="0"
                    step="100"
                    class="glass-input"
                    placeholder="35000"
                  />
                </div>

                <div class="form-group flex-1">
                  <label class="form-label">交付周期 (天)</label>
                  <input
                    v-model.number="publishForm.deadline_days"
                    type="number"
                    min="1"
                    max="365"
                    class="glass-input"
                    placeholder="14"
                  />
                </div>
              </div>

              <div class="modal-footer-actions">
                <button type="button" class="btn-liquid-outline submit-btn" @click="closePublishModal">取消</button>
                <button type="submit" class="btn-liquid submit-btn" :disabled="submitting">
                  {{ submitting ? '发布中...' : '确认发布委托' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Bid Submission Modal -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="bidTarget" class="modal-backdrop" @click="closeBidModal">
          <div class="modal-window glass-box publish-modal" @click.stop>
            <div class="modal-header">
              <div>
                <h2 class="modal-title">提交竞标方案</h2>
                <p class="modal-subtitle">{{ bidTarget.title }}</p>
              </div>
              <button class="modal-close-btn" @click="closeBidModal"><OpcIcon name="close" :size="16" /></button>
            </div>

            <form class="publish-form" @submit.prevent="submitBid">
              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">报价金额 (¥) <span class="req">*</span></label>
                  <input
                    v-model.number="bidForm.bid_amount_cny"
                    type="number"
                    min="0"
                    step="100"
                    required
                    class="glass-input"
                    placeholder="32000"
                  />
                </div>

                <div class="form-group flex-1">
                  <label class="form-label">交付周期 (天) <span class="req">*</span></label>
                  <input
                    v-model.number="bidForm.delivery_days"
                    type="number"
                    min="1"
                    max="365"
                    required
                    class="glass-input"
                    placeholder="14"
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">方案说明 <span class="req">*</span></label>
                <textarea
                  v-model="bidForm.proposal_text"
                  required
                  rows="5"
                  minlength="5"
                  class="glass-input"
                  placeholder="阐述技术方案、交付物清单与既往同类项目经验..."
                ></textarea>
              </div>

              <div class="modal-footer-actions">
                <button type="button" class="btn-liquid-outline submit-btn" @click="closeBidModal">取消</button>
                <button type="submit" class="btn-liquid submit-btn" :disabled="submitting">
                  {{ submitting ? '提交中...' : '确认提交竞标' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
import HoverRevealText from '@/components/HoverRevealText.vue';
import { enrichInteractions, applyBarChange } from '@/utils/contentInteractions';

const emit = defineEmits(['open-register', 'open-login', 'toast']);

function handleInteractionChanged(item, payload) {
  applyBarChange(item, payload);
}

// Current User Session
const currentUserSession = computed(() => {
  try {
    const raw = localStorage.getItem('opchub_user_session');
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return null;
});

// Paged & Infinite Scrolling States
const displayDemands = ref([]);
const currentPage = ref(1);
const pageSize = ref(8);
const hasMore = ref(true);
const totalCount = ref(0);
const loading = ref(false);
const loadingMore = ref(false);
const submitting = ref(false);
const isCacheHit = ref(false);

const searchQuery = ref('');
const isSearching = ref(false);
const isSearchActive = ref(false);
const activeSearchQuery = ref('');
const currentCategory = ref('ALL');
const selectedDemand = ref(null);
const showPublishModal = ref(false);
const bidTarget = ref(null);
const sentinelRef = ref(null);
const demandsScrollContainerRef = ref(null);
let observer = null;

// Sort options
const sortOptions = [
  { key: 'new', label: '最新发布', icon: 'bolt' },
  { key: 'budget', label: '预算最高', icon: 'coin' },
  { key: 'hot', label: '竞标最热', icon: 'flame' },
];
const currentSort = ref('new');

// Category Tabs Definition
const categoryList = [
  { key: 'ALL', label: '全部商机' },
  { key: 'DEV', label: '技术开发' },
  { key: 'AI', label: 'AI 智能体' },
  { key: 'TAX', label: '财税合规' },
  { key: 'LEGAL', label: '法律求助' },
  { key: 'BIZ', label: '商业运营' },
];

const CATEGORY_LABELS = {
  DEV: '技术开发',
  AI: 'AI 智能体',
  TAX: '财税合规',
  LEGAL: '法律求助',
  BIZ: '商业运营',
};

const CATEGORY_ICONS = {
  DEV: 'code',
  AI: 'robot',
  TAX: 'coin',
  LEGAL: 'scale',
  BIZ: 'briefcase',
};

const STATUS_LABELS = {
  OPEN: '公开招募中',
  BIDDING: '竞标中',
  CLOSED: '已截止',
};

const currentCategoryLabel = computed(() => {
  return categoryList.find((c) => c.key === currentCategory.value)?.label || '全部商机';
});

// Publish Form State
const publishForm = reactive({
  title: '',
  description: '',
  category: 'DEV',
  budget_cny: 0,
  deadline_days: 14,
});

// Bid Form State
const bidForm = reactive({
  bid_amount_cny: 0,
  delivery_days: 14,
  proposal_text: '',
});

// Client-side Memory Cache with TTL (60s)
const clientCache = new Map();
const CACHE_TTL_MS = 60 * 1000;

function getClientCache(key) {
  const entry = clientCache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    clientCache.delete(key);
    return null;
  }
  return entry.data;
}

function setClientCache(key, data) {
  clientCache.set(key, { data, timestamp: Date.now() });
}

function invalidateClientCache() {
  clientCache.clear();
}

function getCategoryLabel(category) {
  return CATEGORY_LABELS[category] || category || '企业委托';
}

function getCategoryIcon(category) {
  return CATEGORY_ICONS[category] || 'box';
}

function getStatusLabel(status) {
  return STATUS_LABELS[status] || status || '公开招募中';
}

function getStatusClass(status) {
  if (status === 'CLOSED') return 'pricing-freemium';
  if (status === 'BIDDING') return 'pricing-sub';
  return 'pricing-free';
}

function formatBudget(budget) {
  const num = Number(budget) || 0;
  return num.toLocaleString('zh-CN');
}

function formatDate(isoStr) {
  if (!isoStr) return '近期发布';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return '近期发布';
  }
}

function formatDateShort(isoStr) {
  if (!isoStr) return '近期';
  try {
    const diff = Date.now() - new Date(isoStr).getTime();
    if (isNaN(diff)) return '近期';
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return `${mins}分钟前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}小时前`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}天前`;
    return new Date(isoStr).toLocaleDateString('zh-CN');
  } catch {
    return '近期';
  }
}

function formatDeadline(isoStr) {
  if (!isoStr) return '待定';
  try {
    const diff = new Date(isoStr).getTime() - Date.now();
    if (isNaN(diff)) return '待定';
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    if (days < 0) return '已截止';
    if (days === 0) return '今日';
    return `${days} 天后`;
  } catch {
    return '待定';
  }
}

function getInitials(name) {
  if (!name) return '企';
  const clean = String(name).replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
  return clean.slice(0, 2).toUpperCase() || '企';
}

function getIconFallbackStyle(item) {
  return {
    background: 'linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--glass-border-subtle)',
  };
}

function getAuthorAvatarStyle(item) {
  return {
    background: 'linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--glass-border-subtle)',
  };
}

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  card.style.setProperty('--mouse-x', `${x}px`);
  card.style.setProperty('--mouse-y', `${y}px`);
}

function handleDemandsScroll(e) {
  const el = e.target;
  if (!el || !hasMore.value || loading.value || loadingMore.value || isSearchActive.value) return;
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 250) {
    fetchDemandsPage(currentPage.value + 1, true);
  }
}

function selectCategory(catKey) {
  if (currentCategory.value === catKey) return;
  currentCategory.value = catKey;
  if (demandsScrollContainerRef.value) {
    demandsScrollContainerRef.value.scrollTop = 0;
  }
  if (isSearchActive.value && searchQuery.value.trim()) {
    handleSearch();
  } else {
    resetAndReload();
  }
}

async function handleSearch() {
  const query = searchQuery.value.trim();
  if (!query) {
    handleClearSearch();
    return;
  }

  isSearching.value = true;
  try {
    const res = await dispatchGateway('demands.list', {
      category: currentCategory.value === 'ALL' ? null : currentCategory.value,
      search: query,
      page: 1,
      page_size: 100,
    });

    if (res.ok && res.data) {
      const items = Array.isArray(res.data.items) ? res.data.items : (Array.isArray(res.data) ? res.data : []);
      displayDemands.value = items;
      await enrichInteractions(items, 'DEMAND');
      totalCount.value = res.data.total !== undefined ? res.data.total : items.length;
      isSearchActive.value = true;
      activeSearchQuery.value = query;
      hasMore.value = false;
      emit('toast', {
        title: '搜索完成',
        message: `已为您找到 ${items.length} 条相关企业委托。`,
        type: 'SUCCESS',
      });
    } else {
      emit('toast', {
        title: '搜索未完成',
        message: res.error || '未能检索到匹配的商机，请稍后重试。',
        type: 'WARN',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '搜索异常',
      message: '商机检索服务暂时不可用，请稍后重试。',
      type: 'ERROR',
    });
  } finally {
    isSearching.value = false;
  }
}

function handleClearSearch() {
  searchQuery.value = '';
  activeSearchQuery.value = '';
  isSearchActive.value = false;
  invalidateClientCache();
  resetAndReload();
}

// Core Paged Fetcher with Multi-layer Caching (Client Memory + Server Invalidation)
async function fetchDemandsPage(page, isAppend = false) {
  const catParam = currentCategory.value === 'ALL' ? null : currentCategory.value;
  const searchParam = searchQuery.value.trim() || null;
  const cacheKey = `${catParam || 'ALL'}_${searchParam || ''}_${page}_${pageSize.value}`;

  // 1. Check client memory cache
  const cachedData = getClientCache(cacheKey);
  if (cachedData) {
    isCacheHit.value = true;
    applyPageData(cachedData, isAppend);
    return;
  }

  // 2. Network request via gateway
  if (isAppend) {
    loadingMore.value = true;
  } else {
    loading.value = true;
  }

  try {
    const res = await dispatchGateway('demands.list', {
      category: catParam,
      search: searchParam,
      page,
      page_size: pageSize.value,
    });

    if (res.ok && res.data) {
      const pagedData = res.data;
      isCacheHit.value = Boolean(pagedData.from_cache);
      setClientCache(cacheKey, pagedData);
      applyPageData(pagedData, isAppend);
    } else {
      if (!isAppend) {
        displayDemands.value = [];
        totalCount.value = 0;
        hasMore.value = false;
      }
    }
  } catch (e) {
    console.error('Failed to load demands page:', e);
    if (!isAppend) {
      displayDemands.value = [];
      hasMore.value = false;
    }
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function applyPageData(pagedData, isAppend) {
  const items = pagedData.items || [];
  if (isAppend) {
    const existingIds = new Set(displayDemands.value.map((d) => d.id));
    for (const item of items) {
      if (!existingIds.has(item.id)) {
        displayDemands.value.push(item);
      }
    }
  } else {
    displayDemands.value = items;
  }
  enrichInteractions(items, 'DEMAND');
  currentPage.value = pagedData.page || 1;
  hasMore.value = Boolean(pagedData.has_more);
  totalCount.value = pagedData.total !== undefined ? pagedData.total : displayDemands.value.length;
}

// Reset and reload first page
function resetAndReload() {
  currentPage.value = 1;
  hasMore.value = true;
  fetchDemandsPage(1, false);
}

// Manual Refresh
function handleManualRefresh() {
  invalidateClientCache();
  isCacheHit.value = false;
  resetAndReload();
  emit('toast', { title: '缓存已刷新', message: '已同步最新数据库企业委托与竞标热榜。', type: 'INFO' });
}

// Watch filters to trigger reload
watch(currentCategory, () => {
  if (!isSearchActive.value) {
    resetAndReload();
  }
});

// Sorted & Filtered Demands Display
const sortedDisplayDemands = computed(() => {
  const list = [...displayDemands.value];

  if (isSearchActive.value) {
    return list;
  }

  if (currentSort.value === 'hot') {
    list.sort((a, b) => (b.bidders_count || 0) - (a.bidders_count || 0));
  } else if (currentSort.value === 'budget') {
    list.sort((a, b) => (b.budget_cny || 0) - (a.budget_cny || 0));
  } else {
    list.sort((a, b) => {
      const tA = new Date(a.created_at || 0).getTime();
      const tB = new Date(b.created_at || 0).getTime();
      return tB - tA;
    });
  }
  return list;
});

const hotRankDemands = computed(() => {
  return [...displayDemands.value]
    .sort((a, b) => (b.bidders_count || 0) - (a.bidders_count || 0))
    .slice(0, 5);
});

// Setup native IntersectionObserver for infinite scrolling
function setupIntersectionObserver() {
  if (observer) {
    observer.disconnect();
  }
  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0];
      if (entry && entry.isIntersecting) {
        if (!isSearchActive.value && hasMore.value && !loading.value && !loadingMore.value && displayDemands.value.length > 0) {
          fetchDemandsPage(currentPage.value + 1, true);
        }
      }
    },
    {
      root: demandsScrollContainerRef.value || null,
      rootMargin: '180px',
    }
  );

  if (sentinelRef.value) {
    observer.observe(sentinelRef.value);
  }
}

// Modal controls
function openDemandDetail(item) {
  selectedDemand.value = item;
}

function closeDemandDetail() {
  selectedDemand.value = null;
}

function handleOpenPublish() {
  if (!currentUserSession.value) {
    emit('toast', {
      title: '需创客准入',
      message: '发布企业委托需先登录或入驻平台创客账号！',
      type: 'INFO',
    });
    emit('open-login');
    return;
  }
  showPublishModal.value = true;
}

function closePublishModal() {
  showPublishModal.value = false;
}

async function submitPublishDemand() {
  if (!publishForm.title || !publishForm.description) {
    emit('toast', { title: '信息不全', message: '请完整填写委托标题与详细需求说明！', type: 'WARN' });
    return;
  }

  submitting.value = true;
  try {
    const payload = {
      title: publishForm.title.trim(),
      description: publishForm.description.trim(),
      category: publishForm.category,
      budget_cny: Number(publishForm.budget_cny) || 0,
      deadline_days: Number(publishForm.deadline_days) || 14,
      creator_id: currentUserSession.value?.uid || 'usr_maker',
      creator_name: currentUserSession.value?.nickname || currentUserSession.value?.username || '@企业委托方',
    };

    const res = await dispatchGateway('demands.publish', payload);
    if (res.ok) {
      emit('toast', {
        title: '发布成功',
        message: `企业委托《${payload.title}》已成功收录入库并向超级个体公开！`,
        type: 'SUCCESS',
      });
      closePublishModal();
      publishForm.title = '';
      publishForm.description = '';
      publishForm.budget_cny = 0;
      publishForm.deadline_days = 14;
      invalidateClientCache();
      resetAndReload();
    } else {
      emit('toast', {
        title: '发布受阻',
        message: res.error || '企业委托发布未成功，请稍后重试。',
        type: 'ERROR',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '发布异常',
      message: '企业委托发布服务暂时不可用，请稍后重试。',
      type: 'ERROR',
    });
  } finally {
    submitting.value = false;
  }
}

function handleOpenBid(item) {
  if (!currentUserSession.value) {
    emit('toast', {
      title: '需创客准入',
      message: '参与商机竞标需先登录或入驻平台创客账号！',
      type: 'INFO',
    });
    emit('open-login');
    return;
  }
  bidTarget.value = item;
  bidForm.bid_amount_cny = Number(item.budget_cny) || 0;
  bidForm.delivery_days = 14;
  bidForm.proposal_text = '';
}

function closeBidModal() {
  bidTarget.value = null;
}

async function submitBid() {
  if (!bidTarget.value) return;
  if (!bidForm.proposal_text || bidForm.proposal_text.trim().length < 5) {
    emit('toast', { title: '信息不全', message: '请填写至少 5 个字的竞标方案说明！', type: 'WARN' });
    return;
  }

  submitting.value = true;
  try {
    const res = await dispatchGateway('demands.bid', {
      demand_id: bidTarget.value.id,
      bidder_id: currentUserSession.value?.uid || 'usr_maker',
      bid_amount_cny: Number(bidForm.bid_amount_cny) || 0,
      delivery_days: Number(bidForm.delivery_days) || 14,
      proposal_text: bidForm.proposal_text.trim(),
    });

    if (res.ok) {
      emit('toast', {
        title: '竞标提交成功',
        message: `您对《${bidTarget.value.title}》的商务报价与技术案已直达委托发起人！`,
        type: 'SUCCESS',
      });
      closeBidModal();
      invalidateClientCache();
      resetAndReload();
    } else {
      emit('toast', {
        title: '竞标受阻',
        message: res.error || '竞标方案提交未成功，请稍后重试。',
        type: 'ERROR',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '竞标异常',
      message: '竞标服务暂时不可用，请稍后重试。',
      type: 'ERROR',
    });
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  document.body.classList.add('fixed-screen-feed');
  fetchDemandsPage(1, false);
  nextTick(() => {
    setupIntersectionObserver();
  });
});

onUnmounted(() => {
  document.body.classList.remove('fixed-screen-feed');
  if (observer) {
    observer.disconnect();
  }
});
</script>

<style scoped>
.demands-view-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.demands-main-content {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

/* Dual-Column Feed Layout identical to Product Showcase */
.demands-feed-layout {
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

.demands-feed-stream {
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

/* 滚动容器由全局 .opc-cards-scroll 承载 */

/* Right Auxiliary Sidebar: Exactly matching Product Showcase */
.demands-feed-sidebar {
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

.demands-feed-sidebar::-webkit-scrollbar {
  display: none;
}

.refresh-mini-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: var(--radius-full);
}

/* 2. Category Filter Bar */
.feed-filter-bar {
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
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.35);
}

.semantic-search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Search Status Banner */
.semantic-search-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
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
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
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
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;
}

.sort-pill:hover {
  color: var(--text-primary);
}

.sort-pill.active {
  background: var(--glass-surface);
  color: var(--accent);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

/* 3. Demand Cards Container: 以卡片为主！ */
/* 卡片网格与外壳：由全局统一卡片体系 (.opc-cards-grid / .opc-card-shell) 承载 */

/* Card Header: 图标 tile 专属样式 */
.app-icon-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 19px;
  letter-spacing: -0.02em;
}

.demand-title {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.demand-status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.badge-pricing {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

.pricing-free,
.pricing-freemium,
.pricing-sub,
.pricing-onetime {
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.badge-semantic-score {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  background: var(--accent-glass);
  color: var(--accent);
  border: 1px solid var(--glass-border-subtle);
}

.product-desc-snippet {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.demand-desc-snippet {
  -webkit-line-clamp: 3;
}

/* Highlights chips 专属色（基础 .highlight-chip 由全局承载） */
.chip-escrow {
  color: var(--text-secondary);
}

.chip-deadline {
  color: var(--text-secondary);
}

.chip-storage {
  color: var(--accent);
}

/* Card Footer: 全局统一 (.card-footer-row / .author-* / .card-actions-cell / .card-interaction-row) */
.author-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10.5px;
  font-weight: 700;
  flex-shrink: 0;
}

.demand-bidder-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 11.5px;
  font-weight: 600;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-secondary);
}

.btn-bid-sm {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.btn-detail-sm {
  padding: 4px 12px;
  font-size: 11.5px;
  font-weight: 500;
  border-radius: var(--radius-full);
}

/* 4. Stream Banners & Sentinels */
.posts-loading-banner,
.feed-stream-loading,
.feed-stream-end {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 20px;
  border-radius: var(--radius-md, 12px);
  font-size: 12.5px;
  color: var(--text-tertiary);
  text-align: center;
}

.feed-sentinel-anchor {
  width: 100%;
  height: 2px;
  opacity: 0;
  pointer-events: none;
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

/* 5. Empty State */
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

/* ---------------- Right Auxiliary Sidebar ---------------- */
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

/* Sidebar 1: Publisher Center Card */
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

/* Sidebar 2: Hot Ranking Card */
.sidebar-card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
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
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.hot-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
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
  padding: 5px 8px;
  border-radius: 8px;
  transition: background 0.18s ease;
}

.hot-rank-item:hover {
  background: rgba(0, 113, 227, 0.06);
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

.rank-1 { color: var(--text-primary); font-weight: 700; }
.rank-2 { color: var(--text-secondary); }
.rank-3 { color: var(--text-tertiary); }

.hot-item-content {
  flex: 1;
  min-width: 0;
}

.hot-item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.45;
  margin: 0 0 3px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.18s ease;
}

.hot-rank-item:hover .hot-item-title {
  color: var(--accent);
}

.hot-item-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot-sep {
  opacity: 0.5;
}

/* Sidebar 3: Guidelines Card */
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

.link-span {
  color: var(--accent);
  cursor: pointer;
}

.link-span:hover {
  text-decoration: underline;
}

/* ---------------- Detail Modal ---------------- */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
  box-sizing: border-box;
}

.product-detail-modal {
  width: 100%;
  max-width: 680px;
  max-height: 85vh;
  border-radius: var(--radius-xl, 24px);
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  box-sizing: border-box;
  overflow: hidden;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.95));
  border: 1px solid var(--glass-border);
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
}

.detail-icon-fallback {
  width: 100%;
  height: 100%;
  font-size: 26px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
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
  color: var(--text-primary);
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
.detail-pricing-pill {
  font-size: 11.5px;
  padding: 2px 9px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.detail-pricing-pill {
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-glass);
}

.modal-close-btn {
  border: none;
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.modal-close-btn:hover {
  background: var(--glass-surface-hover);
  color: var(--text-primary);
}

.detail-action-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-full);
  text-decoration: none;
  cursor: pointer;
}

.action-btn-primary {
  background: var(--accent, #0071E3);
  color: #ffffff;
  border: none;
}

.action-btn-muted {
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.detail-body-scroll {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-right: 4px;
}

/* ---------------- Inline Detail (content area, no modal) ---------------- */
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

.inline-detail-slot .detail-body-scroll {
  overflow: visible;
  max-height: none;
  padding-right: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 10px 0;
}

.detail-full-description {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.65;
  margin: 0;
  white-space: pre-wrap;
}

.spec-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px 16px;
  background: var(--glass-surface-subtle);
  padding: 14px 18px;
  border-radius: var(--radius-md);
  border: 1px solid var(--glass-border-subtle);
}

.spec-item {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
}

.spec-label {
  color: var(--text-tertiary);
}

.spec-value {
  color: var(--text-primary);
  font-weight: 500;
}

.mono-val {
  font-family: var(--font-mono, monospace);
}

.spec-success {
  color: var(--status-success);
}

/* ---------------- Publish / Bid Modal ---------------- */
.publish-modal {
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  border-radius: var(--radius-xl, 24px);
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  box-sizing: border-box;
  overflow-y: auto;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.95));
  border: 1px solid var(--glass-border);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.modal-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 4px 0;
}

.modal-subtitle {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin: 0;
}

.publish-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.flex-1 { flex: 1; }
.flex-2 { flex: 2; }

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.req {
  color: var(--status-danger);
}

.glass-input {
  width: 100%;
  padding: 9px 12px;
  border-radius: var(--radius-sm, 10px);
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  color: var(--text-primary);
  font-size: 13px;
  box-sizing: border-box;
  outline: none;
  transition: all 0.2s ease;
}

.glass-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 8px var(--accent-glow);
  background: var(--glass-surface);
}

.glass-select {
  cursor: pointer;
}

.modal-footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}

.submit-btn {
  padding: 8px 20px;
  font-size: 13.5px;
  font-weight: 600;
  border-radius: var(--radius-full);
}

/* Modal Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* Responsive adjustments */
@media (max-width: 960px) {
  .demands-feed-layout {
    flex-direction: column;
  }
  .demands-feed-sidebar {
    width: 100%;
    position: static;
    max-height: none;
  }
  .opc-cards-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .feed-filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
  .feed-filter-right {
    justify-content: space-between;
  }
}

/* Dark Mode Theme Adjustments */
[data-theme="dark"] .sidebar-card,
[data-theme="dark"] .demands-demand-card,
[data-theme="dark"] .feed-filter-bar {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .product-detail-modal,
[data-theme="dark"] .publish-modal {
  background: rgba(24, 27, 34, 0.95);
  border-color: rgba(255, 255, 255, 0.12);
}

[data-theme="dark"] .quick-pill {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

[data-theme="dark"] .hot-rank-item:hover {
  background: rgba(0, 113, 227, 0.14);
}
</style>
