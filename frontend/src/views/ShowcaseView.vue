<template>
  <div class="view-panel active showcase-view-wrapper">
    <div class="showcase-main-content">
      <!-- Dual-column Layout identical to Brainstorm (头脑风暴) -->
      <div class="showcase-feed-layout">
        <!-- Main Product Stream (左侧产品流) -->
        <section class="showcase-feed-stream">
          <!-- Category Filter Bar (产品分区选项卡 + 搜索 + 排序选择) -->
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
                    placeholder="搜索..."
                    @keydown.enter="handleSemanticSearch"
                  />
                  <button v-if="searchQuery" type="button" class="clear-search-btn" @click="handleClearSearch" title="清空搜索">×</button>
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

              <button class="btn-liquid-outline refresh-mini-btn" @click="handleManualRefresh" title="刷新并重置本地缓存">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                </svg>
                <span>刷新</span>
              </button>
            </div>
          </div>

          <!-- Semantic Search Status Banner -->
          <div v-if="isSemanticSearchActive" class="semantic-search-banner glass-box">
            <div class="banner-left">
              <span class="sparkle-badge"><OpcIcon name="search" :size="13" /> 搜索结果</span>
              <span class="banner-text">
                已为您找到与「<strong>{{ activeSearchQuery }}</strong>」相关的 <strong>{{ sortedDisplayProducts.length }}</strong> 款商业作品
              </span>
            </div>
            <button class="btn-liquid-outline btn-reset-search" @click="handleClearSearch">
              <span>恢复全部作品</span>
            </button>
          </div>

          <!-- Product Cards Scroll Container (ONLY this container scrolls with mouse wheel) -->
          <div
            class="showcase-cards-scroll-container"
            ref="productsScrollContainerRef"
            @scroll.passive="handleProductsScroll"
          >
            <!-- Loading State Indicator -->
            <div v-if="loading && displayProducts.length === 0" class="posts-loading-banner glass-box">
              <span class="loading-spinner"></span>
              <span>正在从数据库检索并加载「{{ currentCategoryLabel }}」优质创客商业作品...</span>
            </div>

            <!-- Product Cards Stream (产品橱窗内容：以卡片为主！) -->
            <div
              v-if="sortedDisplayProducts.length > 0 && !selectedProduct"
              class="showcase-cards-container opc-cards-grid"
              id="productCardsGrid"
            >
              <div
                v-for="item in sortedDisplayProducts"
                :key="item.id"
                class="glass-card showcase-product-card opc-card-shell opc-card opc-reveal-host"
                @mousemove="handleMouseMove"
                @click="openProductDetail(item)"
              >
                <!-- Card Top: Icon & Basic Info -->
                <div class="card-header-row">
                  <div class="app-icon-wrapper opc-card-icon">
                    <img
                      v-if="item.icon_url"
                      :src="item.icon_url"
                      :alt="item.title"
                      class="app-icon-img"
                      @error="handleIconError($event, item)"
                    />
                    <div v-else class="app-icon-fallback" :style="getIconFallbackStyle(item)">
                      {{ getInitials(item.title) }}
                    </div>
                  </div>

                  <div class="card-title-group">
                    <div class="card-title-line">
                      <h3 class="product-title opc-clamp opc-clamp-2" :title="item.title">{{ item.title }}</h3>
                    </div>
                    <div class="card-badges-line">
                      <span class="badge-cat">{{ item.category || '独立商业作品' }}</span>
                      <span class="badge-pricing" :class="getPricingClass(item.pricing_model)">
                        {{ formatPricing(item.pricing_model, item.price_cny) }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Card Body: Tagline (concise core summary, hover reveals full) -->
                <div class="card-body">
                  <HoverRevealText :text="item.tagline || item.description" :lines="2" />
                </div>

                <!-- Card Footer: Author -->
                <div class="card-footer-row" @click.stop>
                  <div class="author-cell">
                    <div class="author-avatar" :style="getAuthorAvatarStyle(item)">
                      {{ (item.author_name || item.author || '创')[1] || (item.author_name || item.author || '创')[0] }}
                    </div>
                    <div class="author-text">
                      <span class="author-name">{{ item.author_name || item.author || '@创客' }}</span>
                      <span class="publish-time">{{ formatDateShort(item.created_at) }}</span>
                    </div>
                  </div>
                </div>

                <!-- Card Interaction Band (unified like/comment/love/favorite) -->
                <div class="card-interaction-row" @click.stop>
                  <ContentInteractionBar
                    target-type="PRODUCT"
                    :target-id="item.id"
                    :target-title="item.title"
                    :like-count="item.like_count ?? item.upvote_count ?? item.upvotes ?? 0"
                    :favorite-count="item.favorite_count ?? 0"
                    :love-count="item.love_count ?? 0"
                    :comment-count="item.comment_count ?? 0"
                    :dislike-count="item.dislike_count ?? 0"
                    :rating-avg="item.rating_avg ?? 0"
                    :rating-count="item.rating_count ?? 0"
                    :my-rating="item.viewer?.rating ?? 0"
                    :liked="item.viewer ? item.viewer.liked : isUpvoted(item.id)"
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

            <!-- Inline Product Detail (content area, no modal) -->
            <div v-if="selectedProduct" class="inline-detail-slot glass-box">
              <div class="inline-detail-head">
                <button type="button" class="btn-back-inline" @click="closeProductDetail" title="返回作品列表">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                  </svg>
                  <span>返回作品列表</span>
                </button>
                <span class="inline-detail-crumb">产品橱窗 / {{ selectedProduct.title }}</span>
              </div>

              <div class="detail-header">
                <div class="detail-icon-wrap">
                  <img
                    v-if="selectedProduct.icon_url"
                    :src="selectedProduct.icon_url"
                    :alt="selectedProduct.title"
                    class="detail-icon-img"
                    @error="handleIconError($event, selectedProduct)"
                  />
                  <div v-else class="app-icon-fallback detail-icon-fallback" :style="getIconFallbackStyle(selectedProduct)">
                    {{ getInitials(selectedProduct.title) }}
                  </div>
                </div>

                <div class="detail-title-block">
                  <div class="detail-title-row">
                    <h2 class="detail-title">{{ selectedProduct.title }}</h2>
                    <span v-if="selectedProduct.version" class="mono-tag version-pill">
                      {{ selectedProduct.version }}
                    </span>
                  </div>
                  <p class="detail-tagline">{{ selectedProduct.tagline || selectedProduct.description }}</p>
                  <div class="detail-meta-pills">
                    <span class="detail-cat-pill">{{ selectedProduct.category }}</span>
                    <span class="detail-author-pill">作者: {{ selectedProduct.author_name || '@创客' }}</span>
                    <span class="detail-pricing-pill">
                      {{ formatPricing(selectedProduct.pricing_model, selectedProduct.price_cny) }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="detail-action-bar">
                <a
                  v-if="selectedProduct.official_url"
                  :href="selectedProduct.official_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn-liquid action-btn official-btn"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                  </svg>
                  <span>官方网站</span>
                </a>

                <a
                  v-if="selectedProduct.download_url"
                  :href="selectedProduct.download_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn-liquid action-btn download-btn"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  <span>下载安装包</span>
                </a>

                <a
                  v-if="selectedProduct.demo_url"
                  :href="selectedProduct.demo_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn-liquid-outline action-btn demo-btn"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                  </svg>
                  <span>在线体验</span>
                </a>

                <ContentInteractionBar
                  target-type="PRODUCT"
                  :target-id="selectedProduct.id"
                  :target-title="selectedProduct.title"
                  :like-count="selectedProduct.like_count ?? selectedProduct.upvote_count ?? selectedProduct.upvotes ?? 0"
                  :favorite-count="selectedProduct.favorite_count ?? 0"
                  :love-count="selectedProduct.love_count ?? 0"
                  :comment-count="selectedProduct.comment_count ?? 0"
                  :dislike-count="selectedProduct.dislike_count ?? 0"
                  :rating-avg="selectedProduct.rating_avg ?? 0"
                  :rating-count="selectedProduct.rating_count ?? 0"
                  :my-rating="selectedProduct.viewer?.rating ?? 0"
                  :liked="selectedProduct.viewer ? selectedProduct.viewer.liked : isUpvoted(selectedProduct.id)"
                  :favorited="selectedProduct.viewer?.favorited ?? false"
                  :loved="selectedProduct.viewer?.loved ?? false"
                  :commented="selectedProduct.viewer?.commented ?? false"
                  :disliked="selectedProduct.viewer?.disliked ?? false"
                  :authenticated="Boolean(currentUserSession)"
                  show-labels
                  @changed="handleInteractionChanged(selectedProduct, $event)"
                  @require-login="$emit('open-login')"
                  @toast="$emit('toast', $event)"
                />
              </div>

              <div class="detail-body-scroll">
                <div v-if="selectedProduct.screenshots && selectedProduct.screenshots.length > 0" class="detail-screenshots-section">
                  <h4 class="section-title">应用截图预览</h4>
                  <div class="screenshots-carousel">
                    <img
                      v-for="(img, idx) in selectedProduct.screenshots"
                      :key="idx"
                      :src="img"
                      class="screenshot-thumb"
                      alt="应用预览截图"
                    />
                  </div>
                </div>

                <div class="detail-section">
                  <h4 class="section-title">应用介绍</h4>
                  <p class="detail-full-description">{{ selectedProduct.description }}</p>
                </div>

                <div class="detail-section">
                  <h4 class="section-title">应用信息与规格</h4>
                  <div class="spec-grid">
                    <div class="spec-item">
                      <span class="spec-label">创客作者</span>
                      <span class="spec-value">{{ selectedProduct.author_name || selectedProduct.author_id || '@创客' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">当前版本</span>
                      <span class="spec-value mono-val">{{ selectedProduct.version || 'v1.0.0' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">类别属性</span>
                      <span class="spec-value">{{ selectedProduct.category }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">定价方案</span>
                      <span class="spec-value">{{ formatPricing(selectedProduct.pricing_model, selectedProduct.price_cny) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">上架时间</span>
                      <span class="spec-value mono-val">{{ formatDate(selectedProduct.created_at) }}</span>
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
            <div v-if="sortedDisplayProducts.length > 0 && hasMore && !selectedProduct" ref="sentinelRef" class="feed-sentinel-anchor"></div>

            <!-- Loading Next Batch Spinner -->
            <div v-if="loadingMore && !selectedProduct" class="feed-stream-loading glass-box">
              <span class="loading-spinner"></span>
              <span>正在滚动加载更多创客应用与商业作品...</span>
            </div>

            <!-- Empty State -->
            <div v-else-if="!loading && sortedDisplayProducts.length === 0" class="glass-box empty-state-box">
              <div class="empty-icon-wrap">
                <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                  <line x1="8" y1="21" x2="16" y2="21"/>
                  <line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
              </div>
              <h3 class="empty-title">当前分类下暂无已收录的产品</h3>
              <p class="empty-desc">
                {{ searchQuery ? `没有找到与 “${searchQuery}” 匹配的应用。` : '平台坚持代码与数据严格分离，数据库中尚未录入该分类产品。' }}
              </p>
              <div class="empty-actions">
                <button v-if="searchQuery" class="btn-liquid-outline" @click="searchQuery = ''">
                  清除搜索条件
                </button>
                <button class="btn-liquid" @click="handleOpenPublish">
                  发布首个作品
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Right Auxiliary Sidebar: Exactly matching ForumView -->
        <aside class="showcase-feed-sidebar">
          <!-- 1. Creator Center Card -->
          <div class="glass-box sidebar-card creator-center-card">
            <div class="creator-card-header">
              <div class="creator-icon-orb">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                </svg>
              </div>
              <div>
                <h4 class="creator-title">创客作品中心</h4>
                <p class="creator-desc">超级个体商业化与作品分发枢纽</p>
              </div>
            </div>
            <button class="btn-liquid btn-creator-publish" @click="handleOpenPublish">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span>上架新作品</span>
            </button>
            <div class="creator-quick-links">
              <span class="quick-pill" @click="selectCategory('AI 原生写作')">AI 写作</span>
              <span class="quick-pill" @click="selectCategory('跨境出海')">跨境出海</span>
              <span class="quick-pill" @click="selectCategory('开发工具')">开发工具</span>
              <span class="quick-pill" @click="selectCategory('微SaaS工具')">微SaaS</span>
            </div>
          </div>

          <!-- 2. Today's Hot Product Rank (今日作品打榜) -->
          <div class="glass-box sidebar-card hot-ranking-card">
            <div class="sidebar-card-title-row">
              <div class="title-with-icon">
                <span class="hot-badge-fire"><OpcIcon name="flame" :size="14" /></span>
                <h4 class="sidebar-title">今日作品打榜</h4>
              </div>
              <span class="hot-subtitle">实时更新</span>
            </div>

            <div class="hot-ranking-list">
              <div
                v-for="(item, idx) in hotRankProducts"
                :key="item.id"
                class="hot-rank-item"
                @click="openProductDetail(item)"
              >
                <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                <div class="hot-item-content">
                  <h5 class="hot-item-title">{{ item.title }}</h5>
                  <div class="hot-item-meta">
                    <span><OpcIcon name="flame" :size="12" /> {{ (item.upvote_count || item.upvotes || 0) * 3 + 42 }} 热度</span>
                    <span class="dot-sep">·</span>
                    <span>{{ item.category }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. Showcase Guidelines Card -->
          <div class="glass-box sidebar-card guidelines-card">
            <h4 class="sidebar-title-sm">超级个体橱窗规范</h4>
            <p class="guidelines-desc">
              产品橱窗倡导<strong>「真实商用闭环、支持官网直达、倡导正版独立开发」</strong>。所有上架作品均通过合规审核并直达开发者官方交付入口。
            </p>
            <div class="guidelines-footer">
              <span>OpcHub 商业作品协议 v1.0</span>
              <span class="dot-sep">·</span>
              <span class="link-span" @click="handleOpenPublish">申请上架</span>
            </div>
          </div>
        </aside>
      </div>
    </div>


    <!-- Product Publish Modal -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="showPublishModal" class="modal-backdrop" @click="closePublishModal">
          <div class="modal-window glass-box publish-modal" @click.stop>
            <div class="modal-header">
              <div>
                <h2 class="modal-title">发布创客独立作品</h2>
                <p class="modal-subtitle">上架商用作品至超级个体橱窗与首页打榜，支持官网与下载直达</p>
              </div>
              <button class="modal-close-btn" @click="closePublishModal"><OpcIcon name="close" :size="16" /></button>
            </div>

            <form class="publish-form" @submit.prevent="submitPublishProduct">
              <div class="form-row">
                <div class="form-group flex-2">
                  <label class="form-label">产品名称 <span class="req">*</span></label>
                  <input
                    v-model="publishForm.title"
                    type="text"
                    required
                    class="glass-input"
                    placeholder="如：InkFlow AI 专注编辑器"
                  />
                </div>
                <div class="form-group flex-1">
                  <label class="form-label">软件版本</label>
                  <input
                    v-model="publishForm.version"
                    type="text"
                    class="glass-input"
                    placeholder="如：v1.0.0"
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">一句话卖点简介 (Tagline) <span class="req">*</span></label>
                <input
                  v-model="publishForm.tagline"
                  type="text"
                  required
                  class="glass-input"
                  placeholder="如：专为长文研究员与独立小说家打造的本地离线增强写作工作台"
                />
              </div>

              <div class="form-group">
                <label class="form-label">详细应用介绍 <span class="req">*</span></label>
                <textarea
                  v-model="publishForm.description"
                  required
                  rows="4"
                  class="glass-input"
                  placeholder="详细介绍产品核心功能、应用场景、技术亮点与解决的用户痛点..."
                ></textarea>
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">应用分类</label>
                  <select v-model="publishForm.category" class="glass-input glass-select">
                    <option value="AI 原生写作">AI 原生写作</option>
                    <option value="跨境出海">跨境出海</option>
                    <option value="开发工具">开发工具</option>
                    <option value="微SaaS工具">微SaaS工具</option>
                    <option value="自动化工作流">自动化工作流</option>
                    <option value="设计系统">设计系统</option>
                  </select>
                </div>

                <div class="form-group flex-1">
                  <label class="form-label">商业计费模式</label>
                  <select v-model="publishForm.pricing_model" class="glass-input glass-select">
                    <option value="FREE">免费体验</option>
                    <option value="FREEMIUM">免费增值 (Freemium)</option>
                    <option value="ONE_TIME">买断制 (One-Time)</option>
                    <option value="SUBSCRIPTION">周期订阅 (Subscription)</option>
                  </select>
                </div>

                <div class="form-group flex-1" v-if="publishForm.pricing_model !== 'FREE'">
                  <label class="form-label">参考定价 (¥)</label>
                  <input
                    v-model.number="publishForm.price_cny"
                    type="number"
                    min="0"
                    step="0.01"
                    class="glass-input"
                    placeholder="0.00"
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">应用图标 Icon (图片或 SVG 地址)</label>
                <div class="icon-input-row">
                  <input
                    v-model="publishForm.icon_url"
                    type="url"
                    class="glass-input"
                    placeholder="https://... (支持 PNG、JPG、SVG 或留空使用生成渐变)"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">官方网站地址 (Official URL)</label>
                  <input
                    v-model="publishForm.official_url"
                    type="url"
                    class="glass-input"
                    placeholder="https://yourproduct.com"
                  />
                </div>

                <div class="form-group flex-1">
                  <label class="form-label">安装包下载地址 (Download URL)</label>
                  <input
                    v-model="publishForm.download_url"
                    type="url"
                    class="glass-input"
                    placeholder="https://download.yourproduct.com/setup.dmg"
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">在线体验或演示链接 (Demo URL)</label>
                <input
                  v-model="publishForm.demo_url"
                  type="url"
                  class="glass-input"
                  placeholder="https://yourproduct.com/demo"
                />
              </div>

              <div class="modal-footer-actions">
                <button type="button" class="btn-liquid-outline" @click="closePublishModal">
                  取消
                </button>
                <button type="submit" class="btn-liquid submit-btn" :disabled="submitting">
                  <span v-if="submitting">正在发布入库...</span>
                  <span v-else>立即发布入库</span>
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

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['open-register', 'open-login', 'toast']);

// Current User Session
const currentUserSession = computed(() => {
  if (props.userSession) return props.userSession;
  try {
    const raw = localStorage.getItem('opchub_user_session');
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return null;
});

// Paged & Infinite Scrolling States
const displayProducts = ref([]);
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
const isSemanticSearchActive = ref(false);
const activeSearchQuery = ref('');
const currentCategory = ref('ALL');
const selectedProduct = ref(null);
const showPublishModal = ref(false);
const upvotedIds = ref(new Set());
const sentinelRef = ref(null);
let observer = null;

// Sort options
const sortOptions = [
  { key: 'hot', label: '最热打榜', icon: 'flame' },
  { key: 'new', label: '最新上架', icon: 'bolt' },
  { key: 'featured', label: '商业精选', icon: 'gem' },
];
const currentSort = ref('hot');

// Category Tabs Definition
const categoryList = [
  { key: 'ALL', label: '全部作品' },
  { key: 'AI 原生写作', label: 'AI 原生写作' },
  { key: '跨境出海', label: '跨境出海' },
  { key: '开发工具', label: '开发工具' },
  { key: '微SaaS工具', label: '微SaaS工具' },
  { key: '自动化工作流', label: '自动化工作流' },
];

const currentCategoryLabel = computed(() => {
  return categoryList.find((c) => c.key === currentCategory.value)?.label || '全部作品';
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

// Publish Form State
const publishForm = reactive({
  title: '',
  tagline: '',
  description: '',
  category: 'AI 原生写作',
  version: 'v1.0.0',
  pricing_model: 'FREE',
  price_cny: 0,
  icon_url: '',
  official_url: '',
  download_url: '',
  demo_url: '',
});

const productsScrollContainerRef = ref(null);

function handleProductsScroll(e) {
  const el = e.target;
  if (!el || !hasMore.value || loading.value || loadingMore.value || isSemanticSearchActive.value) return;
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 250) {
    fetchProductsPage(currentPage.value + 1, true);
  }
}

function selectCategory(catKey) {
  if (currentCategory.value === catKey) return;
  currentCategory.value = catKey;
  if (productsScrollContainerRef.value) {
    productsScrollContainerRef.value.scrollTop = 0;
  }
  if (isSemanticSearchActive.value && searchQuery.value.trim()) {
    handleSemanticSearch();
  } else {
    resetAndReload();
  }
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
  const query = searchQuery.value.trim();
  if (!query) {
    handleClearSearch();
    return;
  }

  isSearching.value = true;
  try {
    const res = await dispatchGateway('products.search.semantic', {
      query: query,
      category: currentCategory.value === 'ALL' ? null : currentCategory.value,
      top_k: 25,
    });

    if (res.ok && res.data && Array.isArray(res.data.items) && res.data.items.length > 0) {
      displayProducts.value = res.data.items;
      await enrichInteractions(displayProducts.value, 'PRODUCT');
      totalCount.value = res.data.items.length;
      isSemanticSearchActive.value = true;
      activeSearchQuery.value = query;
      hasMore.value = false;
      emit('toast', {
        title: '搜索完成',
        message: `已为您找到 ${res.data.items.length} 款相关作品。`,
        type: 'SUCCESS',
      });
    } else {
      // In-browser fallback scoring over current products
      const scored = displayProducts.value.map((item) => {
        const fullText = `${item.title || ''} ${item.tagline || ''} ${item.description || ''} ${item.category || ''}`;
        const sim = computeTextSemanticScore(query, fullText);
        return {
          ...item,
          similarity: Math.round(sim * 10000) / 10000,
          similarity_score: Math.round(sim * 10000) / 10000,
          semantic_score: Math.round(sim * 1000) / 10,
        };
      });
      scored.sort((a, b) => (b.semantic_score || 0) - (a.semantic_score || 0));
      displayProducts.value = scored;
      totalCount.value = scored.length;
      isSemanticSearchActive.value = true;
      activeSearchQuery.value = query;
      hasMore.value = false;
      emit('toast', {
        title: '搜索完成',
        message: `已为您匹配相关商业作品。`,
        type: 'SUCCESS',
      });
    }
  } catch (e) {
    const scored = displayProducts.value.map((item) => {
      const fullText = `${item.title || ''} ${item.tagline || ''} ${item.description || ''} ${item.category || ''}`;
      const sim = computeTextSemanticScore(query, fullText);
      return {
        ...item,
        similarity: Math.round(sim * 10000) / 10000,
        similarity_score: Math.round(sim * 10000) / 10000,
        semantic_score: Math.round(sim * 1000) / 10,
      };
    });
    scored.sort((a, b) => (b.semantic_score || 0) - (a.semantic_score || 0));
    displayProducts.value = scored;
    totalCount.value = scored.length;
    isSemanticSearchActive.value = true;
    activeSearchQuery.value = query;
    hasMore.value = false;
  } finally {
    isSearching.value = false;
  }
}

function handleClearSearch() {
  searchQuery.value = '';
  activeSearchQuery.value = '';
  isSemanticSearchActive.value = false;
  invalidateClientCache();
  resetAndReload();
}

// Core Paged Fetcher with Multi-layer Caching (Client Memory + Server Invalidation)
async function fetchProductsPage(page, isAppend = false) {
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
    const res = await dispatchGateway('products.list', {
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
        displayProducts.value = [];
        totalCount.value = 0;
        hasMore.value = false;
      }
    }
  } catch (e) {
    console.error('Failed to load products page:', e);
    if (!isAppend) {
      displayProducts.value = [];
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
    const existingIds = new Set(displayProducts.value.map((p) => p.id));
    for (const item of items) {
      if (!existingIds.has(item.id)) {
        displayProducts.value.push(item);
      }
    }
  } else {
    displayProducts.value = items;
  }
  enrichInteractions(items, 'PRODUCT');
  currentPage.value = pagedData.page || 1;
  hasMore.value = Boolean(pagedData.has_more);
  totalCount.value = pagedData.total !== undefined ? pagedData.total : displayProducts.value.length;
}

// Reset and reload first page
function resetAndReload() {
  currentPage.value = 1;
  hasMore.value = true;
  fetchProductsPage(1, false);
}

// Manual Refresh
function handleManualRefresh() {
  invalidateClientCache();
  isCacheHit.value = false;
  resetAndReload();
  emit('toast', { title: '缓存已刷新', message: '已同步最新数据库橱窗作品与打榜排行。', type: 'INFO' });
}

// Watch filters to trigger reload
watch(currentCategory, () => {
  if (!isSemanticSearchActive.value) {
    resetAndReload();
  }
});

// Sorted & Filtered Products Display
const sortedDisplayProducts = computed(() => {
  let list = [...displayProducts.value];

  if (isSemanticSearchActive.value) {
    return list.sort((a, b) => (b.semantic_score || 0) - (a.semantic_score || 0));
  }

  if (currentSort.value === 'hot') {
    list.sort((a, b) => {
      const upA = a.upvote_count ?? a.upvotes ?? 0;
      const upB = b.upvote_count ?? b.upvotes ?? 0;
      return upB - upA;
    });
  } else if (currentSort.value === 'new') {
    list.sort((a, b) => {
      const tA = new Date(a.created_at || a.updated_at || 0).getTime();
      const tB = new Date(b.created_at || b.updated_at || 0).getTime();
      return tB - tA;
    });
  } else if (currentSort.value === 'featured') {
    list.sort((a, b) => {
      const scoreA = (a.pricing_model !== 'FREE' ? 100 : 0) + (a.upvote_count ?? a.upvotes ?? 0);
      const scoreB = (b.pricing_model !== 'FREE' ? 100 : 0) + (b.upvote_count ?? b.upvotes ?? 0);
      return scoreB - scoreA;
    });
  }

  return list;
});

// Top 5 Hot Products for Right Auxiliary Sidebar
const hotRankProducts = computed(() => {
  return [...displayProducts.value]
    .sort((a, b) => {
      const upA = a.upvote_count ?? a.upvotes ?? 0;
      const upB = b.upvote_count ?? b.upvotes ?? 0;
      return upB - upA;
    })
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
        if (!isSemanticSearchActive.value && hasMore.value && !loading.value && !loadingMore.value && displayProducts.value.length > 0) {
          fetchProductsPage(currentPage.value + 1, true);
        }
      }
    },
    {
      root: productsScrollContainerRef.value || null,
      rootMargin: '180px',
    }
  );

  if (sentinelRef.value) {
    observer.observe(sentinelRef.value);
  }
}

// Upvote Handler
async function handleUpvote(item) {
  if (upvotedIds.value.has(item.id)) {
    emit('toast', { title: '已打榜', message: `您已经为《${item.title}》投过打榜票了！`, type: 'INFO' });
    return;
  }
  try {
    const res = await dispatchGateway('products.upvote', { product_id: item.id });
    if (res.ok) {
      item.upvote_count = (item.upvote_count || item.upvotes || 0) + 1;
      item.upvotes = item.upvote_count;
      upvotedIds.value.add(item.id);
      saveUpvotedIds();
      invalidateClientCache();
      emit('toast', { title: '打榜成功', message: `已成功为《${item.title}》投出宝贵一票！`, type: 'SUCCESS' });
    } else {
      item.upvote_count = (item.upvote_count || 0) + 1;
      item.upvotes = item.upvote_count;
      upvotedIds.value.add(item.id);
      saveUpvotedIds();
      invalidateClientCache();
      emit('toast', { title: '打榜已记录', message: `感谢支持创客作品《${item.title}》！`, type: 'SUCCESS' });
    }
  } catch (e) {
    item.upvote_count = (item.upvote_count || 0) + 1;
    item.upvotes = item.upvote_count;
    upvotedIds.value.add(item.id);
    saveUpvotedIds();
    emit('toast', { title: '打榜已记录', message: `已为《${item.title}》累计打榜！`, type: 'SUCCESS' });
  }
}

function isUpvoted(id) {
  return upvotedIds.value.has(id);
}

function handleInteractionChanged(item, payload) {
  applyBarChange(item, payload);
  if (item) {
    item.upvote_count = Number(payload.like_count || 0);
    item.upvotes = item.upvote_count;
  }
}

function saveUpvotedIds() {
  try {
    localStorage.setItem('opchub_product_upvotes', JSON.stringify([...upvotedIds.value]));
  } catch (e) {}
}

function loadUpvotedIds() {
  try {
    const raw = localStorage.getItem('opchub_product_upvotes');
    if (raw) {
      const list = JSON.parse(raw);
      if (Array.isArray(list)) {
        upvotedIds.value = new Set(list);
      }
    }
  } catch (e) {}
}

// Modal controls
function openProductDetail(item) {
  selectedProduct.value = item;
}

function closeProductDetail() {
  selectedProduct.value = null;
}

function handleOpenPublish() {
  if (!currentUserSession.value) {
    emit('toast', {
      title: '需创客准入',
      message: '发布商业作品需先登录或入驻平台创客账号！',
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

// Submit publish form to backend microkernel DAG
async function submitPublishProduct() {
  if (!publishForm.title || !publishForm.tagline || !publishForm.description) {
    emit('toast', { title: '信息不全', message: '请完整填写产品名称、卖点简介与详细描述！', type: 'WARN' });
    return;
  }

  submitting.value = true;
  try {
    const payload = {
      title: publishForm.title.trim(),
      tagline: publishForm.tagline.trim(),
      description: publishForm.description.trim(),
      category: publishForm.category,
      version: publishForm.version || 'v1.0.0',
      pricing_model: publishForm.pricing_model,
      price_cny: parseFloat(publishForm.price_cny) || 0.0,
      icon_url: publishForm.icon_url ? publishForm.icon_url.trim() : null,
      official_url: publishForm.official_url ? publishForm.official_url.trim() : null,
      download_url: publishForm.download_url ? publishForm.download_url.trim() : null,
      demo_url: publishForm.demo_url ? publishForm.demo_url.trim() : null,
      author_id: currentUserSession.value?.uid || 'usr_maker',
      author_name: currentUserSession.value?.nickname || currentUserSession.value?.username || '@独立创客',
    };

    const res = await dispatchGateway('products.publish', payload);
    if (res.ok) {
      emit('toast', {
        title: '发布成功',
        message: `商业作品《${payload.title}》已成功收录入库并发布！`,
        type: 'SUCCESS',
      });
      closePublishModal();
      // Reset form
      publishForm.title = '';
      publishForm.tagline = '';
      publishForm.description = '';
      publishForm.icon_url = '';
      publishForm.official_url = '';
      publishForm.download_url = '';
      publishForm.demo_url = '';

      // Invalidate cache and reload
      invalidateClientCache();
      resetAndReload();
    } else {
      emit('toast', {
        title: '发布未完成',
        message: res.raw?.message || '发布流水线校验未通过，请检查所填字段',
        type: 'ERROR',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '发布异常',
      message: '网关通信失败，请检查后端运行状态。',
      type: 'ERROR',
    });
  } finally {
    submitting.value = false;
  }
}

// Helpers
function handleIconError(e, item) {
  e.target.style.display = 'none';
  if (e.target.nextElementSibling) {
    e.target.nextElementSibling.style.display = 'flex';
  }
}

function getInitials(name) {
  if (!name) return 'OPC';
  const clean = name.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
  return clean.slice(0, 2).toUpperCase() || 'OP';
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

function formatPricing(model, price) {
  if (model === 'FREE') return '免费使用';
  if (model === 'FREEMIUM') return '免费增值';
  if (price && price > 0) {
    return model === 'SUBSCRIPTION' ? `¥${price}/月 订阅` : `¥${price} 买断`;
  }
  return '商用授权';
}

function getPricingClass(model) {
  if (model === 'FREE') return 'pricing-free';
  if (model === 'FREEMIUM') return 'pricing-freemium';
  if (model === 'SUBSCRIPTION') return 'pricing-sub';
  return 'pricing-onetime';
}

function formatDate(isoStr) {
  if (!isoStr) return '近期上架';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return '近期上架';
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

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  card.style.setProperty('--mouse-x', `${x}px`);
  card.style.setProperty('--mouse-y', `${y}px`);
}

onMounted(() => {
  document.body.classList.add('fixed-screen-feed');
  loadUpvotedIds();
  fetchProductsPage(1, false);
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
.showcase-view-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.showcase-main-content {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

/* Dual-Column Feed Layout identical to ForumView */
.showcase-feed-layout {
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

.showcase-feed-stream {
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

/* Scrollable Container: ONLY product cards scroll with mouse wheel, NO scrollbar displayed */
.showcase-cards-scroll-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-right: 0;
  padding-bottom: 24px;
  box-sizing: border-box;
  overscroll-behavior: contain;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.showcase-cards-scroll-container::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

/* Right Auxiliary Sidebar: Exactly matching ForumView */
.showcase-feed-sidebar {
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

.showcase-feed-sidebar::-webkit-scrollbar {
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

/* Semantic Search Status Banner */
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

/* 3. Product Cards Container: 以卡片为主！ */
/* 卡片网格与外壳：由全局统一卡片体系 (.opc-cards-grid / .opc-card-shell) 承载 */

/* Card Header: 图标 tile 专属样式 */
.app-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.app-icon-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.app-icon-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  letter-spacing: -0.02em;
}

.product-title {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-version-badge {
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
  border: 1px solid var(--glass-border-subtle);
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

/* Card Body & Highlights: 全局统一 (.card-body / .card-highlights-row / .highlight-chip) */

.product-tagline {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-desc-snippet {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Card Highlights chips 专属色 */
.chip-link {
  color: var(--accent);
}

.chip-demo {
  color: var(--text-secondary);
}

.chip-download {
  color: var(--text-secondary);
}

/* Card Footer: 全局统一 (.card-footer-row / .author-cell / .author-text / .author-name / .publish-time / .card-actions-cell) */
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

/* Unified interaction band lives at the very bottom of the card: 全局统一 */

.upvote-btn-pill {
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
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.upvote-btn-pill:hover {
  background: var(--accent-glass);
  border-color: rgba(0, 113, 227, 0.25);
  color: var(--accent);
}

.upvote-btn-pill.active {
  background: var(--accent-glass);
  border-color: rgba(0, 113, 227, 0.35);
  color: var(--accent);
  box-shadow: 0 0 10px var(--accent-glow);
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

.crystal-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  opacity: 0.6;
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

/* ---------------- Right Auxiliary Sidebar (同头脑风暴) ---------------- */
.showcase-feed-sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 76px;
  align-self: flex-start;
  max-height: calc(100vh - 96px);
  overflow-y: auto;
  scrollbar-width: none;
  box-sizing: border-box;
}

.showcase-feed-sidebar::-webkit-scrollbar {
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

/* Sidebar 1: Creator Center Card */
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

/* ---------------- Detail Modal (VisionOS App Store Style) ---------------- */
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

.detail-icon-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.detail-icon-fallback {
  width: 100%;
  height: 100%;
  font-size: 20px;
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
.detail-author-pill,
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

.detail-screenshots-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.screenshots-carousel {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 6px;
}

.screenshot-thumb {
  height: 180px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  object-fit: cover;
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

/* ---------------- Publish Modal ---------------- */
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

.icon-input-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  .showcase-feed-layout {
    flex-direction: column;
  }
  .showcase-feed-sidebar {
    width: 100%;
    position: static;
    max-height: none;
  }
  .showcase-cards-container {
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
  .feed-search-mini {
    flex: 1;
    width: auto;
  }
}

/* Dark Mode Theme Adjustments */
[data-theme="dark"] .sidebar-card,
[data-theme="dark"] .showcase-product-card,
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
