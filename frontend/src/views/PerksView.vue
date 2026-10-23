<template>
  <div class="view-panel active perks-view-wrapper">
    <div class="perks-main-content">
      <!-- Dual-column Layout referencing PolicyView (政策中心) -->
      <div class="perks-feed-layout">
        <!-- Main Perks Stream (左侧优惠公告流) -->
        <section class="perks-feed-stream">
          <!-- Category Filter Bar (公告分区选项卡 + 搜索 + 排序选择 + 刷新) -->
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
                <span v-else-if="cat.key !== 'ALL' && getCategoryCount(cat.key) > 0" class="cat-pill-count">
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
                    placeholder="搜索优惠公告..."
                    @keydown.enter="handleSearch"
                  />
                  <button v-if="searchQuery" type="button" class="clear-search-btn" @click="resetSearch" title="清空搜索">×</button>
                </div>
                <button
                  type="button"
                  class="btn-liquid semantic-search-btn"
                  :disabled="isSearching"
                  @click="handleSearch"
                  title="检索优惠公告"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                  <span>{{ isSearching ? '检索中...' : '搜索' }}</span>
                </button>
              </div>

              <!-- Sort Segmented -->
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

              <!-- Refresh Button -->
              <button class="btn-liquid-outline refresh-mini-btn" @click="handleManualRefresh" title="刷新并同步优惠公告">
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
              <span class="sparkle-badge"><OpcIcon name="search" :size="13" /> 检索结果</span>
              <span class="banner-text">
                已为您找到与「<strong>{{ activeSearchQuery }}</strong>」相关的 <strong>{{ sortedDisplayPerks.length }}</strong> 条生态优惠公告
              </span>
            </div>
            <button class="btn-liquid-outline btn-reset-search" @click="resetSearch">
              <span>恢复全部公告</span>
            </button>
          </div>

          <!-- Perks Cards Scroll Container -->
          <div class="opc-cards-scroll" ref="perksScrollContainerRef">
            <!-- Loading State Indicator -->
            <div v-if="isLoading && displayPerks.length === 0" class="posts-loading-banner glass-box">
              <span class="loading-spinner"></span>
              <span>正在从网关加载「{{ currentCategoryLabel }}」生态优惠公告...</span>
            </div>

            <!-- Perks Cards Grid (政策中心同款卡片流) -->
            <div
              v-if="sortedDisplayPerks.length > 0 && !selectedPerk"
              class="perks-cards-container opc-cards-grid"
              id="perksCardsGrid"
            >
              <div
                v-for="item in sortedDisplayPerks"
                :key="item.id"
                class="glass-card perk-card opc-card-shell opc-card opc-reveal-host"
                @mousemove="handleMouseMove"
                @click="openPerkDetail(item)"
              >
                <!-- Card Header: Category Emblem & Title Group -->
                <div class="card-header-row">
                  <div class="perk-icon-wrapper opc-card-icon" :class="getCategoryEmblemClass(item.category)">
                    <span class="perk-emblem-icon"><OpcIcon :name="getCategoryEmblemIcon(item.category)" :size="20" /></span>
                  </div>

                  <div class="card-title-group">
                    <div class="card-title-line">
                      <h3 class="perk-title opc-clamp opc-clamp-2" :title="item.name">{{ item.name }}</h3>
                    </div>
                    <div class="card-badges-line">
                      <span class="badge-cat" :class="getCategoryBadgeClass(item.category)">
                        {{ formatCategoryLabel(item.category) }}
                      </span>
                      <span v-if="item.priority >= PERK_FEATURED_PRIORITY" class="badge-featured"><OpcIcon name="flame" :size="12" /> 热荐</span>
                      <span class="badge-provider">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                        </svg>
                        {{ item.provider }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Card Body: Plain Chinese Summary (hover reveals full) -->
                <div class="card-body">
                  <HoverRevealText :text="item.summary" :lines="2" />
                </div>

                <!-- Card Highlights / Quick Spec Chips -->
                <div class="card-highlights-row">
                  <span class="highlight-chip chip-value">
                    <OpcIcon name="coin" :size="12" /> {{ formatValue(item.value_cny) }}
                  </span>
                  <span class="highlight-chip chip-validity">
                    <OpcIcon name="calendar" :size="12" /> {{ validityText(item) }}
                  </span>
                  <span v-if="item.quota_remaining > 0" class="highlight-chip chip-quota">
                    <OpcIcon name="ticket" :size="12" /> 余量 {{ item.quota_remaining }}
                  </span>
                </div>

                <!-- Card Footer: Provider & Action Buttons -->
                <div class="card-footer-row" @click.stop>
                  <div class="issuer-cell">
                    <div class="issuer-avatar">
                      <OpcIcon name="gift" :size="18" />
                    </div>
                    <div class="issuer-text">
                      <span class="issuer-name">{{ item.provider }}</span>
                      <span class="issuer-level-tag">{{ item.redeem_url ? '生态伙伴直达' : '生态伙伴公告' }}</span>
                    </div>
                  </div>

                  <div class="card-actions-cell">
                    <button
                      type="button"
                      class="btn-liquid-outline btn-go"
                      @click.stop="openPerkUrl(item)"
                      title="跳转服务商领取"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                      </svg>
                      <span>前往领取</span>
                    </button>

                    <button
                      type="button"
                      class="btn-liquid btn-detail"
                      @click.stop="openPerkDetail(item)"
                      title="查看优惠公告详情"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      <span>查看详情</span>
                    </button>
                  </div>
                </div>

                <!-- Card Interaction Band (unified like/comment/love/favorite) -->
                <div class="card-interaction-row" @click.stop>
                  <ContentInteractionBar
                    target-type="PERK"
                    :target-id="item.id"
                    :target-title="item.name"
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

            <!-- Inline Perk Detail (content area, no modal) -->
            <div v-if="selectedPerk" class="inline-detail-slot glass-box">
              <div class="inline-detail-head">
                <button type="button" class="btn-back-inline" @click="closePerkDetail" title="返回公告列表">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                  </svg>
                  <span>返回公告列表</span>
                </button>
                <span class="inline-detail-crumb">生态特权 / {{ selectedPerk.name }}</span>
              </div>

              <div class="detail-header">
                <div class="detail-icon-wrap" :class="getCategoryEmblemClass(selectedPerk.category)">
                  <span class="detail-emblem-icon"><OpcIcon :name="getCategoryEmblemIcon(selectedPerk.category)" :size="24" /></span>
                </div>

                <div class="detail-title-block">
                  <div class="detail-title-row">
                    <h2 class="detail-title">{{ selectedPerk.name }}</h2>
                    <span class="mono-tag version-pill">{{ selectedPerk.id }}</span>
                  </div>
                  <p class="detail-tagline">{{ selectedPerk.summary }}</p>
                  <div class="detail-meta-pills">
                    <span class="detail-cat-pill">{{ formatCategoryLabel(selectedPerk.category) }}</span>
                    <span class="detail-provider-pill">{{ selectedPerk.provider }}</span>
                    <span class="detail-value-pill">{{ formatValue(selectedPerk.value_cny) }}</span>
                    <span class="detail-validity-pill"><OpcIcon name="calendar" :size="12" /> {{ validityText(selectedPerk) }}</span>
                  </div>
                </div>
              </div>

              <div class="detail-action-bar">
                <button
                  v-if="selectedPerk.redeem_url"
                  type="button"
                  class="btn-liquid action-btn primary-action"
                  @click="openPerkUrl(selectedPerk)"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                  </svg>
                  <span>前往服务商领取</span>
                </button>

                <ContentInteractionBar
                  target-type="PERK"
                  :target-id="selectedPerk.id"
                  :target-title="selectedPerk.name"
                  :like-count="selectedPerk.like_count ?? 0"
                  :favorite-count="selectedPerk.favorite_count ?? 0"
                  :love-count="selectedPerk.love_count ?? 0"
                  :comment-count="selectedPerk.comment_count ?? 0"
                  :dislike-count="selectedPerk.dislike_count ?? 0"
                  :rating-avg="selectedPerk.rating_avg ?? 0"
                  :rating-count="selectedPerk.rating_count ?? 0"
                  :my-rating="selectedPerk.viewer?.rating ?? 0"
                  :liked="selectedPerk.viewer?.liked ?? false"
                  :favorited="selectedPerk.viewer?.favorited ?? false"
                  :loved="selectedPerk.viewer?.loved ?? false"
                  :commented="selectedPerk.viewer?.commented ?? false"
                  :disliked="selectedPerk.viewer?.disliked ?? false"
                  :authenticated="Boolean(currentUserSession)"
                  show-labels
                  @changed="handleInteractionChanged(selectedPerk, $event)"
                  @require-login="$emit('open-login')"
                  @toast="$emit('toast', $event)"
                />

                <div class="legal-badge-pill" :title="selectedPerk.redeem_url || '公告直达'">
                  <span><OpcIcon name="gift" :size="12" /> {{ selectedPerk.provider }} · 生态伙伴直供</span>
                </div>
              </div>

              <div class="detail-body-scroll">
                <div class="detail-section">
                  <h4 class="section-title">优惠核心白话要点</h4>
                  <p class="detail-full-description">{{ selectedPerk.summary }}</p>
                </div>

                <div v-if="selectedPerk.highlights && selectedPerk.highlights.length > 0" class="detail-section">
                  <h4 class="section-title">核心卖点</h4>
                  <div class="conditions-checklist">
                    <div
                      v-for="(h, idx) in selectedPerk.highlights"
                      :key="idx"
                      class="condition-check-item"
                    >
                      <span class="check-icon"><OpcIcon name="check" :size="13" /></span>
                      <span class="check-text">{{ h }}</span>
                    </div>
                  </div>
                </div>

                <div class="detail-section">
                  <h4 class="section-title">优惠规格详情</h4>
                  <div class="spec-grid">
                    <div class="spec-item">
                      <span class="spec-label">公告编号</span>
                      <span class="spec-value mono-val">{{ selectedPerk.id }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">服务商</span>
                      <span class="spec-value">{{ selectedPerk.provider }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">优惠类别</span>
                      <span class="spec-value">{{ formatCategoryLabel(selectedPerk.category) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">预估价值</span>
                      <span class="spec-value spec-highlight">{{ formatValue(selectedPerk.value_cny) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">生效时间</span>
                      <span class="spec-value mono-val">{{ selectedPerk.effective_start || '长期有效' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">截止时间</span>
                      <span class="spec-value mono-val">{{ selectedPerk.effective_end || '暂无明确截止' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">领取配额</span>
                      <span class="spec-value">{{ selectedPerk.quota_remaining > 0 ? `剩余 ${selectedPerk.quota_remaining} 份` : '已领完' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">直达链接</span>
                      <span class="spec-value">{{ selectedPerk.redeem_url || '暂未开放线上直达' }}</span>
                    </div>
                    <div class="spec-item" style="grid-column: span 2;">
                      <span class="spec-label">微内核数据校验</span>
                      <span class="spec-value spec-success">PostgreSQL 公告库持久化 & 微内核发布门禁校验</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else-if="!isLoading && sortedDisplayPerks.length === 0" class="glass-box empty-state-box">
              <div class="empty-icon-wrap">
                <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                </svg>
              </div>
              <h3 class="empty-title">当前筛选下暂无优惠公告</h3>
              <p class="empty-desc">
                {{ searchQuery ? `没有检索到与 “${searchQuery}” 匹配的生态优惠公告。` : '当前分类下暂无已上架的优惠公告。' }}
              </p>
              <div class="empty-actions">
                <button v-if="searchQuery || currentCategory !== 'ALL'" class="btn-liquid-outline" @click="resetSearch">
                  重置筛选条件
                </button>
                <button class="btn-liquid" @click="openPublishModal">
                  提报优惠公告
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Right Auxiliary Sidebar: matching PolicyView -->
        <aside class="perks-feed-sidebar">
          <!-- 1. Perks Center Card (公告与提报中心) -->
          <div class="glass-box sidebar-card creator-center-card">
            <div class="creator-card-header">
              <div class="creator-icon-orb">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>
              </div>
              <div>
                <h4 class="creator-title">生态优惠公告中心</h4>
                <p class="creator-desc">Token · 服务器 · SaaS 生态特权速递</p>
              </div>
            </div>

            <button class="btn-liquid btn-creator-publish" @click="openPublishModal">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span>提报优惠公告</span>
            </button>

            <div class="creator-quick-links">
              <span
                v-for="cat in quickLinkCategories"
                :key="cat.key"
                class="quick-pill"
                @click="selectCategory(cat.key)"
              >{{ cat.label }}</span>
            </div>
          </div>

          <!-- 2. Perks Overview Card (公告统计速览) -->
          <div class="glass-box sidebar-card overview-card">
            <div class="sidebar-card-title-row">
              <div class="title-with-icon">
                <span class="hot-badge-fire"><OpcIcon name="target" :size="14" /></span>
                <h4 class="sidebar-title">公告统计速览</h4>
              </div>
              <span class="hot-subtitle">生态联盟</span>
            </div>

            <div class="overview-stat-grid">
              <div class="overview-stat-item">
                <span class="overview-stat-value">{{ totalCount }}</span>
                <span class="overview-stat-label">在架公告</span>
              </div>
              <div class="overview-stat-item">
                <span class="overview-stat-value">{{ coveredCategoryCount }}</span>
                <span class="overview-stat-label">覆盖分类</span>
              </div>
              <div class="overview-stat-item">
                <span class="overview-stat-value">{{ maxValueText }}</span>
                <span class="overview-stat-label">单条最高价值</span>
              </div>
            </div>

            <p class="calc-card-desc">
              本页为生态伙伴优惠公告板，仅收录<strong>优惠资讯</strong>，不含任何会员等级体系；
              领取资格与使用规则以各服务商官方页面为准。
            </p>
          </div>

          <!-- 3. Disclaimer Card (免责声明) -->
          <div class="glass-box sidebar-card guidelines-card">
            <h4 class="sidebar-title-sm">免责声明</h4>
            <p class="guidelines-desc">
              生态特权页面所展示的优惠公告均由生态伙伴提报，<strong>平台仅作信息聚合与展示，不构成任何承诺或担保</strong>。
              优惠力度、适用范围、有效期与领取资格均以各服务商官方页面及规则为准；因第三方调整、变更或下架导致的差异，平台不承担相关责任。
            </p>
            <div class="guidelines-footer">
              <span>OpcHub · 生态特权免责声明 v1.0</span>
              <span class="dot-sep">·</span>
              <span>2026</span>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- Perks Publish Modal (PolicyView style form) -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="showPublishModal" class="modal-backdrop" @click="closePublishModal">
          <div class="modal-window glass-box perks-publish-modal" @click.stop>
            <div class="modal-header">
              <div>
                <h2 class="modal-title">提报与发布生态优惠公告</h2>
                <p class="modal-subtitle">写入 PostgreSQL 公告主表，经微内核发布门禁与内容合规审查后上架公告板</p>
              </div>
              <button class="modal-close-btn" @click="closePublishModal"><OpcIcon name="close" :size="16" /></button>
            </div>

            <form class="publish-form" @submit.prevent="submitPublishPerk">
              <div class="form-group">
                <label class="form-label">公告标题 <span class="req">*</span></label>
                <input
                  v-model="publishForm.name"
                  type="text"
                  required
                  class="glass-input"
                  placeholder="如：火山方舟 豆包大模型 Token 畅用券"
                />
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">服务商 <span class="req">*</span></label>
                  <input
                    v-model="publishForm.provider"
                    type="text"
                    required
                    class="glass-input"
                    placeholder="如：火山引擎方舟 / 阿里云"
                  />
                </div>
                <div class="form-group flex-1">
                  <label class="form-label">优惠类别</label>
                  <select v-model="publishForm.category" class="glass-input glass-select">
                    <option
                      v-for="cat in PERK_CATEGORY_ORDER"
                      :key="cat.key"
                      :value="cat.key"
                    >{{ cat.key }} ({{ cat.label }})</option>
                  </select>
                </div>
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">预估价值 (元)</label>
                  <input
                    v-model.number="publishForm.value_cny"
                    type="number"
                    min="0"
                    class="glass-input"
                    placeholder="0"
                  />
                </div>
                <div class="form-group flex-1">
                  <label class="form-label">领取配额</label>
                  <input
                    v-model.number="publishForm.quota_remaining"
                    type="number"
                    min="1"
                    class="glass-input"
                    placeholder="100"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">生效时间</label>
                  <input
                    v-model="publishForm.effective_start"
                    type="date"
                    class="glass-input"
                  />
                </div>
                <div class="form-group flex-1">
                  <label class="form-label">截止时间</label>
                  <input
                    v-model="publishForm.effective_end"
                    type="date"
                    class="glass-input"
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">领取 / 详情直达链接</label>
                <input
                  v-model="publishForm.redeem_url"
                  type="url"
                  class="glass-input"
                  placeholder="如：https://console.volcengine.com/ark"
                />
              </div>

              <div class="form-group">
                <label class="form-label">公告摘要 <span class="req">*</span></label>
                <textarea
                  v-model="publishForm.summary"
                  required
                  rows="3"
                  class="glass-input"
                  placeholder="【白话要点】简明扼要说明优惠力度、适用范围与限制条件..."
                ></textarea>
              </div>

              <div class="form-group">
                <label class="form-label">核心卖点 (以逗号分隔)</label>
                <input
                  v-model="publishForm.highlightsText"
                  type="text"
                  class="glass-input"
                  placeholder="如：豆包 doubao-pro 全系可用, 抵扣额度 ¥5,000, 新老创客均可领取"
                />
              </div>

              <div class="form-actions">
                <button type="button" class="btn-liquid-outline" @click="closePublishModal">取消</button>
                <button type="submit" class="btn-liquid" :disabled="isPublishing">
                  {{ isPublishing ? '提交上架中...' : '确认发布上架' }}
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
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
import HoverRevealText from '@/components/HoverRevealText.vue';
import { enrichInteractions, applyBarChange } from '@/utils/contentInteractions';
import {
  PERK_CATEGORIES,
  PERK_CATEGORY_ORDER,
  PERK_FEATURED_PRIORITY,
  PERK_SORT_OPTIONS,
  PERK_STATUSES,
  PERK_PUBLISH_DEFAULT_PRIORITY,
  PERK_PUBLISH_DEFAULT_QUOTA,
} from '@/config/ecosystemPerks';

const emit = defineEmits(['toast', 'open-login']);

const props = defineProps({
  userSession: { type: Object, default: null },
});

const currentUserSession = computed(() => {
  if (props.userSession) return props.userSession;
  try {
    const raw = localStorage.getItem('opchub_user_session');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
});

function handleInteractionChanged(item, payload) {
  applyBarChange(item, payload);
}

// Perks raw list from gateway (公告库)
const perks = ref([]);
const isLoading = ref(false);
const isSearching = ref(false);
const isSearchActive = ref(false);
const activeSearchQuery = ref('');
const searchQuery = ref('');

// Category & Sorting
const currentCategory = ref('ALL');
const currentSort = ref('relevance');

// 分类与排序配置统一来自 frontend/src/config/ecosystemPerks.js（代码/配置分离）
const categoryList = computed(() => [
  { key: 'ALL', label: '全部公告' },
  ...PERK_CATEGORY_ORDER.map((c) => ({ key: c.key, label: c.label })),
]);

// 侧栏快捷筛选：排除兜底分类 OTHER
const quickLinkCategories = computed(() =>
  PERK_CATEGORY_ORDER.filter((c) => c.key !== 'OTHER').map((c) => ({ key: c.key, label: c.label }))
);

const sortOptions = PERK_SORT_OPTIONS;

// Lifecycle: lock body scroll to feed like PolicyView & ShowcaseView
onMounted(() => {
  document.body.classList.add('fixed-screen-feed');
  loadPerks();
});

onUnmounted(() => {
  document.body.classList.remove('fixed-screen-feed');
});

// Load perks from gateway
async function loadPerks() {
  isLoading.value = true;
  try {
    const res = await dispatchGateway('perks.list', {});
    if (res.ok && Array.isArray(res.data)) {
      perks.value = res.data;
      await enrichInteractions(perks.value, 'PERK');
    } else {
      perks.value = [];
      emit('toast', {
        title: '公告加载未完成',
        message: res.error || '未能从网关获取生态优惠公告，请稍后重试。',
        type: 'WARN',
      });
    }
  } catch (err) {
    console.error('Failed to load perks from gateway:', err);
    perks.value = [];
    emit('toast', {
      title: '数据同步异常',
      message: '未能从网关同步优惠公告列表，请稍后重试。',
      type: 'ERROR',
    });
  } finally {
    isLoading.value = false;
  }
}

// Category filter
function selectCategory(catKey) {
  currentCategory.value = catKey;
}

const totalCount = computed(() => perks.value.length);

const coveredCategoryCount = computed(() => {
  const set = new Set(perks.value.map((p) => String(p.category || 'OTHER').toUpperCase()));
  return set.size;
});

const maxValueText = computed(() => {
  if (!perks.value.length) return '—';
  const max = Math.max(...perks.value.map((p) => Number(p.value_cny) || 0));
  if (max <= 0) return '公告制';
  return `¥${(max / 10000).toFixed(1).replace(/\.0$/, '')} 万`;
});

function getCategoryCount(catKey) {
  return perks.value.filter((p) => (p.category || '').toUpperCase() === catKey.toUpperCase()).length;
}

const currentCategoryLabel = computed(() => {
  const c = categoryList.value.find((item) => item.key === currentCategory.value);
  return c ? c.label : '全部公告';
});

// Display list with category filter
const displayPerks = computed(() => {
  let list = [...perks.value];
  if (currentCategory.value !== 'ALL') {
    list = list.filter((p) => (p.category || '').toUpperCase() === currentCategory.value.toUpperCase());
  }
  return list;
});

// Sorted perks
const sortedDisplayPerks = computed(() => {
  let list = [...displayPerks.value];

  if (currentSort.value === 'value') {
    return list.sort((a, b) => (Number(b.value_cny) || 0) - (Number(a.value_cny) || 0));
  }

  if (currentSort.value === 'ending') {
    const endWeight = (p) => {
      if (!p.effective_end) return 9999;
      return Date.parse(p.effective_end.replace('T', ' ')) || 9999;
    };
    return list.sort((a, b) => endWeight(a) - endWeight(b));
  }

  if (currentSort.value === 'latest') {
    return list.sort((a, b) => String(b.id || '').localeCompare(String(a.id || '')));
  }

  // relevance: featured (priority) first, then fresher effective start
  return list.sort((a, b) => (Number(b.priority) || 0) - (Number(a.priority) || 0));
});

// Search handling (local keyword filter over the announcement corpus)
async function handleSearch() {
  const q = searchQuery.value.trim();
  if (!q) {
    resetSearch();
    return;
  }

  isSearching.value = true;
  try {
    const qLower = q.toLowerCase();
    const matched = perks.value.filter((p) => {
      const text = [p.name, p.provider, p.summary, ...(p.highlights || [])]
        .join(' ')
        .toLowerCase();
      return text.includes(qLower);
    });
    perks.value = matched;
    isSearchActive.value = true;
    activeSearchQuery.value = q;
    emit('toast', {
      title: '搜索完成',
      message: `已为您完成关键词 “${q}” 的精确比对，共匹配 ${matched.length} 条优惠公告。`,
      type: 'INFO',
    });
  } finally {
    isSearching.value = false;
  }
}

async function resetSearch() {
  searchQuery.value = '';
  isSearchActive.value = false;
  activeSearchQuery.value = '';
  await loadPerks();
}

// Mouse glow effect
function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  card.style.setProperty('--mouse-x', `${x}px`);
  card.style.setProperty('--mouse-y', `${y}px`);
}

// Manual Refresh
async function handleManualRefresh() {
  await loadPerks();
  emit('toast', {
    title: '公告板已更新',
    message: '已从网关同步最新生态优惠公告。',
    type: 'SUCCESS',
  });
}

// Open external redeem URL
function openPerkUrl(perk) {
  if (perk.redeem_url) {
    window.open(perk.redeem_url, '_blank', 'noopener,noreferrer');
    return;
  }
  emit('toast', {
    title: '公告详情',
    message: `「${perk.name}」暂未开放线上直达领取，请关注平台后续公告或联系对应服务商。`,
    type: 'INFO',
  });
}

// Inline Detail
function openPerkDetail(p) {
  selectedPerk.value = p;
}

function closePerkDetail() {
  selectedPerk.value = null;
}

// Publish Modal
const selectedPerk = ref(null);
const showPublishModal = ref(false);
const isPublishing = ref(false);

const publishForm = ref({
  name: '',
  provider: '',
  category: PERK_CATEGORIES[0].key,
  value_cny: 0,
  quota_remaining: PERK_PUBLISH_DEFAULT_QUOTA,
  effective_start: '',
  effective_end: '',
  redeem_url: '',
  summary: '',
  highlightsText: '',
});

function openPublishModal() {
  publishForm.value = {
    name: '',
    provider: '',
    category: PERK_CATEGORIES[0].key,
    value_cny: 0,
    quota_remaining: PERK_PUBLISH_DEFAULT_QUOTA,
    effective_start: '',
    effective_end: '',
    redeem_url: '',
    summary: '',
    highlightsText: '',
  };
  showPublishModal.value = true;
}

function closePublishModal() {
  showPublishModal.value = false;
}

async function submitPublishPerk() {
  isPublishing.value = true;
  try {
    const highlights = publishForm.value.highlightsText
      .split(/[,，、]/)
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = {
      name: publishForm.value.name,
      provider: publishForm.value.provider,
      category: publishForm.value.category,
      value_cny: Number(publishForm.value.value_cny) || 0.0,
      summary: publishForm.value.summary,
      quota_remaining: Number(publishForm.value.quota_remaining) || PERK_PUBLISH_DEFAULT_QUOTA,
      effective_start: publishForm.value.effective_start || null,
      effective_end: publishForm.value.effective_end || null,
      redeem_url: publishForm.value.redeem_url || null,
      highlights,
      priority: PERK_PUBLISH_DEFAULT_PRIORITY,
      status: PERK_STATUSES[0],
    };

    const res = await dispatchGateway('perks.publish', payload);
    if (res.ok) {
      emit('toast', {
        title: '公告发布成功',
        message: `《${publishForm.value.name}》已通过微内核门禁并上架生态优惠公告板！`,
        type: 'SUCCESS',
      });
      showPublishModal.value = false;
      await loadPerks();
    } else {
      emit('toast', {
        title: '发布提示',
        message: res.error || '公告发布需要管理员权限，请登录管理员账号。',
        type: 'WARN',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '发布失败',
      message: e.message || '网络或接口通信异常，请检查权限。',
      type: 'ERROR',
    });
  } finally {
    isPublishing.value = false;
  }
}

// Helpers for badges & styles —— 分类元数据统一来自配置层
const CATEGORY_META = Object.fromEntries(PERK_CATEGORIES.map((c) => [c.key, c]));
const DEFAULT_CAT_META = CATEGORY_META.OTHER || { label: '其他优惠', icon: 'gift', color: '#5B6472', badgeClass: 'cat-other' };

function catMeta(cat) {
  const key = String(cat || 'OTHER').toUpperCase();
  return CATEGORY_META[key] || DEFAULT_CAT_META;
}

function formatCategoryLabel(cat) {
  return catMeta(cat).label;
}

function getCategoryEmblemIcon(cat) {
  return catMeta(cat).icon;
}

function getCategoryEmblemClass(cat) {
  return catMeta(cat).badgeClass;
}

function getCategoryBadgeClass(cat) {
  return catMeta(cat).badgeClass;
}

function formatValue(cny) {
  const v = Number(cny || 0);
  if (v <= 0) return '优惠公告';
  if (v >= 10000) return `约 ¥${(v / 10000).toFixed(1).replace(/\.0$/, '')} 万`;
  return `¥${Math.round(v).toLocaleString()}`;
}

function validityText(perk) {
  const start = perk.effective_start || '';
  const end = perk.effective_end || '';
  if (!start && !end) return '长期有效';
  if (start && !end) return `${start} 起`;
  if (!start && end) return `截止 ${end}`;
  return `${start} ~ ${end}`;
}
</script>

<style scoped>
/* ---------------- 1. Overall Wrapper Layout matching PolicyView ---------------- */
.perks-view-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.perks-main-content {
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
.perks-feed-layout {
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

.perks-feed-stream {
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

.refresh-mini-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: var(--radius-full);
}

/* Semantic Search Status Banner */
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

/* 滚动容器由全局 .opc-cards-scroll 承载 */

/* 卡片网格与外壳：由全局统一卡片体系 (.opc-cards-grid / .opc-card-shell) 承载 */

/* Perk 图标 tile：仅保留分类 emblem 主题色，尺寸由全局 .opc-card-icon 承载 */
.perk-icon-wrapper {
  font-size: 22px;
}

.cat-token,
.cat-server,
.cat-saas,
.cat-ai,
.cat-finance,
.cat-infra,
.cat-other {
  background: linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
  border: 1px solid var(--glass-border-subtle);
}

.perk-title {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.35;
}

/* badge-cat 分类主题色（基础 .badge-cat 由全局承载）—— 全部统一为中性玻璃胶囊 */
.badge-cat.cat-token,
.badge-cat.cat-server,
.badge-cat.cat-saas,
.badge-cat.cat-ai,
.badge-cat.cat-finance,
.badge-cat.cat-infra,
.badge-cat.cat-other {
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.badge-featured {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--status-warning-soft);
  color: var(--status-warning);
  border: 1px solid var(--status-warning-soft);
}

.badge-provider {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-tertiary);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Card Body & Highlights: 全局统一 (.card-body / .card-highlights-row / .highlight-chip) */

/* Highlights chips 专属色 */
.chip-value {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.06);
  border-color: rgba(0, 113, 227, 0.18);
  font-weight: 600;
}

.chip-validity {
  color: var(--text-tertiary);
}

.chip-quota {
  color: var(--text-tertiary);
}

/* Card Footer: 全局统一 (.card-footer-row / .issuer-* / .card-actions-cell / .card-interaction-row) */
.issuer-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  min-width: 0;
}

.issuer-name {
  max-width: 120px;
}

.btn-go {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  font-size: 11px;
  border-radius: var(--radius-full);
}

.btn-detail {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 11.5px;
  font-weight: 600;
  border-radius: var(--radius-full);
}

/* ---------------- 3. Stream Loading & Empty States ---------------- */
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

/* ---------------- 4. Right Auxiliary Sidebar matching PolicyView ---------------- */
.perks-feed-sidebar {
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

.perks-feed-sidebar::-webkit-scrollbar {
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

/* Sidebar 1: Perks Center Card */
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

/* Sidebar 2: Overview Card */
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

.overview-stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.overview-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 4px;
  border-radius: var(--radius-sm, 10px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.overview-stat-value {
  font-size: 20px;
  font-weight: 800;
  font-family: var(--font-display, sans-serif);
  color: var(--accent);
  letter-spacing: -0.02em;
}

.overview-stat-label {
  font-size: 10.5px;
  color: var(--text-tertiary);
}

.calc-card-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
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

.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
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
.detail-provider-pill,
.detail-value-pill,
.detail-validity-pill {
  font-size: 11.5px;
  padding: 2px 9px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.detail-value-pill {
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-glass);
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

.legal-badge-pill {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
  border: 1px solid var(--glass-border-subtle);
  margin-left: auto;
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.conditions-checklist {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.condition-check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-primary);
}

.check-icon {
  color: var(--status-success);
  font-weight: 700;
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
  word-break: break-all;
}

.spec-highlight {
  color: var(--accent);
  font-weight: 700;
}

.spec-success {
  color: var(--status-success);
  font-size: 11.5px;
}

/* ---------------- Publish Modal ---------------- */
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

.perks-publish-modal {
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
  overflow: hidden;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.98));
  border: 1px solid var(--glass-border);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.modal-title {
  font-size: 19px;
  font-weight: 700;
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
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

.publish-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding-right: 4px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.flex-1 { flex: 1; }

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.req {
  color: var(--status-danger);
}

.glass-select {
  height: 38px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

/* Modal animation */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-window,
.modal-fade-leave-active .modal-window {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-fade-enter-from .modal-window {
  transform: scale(0.96) translateY(8px);
}

.modal-fade-leave-to .modal-window {
  transform: scale(0.96) translateY(8px);
}

/* Responsive */
@media (max-width: 960px) {
  .perks-feed-layout {
    flex-direction: column;
  }
  .perks-feed-sidebar {
    width: 100%;
    height: auto;
  }
}
</style>
