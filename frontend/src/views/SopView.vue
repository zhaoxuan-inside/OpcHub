<template>
  <div class="view-panel active sop-view-wrapper">
    <!-- Full-page document reader & writer (replaces the workspace, not a modal) -->
    <SopDocPage
      v-if="currentViewMode === 'doc'"
      :node="docPageNode"
      :catalog="documentNodes"
      :children="docPageChildren"
      :authenticated="Boolean(currentUserSession)"
      :user-id="currentUserSession?.uid || ''"
      :creation-mode="docCreationMode"
      @back="handleBackFromDoc"
      @pick="handlePickDocument"
      @saved="handleDocumentSaved"
      @require-login="$emit('open-login')"
      @toast="emit('toast', $event)"
    />

    <!-- Full-page flow reader (replaces the workspace, not a modal) -->
    <SopFlowPage
      v-else-if="currentViewMode === 'flow'"
      :detail="flowPageDetail"
      :owner="flowOwnerMode"
      :authenticated="Boolean(currentUserSession)"
      @back="handleBackFromFlow"
      @open-step="handleOpenNode"
      @edit="handleEditMyFlow"
      @delete="handleDeleteMyFlowFromPage"
      @require-login="$emit('open-login')"
      @toast="emit('toast', $event)"
    />

    <!-- Full-page flow builder (replaces the workspace, not a modal) -->
    <div v-else-if="currentViewMode === 'flowbuilder'" class="sop-flow-builder-page">
      <div class="glass-box sop-flow-builder-head">
        <div class="sop-flow-builder-title-wrap">
          <button class="btn-liquid-outline sop-flow-builder-back" @click="closeFlowBuilder" title="返回">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span>返回</span>
          </button>
          <div>
            <h2 class="sop-flow-builder-title">{{ editingFlowId ? '编辑流程' : '创建流程' }}</h2>
            <p class="sop-flow-builder-sub">挑选文书节点组成你的专属办理流程，可随时回来继续</p>
          </div>
        </div>
      </div>
      <div class="glass-box sop-flow-builder-body">
        <SopFlowBuilder
          :goals="goals"
          :nodes="nodes"
          :initial="flowBuilderInitial"
          :submitting="flowSubmitting"
          @submit="submitFlow"
          @cancel="closeFlowBuilder"
        />
      </div>
    </div>

    <!-- Full-page private-document reader (replaces the workspace, not a modal) -->
    <SopMyDocPage
      v-else-if="currentViewMode === 'mydoc'"
      :doc="myDocPageDoc"
      :template-name-of="templateNameOf"
      @back="handleBackFromMyDoc"
      @delete="handleDeleteMyDocument"
    />

    <div v-else class="sop-main-content">
      <!-- View mode switcher: 节点工作台 / 流程向导 / 目标反查 -->
      <div class="glass-box sop-mode-bar">
        <div class="sop-mode-tabs">
          <button
            v-for="mode in viewModes"
            :key="mode.key"
            type="button"
            :class="['sop-mode-tab', { active: viewMode === mode.key }]"
            @click="viewMode = mode.key"
          >
            <span class="sop-mode-tab-label">{{ mode.label }}</span>
            <span class="sop-mode-tab-desc">{{ mode.desc }}</span>
          </button>
        </div>

        <div class="sop-mode-right">
          <span class="sop-mode-stat">
            {{ documentCatalog.length }} 份标准文书 · {{ documentNodes.length }} 份可填写文书 · {{ subgraphNodes.length }} 个子图
          </span>
        </div>
      </div>

      <!-- Dual-column layout identical to Product Showcase -->
      <div class="sop-feed-layout">
        <!-- Main stream -->
        <section class="sop-feed-stream">
          <!-- ① Standard document catalog (标准文书) -->
          <template v-if="viewMode === 'workbench'">
            <div class="glass-box feed-filter-bar">
              <div class="category-tabs-scroll">
                <button
                  v-for="cat in categoryFilters"
                  :key="cat.key"
                  type="button"
                  :class="['category-tab-pill', { active: currentCategory === cat.key }]"
                  @click="currentCategory = cat.key"
                >
                  <span>{{ cat.label }}</span>
                  <span v-if="cat.key === 'ALL' && documentCatalog.length > 0" class="cat-pill-count">{{ documentCatalog.length }}</span>
                </button>
              </div>

              <div class="feed-filter-right">
                <div class="semantic-search-box">
                  <div class="search-input-wrap">
                    <input
                      v-model="searchQuery"
                      type="text"
                      class="semantic-search-input"
                      placeholder="搜索文书..."
                      @keydown.enter="handleSearch"
                    />
                    <button v-if="searchQuery" type="button" class="clear-search-btn" @click="searchQuery = ''" title="清空搜索">×</button>
                  </div>
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

                <button class="btn-liquid-outline refresh-mini-btn" @click="handleRefresh" title="重新加载标准文书库">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                  </svg>
                  <span>刷新</span>
                </button>
              </div>
            </div>

            <div v-if="isSearchActive" class="semantic-search-banner glass-box">
              <div class="banner-left">
                <span class="sparkle-badge"><OpcIcon name="search" :size="13" /> 搜索结果</span>
                <span class="banner-text">
                  已为您找到与「<strong>{{ activeSearchQuery }}</strong>」相关的 <strong>{{ filteredDocuments.length }}</strong> 份标准文书
                </span>
              </div>
              <button class="btn-liquid-outline btn-reset-search" @click="handleClearSearch">
                <span>恢复全部文书</span>
              </button>
            </div>

            <div class="opc-cards-scroll">
              <div v-if="loading && documentCatalog.length === 0" class="posts-loading-banner glass-box">
                <span class="loading-spinner"></span>
                <span>正在从数据库加载标准文书库...</span>
              </div>

              <div v-if="filteredDocuments.length > 0" class="sop-cards-container opc-cards-grid" id="sopDocumentsGrid">
                <SopDocumentCard
                  v-for="doc in filteredDocuments"
                  :key="doc.id"
                  :doc="doc"
                  :authenticated="Boolean(currentUserSession)"
                  @open="handleOpenDocument"
                  @like="handleLikeDocument"
                  @favorite="handleFavoriteDocument"
                  @require-login="$emit('open-login')"
                  @toast="$emit('toast', $event)"
                />
              </div>

              <div v-else-if="!loading" class="glass-box empty-state-box">
                <div class="empty-icon-wrap">
                  <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  </svg>
                </div>
                <h3 class="empty-title">没有匹配的标准文书</h3>
                <p class="empty-desc">
                  {{ searchQuery ? `没有找到与 “${searchQuery}” 匹配的文书。` : '标准文书库中暂无可用文书。' }}
                </p>
                <div class="empty-actions">
                  <button v-if="searchQuery" class="btn-liquid-outline" @click="handleClearSearch">清除搜索条件</button>
                </div>
              </div>
            </div>
          </template>

          <!-- ② Flow guide: same layout as the document workbench, but each card is a flow -->
          <template v-else-if="viewMode === 'guide'">
            <div class="glass-box feed-filter-bar">
              <div class="category-tabs-scroll">
                <button
                  v-for="cat in flowCategoryFilters"
                  :key="cat.key"
                  type="button"
                  :class="['category-tab-pill', { active: flowCategory === cat.key }]"
                  @click="flowCategory = cat.key"
                >
                  <span>{{ cat.label }}</span>
                  <span v-if="cat.key === 'ALL' && flowCatalog.length > 0" class="cat-pill-count">{{ flowCatalog.length }}</span>
                </button>
              </div>

              <div class="feed-filter-right">
                <div class="semantic-search-box">
                  <div class="search-input-wrap">
                    <input
                      v-model="flowSearchQuery"
                      type="text"
                      class="semantic-search-input"
                      placeholder="搜索流程..."
                      @keydown.enter="handleFlowSearch"
                    />
                    <button v-if="flowSearchQuery" type="button" class="clear-search-btn" @click="handleFlowClearSearch" title="清空搜索">×</button>
                  </div>
                </div>

                <div class="sort-segmented">
                  <button
                    v-for="opt in flowSortOptions"
                    :key="opt.key"
                    type="button"
                    :class="['sort-pill', { active: flowSort === opt.key }]"
                    @click="flowSort = opt.key"
                  >
                    <OpcIcon :name="opt.icon" :size="13" /> {{ opt.label }}
                  </button>
                </div>

                <button class="btn-liquid-outline refresh-mini-btn" @click="handleFlowRefresh" title="重新加载流程库">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                  </svg>
                  <span>刷新</span>
                </button>
              </div>
            </div>

            <div v-if="isFlowSearchActive" class="semantic-search-banner glass-box">
              <div class="banner-left">
                <span class="sparkle-badge"><OpcIcon name="search" :size="13" /> 搜索结果</span>
                <span class="banner-text">
                  已为您找到与「<strong>{{ activeFlowSearchQuery }}</strong>」相关的 <strong>{{ filteredFlows.length }}</strong> 条标准流程
                </span>
              </div>
              <button class="btn-liquid-outline btn-reset-search" @click="handleFlowClearSearch">
                <span>恢复全部流程</span>
              </button>
            </div>

            <div class="opc-cards-scroll">
              <div v-if="flowLoading && flowCatalog.length === 0" class="posts-loading-banner glass-box">
                <span class="loading-spinner"></span>
                <span>正在从数据库加载标准流程库...</span>
              </div>

              <div v-if="filteredFlows.length > 0" class="sop-cards-container opc-cards-grid" id="sopFlowsGrid">
                <SopFlowCard
                  v-for="flow in filteredFlows"
                  :key="flow.id"
                  :flow="flow"
                  :authenticated="Boolean(currentUserSession)"
                  @open="handleOpenFlow"
                  @like="handleLikeFlow"
                  @favorite="handleFavoriteFlow"
                  @require-login="$emit('open-login')"
                  @toast="$emit('toast', $event)"
                />
              </div>

              <div v-else-if="!flowLoading" class="glass-box empty-state-box">
                <div class="empty-icon-wrap">
                  <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M9 11l3 3L22 4"></path>
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                  </svg>
                </div>
                <h3 class="empty-title">没有匹配的流程</h3>
                <p class="empty-desc">
                  {{ flowSearchQuery ? `没有找到与 “${flowSearchQuery}” 匹配的流程。` : '标准流程库中暂无可用流程。' }}
                </p>
                <div class="empty-actions">
                  <button v-if="flowSearchQuery" class="btn-liquid-outline" @click="handleFlowClearSearch">清除搜索条件</button>
                </div>
              </div>
            </div>
          </template>

          <!-- ③ My documents (我的文书) — same layout as the standard-document workbench -->
          <template v-else-if="viewMode === 'mydocs'">
            <div class="glass-box feed-filter-bar">
              <div class="feed-filter-right">
                <div class="semantic-search-box">
                  <div class="search-input-wrap">
                    <input
                      v-model="myDocSearchQuery"
                      type="text"
                      class="semantic-search-input"
                      placeholder="搜索我的文书..."
                      @keydown.enter="handleMyDocSearch"
                    />
                    <button v-if="myDocSearchQuery" type="button" class="clear-search-btn" @click="handleMyDocClearSearch" title="清空搜索">×</button>
                  </div>
                </div>

                <div class="sort-segmented">
                  <button
                    v-for="opt in myDocSortOptions"
                    :key="opt.key"
                    type="button"
                    :class="['sort-pill', { active: myDocSort === opt.key }]"
                    @click="myDocSort = opt.key"
                  >
                    <OpcIcon :name="opt.icon" :size="13" /> {{ opt.label }}
                  </button>
                </div>

                <button class="btn-liquid-outline refresh-mini-btn" @click="handleMyDocRefresh" title="重新加载我的文书">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                  </svg>
                  <span>刷新</span>
                </button>
              </div>
            </div>

            <div class="opc-cards-scroll">
              <div v-if="myDocumentsLoading && myDocuments.length === 0" class="posts-loading-banner glass-box">
                <span class="loading-spinner"></span>
                <span>正在从数据库加载我的文书...</span>
              </div>

              <div v-if="filteredMyDocuments.length > 0" class="sop-cards-container opc-cards-grid" id="sopMyDocsGrid">
                <SopMyDocCard
                  v-for="doc in filteredMyDocuments"
                  :key="doc.id"
                  :doc="doc"
                  :template-name-of="templateNameOf"
                  @open="openMyDocPage"
                  @delete="handleDeleteMyDocument"
                  @publish="handlePublishMyDocument"
                />
              </div>

              <div v-else-if="!myDocumentsLoading" class="glass-box empty-state-box">
                <div class="empty-icon-wrap">
                  <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                </div>
                <h3 class="empty-title">没有匹配的文书</h3>
                <p class="empty-desc">
                  {{ myDocSearchQuery ? `没有找到与 “${myDocSearchQuery}” 匹配的文书。` : '你还没有生成过文书。点右侧「创建文书」，从标准文书中挑选模板并填写要素，保存后就会出现在这里。' }}
                </p>
                <div class="empty-actions">
                  <button v-if="myDocSearchQuery" class="btn-liquid-outline" @click="handleMyDocClearSearch">清除搜索条件</button>
                </div>
              </div>
            </div>
          </template>

          <!-- ④ My flows — same layout as the flow-guide workspace -->
          <template v-else>
            <div class="glass-box feed-filter-bar">
              <div class="feed-filter-right">
                <div class="semantic-search-box">
                  <div class="search-input-wrap">
                    <input
                      v-model="myFlowSearchQuery"
                      type="text"
                      class="semantic-search-input"
                      placeholder="搜索我的流程..."
                      @keydown.enter="handleMyFlowSearch"
                    />
                    <button v-if="myFlowSearchQuery" type="button" class="clear-search-btn" @click="handleMyFlowClearSearch" title="清空搜索">×</button>
                  </div>
                </div>

                <div class="sort-segmented">
                  <button
                    v-for="opt in myFlowSortOptions"
                    :key="opt.key"
                    type="button"
                    :class="['sort-pill', { active: myFlowSort === opt.key }]"
                    @click="myFlowSort = opt.key"
                  >
                    <OpcIcon :name="opt.icon" :size="13" /> {{ opt.label }}
                  </button>
                </div>

                <button class="btn-liquid-outline refresh-mini-btn" @click="handleMyFlowRefresh" title="重新加载我的流程">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                  </svg>
                  <span>刷新</span>
                </button>
              </div>
            </div>

            <div class="opc-cards-scroll">
              <div v-if="myFlowsLoading && myFlowCards.length === 0" class="posts-loading-banner glass-box">
                <span class="loading-spinner"></span>
                <span>正在从数据库加载我的流程...</span>
              </div>

              <div v-if="filteredMyFlows.length > 0" class="sop-cards-container opc-cards-grid" id="sopMyFlowsGrid">
                <SopMyFlowCard
                  v-for="flow in filteredMyFlows"
                  :key="flow.id"
                  :flow="flow"
                  @open="openMyFlowPage"
                  @edit="openFlowBuilder"
                  @delete="handleDeleteFlow"
                  @publish="handlePublishMyFlow"
                />
              </div>

              <div v-else-if="!myFlowsLoading" class="glass-box empty-state-box">
                <div class="empty-icon-wrap">
                  <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <circle cx="6" cy="6" r="3"></circle>
                    <circle cx="18" cy="12" r="3"></circle>
                    <circle cx="6" cy="18" r="3"></circle>
                    <line x1="9" y1="7" x2="15" y2="11"></line>
                    <line x1="9" y1="17" x2="15" y2="13"></line>
                  </svg>
                </div>
                <h3 class="empty-title">没有匹配的流程</h3>
                <p class="empty-desc">
                  {{ myFlowSearchQuery ? `没有找到与 “${myFlowSearchQuery}” 匹配的流程。` : '你还没有创建过流程。点右侧「创建流程」，从节点库中挑选文书组成你的专属办理流程。' }}
                </p>
                <div class="empty-actions">
                  <button v-if="myFlowSearchQuery" class="btn-liquid-outline" @click="handleMyFlowClearSearch">清除搜索条件</button>
                </div>
              </div>
            </div>
          </template>
        </section>

        <!-- Right sidebar: contextual explanation (switches with the active view) -->
        <aside class="sop-feed-sidebar">
          <!-- ① Standard documents sidebar (workbench) -->
          <template v-if="viewMode === 'workbench'">
            <!-- 1. Document Publisher Center (发布新文档) -->
            <div class="glass-box sidebar-card creator-center-card">
              <div class="creator-card-header">
                <div class="creator-icon-orb">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                  </svg>
                </div>
                <div>
                  <h4 class="creator-title">标准文书中心</h4>
                  <p class="creator-desc">超级个体合规材料起草与留痕枢纽</p>
                </div>
              </div>
              <button class="btn-liquid btn-creator-publish" @click="openDocFromCatalog">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                <span>发布新文档</span>
              </button>
              <div class="creator-quick-links">
                <span class="quick-pill" @click="openDocByCategory('ENTITY')">主体登记</span>
                <span class="quick-pill" @click="openDocByCategory('TAX')">税务合规</span>
                <span class="quick-pill" @click="openDocByCategory('IP')">知识产权</span>
                <span class="quick-pill" @click="openDocByCategory('CROSS_BORDER')">跨境出海</span>
              </div>
            </div>

            <!-- 2. Today's Hot Document Rank (今日文书热榜) -->
            <div class="glass-box sidebar-card hot-ranking-card">
              <div class="sidebar-card-title-row">
                <div class="title-with-icon">
                  <span class="hot-badge-fire"><OpcIcon name="flame" :size="14" /></span>
                  <h4 class="sidebar-title">今日文书热榜</h4>
                </div>
                <span class="hot-subtitle">实时更新</span>
              </div>

              <div class="hot-ranking-list">
                <div
                  v-for="(item, idx) in hotRankDocuments"
                  :key="item.id"
                  class="hot-rank-item"
                  @click="handleOpenDocument(item)"
                >
                  <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                  <div class="hot-item-content">
                    <h5 class="hot-item-title">{{ item.name }}</h5>
                    <div class="hot-item-meta">
                      <span><OpcIcon name="flame" :size="12" /> {{ item.heat }} 热度</span>
                      <span class="dot-sep">·</span>
                      <span>{{ item.usedCount }} 人使用</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 3. Disclaimer (免责声明) -->
            <div class="glass-box sidebar-card guidelines-card">
              <h4 class="sidebar-title-sm">文书使用免责声明</h4>
              <p class="guidelines-desc">
                平台生成的文书为<strong>「标准化模板辅助起草」</strong>，不构成法律、税务或投资意见。正式提交前请自行复核条款细节与最新法规口径，必要时咨询执业律师或税务师。
              </p>
              <div class="guidelines-footer">
                <span>OpcHub 合规文书协议 v1.0</span>
                <span class="dot-sep">·</span>
                <span class="link-span" @click="viewMode = 'guide'">查看流程指引</span>
              </div>
            </div>
          </template>

          <!-- ② Flow sidebar (guide: 流程中心 / 今日流程热榜 / 免责声明) -->
          <template v-else-if="viewMode === 'guide'">
            <!-- 1. Flow Center (流程中心) -->
            <div class="glass-box sidebar-card creator-center-card">
              <div class="creator-card-header">
                <div class="creator-icon-orb">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <circle cx="6" cy="6" r="3"></circle>
                    <circle cx="18" cy="12" r="3"></circle>
                    <circle cx="6" cy="18" r="3"></circle>
                    <line x1="9" y1="7" x2="15" y2="11"></line>
                    <line x1="9" y1="17" x2="15" y2="13"></line>
                  </svg>
                </div>
                <div>
                  <h4 class="creator-title">流程中心</h4>
                  <p class="creator-desc">标准办事流程编排与复用枢纽</p>
                </div>
              </div>
              <button class="btn-liquid btn-creator-publish" @click="openFlowBuilder(null, 'guide')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                <span>发布新流程</span>
              </button>
              <div class="creator-quick-links">
                <span class="quick-pill" @click="flowCategory = 'ENTITY'">主体设立</span>
                <span class="quick-pill" @click="flowCategory = 'IP'">科技资质</span>
                <span class="quick-pill" @click="flowCategory = 'CROSS_BORDER'">跨境出海</span>
                <span class="quick-pill" @click="flowCategory = 'COMPLIANCE'">全生命周期</span>
              </div>
            </div>

            <!-- 2. Today's Hot Flow Rank (今日流程热榜) -->
            <div class="glass-box sidebar-card hot-ranking-card">
              <div class="sidebar-card-title-row">
                <div class="title-with-icon">
                  <span class="hot-badge-fire"><OpcIcon name="flame" :size="14" /></span>
                  <h4 class="sidebar-title">今日流程热榜</h4>
                </div>
                <span class="hot-subtitle">实时更新</span>
              </div>

              <div class="hot-ranking-list">
                <div
                  v-for="(item, idx) in hotRankFlows"
                  :key="item.id"
                  class="hot-rank-item"
                  @click="handleOpenFlow(item)"
                >
                  <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                  <div class="hot-item-content">
                    <h5 class="hot-item-title">{{ item.name }}</h5>
                    <div class="hot-item-meta">
                      <span><OpcIcon name="flame" :size="12" /> {{ item.heat }} 热度</span>
                      <span class="dot-sep">·</span>
                      <span>{{ item.usage_count }} 人使用</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 3. Disclaimer (免责声明) -->
            <div class="glass-box sidebar-card guidelines-card">
              <h4 class="sidebar-title-sm">流程使用免责声明</h4>
              <p class="guidelines-desc">
                平台提供的流程为<strong>「标准办事路径参考」</strong>，不构成法律、税务或投资意见。各地办理口径存在差异，落地前请自行核对最新监管要求，必要时咨询执业律师或税务师。
              </p>
              <div class="guidelines-footer">
                <span>OpcHub 流程编排协议 v1.0</span>
                <span class="dot-sep">·</span>
                <span class="link-span" @click="viewMode = 'workbench'">查看标准文书</span>
              </div>
            </div>
          </template>

          <!-- ③ My documents sidebar (mydocs: 我的文书中心 / 最近生成 / 免责声明) -->
          <template v-else-if="viewMode === 'mydocs'">
            <!-- 1. My Document Center (我的文书中心) -->
            <div class="glass-box sidebar-card creator-center-card">
              <div class="creator-card-header">
                <div class="creator-icon-orb">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" opacity="0.5"></rect>
                  </svg>
                </div>
                <div>
                  <h4 class="creator-title">我的文书中心</h4>
                  <p class="creator-desc">私有文书留痕与再利用枢纽</p>
                </div>
              </div>
              <button class="btn-liquid btn-creator-publish" @click="createNewMyDocument()">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                <span>创建文书</span>
              </button>
              <div class="creator-quick-links">
                <span class="quick-pill">{{ myDocuments.length }} 份私有文书</span>
                <span class="quick-pill" @click="myDocSort = 'new'">最新在前</span>
                <span class="quick-pill" @click="myDocSort = 'old'">最早在前</span>
              </div>
            </div>

            <!-- 2. Recently generated (最近生成) -->
            <div class="glass-box sidebar-card hot-ranking-card">
              <div class="sidebar-card-title-row">
                <div class="title-with-icon">
                  <span class="hot-badge-fire"><OpcIcon name="file" :size="14" /></span>
                  <h4 class="sidebar-title">最近生成</h4>
                </div>
                <span class="hot-subtitle">私有留痕</span>
              </div>

              <div class="hot-ranking-list">
                <div
                  v-for="(item, idx) in recentMyDocuments"
                  :key="item.id"
                  class="hot-rank-item"
                  @click="openMyDocPage(item)"
                >
                  <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                  <div class="hot-item-content">
                    <h5 class="hot-item-title">{{ item.document_title }}</h5>
                    <div class="hot-item-meta">
                      <span>{{ templateNameOf(item.template_id) }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="!recentMyDocuments.length" class="hot-empty-hint">还没有生成过文书。</div>
              </div>
            </div>

            <!-- 3. Disclaimer (免责声明) -->
            <div class="glass-box sidebar-card guidelines-card">
              <h4 class="sidebar-title-sm">私有文书说明</h4>
              <p class="guidelines-desc">
                「我的文书」是你<strong>个人起草并保存</strong>的合规文书，仅自己可见。文书内容为模板辅助生成，不构成法律、税务或投资意见，正式提交前请自行复核。
              </p>
              <div class="guidelines-footer">
                <span>OpcHub 私有文书协议 v1.0</span>
                <span class="dot-sep">·</span>
                <span class="link-span" @click="viewMode = 'workbench'">查看标准文书</span>
              </div>
            </div>
          </template>

          <!-- ④ My flows sidebar (flows: 我的流程中心 / 最近创建 / 免责声明) -->
          <template v-else>
            <!-- 1. My Flow Center (我的流程中心) -->
            <div class="glass-box sidebar-card creator-center-card">
              <div class="creator-card-header">
                <div class="creator-icon-orb">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <circle cx="6" cy="6" r="3"></circle>
                    <circle cx="18" cy="12" r="3"></circle>
                    <circle cx="6" cy="18" r="3"></circle>
                    <line x1="9" y1="7" x2="15" y2="11"></line>
                    <line x1="9" y1="17" x2="15" y2="13"></line>
                  </svg>
                </div>
                <div>
                  <h4 class="creator-title">我的流程中心</h4>
                  <p class="creator-desc">私有流程编排与复用枢纽</p>
                </div>
              </div>
              <button class="btn-liquid btn-creator-publish" @click="openFlowBuilder(null, 'flows')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                <span>创建流程</span>
              </button>
              <div class="creator-quick-links">
                <span class="quick-pill">{{ myFlows.length }} 条私有流程</span>
                <span class="quick-pill" @click="viewMode = 'guide'">逛逛平台流程</span>
              </div>
            </div>

            <!-- 2. Recently created (最近创建) -->
            <div class="glass-box sidebar-card hot-ranking-card">
              <div class="sidebar-card-title-row">
                <div class="title-with-icon">
                  <span class="hot-badge-fire"><OpcIcon name="compass" :size="14" /></span>
                  <h4 class="sidebar-title">最近创建</h4>
                </div>
                <span class="hot-subtitle">私有编排</span>
              </div>

              <div class="hot-ranking-list">
                <div
                  v-for="(item, idx) in recentMyFlows"
                  :key="item.id"
                  class="hot-rank-item"
                  @click="openMyFlowPage(item)"
                >
                  <span class="rank-num" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                  <div class="hot-item-content">
                    <h5 class="hot-item-title">{{ item.name }}</h5>
                    <div class="hot-item-meta">
                      <span>{{ (item.node_refs || []).length }} 个节点</span>
                    </div>
                  </div>
                </div>
                <div v-if="!recentMyFlows.length" class="hot-empty-hint">还没有创建过流程。</div>
              </div>
            </div>

            <!-- 3. Disclaimer (免责声明) -->
            <div class="glass-box sidebar-card guidelines-card">
              <h4 class="sidebar-title-sm">私有流程说明</h4>
              <p class="guidelines-desc">
                「我的流程」是你<strong>个人编排的办事路径</strong>，仅自己可见。流程仅作为个人办理提醒与文书入口，不构成法律、税务或投资意见。
              </p>
              <div class="guidelines-footer">
                <span>OpcHub 私有流程协议 v1.0</span>
                <span class="dot-sep">·</span>
                <span class="link-span" @click="viewMode = 'guide'">查看平台流程</span>
              </div>
            </div>
          </template>
        </aside>
      </div>
    </div>

    <!-- Subgraph expansion: one business outcome composed of several documents -->
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch, onMounted, onUnmounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import { enrichInteractions } from '@/utils/contentInteractions';
import SopDocumentCard from '@/components/sop/SopDocumentCard.vue';
import SopFlowBuilder from '@/components/sop/SopFlowBuilder.vue';
import SopFlowCard from '@/components/sop/SopFlowCard.vue';
import SopDocPage from '@/components/sop/SopDocPage.vue';
import SopFlowPage from '@/components/sop/SopFlowPage.vue';
import SopMyDocPage from '@/components/sop/SopMyDocPage.vue';
import SopMyDocCard from '@/components/sop/SopMyDocCard.vue';
import SopMyFlowCard from '@/components/sop/SopMyFlowCard.vue';

const emit = defineEmits(['toast', 'open-login']);

const currentUserSession = computed(() => safeSession());

const viewModes = [
  { key: 'workbench', label: '标准文书', desc: '官方标准文书库' },
  { key: 'guide', label: '流程向导', desc: '不懂流程也能走对' },
  { key: 'mydocs', label: '我的文书', desc: '我起草并保存的文书' },
  { key: 'flows', label: '我的流程', desc: '自建与复用流程' },
];

const viewMode = ref('workbench');

// Graph data
const stages = ref([]);
const nodes = ref([]);
const edges = ref([]);
const goals = ref([]);
// Standard document catalog (标准文书库) — read from PostgreSQL via sop.documents
const documentCatalog = ref([]);
// Platform flow catalog (标准流程库) — read from PostgreSQL via sop.flow.templates
const flowCatalog = ref([]);

const loading = ref(false);
const searchQuery = ref('');
const isSearchActive = ref(false);
const activeSearchQuery = ref('');
const currentCategory = ref('ALL');
const currentSort = ref('new');

const sortOptions = [
  { key: 'new', label: '最新发布', icon: 'bolt' },
  { key: 'hot', label: '最受欢迎', icon: 'flame' },
  { key: 'used', label: '真实使用', icon: 'book' },
];

// Flow-guide workspace state (mirrors the document workspace)
const flowLoading = ref(false);
const flowSearchQuery = ref('');
const isFlowSearchActive = ref(false);
const activeFlowSearchQuery = ref('');
const flowCategory = ref('ALL');
const flowSort = ref('hot');
// The flow currently opened on the full-page reader (same idiom as the doc page).
const flowPageDetail = ref(null);
const flowReturnMode = ref('guide');
// 我的流程详情与平台流程详情共用整页；owner 模式显示编辑/删除。
const flowOwnerMode = ref(false);

const flowSortOptions = [
  { key: 'hot', label: '最受欢迎', icon: 'flame' },
  { key: 'used', label: '真实使用', icon: 'book' },
  { key: 'new', label: '最新发布', icon: 'bolt' },
];

// User-authored documents (我的文书)
const myDocuments = ref([]);
const myDocumentsLoading = ref(false);
// 我的文书筛选与整页详情
const myDocSearchQuery = ref('');
const myDocSort = ref('new');
const myDocPageDoc = ref(null);
const myDocReturnMode = ref('mydocs');

// User-authored flows
const myFlows = ref([]);
const myFlowsLoading = ref(false);
// 我的流程筛选与整页详情
const myFlowSearchQuery = ref('');
const myFlowSort = ref('new');
const flowBuilderReturnMode = ref('flows');
const flowBuilderInitial = ref(null);
const editingFlowId = ref('');
const flowSubmitting = ref(false);

// Full-page document mode ('workspace' | 'doc')
const currentViewMode = ref('workspace');
const docPageNode = ref(null);
const docPageChildren = ref([]);
// Where the full-page document writer should return to on back.
const docReturnMode = ref('workspace');
// Creation entry (创建文书 / 发布新文档): keep the writing area open and show
// templates as a right-side panel instead of a full-page picker takeover.
const docCreationMode = ref(false);


const CATEGORY_LABELS = {
  ENTITY: '主体登记',
  TAX: '税务合规',
  LEGAL: '法律文书',
  BANK: '银行账户',
  IP: '知识产权',
  CROSS_BORDER: '跨境出海',
  FINANCE: '财务票据',
};

const categoryFilters = computed(() => {
  const used = new Set(documentCatalog.value.map((n) => n.category));
  const list = [{ key: 'ALL', label: '全部文书' }];
  for (const [key, label] of Object.entries(CATEGORY_LABELS)) {
    if (used.has(key)) list.push({ key, label });
  }
  return list;
});

const documentNodes = computed(() => nodes.value.filter((n) => n.kind === 'document'));
const subgraphNodes = computed(() => nodes.value.filter((n) => n.kind === 'subgraph'));

/**
 * The standard document catalog shown on the workbench.
 * Only documents live here — subgraphs are workflow structures, not documents.
 */
const filteredDocuments = computed(() => {
  let list = [...documentCatalog.value];

  if (currentCategory.value !== 'ALL') {
    list = list.filter((n) => n.category === currentCategory.value);
  }

  if (isSearchActive.value && activeSearchQuery.value) {
    const q = activeSearchQuery.value.toLowerCase();
    list = list.filter(
      (n) =>
        (n.name && n.name.toLowerCase().includes(q)) ||
        (n.summary && n.summary.toLowerCase().includes(q)) ||
        (n.author_name && n.author_name.toLowerCase().includes(q)) ||
        (n.publisher_org && n.publisher_org.toLowerCase().includes(q))
    );
  }

  if (currentSort.value === 'hot') {
    list.sort((a, b) => ((b.love_count ?? b.like_count) || 0) - ((a.love_count ?? a.like_count) || 0));
  } else if (currentSort.value === 'used') {
    list.sort((a, b) => (b.usage_count || 0) - (a.usage_count || 0));
  } else {
    list.sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));
  }
  return list;
});

/**
 * Today's hot document ranking.
 * Heat blends how many fields the document carries (more work -> more heat)
 * with how often it was already generated, mirroring the demands marketplace.
 */
const hotRankDocuments = computed(() => {
  return documentCatalog.value
    .map((doc) => ({
      ...doc,
      // Heat blends persisted 喜欢 (unified LOVE) with the real usage count.
      heat: ((doc.love_count ?? doc.like_count) || 0) + (doc.usage_count || 0) * 3,
      usedCount: doc.usage_count || 0,
    }))
    .sort((a, b) => b.heat - a.heat)
    .slice(0, 5);
});

const FLOW_CATEGORY_LABELS = {
  ENTITY: '主体设立',
  IP: '科技资质',
  CROSS_BORDER: '跨境出海',
  COMPLIANCE: '全生命周期',
};

const flowCategoryFilters = computed(() => {
  const used = new Set(flowCatalog.value.map((f) => f.category));
  const list = [{ key: 'ALL', label: '全部流程' }];
  for (const [key, label] of Object.entries(FLOW_CATEGORY_LABELS)) {
    if (used.has(key)) list.push({ key, label });
  }
  return list;
});

const filteredFlows = computed(() => {
  let list = [...flowCatalog.value];

  if (flowCategory.value !== 'ALL') {
    list = list.filter((f) => f.category === flowCategory.value);
  }

  if (isFlowSearchActive.value && activeFlowSearchQuery.value) {
    const q = activeFlowSearchQuery.value.toLowerCase();
    list = list.filter(
      (f) =>
        (f.name && f.name.toLowerCase().includes(q)) ||
        (f.summary && f.summary.toLowerCase().includes(q)) ||
        (f.description && f.description.toLowerCase().includes(q)) ||
        (f.author_name && f.author_name.toLowerCase().includes(q)) ||
        (f.publisher_org && f.publisher_org.toLowerCase().includes(q))
    );
  }

  if (flowSort.value === 'used') {
    list.sort((a, b) => (b.usage_count || 0) - (a.usage_count || 0));
  } else if (flowSort.value === 'new') {
    list.sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));
  } else {
    list.sort((a, b) => ((b.love_count ?? b.like_count) || 0) - ((a.love_count ?? a.like_count) || 0));
  }
  return list;
});

const hotRankFlows = computed(() => {
  return flowCatalog.value
    .map((flow) => ({
      ...flow,
      heat: ((flow.love_count ?? flow.like_count) || 0) + (flow.usage_count || 0) * 3,
    }))
    .sort((a, b) => b.heat - a.heat)
    .slice(0, 5);
});

// ---------------------------------------------------------------------------
// My documents (我的文书) — same filter/sort idiom as the standard workbench
// ---------------------------------------------------------------------------
const myDocSortOptions = [
  { key: 'new', label: '最新生成', icon: 'bolt' },
  { key: 'old', label: '最早生成', icon: 'clock' },
];

const filteredMyDocuments = computed(() => {
  let list = [...myDocuments.value];
  const q = myDocSearchQuery.value.trim().toLowerCase();
  if (q) {
    list = list.filter(
      (d) =>
        (d.document_title && d.document_title.toLowerCase().includes(q)) ||
        (d.template_id && templateNameOf(d.template_id).toLowerCase().includes(q))
    );
  }
  if (myDocSort.value === 'old') {
    list.sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));
  } else {
    list.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
  }
  return list;
});

const recentMyDocuments = computed(() => {
  return [...myDocuments.value]
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
    .slice(0, 5);
});

function handleMyDocSearch() {
  // search is live against myDocSearchQuery
}

function handleMyDocClearSearch() {
  myDocSearchQuery.value = '';
}

function handleMyDocRefresh() {
  loadMyDocuments();
  emit('toast', { title: '已刷新', message: '已同步最新私有文书。', type: 'INFO' });
}

// ---------------------------------------------------------------------------
// My flows (我的流程) — same filter/sort idiom as the flow-guide workspace
// ---------------------------------------------------------------------------
const myFlowSortOptions = [
  { key: 'new', label: '最新创建', icon: 'bolt' },
  { key: 'old', label: '最早创建', icon: 'clock' },
];

const filteredMyFlows = computed(() => {
  let list = [...myFlows.value];
  const q = myFlowSearchQuery.value.trim().toLowerCase();
  if (q) {
    list = list.filter(
      (f) =>
        (f.name && f.name.toLowerCase().includes(q)) ||
        (f.description && f.description.toLowerCase().includes(q)) ||
        (f.summary && f.summary.toLowerCase().includes(q))
    );
  }
  if (myFlowSort.value === 'old') {
    list.sort((a, b) => (a.published_at || '').localeCompare(b.published_at || ''));
  } else {
    list.sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));
  }
  return list;
});

const recentMyFlows = computed(() => {
  return [...myFlows.value]
    .sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''))
    .slice(0, 5);
});

function handleMyFlowSearch() {
  // search is live against myFlowSearchQuery
}

function handleMyFlowClearSearch() {
  myFlowSearchQuery.value = '';
}

function handleMyFlowRefresh() {
  loadMyFlows();
  emit('toast', { title: '已刷新', message: '已同步最新私有流程。', type: 'INFO' });
}

async function loadGraph() {
  loading.value = true;
  try {
    const res = await dispatchGateway('sop.graph', {}, { silent: true });
    if (res.ok && res.data) {
      stages.value = res.data.stages || [];
      nodes.value = res.data.nodes || [];
      edges.value = res.data.edges || [];
      goals.value = res.data.goals || [];
    } else {
      emit('toast', {
        title: '流程图谱加载受阻',
        message: res.error || '未能加载合规流程图谱，请稍后重试。',
        type: 'ERROR',
      });
    }
  } catch (e) {
    emit('toast', { title: '加载异常', message: '流程图谱服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    loading.value = false;
  }
}

/**
 * Load the standard document catalog.
 * The data comes from PostgreSQL (sop.nodes snapshots) via the sop.documents
 * gateway scenario — the workbench never renders hardcoded frontend records.
 */
async function loadDocumentCatalog() {
  const session = safeSession();
  try {
    const res = await dispatchGateway(
      'sop.documents',
      { user_id: session?.uid || '' },
      { silent: true }
    );
    if (res.ok && res.data) {
      documentCatalog.value = res.data.items || [];
      await enrichInteractions(documentCatalog.value, 'SOP_DOCUMENT');
    } else {
      documentCatalog.value = [];
    }
  } catch (e) {
    documentCatalog.value = [];
  }
}

/** Open a standard document in the full-page reader/writer. */
function handleOpenDocument(doc) {
  openDocPage(doc);
}

/**
 * Load the platform flow catalog.
 * The data comes from PostgreSQL (sop.flow_templates snapshots) via the
 * sop.flow.templates gateway scenario.
 */
async function loadFlowCatalog() {
  flowLoading.value = true;
  const session = safeSession();
  try {
    const res = await dispatchGateway(
      'sop.flow.templates',
      { user_id: session?.uid || '' },
      { silent: true }
    );
    if (res.ok && res.data) {
      flowCatalog.value = res.data.items || [];
      await enrichInteractions(flowCatalog.value, 'SOP_FLOW');
    } else {
      flowCatalog.value = [];
    }
  } catch (e) {
    flowCatalog.value = [];
  } finally {
    flowLoading.value = false;
  }
}

/** Open a flow on the full-page reader — same interaction as opening a standard
 * document: the page replaces the workspace, never a modal. */
function handleOpenFlow(flow) {
  flowReturnMode.value = viewMode.value || 'guide';
  flowOwnerMode.value = false;
  flowPageDetail.value = null;
  currentViewMode.value = 'flow';
  window.scrollTo({ top: 0, behavior: 'smooth' });
  dispatchGateway('sop.flow.template.detail', { flow_id: flow.id }, { silent: true })
    .then((res) => {
      if (res.ok && res.data) {
        flowPageDetail.value = res.data;
      } else {
        emit('toast', { title: '流程加载受阻', message: res.error || '未能加载该流程的步骤明细。', type: 'ERROR' });
        handleBackFromFlow();
      }
    })
    .catch(() => {
      emit('toast', { title: '加载异常', message: '流程服务暂时不可用，请稍后重试。', type: 'ERROR' });
      handleBackFromFlow();
    });
}

/** Leave the full-page flow reader and return to the originating workspace. */
function handleBackFromFlow() {
  currentViewMode.value = flowReturnMode.value || 'guide';
  flowPageDetail.value = null;
  flowOwnerMode.value = false;
}

async function handleLikeFlow(flow) {
  const res = await dispatchGateway('sop.flow.like', { flow_id: flow.id });
  if (res.ok && res.data) {
    flow.liked = res.data.liked;
    flow.like_count = res.data.like_count;
  } else {
    emit('toast', { title: '操作未完成', message: res.error || '喜欢操作未成功，请稍后重试。', type: 'ERROR' });
  }
}

async function handleFavoriteFlow(flow) {
  const res = await dispatchGateway('sop.flow.favorite', { flow_id: flow.id });
  if (res.ok && res.data) {
    flow.favorited = res.data.favorited;
    flow.favorite_count = res.data.favorite_count;
  } else {
    emit('toast', { title: '操作未完成', message: res.error || '收藏操作未成功，请稍后重试。', type: 'ERROR' });
  }
}

function handleFlowSearch() {
  const query = flowSearchQuery.value.trim();
  if (!query) {
    handleFlowClearSearch();
    return;
  }
  activeFlowSearchQuery.value = query;
  isFlowSearchActive.value = true;
}

function handleFlowClearSearch() {
  flowSearchQuery.value = '';
  activeFlowSearchQuery.value = '';
  isFlowSearchActive.value = false;
}

function handleFlowRefresh() {
  loadFlowCatalog();
  emit('toast', { title: '已刷新', message: '已同步最新标准流程库。', type: 'INFO' });
}

async function handleLikeDocument(doc) {
  const res = await dispatchGateway('sop.document.like', { node_id: doc.id });
  if (res.ok && res.data) {
    doc.liked = res.data.liked;
    doc.like_count = res.data.like_count;
  } else {
    emit('toast', { title: '操作未完成', message: res.error || '喜欢操作未成功，请稍后重试。', type: 'ERROR' });
  }
}

async function handleFavoriteDocument(doc) {
  const res = await dispatchGateway('sop.document.favorite', { node_id: doc.id });
  if (res.ok && res.data) {
    doc.favorited = res.data.favorited;
    doc.favorite_count = res.data.favorite_count;
  } else {
    emit('toast', { title: '操作未完成', message: res.error || '收藏操作未成功，请稍后重试。', type: 'ERROR' });
  }
}

function handleOpenNode(payload) {
  const nodeId = payload?.node_id || payload?.id;
  const node = nodes.value.find((n) => n.id === nodeId);
  if (!node) return;
  // A subgraph opens its composition list; a document opens the reader/writer.
  openDocPage(node);
}

// ---------------------------------------------------------------------------
// My documents (我的文书)
// ---------------------------------------------------------------------------
async function loadMyDocuments() {
  myDocumentsLoading.value = true;
  const session = safeSession();
  try {
    const res = await dispatchGateway(
      'sop.document.list',
      { user_id: session?.uid || '' },
      { silent: true }
    );
    if (res.ok && res.data) {
      myDocuments.value = Array.isArray(res.data) ? res.data : [];
    } else {
      myDocuments.value = [];
    }
  } catch (e) {
    myDocuments.value = [];
  } finally {
    myDocumentsLoading.value = false;
  }
}

/**
 * Open a private document on the full-page reader — same interaction as the
 * standard document page: the page replaces the workspace, never a modal.
 */
function openMyDocPage(doc) {
  if (!doc) return;
  myDocReturnMode.value = viewMode.value || 'mydocs';
  myDocPageDoc.value = doc;
  currentViewMode.value = 'mydoc';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleBackFromMyDoc() {
  currentViewMode.value = myDocReturnMode.value || 'mydocs';
  myDocPageDoc.value = null;
}

async function handleDeleteMyDocument(doc) {
  try {
    const res = await dispatchGateway('sop.document.delete', { doc_id: doc.id });
    if (res.ok) {
      emit('toast', { title: '文书已删除', message: `《${doc.document_title}》已移除。`, type: 'SUCCESS' });
      if (myDocPageDoc.value?.id === doc.id) {
        handleBackFromMyDoc();
      }
      await loadMyDocuments();
    } else {
      emit('toast', { title: '删除受阻', message: res.error || '文书删除未成功。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '删除异常', message: '文书删除服务暂时不可用，请稍后重试。', type: 'ERROR' });
  }
}

/**
 * Publish one of the maker's own documents: it is submitted to the review
 * queue and enters 待审核 (PENDING_REVIEW); the backend consumer audits it
 * and, on approval, publishes it into the 标准文书库.
 */
async function handlePublishMyDocument(doc) {
  const res = await dispatchGateway('sop.document.publish', { doc_id: doc.id });
  if (res.ok && res.data) {
    emit('toast', {
      title: '发布成功',
      message: `《${doc.document_title}》已提交审核，进入待审核状态；审核通过后将发布至标准文书库。`,
      type: 'SUCCESS',
    });
    await loadMyDocuments();
  } else {
    emit('toast', { title: '发布未完成', message: res.error || '提交审核未成功，请稍后重试。', type: 'ERROR' });
  }
}

function templateNameOf(templateId) {
  const node = nodes.value.find((n) => n.id === templateId);
  return node?.name || templateId || '标准文书';
}

// ---------------------------------------------------------------------------
// User-authored flows
// ---------------------------------------------------------------------------
/**
 * Load the maker's own flows as cards (same idiom as the platform flow catalog).
 */
async function loadMyFlows() {
  myFlowsLoading.value = true;
  const session = safeSession();
  try {
    const res = await dispatchGateway(
      'sop.myflow.cards',
      { owner_id: session?.uid || '' },
      { silent: true }
    );
    if (res.ok && res.data) {
      myFlows.value = Array.isArray(res.data) ? res.data : [];
    } else {
      myFlows.value = [];
    }
  } catch (e) {
    myFlows.value = [];
  } finally {
    myFlowsLoading.value = false;
  }
}

/**
 * Open one of the maker's own flows on the full-page reader — same interaction
 * as opening a platform flow, but in owner mode (edit / delete available).
 */
function openMyFlowPage(flow) {
  if (!flow) return;
  flowReturnMode.value = viewMode.value || 'flows';
  flowOwnerMode.value = true;
  flowPageDetail.value = null;
  currentViewMode.value = 'flow';
  window.scrollTo({ top: 0, behavior: 'smooth' });
  dispatchGateway('sop.flow.get', { flow_id: flow.id }, { silent: true })
    .then((res) => {
      if (res.ok && res.data) {
        const stages = [...new Set((res.data.items || []).map((i) => i.stage))].sort((a, b) => a - b);
        flowPageDetail.value = {
          template: {
            ...res.data.flow,
            category: 'MY',
            stages,
            outcome: '',
            unlocks: [],
            is_official: false,
            publisher_org: '私有流程',
            author_name: '我',
            author_title: '流程编排人',
          },
          steps: res.data.items || [],
          missing_nodes: res.data.missing_nodes || [],
        };
      } else {
        emit('toast', { title: '流程加载受阻', message: res.error || '未能加载该流程。', type: 'ERROR' });
        handleBackFromFlow();
      }
    })
    .catch(() => {
      emit('toast', { title: '加载异常', message: '流程服务暂时不可用，请稍后重试。', type: 'ERROR' });
      handleBackFromFlow();
    });
}

/** Edit one of the maker's own flows from the full-page reader. */
function handleEditMyFlow(flow) {
  openFlowBuilder(flow);
}

/** Delete one of the maker's own flows from the full-page reader. */
async function handleDeleteMyFlowFromPage(flow) {
  await handleDeleteFlow(flow);
  handleBackFromFlow();
}

/**
 * Open the flow builder as a full page on the current tab.
 *
 * With a flow argument it edits that personal flow. Without one it creates a
 * new flow, pre-filled from the platform flow currently being inspected so the
 * maker can fork a standard flow into their own.
 *
 * `returnMode` controls where "back" lands after the builder closes. It is
 * passed explicitly by the sidebar buttons ('flows' / 'guide'); when omitted it
 * is inferred from the context: editing from the full-page flow reader returns
 * to that flow page, anything else returns to the active mode tab. The builder
 * never navigates to another mode tab — it replaces the workspace in place.
 */
function openFlowBuilder(flow = null, returnMode = null) {
  // Guard against a DOM event being passed in as the flow argument.
  const target = flow && typeof flow === 'object' && !flow.type ? flow : null;
  if (target) {
    editingFlowId.value = target.id || '';
    flowBuilderInitial.value = {
      name: target.name,
      description: target.description,
      goal_id: target.goal_id || '',
      node_refs: (target.node_refs || []).map((r) => ({ ...r })),
    };
  } else {
    const source = flowPageDetail.value?.template;
    editingFlowId.value = '';
    flowBuilderInitial.value = {
      name: source ? `${source.name} · 我的流程` : '',
      description: source ? (source.description || source.summary || '') : '',
      goal_id: '',
      node_refs: source ? (source.node_refs || []).map((r) => ({ ...r })) : [],
    };
  }
  flowBuilderReturnMode.value =
    returnMode || (currentViewMode.value === 'flow' ? 'flow' : (viewMode.value || 'flows'));
  currentViewMode.value = 'flowbuilder';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function closeFlowBuilder() {
  if (currentViewMode.value !== 'flowbuilder') return;
  const returnMode = flowBuilderReturnMode.value || 'flows';
  const editedId = editingFlowId.value;
  flowBuilderReturnMode.value = 'flows';
  flowBuilderInitial.value = null;
  editingFlowId.value = '';
  if (returnMode === 'flow' && editedId) {
    // Editing from the full-page flow reader: reopen the (updated) flow page.
    const flow = myFlows.value.find((f) => f.id === editedId);
    if (flow) openMyFlowPage(flow);
    else currentViewMode.value = 'flows';
  } else {
    currentViewMode.value = returnMode;
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function submitFlow(payload) {
  if (!payload.name || payload.name.length < 2) {
    emit('toast', { title: '信息不全', message: '请为流程取一个至少 2 个字的名字。', type: 'WARN' });
    return;
  }
  if (!payload.node_refs.length) {
    emit('toast', { title: '信息不全', message: '请至少选择一个流程节点。', type: 'WARN' });
    return;
  }

  flowSubmitting.value = true;
  try {
    const scene = editingFlowId.value ? 'sop.flow.update' : 'sop.flow.create';
    const body = { ...payload };
    if (editingFlowId.value) body.flow_id = editingFlowId.value;

    const res = await dispatchGateway(scene, body);
    if (res.ok) {
      emit('toast', {
        title: editingFlowId.value ? '流程已更新' : '流程创建成功',
        message: `《${payload.name}》已保存，可在「我的流程」中随时打开继续办理。`,
        type: 'SUCCESS',
      });
      closeFlowBuilder();
      await loadMyFlows();
    } else {
      emit('toast', {
        title: '保存受阻',
        message: res.error || '流程保存未成功，请稍后重试。',
        type: 'ERROR',
      });
    }
  } catch (e) {
    emit('toast', { title: '保存异常', message: '流程保存服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    flowSubmitting.value = false;
  }
}

async function handleDeleteFlow(flow) {
  flowSubmitting.value = true;
  try {
    const res = await dispatchGateway('sop.flow.delete', { flow_id: flow.id });
    if (res.ok) {
      emit('toast', { title: '流程已删除', message: `《${flow.name}》已移除。`, type: 'SUCCESS' });
      await loadMyFlows();
    } else {
      emit('toast', { title: '删除受阻', message: res.error || '流程删除未成功。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '删除异常', message: '流程删除服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    flowSubmitting.value = false;
  }
}

/**
 * Publish one of the maker's own flows: it is submitted to the review queue
 * and enters 待审核 (PENDING_REVIEW); the backend consumer audits it and, on
 * approval, publishes it into the 流程向导.
 */
async function handlePublishMyFlow(flow) {
  const res = await dispatchGateway('sop.flow.publish', { flow_id: flow.id });
  if (res.ok && res.data) {
    emit('toast', {
      title: '发布成功',
      message: `《${flow.name}》已提交审核，进入待审核状态；审核通过后将发布至流程向导。`,
      type: 'SUCCESS',
    });
    await loadMyFlows();
  } else {
    emit('toast', { title: '发布未完成', message: res.error || '提交审核未成功，请稍后重试。', type: 'ERROR' });
  }
}

function groupName(parentId) {
  const node = nodes.value.find((n) => n.id === parentId);
  return node ? node.name : parentId;
}

/**
 * Open the full-page document reader/writer for a node.
 * The document page owns its own form state, so the workspace keeps no copy.
 */
function openDocPage(node) {
  if (!node) return;
  const nodeId = node.node_id || node.id;
  const target = nodes.value.find((n) => n.id === nodeId);
  if (!target) {
    emit('toast', { title: '节点缺失', message: '该文书节点在图谱中不存在。', type: 'ERROR' });
    return;
  }
  // Remember where the writer was opened from so back returns to the same
  // page — a flow step keeps the flow page, everything else keeps the tab.
  docReturnMode.value = currentViewMode.value === 'flow' ? 'flow' : 'workspace';
  docCreationMode.value = false;
  docPageNode.value = target;
  docPageChildren.value = target.kind === 'subgraph' ? subgraphChildren(target) : [];
  currentViewMode.value = 'doc';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/** Resolve the document children of a subgraph from the graph itself. */
function subgraphChildren(subgraph) {
  const out = [];
  const walk = (nodeId) => {
    const node = nodes.value.find((n) => n.id === nodeId);
    if (!node) return;
    if (node.kind === 'subgraph') {
      node.children.forEach(walk);
      return;
    }
    out.push(node);
  };
  (subgraph.children || []).forEach(walk);
  return out;
}

/** Pick another document from within the page (subgraph child or template picker). */
function handlePickDocument(doc) {
  const target = nodes.value.find((n) => n.id === (doc?.id || doc?.node_id));
  if (!target) return;
  docPageNode.value = target;
  docPageChildren.value = target.kind === 'subgraph' ? subgraphChildren(target) : [];
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * A document was just saved from the writer (SopDocPage「保存文书」).
 * Refresh「我的文书」so the newly created document shows up immediately.
 */
async function handleDocumentSaved(savedDoc) {
  try {
    await loadMyDocuments();
  } catch (e) {
    // The writer already toasts success; list refresh failure is non-fatal.
  }
  // A freshly-created document should be immediately visible. Leave the blank
  // creation page and land on 我的文书, where saved documents live, so the maker
  // sees the new document appear in the (already refreshed) list.
  if (docCreationMode.value) {
    docCreationMode.value = false;
    docReturnMode.value = 'mydocs';
    docPageNode.value = null;
    docPageChildren.value = [];
    currentViewMode.value = 'mydocs';
    viewMode.value = 'mydocs';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function handleBackFromDoc() {
  currentViewMode.value = docReturnMode.value || 'workspace';
  docReturnMode.value = 'workspace';
  docCreationMode.value = false;
  docPageNode.value = null;
  docPageChildren.value = [];
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/** Open the first document of a category — used by the sidebar quick links. */
function openDocByCategory(category) {
  const target = documentNodes.value.find((n) => n.category === category);
  if (target) {
    openDocPage(target);
    return;
  }
  emit('toast', { title: '暂无该类文书', message: '该分类下还没有可填写的标准文书。', type: 'INFO' });
}

/** Open the template picker so the maker can start a brand new document. */
function openDocFromCatalog() {
  docReturnMode.value = 'workspace';
  docCreationMode.value = true;
  docPageNode.value = null;
  docPageChildren.value = [];
  currentViewMode.value = 'doc';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Open the document writer from 我的文书 — stays on the current tab instead of
 * navigating to the 标准文书 workbench. Back returns to 我的文书.
 */
function createNewMyDocument() {
  docReturnMode.value = 'mydocs';
  docCreationMode.value = true;
  docPageNode.value = null;
  docPageChildren.value = [];
  currentViewMode.value = 'doc';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function safeSession() {
  try {
    const raw = localStorage.getItem('opchub_user_session');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function handleSearch() {
  const query = searchQuery.value.trim();
  if (!query) {
    handleClearSearch();
    return;
  }
  activeSearchQuery.value = query;
  isSearchActive.value = true;
}

function handleClearSearch() {
  searchQuery.value = '';
  activeSearchQuery.value = '';
  isSearchActive.value = false;
}

function handleRefresh() {
  loadGraph();
  loadDocumentCatalog();
  emit('toast', { title: '已刷新', message: '已同步最新标准文书库与流程图谱。', type: 'INFO' });
}

watch(viewMode, (mode) => {
  // 流程向导与标准文书一致：只有点击流程卡片才打开详情，不自动展开。
  if (mode === 'guide') {
    loadFlowCatalog();
  }
  if (mode === 'mydocs') {
    loadMyDocuments();
  }
  if (mode === 'flows') {
    loadMyFlows();
  }
});

onMounted(() => {
  document.body.classList.add('fixed-screen-feed');
  loadGraph();
  loadDocumentCatalog();
  loadFlowCatalog();
  loadMyDocuments();
  loadMyFlows();
});

onUnmounted(() => {
  document.body.classList.remove('fixed-screen-feed');
});
</script>

<style scoped>
.sop-view-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.sop-main-content {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.sop-mode-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 14px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.sop-mode-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sop-mode-tab {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 16px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.sop-mode-tab:hover {
  background: var(--glass-surface-subtle);
}

.sop-mode-tab.active {
  background: rgba(0, 113, 227, 0.1);
  border-color: rgba(0, 113, 227, 0.25);
}

.sop-mode-tab-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.sop-mode-tab.active .sop-mode-tab-label {
  color: var(--accent);
}

.sop-mode-tab-desc {
  font-size: 11px;
  color: var(--text-tertiary);
}

.sop-mode-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sop-mode-stat {
  font-size: 11.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

/* Dual-column feed layout identical to Product Showcase */
.sop-feed-layout {
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

.sop-feed-stream {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}

.sop-feed-sidebar {
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

.sop-feed-sidebar::-webkit-scrollbar {
  display: none;
}

.feed-filter-bar {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  margin-bottom: 12px;
  border-radius: var(--radius-md, 14px);
  gap: 12px;
  flex-wrap: wrap;
  background: var(--glass-surface);
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
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-primary);
  outline: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.semantic-search-input:focus {
  width: 250px;
  background: var(--glass-surface);
  border-color: var(--accent);
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-bottom: 12px;
  border-radius: var(--radius-md, 12px);
  background: linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
  border: 1px solid var(--glass-border-subtle);
  font-size: 12.5px;
  gap: 12px;
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

/* 滚动容器与卡片网格：由全局统一卡片体系 (.opc-cards-scroll / .opc-cards-grid) 承载 */

.posts-loading-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 20px;
  border-radius: var(--radius-md, 12px);
  font-size: 12.5px;
  color: var(--text-tertiary);
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

/* Sidebar */
.sidebar-card {
  flex-shrink: 0;
  margin: 0;
  padding: 18px 20px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  box-sizing: border-box;
  width: 100%;
}

.sidebar-card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Creator center (标准文书中心) — same anatomy as the demands marketplace */
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

.hot-badge-fire {
  font-size: 15px;
}

/* Hot ranking list (今日文书热榜) — same anatomy as the demands marketplace */
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

.sidebar-title-sm {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
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
  border-radius: var(--radius-full);
}

/* Empty hint inside a hot-ranking list */
.hot-empty-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  padding: 10px 2px;
}

/* Full-page flow builder */
.sop-flow-builder-page {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
  gap: 14px;
}

.sop-flow-builder-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 22px;
  border-radius: var(--radius-md, 14px);
}

.sop-flow-builder-title-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.sop-flow-builder-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12.5px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.sop-flow-builder-title {
  font-size: 19px;
  font-weight: 700;
  margin: 0 0 4px 0;
}

.sop-flow-builder-sub {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

.sop-flow-builder-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 22px;
  border-radius: var(--radius-md, 14px);
  scrollbar-width: none;
}

.sop-flow-builder-body::-webkit-scrollbar {
  display: none;
}

.dot-sep {
  opacity: 0.5;
}

/* Responsive */
@media (max-width: 960px) {
  .sop-feed-layout {
    flex-direction: column;
  }
  .sop-feed-sidebar {
    width: 100%;
    position: static;
    max-height: none;
  }
  .opc-cards-grid {
    grid-template-columns: 1fr;
  }
}

[data-theme="dark"] .sidebar-card,
[data-theme="dark"] .feed-filter-bar {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}
</style>
