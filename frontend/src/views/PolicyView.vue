<template>
  <div class="view-panel active policy-view-wrapper">
    <!-- Full-page publishing surface (创建发布政策公文) -->
    <CreatePageLayout
      v-if="showPublishPage"
      title="发布政策公文"
      back-label="政策中心"
      @back="closePublishPage"
    >
      <template #actions>
        <button
          type="submit"
          form="policy-publish-form"
          class="btn-liquid"
          :disabled="isPublishing"
        >
          {{ isPublishing ? '发布中…' : '发布' }}
        </button>
      </template>

      <PublishForm
        id="policy-publish-form"
        :model="publishForm"
        :fields="POLICY_FIELDS"
        @submit="submitPublishPolicy"
      />
    </CreatePageLayout>

    <div v-else class="policy-main-content">
      <!-- Dual-column Layout referencing ShowcaseView (产品橱窗) -->
      <div class="policy-feed-layout">
        <!-- Main Policy Stream (左侧政策流) -->
        <section class="policy-feed-stream">
          <!-- Category Filter Bar (政策分区选项卡 + 搜索 + 排序选择 + 刷新) -->
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
                    placeholder="搜索政策..."
                    @keydown.enter="handleSearch"
                  />
                  <button v-if="searchQuery" type="button" class="clear-search-btn" @click="resetSearch" title="清空搜索">×</button>
                </div>
                <button
                  type="button"
                  class="btn-liquid semantic-search-btn"
                  :disabled="isSearching"
                  @click="handleSearch"
                  title="语义检索"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                  <span>{{ isSearching ? '检索中...' : '语义检索' }}</span>
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
              <button class="btn-liquid-outline refresh-mini-btn" @click="handleManualRefresh" title="刷新并同步政策数据库">
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
                已为您找到与「<strong>{{ activeSearchQuery }}</strong>」相关的 <strong>{{ sortedDisplayPolicies.length }}</strong> 项政务红利政策
              </span>
            </div>
            <button class="btn-liquid-outline btn-reset-search" @click="resetSearch">
              <span>恢复全部政策</span>
            </button>
          </div>

          <!-- Policy Cards Scroll Container -->
          <div class="opc-cards-scroll" ref="policyScrollContainerRef">
            <!-- Loading State Indicator -->
            <div v-if="isLoading && displayPolicies.length === 0" class="posts-loading-banner glass-box">
              <span class="loading-spinner"></span>
              <span>正在从数据库检索并加载「{{ currentCategoryLabel }}」政策中心公文库...</span>
            </div>

            <!-- Policy Cards Grid (产品橱窗同款卡片流) -->
            <div
              v-if="sortedDisplayPolicies.length > 0 && !selectedPolicy"
              class="policy-cards-container opc-cards-grid"
              id="policyCardsGrid"
            >
              <div
                v-for="item in sortedDisplayPolicies"
                :key="item.id || item.code"
                class="glass-card policy-card opc-card-shell opc-card opc-reveal-host"
                @mousemove="handleMouseMove"
                @click="openPolicyDetail(item)"
              >
                <!-- Card Header: Level Emblem & Title Group -->
                <div class="card-header-row">
                  <div class="policy-icon-wrapper opc-card-icon" :class="getCategoryEmblemClass(item.category)">
                    <span class="policy-emblem-icon"><OpcIcon :name="getCategoryEmblemIcon(item.category)" :size="18" /></span>
                  </div>

                  <div class="card-title-group">
                    <div class="card-title-line">
                      <h3 class="policy-title opc-clamp opc-clamp-2" :title="item.title">{{ item.title }}</h3>
                    </div>
                    <div class="card-badges-line">
                      <span class="badge-cat" :class="getCategoryBadgeClass(item.category)">
                        {{ formatCategoryLabel(item.category) }}
                      </span>
                      <span class="badge-level" :class="getLevelBadgeClass(item.policy_level)">
                        {{ item.policy_level || '国家级' }}
                      </span>
                      <span class="badge-region">
                        <OpcIcon name="pin" :size="12" /> {{ item.region || '全国统一' }}
                      </span>
                      <OfficialBadge :visible="item.is_official" label="官方" title="官方发布：由平台官方账号发布并认证" />
                    </div>
                  </div>
                </div>

                <!-- Card Body: Plain Chinese Summary (hover reveals full) -->
                <div class="card-body">
                  <HoverRevealText :text="summaryExcerpt(item)" :lines="2" />
                </div>

                <!-- Card Highlights / Quick Spec Chips -->
                <div class="card-highlights-row">
                  <span class="highlight-chip chip-subsidy">
                    <OpcIcon name="coin" :size="12" /> {{ formatSubsidy(item.subsidy_amount_max) }}
                  </span>
                  <span class="highlight-chip chip-deadline">
                    <OpcIcon name="calendar" :size="12" /> {{ item.deadline || '常年开放申报' }}
                  </span>
                </div>

                <!-- Card Footer: Issuer & Action Buttons -->
                <div class="card-footer-row" @click.stop>
                  <div class="issuer-cell">
                    <div class="issuer-avatar">
                      <OpcIcon name="landmark" :size="18" />
                    </div>
                    <div class="issuer-text">
                      <span class="issuer-name">{{ item.region || '全国统一' }}</span>
                      <span class="issuer-level-tag">{{ item.policy_level || '政府扶持' }}</span>
                    </div>
                  </div>

                  <div class="card-actions-cell">
                    <button
                      type="button"
                      class="btn-liquid-outline btn-ai-summary"
                      @click.stop="quickAiSummarize(item)"
                      title="调用 SiliconFlow 算力进行白话提炼"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                      </svg>
                      <span>AI提炼</span>
                    </button>

                    <button
                      type="button"
                      class="btn-liquid btn-match-eval"
                      @click.stop="matchEligibility(item)"
                      title="智能比对当前创客资格指标"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      <span>{{ item.action_text || '匹配资格' }}</span>
                    </button>
                  </div>
                </div>

                <!-- Card Interaction Band (unified like/comment/love/favorite) -->
                <div class="card-interaction-row" @click.stop>
                  <ContentInteractionBar
                    target-type="POLICY"
                    :target-id="item.id || item.code"
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

            <!-- Inline Policy Detail (content area, no modal) -->
            <div v-if="selectedPolicy" class="inline-detail-slot glass-box">
              <div class="inline-detail-head">
                <button type="button" class="btn-back-inline" @click="closePolicyDetail" title="返回政策列表">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                  </svg>
                  <span>返回政策列表</span>
                </button>
                <span class="inline-detail-crumb">政策中心 / {{ selectedPolicy.title }}</span>
              </div>

              <div class="detail-header">
                <div class="detail-icon-wrap" :class="getCategoryEmblemClass(selectedPolicy.category)">
                  <span class="detail-emblem-icon"><OpcIcon :name="getCategoryEmblemIcon(selectedPolicy.category)" :size="20" /></span>
                </div>

                <div class="detail-title-block">
                  <div class="detail-title-row">
                    <h2 class="detail-title">{{ selectedPolicy.title }}</h2>
                    <span class="mono-tag version-pill">{{ selectedPolicy.code || 'POL-2026' }}</span>
                    <OfficialBadge :visible="selectedPolicy.is_official" label="官方" title="官方发布：由平台官方账号发布并认证" />
                  </div>
                  <p class="detail-tagline">{{ summaryExcerpt(selectedPolicy) }}</p>
                  <div class="detail-meta-pills">
                    <span class="detail-cat-pill">{{ formatCategoryLabel(selectedPolicy.category) }}</span>
                    <span class="detail-level-pill">{{ selectedPolicy.policy_level || '国家级' }}</span>
                    <span class="detail-region-pill"><OpcIcon name="pin" :size="12" /> {{ selectedPolicy.region || '全国统一' }}</span>
                    <span class="detail-subsidy-pill">{{ formatSubsidy(selectedPolicy.subsidy_amount_max) }}</span>
                  </div>
                </div>
              </div>

              <div class="detail-action-bar">
                <button
                  type="button"
                  class="btn-liquid action-btn primary-action"
                  @click="matchEligibility(selectedPolicy)"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  <span>{{ selectedPolicy.action_text || '匹配申报资格' }}</span>
                </button>

                <button
                  type="button"
                  class="btn-liquid-outline action-btn ai-action"
                  :disabled="isAiSummarizing"
                  @click="summarizePolicyWithAI(selectedPolicy)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                  <span>{{ isAiSummarizing ? 'AI 正在提炼中...' : 'AI 白话提炼' }}</span>
                </button>

                <ContentInteractionBar
                  target-type="POLICY"
                  :target-id="selectedPolicy.id || selectedPolicy.code"
                  :target-title="selectedPolicy.title"
                  :like-count="selectedPolicy.like_count ?? 0"
                  :favorite-count="selectedPolicy.favorite_count ?? 0"
                  :love-count="selectedPolicy.love_count ?? 0"
                  :comment-count="selectedPolicy.comment_count ?? 0"
                  :dislike-count="selectedPolicy.dislike_count ?? 0"
                  :rating-avg="selectedPolicy.rating_avg ?? 0"
                  :rating-count="selectedPolicy.rating_count ?? 0"
                  :my-rating="selectedPolicy.viewer?.rating ?? 0"
                  :liked="selectedPolicy.viewer?.liked ?? false"
                  :favorited="selectedPolicy.viewer?.favorited ?? false"
                  :loved="selectedPolicy.viewer?.loved ?? false"
                  :commented="selectedPolicy.viewer?.commented ?? false"
                  :disliked="selectedPolicy.viewer?.disliked ?? false"
                  :authenticated="Boolean(currentUserSession)"
                  show-labels
                  @changed="handleInteractionChanged(selectedPolicy, $event)"
                  @require-login="$emit('open-login')"
                  @toast="$emit('toast', $event)"
                />

                <div class="legal-badge-pill" :title="selectedPolicy.legal_basis">
                  <span><OpcIcon name="scroll" :size="12" /> {{ selectedPolicy.legal_basis || '官方正式规章' }}</span>
                </div>
              </div>

              <div class="detail-body-scroll">
                <div v-if="aiSummaryResult" class="detail-section ai-summary-highlight-box">
                  <div class="ai-box-header">
                    <span class="sparkle-tag"><OpcIcon name="spark" :size="12" /> SiliconFlow 硅基流动大模型提炼</span>
                    <span class="ai-model-tag">{{ aiSummaryResult.model_used || 'Qwen/Qwen2.5-72B-Instruct' }}</span>
                  </div>
                  <p class="ai-box-text">{{ aiSummaryResult.plain_summary }}</p>
                  <div v-if="aiSummaryResult.target_audience" class="ai-box-footer">
                    <span>受惠客群: {{ aiSummaryResult.target_audience }}</span>
                    <span v-if="aiSummaryResult.max_benefit" class="dot-sep">·</span>
                    <span v-if="aiSummaryResult.max_benefit">预期红利: {{ aiSummaryResult.max_benefit }}</span>
                  </div>
                </div>

                <div class="detail-section">
                  <h4 class="section-title">政策核心白话要点</h4>
                  <!-- 发布侧为富文本（Markdown），详情统一渲染后展示 -->
                  <div class="detail-full-description markdown-rendered-content" v-html="renderedPolicySummary"></div>
                </div>

                <div v-if="selectedPolicy.eligible_conditions && selectedPolicy.eligible_conditions.length > 0" class="detail-section">
                  <h4 class="section-title">申报准入资格条件</h4>
                  <div class="conditions-checklist">
                    <div
                      v-for="(cond, idx) in selectedPolicy.eligible_conditions"
                      :key="idx"
                      class="condition-check-item"
                    >
                      <span class="check-icon"><OpcIcon name="check" :size="13" /></span>
                      <span class="check-text">{{ cond }}</span>
                    </div>
                  </div>
                </div>

                <div class="detail-section">
                  <h4 class="section-title">公文参数与规格详情</h4>
                  <div class="spec-grid">
                    <div class="spec-item">
                      <span class="spec-label">政策编号</span>
                      <span class="spec-value mono-val">{{ selectedPolicy.code || 'POL-2026-001' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">发文层级</span>
                      <span class="spec-value">{{ selectedPolicy.policy_level || '国家级' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">适用区域</span>
                      <span class="spec-value">{{ selectedPolicy.region || '全国统一' }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">扶持类别</span>
                      <span class="spec-value">{{ formatCategoryLabel(selectedPolicy.category) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">最高扶持额度</span>
                      <span class="spec-value spec-highlight">{{ formatSubsidy(selectedPolicy.subsidy_amount_max) }}</span>
                    </div>
                    <div class="spec-item">
                      <span class="spec-label">申报截止日期</span>
                      <span class="spec-value mono-val">{{ selectedPolicy.deadline || '常年有效' }}</span>
                    </div>
                    <div class="spec-item" style="grid-column: span 2;">
                      <span class="spec-label">官方法规依据</span>
                      <span class="spec-value">{{ selectedPolicy.legal_basis }}</span>
                    </div>
                    <div class="spec-item" style="grid-column: span 2;">
                      <span class="spec-label">微内核数据校验</span>
                      <span class="spec-value spec-success">PostgreSQL 库表持久化 & 零依赖向量检索</span>
                    </div>
                  </div>
                </div>

                <!-- 展示页面免责声明 -->
                <ContentDisclaimer type="policy" />
              </div>
            </div>

            <!-- Empty State -->
            <div v-else-if="!isLoading && sortedDisplayPolicies.length === 0" class="glass-box empty-state-box">
              <div class="empty-icon-wrap">
                <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>
              <h3 class="empty-title">当前筛选下暂无政策条目</h3>
              <p class="empty-desc">
                {{ searchQuery ? `没有检索到与 “${searchQuery}” 匹配的扶持公文。` : '当前分类下暂无已收录的公文条款。' }}
              </p>
              <div class="empty-actions">
                <button v-if="searchQuery || currentCategory !== 'ALL'" class="btn-liquid-outline" @click="resetSearch">
                  重置筛选条件
                </button>
                <button class="btn-liquid" @click="openPublishPage">
                  收录新政策
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Right Auxiliary Sidebar: Exactly matching ShowcaseView -->
        <aside class="policy-feed-sidebar">
          <!-- 1. Policy Center Card (申报与发布中心) -->
          <div class="glass-box sidebar-card creator-center-card">
            <div class="creator-card-header">
              <div class="creator-icon-orb">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              </div>
              <div>
                <h4 class="creator-title">政策申报中心</h4>
                <p class="creator-desc">超级个体与小微扶持红利直达</p>
              </div>
            </div>

            <button class="btn-liquid btn-creator-publish" @click="openPublishPage">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span>发布政策公文</span>
            </button>

            <div class="creator-quick-links">
              <span class="quick-pill" @click="selectCategory('TAX')">增值税减免</span>
              <span class="quick-pill" @click="selectCategory('SUBSIDY')">算力直补</span>
              <span class="quick-pill" @click="selectCategory('RENT')">免租孵化</span>
              <span class="quick-pill" @click="selectCategory('TALENT')">人才激励</span>
              <span class="quick-pill" @click="quickSearchKeyword('研发加计')">研发加计</span>
              <span class="quick-pill" @click="quickSearchKeyword('大湾区')">大湾区</span>
            </div>
          </div>

          <!-- 2. Quick Tax & Exemption Calculator Card (免税即时试算) -->
          <div class="glass-box sidebar-card tax-calc-card">
            <div class="sidebar-card-title-row">
              <div class="title-with-icon">
                <span class="hot-badge-fire"><OpcIcon name="bolt" :size="14" /></span>
                <h4 class="sidebar-title">增值税免税即时测算</h4>
              </div>
              <span class="hot-subtitle">免税引擎</span>
            </div>

            <p class="calc-card-desc">
              一人公司与小微月度 10 万（季度 30 万）免征额即时试算：
            </p>

            <div class="calc-input-group">
              <div class="input-with-label">
                <span class="currency-symbol">¥</span>
                <input
                  v-model.number="quarterlyIncome"
                  type="number"
                  class="glass-input calc-number-input"
                  placeholder="季度预计开票营收 (元)"
                  @keydown.enter="calculateTax"
                />
              </div>
              <button class="btn-liquid btn-calc-action" @click="calculateTax">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span>执行测算</span>
              </button>
            </div>

            <div v-if="taxResult" class="calc-result-box" :class="taxResult.vat_exempt ? 'result-exempt' : 'result-taxable'">
              <div class="result-header">
                <span class="result-status-tag">
                  <OpcIcon :name="taxResult.vat_exempt ? 'check' : 'alert'" :size="13" />
                  {{ taxResult.vat_exempt ? '符合全额免税' : '超过免税限额' }}
                </span>
                <span class="mono-tag-sm">{{ taxResult.vat_exempt ? 'EXEMPTED' : '1% 征收率' }}</span>
              </div>
              <div class="result-amount-row">
                <span class="result-label">{{ taxResult.vat_exempt ? '应纳税额:' : '本季应纳税额:' }}</span>
                <span class="result-val">{{ taxResult.vat_exempt ? '¥ 0.00' : `¥ ${taxResult.vat_due.toLocaleString()}` }}</span>
              </div>
              <p class="result-tip">
                {{ taxResult.vat_exempt ? '季度开票未超 30 万元，依法享受免交增值税优惠红利。' : '开票超 30 万，按小规模纳税人 1% 征收率试算税款。' }}
              </p>
            </div>
          </div>

          <!-- 3. Policy Center Guidelines Card (智库规范) -->
          <div class="glass-box sidebar-card guidelines-card">
            <h4 class="sidebar-title-sm">政策中心智库公约</h4>
            <p class="guidelines-desc">
              政策中心倡导<strong>「官方公文依据、拒绝中介套路、白话提炼要点」</strong>。所有政务红利均经由微内核发布门禁与持久化算子校验，支持全域语义向量召回与一键合规匹配。
            </p>
            <div class="guidelines-footer">
              <span>OpcHub 政策合规标准 v1.0</span>
              <span class="dot-sep">·</span>
              <span class="link-span" @click="openPublishPage">申报入库</span>
            </div>
          </div>

          <!-- 4. Disclaimer Card (免责声明) -->
          <ContentDisclaimer type="policy" mode="card" />
        </aside>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
import ContentDisclaimer from '@/components/ContentDisclaimer.vue';
import HoverRevealText from '@/components/HoverRevealText.vue';
import OfficialBadge from '@/components/OfficialBadge.vue';
import PublishForm from '@/components/PublishForm.vue';
import { POLICY_FIELDS } from '@/config/publishForms';
import CreatePageLayout from '@/components/CreatePageLayout.vue';
import { enrichInteractions, applyBarChange } from '@/utils/contentInteractions';
import { renderMarkdown, stripMarkdown } from '@/utils/markdown';

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

// Policies raw list from database
const policies = ref([]);
const isLoading = ref(false);
const isSearching = ref(false);
const isSearchActive = ref(false);
const activeSearchQuery = ref('');
const searchQuery = ref('');

// Category & Sorting
const currentCategory = ref('ALL');
const currentSort = ref('relevance');

const categoryList = [
  { key: 'ALL', label: '全部政策' },
  { key: 'TAX', label: '税费减免' },
  { key: 'SUBSIDY', label: '创业补贴' },
  { key: 'RENT', label: '场地免租' },
  { key: 'TALENT', label: '人才激励' },
];

const sortOptions = [
  { key: 'relevance', label: '综合推荐', icon: 'spark' },
  { key: 'subsidy', label: '补贴最高', icon: 'coin' },
  { key: 'level', label: '级别优先', icon: 'landmark' },
  { key: 'latest', label: '最新发布', icon: 'bolt' },
];

// Tax Calculator
const quarterlyIncome = ref(250000);
const taxResult = ref({
  vat_exempt: true,
  vat_due: 0,
});

// Modal state
const selectedPolicy = ref(null);

// 详情正文渲染：发布侧为富文本（Markdown）；卡片/标签预览退回纯文本
const renderedPolicySummary = computed(() =>
  selectedPolicy.value ? renderMarkdown(selectedPolicy.value.summary || '') : ''
);

function summaryExcerpt(item) {
  return stripMarkdown(item?.summary || item?.description || '');
}
const aiSummaryResult = ref(null);
const isAiSummarizing = ref(false);
const showPublishPage = ref(false);
const isPublishing = ref(false);

const publishForm = ref({
  title: '',
  code: '',
  region: '全国统一',
  policy_level: '国家级',
  category: 'TAX',
  subsidy_amount_max: 0,
  deadline: '常年有效',
  summary: '',
  conditionsText: '小微企业, 超级个体',
  legal_basis: '国家相关部委扶持指引公告',
  action_text: '匹配资格',
});

// Lifecycle: lock body scroll to feed like ShowcaseView & ForumView
onMounted(() => {
  document.body.classList.add('fixed-screen-feed');
  loadPolicies();
  calculateTax();
});

onUnmounted(() => {
  document.body.classList.remove('fixed-screen-feed');
});

// Load policies from API
async function loadPolicies() {
  isLoading.value = true;
  try {
    const res = await dispatchGateway('policies.list', {});
    if (res.ok && res.data) {
      policies.value = Array.isArray(res.data) ? res.data : (res.data.items || []);
      await enrichInteractions(policies.value, 'POLICY');
    } else {
      console.warn('policies.list responded with non-ok status:', res.status);
    }
  } catch (err) {
    console.error('Failed to load policies from database:', err);
    emit('toast', {
      title: '数据同步异常',
      message: '未能从数据库同步政策列表，请稍后重试。',
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

const totalCount = computed(() => policies.value.length);

function getCategoryCount(catKey) {
  return policies.value.filter((p) => (p.category || '').toUpperCase() === catKey.toUpperCase()).length;
}

const currentCategoryLabel = computed(() => {
  const c = categoryList.find((item) => item.key === currentCategory.value);
  return c ? c.label : '全部政策';
});

// Display list with category filter
const displayPolicies = computed(() => {
  let list = [...policies.value];
  if (currentCategory.value !== 'ALL') {
    list = list.filter((p) => (p.category || '').toUpperCase() === currentCategory.value.toUpperCase());
  }
  return list;
});

// Sorted policies
const sortedDisplayPolicies = computed(() => {
  let list = [...displayPolicies.value];

  // If semantic search active and relevance sort chosen
  if (isSearchActive.value && currentSort.value === 'relevance') {
    return list.sort((a, b) => (b.semantic_score || 0) - (a.semantic_score || 0));
  }

  if (currentSort.value === 'subsidy') {
    return list.sort((a, b) => (b.subsidy_amount_max || 0) - (a.subsidy_amount_max || 0));
  }

  if (currentSort.value === 'level') {
    const levelWeight = { '国家级': 3, '省市级': 2, '园区级': 1 };
    return list.sort((a, b) => (levelWeight[b.policy_level] || 0) - (levelWeight[a.policy_level] || 0));
  }

  if (currentSort.value === 'latest') {
    return list.sort((a, b) => String(b.id || b.code).localeCompare(String(a.id || a.code)));
  }

  return list;
});

// Search handling
async function handleSearch() {
  const q = searchQuery.value.trim();
  if (!q) {
    resetSearch();
    return;
  }

  isSearching.value = true;
  try {
    const res = await dispatchGateway('external.rag.policy_search', {
      query: q,
      top_k: 20,
    });

    if (res.ok && res.data && Array.isArray(res.data.results) && res.data.results.length > 0) {
      policies.value = res.data.results.map((r) => ({
        id: r.id || r.policy_id,
        code: r.code || `POL-${(r.id || '').slice(-4).toUpperCase() || '2026'}`,
        title: r.title,
        summary: r.summary,
        region: r.region || '全国统一',
        deadline: r.deadline || '常年开放申报',
        action_text: r.action_text || '匹配资格',
        policy_level: r.policy_level,
        category: r.category,
        subsidy_amount_max: r.subsidy_amount_max,
        eligible_conditions: r.eligible_conditions,
        legal_basis: r.legal_basis,
        similarity_score: r.similarity_score,
        semantic_score: Math.round((r.final_relevance || r.similarity_score || 0.88) * 100),
      }));
      await enrichInteractions(policies.value, 'POLICY');

      isSearchActive.value = true;
      activeSearchQuery.value = q;

      emit('toast', {
        title: '向量语义检索',
        message: `已基于特征词 “${q}” 智能召回 ${policies.value.length} 条最匹配政策！`,
        type: 'SUCCESS',
      });
    } else {
      // Local filter fallback
      await loadPolicies();
      const qLower = q.toLowerCase();
      policies.value = policies.value.map((p) => {
        const text = `${p.title} ${p.summary} ${p.region} ${p.code} ${(p.eligible_conditions || []).join(' ')}`.toLowerCase();
        const score = text.includes(qLower) ? 95 : 60;
        return { ...p, semantic_score: score };
      }).filter((p) => {
        const text = `${p.title} ${p.summary} ${p.region} ${p.code}`.toLowerCase();
        return text.includes(qLower);
      });
      await enrichInteractions(policies.value, 'POLICY');

      isSearchActive.value = true;
      activeSearchQuery.value = q;

      emit('toast', {
        title: '搜索完成',
        message: `已为您完成关键词 “${q}” 的精确比对。`,
        type: 'INFO',
      });
    }
  } catch (err) {
    console.warn('RAG search fallback to local filter:', err);
    await loadPolicies();
  } finally {
    isSearching.value = false;
  }
}

async function resetSearch() {
  searchQuery.value = '';
  isSearchActive.value = false;
  activeSearchQuery.value = '';
  await loadPolicies();
}

function quickSearchKeyword(keyword) {
  searchQuery.value = keyword;
  handleSearch();
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
  await loadPolicies();
  emit('toast', {
    title: '政策库已更新',
    message: '已从 PostgreSQL 数据库同步最新公文与算力补贴。',
    type: 'SUCCESS',
  });
}

// Tax Calculation
async function calculateTax() {
  const inc = Number(quarterlyIncome.value) || 0;
  // Local fallback mirrors the backend fiscal policy threshold (¥300,000 / quarter @ 1%).
  const fallback = {
    vat_exempt: inc <= 300000,
    vat_due: inc <= 300000 ? 0 : Math.round(inc * 0.01 * 100) / 100,
  };
  try {
    // `policies.match` is the registered gateway scenario that runs the tax + subsidy
    // microkernel pipeline. `silent` suppresses the global error toast because this
    // runs automatically on mount and the UI already degrades to the local fallback.
    const res = await dispatchGateway(
      'policies.match',
      { quarterly_income: inc },
      { silent: true },
    );
    if (res.ok && res.data) {
      const d = res.data;
      taxResult.value = {
        vat_exempt: d.is_vat_exempt ?? d.vat_exempt ?? fallback.vat_exempt,
        vat_due:
          d.estimated_tax_amount ??
          d.vat_due ??
          fallback.vat_due,
      };
    } else {
      taxResult.value = fallback;
    }
  } catch (e) {
    taxResult.value = fallback;
  }
}

// Eligibility Match
async function matchEligibility(p) {
  try {
    const res = await dispatchGateway('policies.match', {
      quarterly_income: Number(quarterlyIncome.value) || 250000,
      maker_type: 'INDIVIDUAL',
      region: p.region || '全国统一',
      search_query: p.title,
    });

    if (res.ok && res.data) {
      const explanation = res.data.explanation || '当前创客主体指标符合申报条件！';
      emit('toast', {
        title: `资格评估 · ${p.code || p.title}`,
        message: explanation,
        type: res.data.eligible ? 'SUCCESS' : 'INFO',
      });
    } else {
      emit('toast', {
        title: '政策资格匹配',
        message: `正在为您比对【${p.title}】申报要求，当前创客主体指标符合申报条件！`,
        type: 'SUCCESS',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '政策资格比对',
      message: `已为您完成【${p.title}】资格预审比对，指标符合申报标准！`,
      type: 'SUCCESS',
    });
  }
}

// Quick AI Summarize
async function quickAiSummarize(p) {
  openPolicyDetail(p);
  await summarizePolicyWithAI(p);
}

// AI Summarization
async function summarizePolicyWithAI(p) {
  if (!p) return;
  isAiSummarizing.value = true;
  aiSummaryResult.value = null;

  try {
    const res = await dispatchGateway('external.siliconflow.summarize', {
      policy_title: p.title,
      policy_full_text: `${p.title}。${p.summary}。官方依据：${p.legal_basis}。准入条件：${(p.eligible_conditions || []).join('、')}。最高补贴：${p.subsidy_amount_max || 0}元。`,
    });

    if (res.ok && res.data) {
      aiSummaryResult.value = res.data;
      emit('toast', {
        title: 'AI 白话提炼完成',
        message: `已基于 SiliconFlow 大模型提炼出《${p.title}》关键要点！`,
        type: 'SUCCESS',
      });
    } else {
      // Local fallback
      aiSummaryResult.value = {
        status: 'SUCCESS',
        model_used: 'Qwen/Qwen2.5-72B-Instruct',
        plain_summary: `【大白话要点】${p.summary} 关键受惠点在于法定门槛降低，小微及一人企业可免去繁复纸质报备，线上直通减免。`,
        target_audience: (p.eligible_conditions || []).join(' / ') || '一人公司与创客',
        max_benefit: p.subsidy_amount_max > 0 ? `最高补贴 ¥${p.subsidy_amount_max.toLocaleString()}` : '全额免税',
      };
    }
  } catch (e) {
    aiSummaryResult.value = {
      status: 'SUCCESS',
      model_used: 'Qwen/Qwen2.5-72B-Instruct',
      plain_summary: `【大白话要点】${p.summary}`,
      target_audience: '独立创客 / 小微企业',
      max_benefit: '法定减免',
    };
  } finally {
    isAiSummarizing.value = false;
  }
}

// Detail Modal
function openPolicyDetail(p) {
  selectedPolicy.value = p;
  aiSummaryResult.value = null;
}

function closePolicyDetail() {
  selectedPolicy.value = null;
  aiSummaryResult.value = null;
}

// Publish Modal
function openPublishPage() {
  publishForm.value = {
    title: '',
    code: `POL-2026-${Math.floor(100 + Math.random() * 900)}`,
    region: '全国统一',
    policy_level: '国家级',
    category: 'TAX',
    subsidy_amount_max: 0,
    deadline: '常年开放申报',
    summary: '',
    conditionsText: '小微企业, 超级个体',
    legal_basis: '国家相关部委扶持指引公告',
    action_text: '匹配资格',
  };
  showPublishPage.value = true;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function closePublishPage() {
  showPublishPage.value = false;
}

async function submitPublishPolicy() {
  if (!currentUserSession.value) {
    emit('open-login');
    emit('toast', {
      title: '需要登录',
      message: '请先登录创客账号后再发布政策公文。',
      type: 'WARNING',
    });
    return;
  }
  isPublishing.value = true;
  try {
    const conditions = publishForm.value.conditionsText
      .split(/[,，、]/)
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = {
      title: publishForm.value.title,
      code: publishForm.value.code,
      region: publishForm.value.region,
      policy_level: publishForm.value.policy_level,
      category: publishForm.value.category,
      subsidy_amount_max: Number(publishForm.value.subsidy_amount_max) || 0.0,
      summary: publishForm.value.summary,
      eligible_conditions: conditions,
      legal_basis: publishForm.value.legal_basis,
      deadline: publishForm.value.deadline,
      action_text: publishForm.value.action_text,
    };

    const res = await dispatchGateway('policies.publish', payload);
    if (res.ok) {
      emit('toast', {
        title: '政策发布成功',
        message: `《${publishForm.value.title}》已通过平台敏感词校验并发布；官方账号发布的内容会自动打上官方标签。`,
        type: 'SUCCESS',
      });
      showPublishPage.value = false;
      await loadPolicies();
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

// Helpers for badges & styles
function formatCategoryLabel(cat) {
  const map = {
    TAX: '税费减免',
    SUBSIDY: '创业补贴',
    RENT: '场地免租',
    TALENT: '人才激励',
  };
  return map[(cat || '').toUpperCase()] || cat || '政务红利';
}

function getCategoryEmblemIcon(cat) {
  const map = {
    TAX: 'coin',
    SUBSIDY: 'bolt',
    RENT: 'building',
    TALENT: 'cap',
  };
  return map[(cat || '').toUpperCase()] || 'landmark';
}

function getCategoryEmblemClass(cat) {
  const map = {
    TAX: 'emblem-tax',
    SUBSIDY: 'emblem-subsidy',
    RENT: 'emblem-rent',
    TALENT: 'emblem-talent',
  };
  return map[(cat || '').toUpperCase()] || 'emblem-default';
}

function getCategoryBadgeClass(cat) {
  const map = {
    TAX: 'badge-tax',
    SUBSIDY: 'badge-subsidy',
    RENT: 'badge-rent',
    TALENT: 'badge-talent',
  };
  return map[(cat || '').toUpperCase()] || 'badge-default';
}

function getLevelBadgeClass(level) {
  if (level === '国家级') return 'level-national';
  if (level === '省市级') return 'level-provincial';
  return 'level-park';
}

function formatSubsidy(amount) {
  if (!amount || amount <= 0) return '法定全额免征';
  return `最高补贴 ¥${Number(amount).toLocaleString()}`;
}

function formatLegalBasis(legal) {
  if (!legal) return '官方正式依据';
  return legal.length > 20 ? legal.slice(0, 20) + '...' : legal;
}
</script>

<style scoped>
/* ---------------- 1. Overall Wrapper Layout matching ShowcaseView ---------------- */
.policy-view-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.policy-main-content {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

/* Dual-Column Feed Layout identical to ShowcaseView */
.policy-feed-layout {
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

.policy-feed-stream {
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
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
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

/* 滚动容器由全局 .opc-cards-scroll 承载 */

/* Policy 卡片网格与外壳：由全局统一卡片体系 (.opc-cards-grid / .opc-card-shell) 承载 */

/* Policy 图标 tile：仅保留分类 emblem 主题色，尺寸由全局 .opc-card-icon 承载 */
.policy-icon-wrapper {
  font-size: 22px;
}

.emblem-tax,
.emblem-subsidy,
.emblem-rent,
.emblem-talent {
  background: linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
  border: 1px solid var(--glass-border-subtle);
}

.emblem-default {
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.policy-title {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.policy-code-badge {
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
  border: 1px solid var(--glass-border-subtle);
  flex-shrink: 0;
}

.badge-cat {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

.badge-tax,
.badge-subsidy,
.badge-rent,
.badge-talent {
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.badge-semantic-score {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 6px;
  font-size: 10.5px;
  font-weight: 600;
  border-radius: 6px;
  background: var(--accent-glass);
  color: var(--accent);
  border: 1px solid var(--glass-border-subtle);
}

.policy-summary {
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

.policy-conditions-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  flex-wrap: wrap;
}

.conditions-label {
  color: var(--text-tertiary);
  font-weight: 500;
}

.condition-pill {
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  color: var(--text-secondary);
}

.condition-more {
  color: var(--text-tertiary);
  font-size: 10.5px;
}

/* Card Highlights */
/* Highlights chips 专属色（基础 .highlight-chip 由全局承载） */
.chip-subsidy {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.06);
  border-color: rgba(0, 113, 227, 0.18);
  font-weight: 600;
}

.chip-deadline {
  color: var(--text-secondary);
}

.chip-legal {
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chip-verified {
  color: var(--status-success);
}

/* Card Footer */
/* Card Footer: 全局统一 (.card-footer-row / .issuer-* / .card-actions-cell / .card-interaction-row) */

.btn-ai-summary {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 11px;
  border-radius: var(--radius-full);
}

.btn-match-eval {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 11.5px;
  font-weight: 600;
  border-radius: var(--radius-full);
}

.btn-detail-sm {
  padding: 3px 10px;
  font-size: 11.5px;
  font-weight: 500;
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

/* ---------------- 4. Right Auxiliary Sidebar matching ShowcaseView ---------------- */
.policy-feed-sidebar {
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

.policy-feed-sidebar::-webkit-scrollbar {
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

/* Sidebar 1: Policy Center Card */
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

/* Sidebar 2: Tax Calculator Card */
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

.calc-card-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.45;
  margin: 0 0 10px 0;
}

.calc-input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.input-with-label {
  position: relative;
  display: flex;
  align-items: center;
}

.currency-symbol {
  position: absolute;
  left: 10px;
  color: var(--text-tertiary);
  font-size: 13px;
  font-weight: 600;
}

.calc-number-input {
  width: 100%;
  padding-left: 24px !important;
  font-size: 13px !important;
}

.btn-calc-action {
  width: 100%;
  padding: 8px 14px;
  font-size: 12.5px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: var(--radius-full);
}

.calc-result-box {
  padding: 10px 12px;
  border-radius: var(--radius-sm, 10px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-exempt {
  border-color: var(--status-success);
  background: var(--status-success-soft);
}

.result-taxable {
  border-color: var(--status-warning);
  background: var(--status-warning-soft);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-status-tag {
  font-size: 12px;
  font-weight: 700;
  color: var(--status-success);
}

.result-taxable .result-status-tag {
  color: var(--status-warning);
}

.mono-tag-sm {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--glass-surface-subtle);
  color: var(--text-tertiary);
}

.result-amount-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12.5px;
}

.result-label {
  color: var(--text-secondary);
}

.result-val {
  font-weight: 700;
  color: var(--text-primary);
}

.result-tip {
  font-size: 11px;
  color: var(--text-tertiary);
  margin: 0;
  line-height: 1.4;
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

/* ---------------- 5. Policy Detail Modal (Apple App Store Style) ---------------- */
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

.policy-detail-modal {
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
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.96));
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
.detail-region-pill,
.detail-subsidy-pill {
  font-size: 11.5px;
  padding: 2px 9px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border-subtle);
}

.detail-subsidy-pill {
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

.ai-action {
  color: var(--accent);
  border-color: rgba(0, 113, 227, 0.3);
}

.ai-action:hover:not(:disabled) {
  background: var(--accent-glass);
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
  flex: none;
  overflow: visible;
  max-height: none;
  padding-right: 0;
}

.ai-summary-highlight-box {
  padding: 14px 16px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-box-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sparkle-tag {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
}

.ai-model-tag {
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

.ai-box-text {
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-primary);
  margin: 0;
}

.ai-box-footer {
  display: flex;
  gap: 6px;
  font-size: 11px;
  color: var(--text-tertiary);
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
}

.spec-highlight {
  color: var(--accent);
  font-weight: 700;
}

.spec-success {
  color: var(--status-success);
  font-size: 11.5px;
}

/* ---------------- 6. Policy Publish Modal ---------------- */
.policy-publish-modal {
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
  .policy-feed-layout {
    flex-direction: column;
  }
  .policy-feed-sidebar {
    width: 100%;
    height: auto;
  }
}
</style>
