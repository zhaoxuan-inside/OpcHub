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
          <!-- Zhihu-style Top Creator Bar (知乎帖子顶部发帖栏) -->
          <ForumTopCreatorBar
            :user-session="currentUserSession"
            :categories="categories"
            @publish-success="handleTopBarPublishSuccess"
            @open-full-editor="handleOpenCreatePage"
            @open-register="$emit('open-register')"
            @toast="$emit('toast', $event)"
          />

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
              <div class="sort-segmented">
                <button
                  v-for="opt in sortOptions"
                  :key="opt.key"
                  type="button"
                  :class="['sort-pill', { active: currentSort === opt.key }]"
                  @click="currentSort = opt.key"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>
          </div>

          <!-- Loading State Indicator -->
          <div v-if="isLoadingPosts" class="posts-loading-banner">
            <span class="loading-spinner"></span>
            <span>正在检索第 {{ currentPage }} 页风暴探讨...</span>
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
              @upvote="handleCardUpvote"
              @bookmark="handleDetailBookmark"
              @delete="handleDeletePost"
              @toast="$emit('toast', $event)"
            />
          </div>

          <!-- VisionOS Liquid Pagination Bar (页号 + 页面长度 + 分页器) -->
          <div v-if="totalCount > 0" class="forum-pagination-bar glass-box">
            <div class="pagination-info">
              <span class="pagination-meta-pill">第 {{ currentPage }} / {{ totalPages }} 页</span>
              <span class="pagination-total-text">共 {{ totalCount }} 篇探讨</span>
              <div class="page-size-selector">
                <span class="page-size-label">页面长度:</span>
                <select
                  :value="pageSize"
                  class="page-size-select"
                  aria-label="选择每页文章数量"
                  @change="handlePageSizeChange($event.target.value)"
                >
                  <option :value="3">3 篇 / 页</option>
                  <option :value="5">5 篇 / 页</option>
                  <option :value="10">10 篇 / 页</option>
                  <option :value="20">20 篇 / 页</option>
                </select>
              </div>
            </div>

            <div class="pagination-actions">
              <button
                type="button"
                class="btn-liquid-outline btn-page-nav"
                :disabled="currentPage <= 1 || isLoadingPosts"
                aria-label="上一页"
                @click="goToPage(currentPage - 1)"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
                <span>上一页</span>
              </button>

              <div class="page-pills">
                <button
                  v-for="p in visiblePageNumbers"
                  :key="p"
                  type="button"
                  :class="['page-number-btn', { active: p === currentPage }]"
                  :disabled="isLoadingPosts"
                  @click="goToPage(p)"
                >
                  {{ p }}
                </button>
              </div>

              <button
                type="button"
                class="btn-liquid-outline btn-page-nav"
                :disabled="currentPage >= totalPages || isLoadingPosts"
                aria-label="下一页"
                @click="goToPage(currentPage + 1)"
              >
                <span>下一页</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="glass-box empty-state-box">
            <div class="empty-icon-wrap">
              <ForumIcon name="empty-galaxy" size="38" />
            </div>
            <h3 class="empty-title">当前筛选下暂无风暴帖</h3>
            <p class="empty-desc">换个关键词试试，或点击下方按钮发起该领域的第一个实战话题！</p>
            <button class="btn-liquid" @click="handleOpenCreatePage">
              <span>发起新风暴</span>
            </button>
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
                <span class="hot-badge-fire">🔥</span>
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
                    <span>🔥 {{ (item.upvotes || 0) * 3 + (item.replies || 0) * 5 + 42 }} 热度</span>
                    <span class="dot-sep">·</span>
                    <span>{{ item.upvotes || 0 }} 赞同</span>
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
import { ref, computed, onMounted, onUnmounted } from 'vue';
import ForumIcon from '@/components/ForumIcon.vue';
import ForumCard from '@/components/ForumCard.vue';
import ForumDetailView from '@/components/ForumDetailView.vue';
import ForumCreateView from '@/components/ForumCreateView.vue';
import ForumTopCreatorBar from '@/components/ForumTopCreatorBar.vue';
import { dispatchGateway } from '@/api/gateway';

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
  { key: 'hot', label: '🔥 最热讨论' },
  { key: 'new', label: '⚡ 最新发表' },
  { key: 'featured', label: '🏆 官方精选' },
];
const currentSort = ref('hot');

// Search
const searchKeyword = ref('');

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

// Default Seed Posts dataset with rich, high-density practical content and executive metrics
const DEFAULT_SEEDS_DATA = [
  {
    id: 1,
    pinned: '置顶',
    category_code: 'TAX',
    category: '工商财税',
    title: '【必读】2026 一人公司工商年报与增值税免征额度最新操作细则',
    snippet: '针对年应税销售额 500 万以下、季度销售额 30 万元以内的小规模纳税人免税实操。复盘新版电子税务局填报《增值税及附加税费申报表》时，免税收入切勿误填入“应税销售额”一栏，附零附加税与研发费用加计扣除全套申报步骤。',
    content: `# 2026 小规模纳税人免税申报与财税合规避坑

## 1. 适用群体与关键政策
适用于年应税销售额在 500 万元以下、季度销售额在 30 万元以内的初创一人科技公司、工作室或独立咨询业务。

## 2. 申报核心避坑点
> [!IMPORTANT]
> 电子税务局填报《增值税及附加税费申报表》时，免税收入切勿误填入“应税销售额”一栏，否则税务系统将直接生成缴税凭单！

### 规范申报流程四步法：
1. **登录新版电子税务局**：选择企业法定代表人或财务人员身份实名登录
2. **核对发票汇总数据**：确认本季度开具普票总金额未超过 30 万元限额（专用发票不可享受该免税政策）
3. **选择减免税政策代码**：勾选“小微企业免征增值税政策”，系统自动计算减免税额
4. **零附加税确认**：增值税免征后，城建税、教育费附加与地方教育附加同步全额免征

## 3. 真实核算对照表
| 项目 | 季度销售额 28 万元 (免税线内) | 季度销售额 35 万元 (突破限额) |
|---|---|---|
| 增值税征收率 | 1% (免征额内) | 1% (按全部 35 万计税) |
| 应纳增值税额 | ¥0.00 | ¥3,500.00 |
| 附加税费 (城建/教育) | ¥0.00 | ¥420.00 |
| 经营合规性 | 凭证齐全，零申报 | 需开票纳税，可抵扣进项 |

> [!TIP]
> 记得在每年 6 月 30 日前完成企业年报公示，逾期会被列入经营异常名录并影响银行对公账户使用！`,
    author: '平台管家',
    author_id: 'usr_platform_steward',
    ip_location: '来自 杭州',
    replies: 89,
    comment_count: 89,
    upvotes: 142,
    upvote_count: 142,
    is_upvoted: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '10 分钟前',
    view_count: 1420,
    tags: ['税务年报', '增值税免征', '电子税务局', '小规模合规'],
    metrics: [
      { label: '季度免征额', val: '¥300,000', icon: '💰', type: 'success' },
      { label: '申报耗时', val: '15分钟', icon: '⏱️', type: 'info' },
      { label: '综合税负', val: '0%', icon: '📊', type: 'accent' },
    ],
  },
  {
    id: 2,
    pinned: '精选',
    category_code: 'POLICY',
    category: '政策申报',
    title: '从 0 到 1 拿到长三角智能算力补贴 12 万元的全周期复盘 (附审批材料格式)',
    snippet: '很多独立创客误以为个体户无法申报算力券。实测只要完成 1 项软件著作权登记 + 科技型中小企业入库登记即可破局。本文梳理从材料初审、机房用量凭证、算力服务商发票到财政直拨入账的 45 天全流程要点与避坑模版。',
    content: `# 长三角智能算力补贴 12 万元全周期实操复盘

## 1. 政策定位与申请门槛
智能算力券是长三角区域针对科技型创客的一项实质性扶持政策。补贴额度通常为算力租赁费用的 30%~50%，年度最高可达 12~20 万元。

## 2. 核心材料准备清单
1. **企业资质**：软件著作权证书（1项以上） + 科技型中小企业入库登记编号
2. **业务证明**：智能体或算法训练业务场景说明书、系统运行日志截图
3. **财务凭证**：与指定算力中心签署的 GPU 算力租赁合同 + 银行付款对账单 + 增值税专用发票

## 3. 审批与核销时间线
| 节点阶段 | 耗时周期 | 交付物/审核重点 |
|---|---|---|
| 材料初审 | 7 个工作日 | 软著与入库资质真实性核查 |
| 用量核验 | 15 个工作日 | GPU 运行时间与算力利用率抽样 |
| 公示与发券 | 10 个工作日 | 财政厅官网公示期无异议 |
| 资金直拨 | 13 个工作日 | 补贴款直接汇入企业对公账户 |

> [!TIP]
> 一定要选择列入当地“算力服务商白名单”的机房节点，第三方未备案转售发票无法通过财政穿透审核。`,
    author: 'CodeNomad',
    author_id: 'usr_codenomad',
    ip_location: '来自 上海',
    replies: 42,
    comment_count: 42,
    upvotes: 98,
    upvote_count: 98,
    is_upvoted: true,
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '35 分钟前',
    view_count: 890,
    tags: ['算力补贴', '科技型中小企业', '软著申报', '政策扶持'],
    metrics: [
      { label: '财政直拨', val: '¥120,000', icon: '🎁', type: 'success' },
      { label: '审批周期', val: '45天', icon: '📅', type: 'info' },
      { label: '资质要件', val: '软著+科技型', icon: '📝', type: 'warning' },
    ],
  },
  {
    id: 3,
    pinned: null,
    category_code: 'BIZ',
    category: '独立出海',
    title: '独立开发者 Stripe 绑定万里汇香港对公户结汇流程避坑指南',
    snippet: '出海一人微型 SaaS 在流水突破 $10,000 时常遭银行抽检风控。本文复盘合规“三流合一”凭证搭建（Stripe 订单流 + 在线服务协议履约流 + 银行对账流），彻底告别个人账户冻结风险，实现 T+1 自动结汇与 1.9% 综合费率通道。',
    content: `# 独立开发者出海支付与合规结汇避坑复盘

## 1. 背景与业务场景
- **业务类型**：一人微型 SaaS / 工具出海
- **目标市场**：北美与欧洲市场
- **支付工具**：Stripe + 万里汇 (WorldFirst) 香港企业对公账户

## 2. 踩坑与合规痛点
> [!WARNING]
> 跨境银行在流水达到 $10,000 以上时会触发随机合规审计，若无法在 7 天内提供符合要求的人工服务协议与对账单，结算账户将被临时冷冻！

- **阻断问题 1**：个人账户直接挂载海外商业账户导致的税务稽查与风控抽检
- **阻断问题 2**：汇率波动过大造成汇损与提现手续费吞噬微利
- **阻断问题 3**：VAT 增值税代扣代缴与跨国数字税发票合规

## 3. 破局实操与解决方案
1. **公司实体搭建**：注册香港有限责任公司 + 香港本地对公商业账户
2. **三流合一凭证建立**：
   - 业务订单流（Stripe Dashboard 导出）
   - 合同履约流（在线用户 Terms of Service 电子存证）
   - 资金结算流（银行流水对账单明细）
3. **资金安全结汇链路**：
   \`\`\`
   海外买家信用卡 -> Stripe 结算 -> 香港商业账户 -> 跨境结汇通 -> 境内合规完税入账
   \`\`\`

## 4. 核心数据与收益实测
| 指标项 | 优化前 | 规范后 |
|---|---|---|
| 资金结算时效 | T+7 天（常被风控卡留） | T+1 日内自动结汇 |
| 综合交易损耗 | 4.8% (中间行+汇损) | 1.9% (企业合规通道) |
| 合规审查阻断率 | 35% 发生率 | 0% (已通过 2 次年检) |

> [!TIP]
> 建议每季度末及时导出 Stripe 报表与税务底稿备查，一人公司必须做好风险防线隔离！`,
    author: 'SoloDev_Z',
    author_id: 'usr_solodev_z',
    ip_location: '来自 深圳',
    replies: 19,
    comment_count: 19,
    upvotes: 64,
    upvote_count: 64,
    is_upvoted: false,
    created_at: '2026-01-03T00:00:00Z',
    updated_at: '2 小时前',
    view_count: 670,
    tags: ['Stripe跨境', '万里汇对公户', '合规风控', '三流合一'],
    metrics: [
      { label: '结汇时效', val: 'T+1 自动到账', icon: '⚡', type: 'success' },
      { label: '综合费率', val: '4.8% → 1.9%', icon: '💵', type: 'accent' },
      { label: '合规阻断', val: '0% 拦截', icon: '🛡️', type: 'info' },
    ],
  },
  {
    id: 4,
    pinned: null,
    category_code: 'AGENTS',
    category: 'AI智能体',
    title: '基于 PostgreSQL + pgvector 打造垂直知识库 Agent 的成本优化与延迟实测',
    snippet: '生产环境下对比 pgvector、Pinecone 与 Milvus 后的落地实测：单台 4C8G 云服务器通过 HNSW 索引参数调优（m=16, ef_construction=64）与微内核流水线异步构建，将百万级向量余弦检索从 120ms 压至 18ms，单月基础设施成本仅需 $42。',
    content: `# 基于 PostgreSQL + pgvector 打造垂直知识库 Agent 的成本优化与延迟实测

## 1. 架构目标与选型对比
在构建垂类企业知识库时，面对专有向量数据库（如 Pinecone、Milvus）的高昂固定租金与维护开销，我们探索将 PostgreSQL 结合 pgvector 插件作为全栈数据底座。

## 2. 核心性能调优实践
\`\`\`sql
-- 启用 pgvector 扩展并创建 HNSW 索引
CREATE EXTENSION IF NOT EXISTS vector;

CREATE INDEX ON document_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
\`\`\`

### 关键优化要点：
1. **HNSW 索引替代 IVFFlat**：构建时间增加 20%，但高并发召回延迟降低 85%
2. **异步流水线微内核**：文档拆分、Embedding 计算与向量入库异步化，解耦前台请求
3. **多模态元数据过滤**：结合 JSONB 进行标签和权限前置过滤，避免全表扫描

## 3. 生产压测基准数据
| 维度指标 | 调优前 (IVFFlat) | 调优后 (HNSW+微内核) |
|---|---|---|
| 200万向量检索延迟 | 120ms (P99: 210ms) | 18ms (P99: 32ms) |
| 内存占用 | 12GB | 4.2GB |
| 月度基础设施成本 | $150/月 (托管集群) | $42/月 (单台高配云机) |`,
    author: 'VectorPilot',
    author_id: 'usr_vectorpilot',
    ip_location: '来自 杭州',
    replies: 31,
    comment_count: 31,
    upvotes: 85,
    upvote_count: 85,
    is_upvoted: false,
    created_at: '2026-01-04T00:00:00Z',
    updated_at: '3 小时前',
    view_count: 540,
    tags: ['PostgreSQL', 'pgvector', 'Agent架构', 'HNSW调优'],
    metrics: [
      { label: '检索延迟', val: '120ms → 18ms', icon: '⚡', type: 'success' },
      { label: '节点容量', val: '200万向量', icon: '💾', type: 'info' },
      { label: '基础设施', val: '$42/月', icon: '📉', type: 'accent' },
    ],
  },
  {
    id: 5,
    pinned: null,
    category_code: 'DEV',
    category: '技术踩坑',
    title: '一人公司全栈开发技术选型：FastAPI + Vue3 + SQLite 轻量化架构支撑 10 万 MAU 经验',
    snippet: '拒绝过早分布式与 K8s 复杂化！深度复盘一人公司如何通过 FastAPI 异步协程 + Vue3 前端 + SQLite WAL 高并发读写模式抗住 10 万 MAU 突发流量。配合系统级自动热重载微内核，实现代码零停机平滑更新，运维投入低于 5%。',
    content: `# 一人公司全栈技术选型与架构复盘

## 1. 核心诉求与技术目标
作为独立超级个体，运维时间必须压缩在 5% 以下，架构必须满足**极致轻量**、**高开发吞吐**与**零专职运维**。

## 2. 技术栈清单
- **后端**：FastAPI (Python 3.12 异步) + Uvicorn
- **前端**：Vue 3 + Vite + VisionOS 液态毛玻璃设计系统
- **数据库**：PostgreSQL 16 + pgvector (配合单机 SQLite 本地高速缓存)
- **调度治理**：轻量级微内核插件流水线 + DAG 事件总线

## 3. 架构设计与避坑
\`\`\`python
# 示例：微内核合规拦截算子
async def compliance_guard_pipeline(context: dict) -> bool:
    content = context.get("content", "")
    if len(content) < 10:
        raise ValueError("正文字数不足，无法形成有效技术风暴帖")
    # 执行异步敏感词与防刷限流校验
    return True
\`\`\`

> [!NOTE]
> 永远不要在初创验证阶段引入复杂的 Kubernetes 分布式集群，单台高配云主机 + Docker Compose 足以支撑 10 万 MAU。

## 4. 真实压测与资源开销
| 场景 | 峰值并发 | CPU 占用 | 内存占用 |
|---|---|---|---|
| 日常平峰 | 200 QPS | 8% | 680MB |
| 突发流量脉冲 | 2,400 QPS | 42% | 1.8GB |
| 自动化流水线构建 | 16 并发 DAG | 65% | 2.2GB |`,
    author: 'Solopreneur_99',
    author_id: 'usr_solopreneur_99',
    ip_location: '来自 北京',
    replies: 56,
    comment_count: 56,
    upvotes: 112,
    upvote_count: 112,
    is_upvoted: false,
    created_at: '2026-01-05T00:00:00Z',
    updated_at: '5 小时前',
    view_count: 1150,
    tags: ['FastAPI', 'Vue3', 'SQLite-WAL', '微内核'],
    metrics: [
      { label: '承载峰值', val: '100,000 MAU', icon: '👥', type: 'success' },
      { label: '硬件规格', val: '2核4G 单机', icon: '🖥️', type: 'info' },
      { label: '运维精力', val: '< 5% 时长', icon: '🚀', type: 'accent' },
    ],
  },
  {
    id: 6,
    pinned: null,
    category_code: 'BIZ',
    category: '独立出海',
    title: '一人公司出海软件如何做定价策略？Freemium vs 买断制年度留存实录',
    snippet: '追踪了 1,200 位海外付费用户 14 个月的生命周期价值（LTV）分析。实证买断制（Lifetime Deal）在初期虽有爆发性现金流但后期服务成本高企导致现金流断裂；转型为阶梯月付/年付订阅后，LTV 提升 3.2 倍且年度留存达 68.4%。',
    content: `# 一人公司出海软件如何做定价策略？Freemium vs 买断制年度留存实录

## 1. 业务背景与样本规模
深度追踪了过去 14 个月中购买我们开发工具的 1,200 位海外付费创客（主要分布在美、德、日、英），对比了买断制（LTD）与订阅制（SaaS）的真实表现。

## 2. 商业模式痛点复盘
- **买断制陷阱**：早期涌入大量低客单价用户，首月冲上 $8,000；但在第 6 个月后，老用户的客服、API 算力与同步存储成本持续累积，现金流几乎断裂。
- **阶梯订阅破局**：引入 $9.9/月 或 $89/年的分层订阅，并提供团队席位版。

## 3. 14 个月关键指标对照
| 核心指标 | 买断制 (LTD $49) | 阶梯订阅制 ($9.9/mo) | 差异幅度 |
|---|---|---|---|
| 用户生命周期价值 (LTV) | $49 (固定上限) | $158.4 (持续攀升) | +223% (3.2倍) |
| 第 12 个月留存率 | 12.3% (日渐沉寂) | 68.4% (高粘性活跃) | +56.1% |
| 净经常性收入 (MRR) | $0 (无持续流入) | $4,850/月 (稳健增长) | 现金流质变 |

> [!TIP]
> 订阅制初期一定要做好“取消挽留流程”（如赠送 1 个月试用或降级至微型版），仅此一项即可挽回 22% 的退订率！`,
    author: 'GlobalNomad',
    author_id: 'usr_globalnomad',
    ip_location: '来自 新加坡',
    replies: 27,
    comment_count: 27,
    upvotes: 73,
    upvote_count: 73,
    is_upvoted: false,
    created_at: '2026-01-06T00:00:00Z',
    updated_at: '6 小时前',
    view_count: 780,
    tags: ['出海定价', 'SaaS订阅', '单元经济学', '留存分析'],
    metrics: [
      { label: '跟踪样本', val: '1,200 付费创客', icon: '📊', type: 'info' },
      { label: 'LTV提升', val: '3.2 倍', icon: '💰', type: 'success' },
      { label: '年度留存', val: '68.4%', icon: '📈', type: 'accent' },
    ],
  },
];

// Deleted posts tracking across reloads
function getDeletedThreadIds() {
  try {
    const raw = localStorage.getItem('opchub_forum_deleted_threads');
    return raw ? new Set(JSON.parse(raw).map(String)) : new Set();
  } catch (e) {
    return new Set();
  }
}

function recordDeletedThreadId(id) {
  try {
    const set = getDeletedThreadIds();
    set.add(String(id));
    localStorage.setItem('opchub_forum_deleted_threads', JSON.stringify([...set]));
  } catch (e) {}
}

// Active Posts dataset (paginated)
const postsList = ref([]);

// Pagination State (id + page + page_length)
const currentPage = ref(1);
const pageSize = ref(5);
const totalCount = ref(0);
const totalPages = ref(1);
const isLoadingPosts = ref(false);

const visiblePageNumbers = computed(() => {
  const pages = [];
  const maxVisible = 5;
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2));
  let end = Math.min(totalPages.value, start + maxVisible - 1);
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1);
  }
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }
  return pages;
});

async function fetchThreads(page = 1, size = pageSize.value, categoryId = selectedCategoryCode.value) {
  isLoadingPosts.value = true;
  currentPage.value = page;
  try {
    const res = await dispatchGateway('forum.threads.list', {
      id: categoryId || 'ALL',
      page: page,
      page_size: size,
      page_length: size,
    }, { silent: true });

    if (res.ok) {
      const data = res.data;
      const rawItems = Array.isArray(data) ? data : (data?.items || []);
      totalCount.value = typeof data?.total === 'number' ? data.total : rawItems.length;
      totalPages.value = typeof data?.total_pages === 'number' ? data.total_pages : (Math.ceil(totalCount.value / size) || 1);

      const deletedIds = getDeletedThreadIds();
      const remotePosts = rawItems
        .filter((t) => !deletedIds.has(String(t.id)))
        .map((t) => {
          const existing = DEFAULT_SEEDS_DATA.find((s) => String(s.id) === String(t.id));
          return {
            id: t.id,
            pinned: t.is_pinned ? '置顶' : (existing?.pinned || null),
            category_code: t.category_code || existing?.category_code || 'DEV',
            category: categories.find((c) => c.code === t.category_code)?.name || existing?.category || '技术踩坑',
            title: t.title,
            snippet: existing?.snippet || (t.content ? (t.content.slice(0, 160) + '...') : ''),
            content: t.content || existing?.content || '',
            metrics: existing?.metrics || [],
            author: t.author_name || existing?.author || (t.author_id ? `创客_${t.author_id.slice(0, 6)}` : '实战创客'),
            author_id: t.author_id || existing?.author_id || '',
            ip_location: existing?.ip_location || '来自 浙江',
            replies: t.comment_count ?? existing?.replies ?? 0,
            comment_count: t.comment_count ?? existing?.comment_count ?? 0,
            upvotes: t.upvote_count ?? existing?.upvotes ?? 0,
            upvote_count: t.upvote_count ?? existing?.upvote_count ?? 0,
            view_count: t.view_count ?? existing?.view_count ?? 500,
            is_upvoted: existing?.is_upvoted || false,
            created_at: t.created_at || existing?.created_at || new Date().toISOString(),
            updated_at: existing?.updated_at || '刚刚',
            tags: existing?.tags || [t.category_code || 'DEV'],
          };
        });

      postsList.value = remotePosts;
      syncStoredInteractions(postsList.value);
    }
  } catch (e) {
    // Graceful fallback to initial seeds filtered by category and deleted
    const deletedIds = getDeletedThreadIds();
    let fallback = DEFAULT_SEEDS_DATA.filter((p) => !deletedIds.has(String(p.id)));
    if (categoryId && categoryId !== 'ALL') {
      fallback = fallback.filter((p) => p.category_code === categoryId);
    }
    totalCount.value = fallback.length;
    totalPages.value = Math.ceil(fallback.length / size) || 1;
    const start = (page - 1) * size;
    postsList.value = fallback.slice(start, start + size);
  } finally {
    isLoadingPosts.value = false;
  }
}

function handleSelectCategory(catCode) {
  selectedCategoryCode.value = catCode;
  currentPage.value = 1;
  fetchThreads(1, pageSize.value, catCode);
}

function handlePageSizeChange(newSize) {
  const size = parseInt(newSize, 10) || 5;
  pageSize.value = size;
  currentPage.value = 1;
  fetchThreads(1, size, selectedCategoryCode.value);
}

function goToPage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  fetchThreads(page, pageSize.value, selectedCategoryCode.value);
  const el = document.querySelector('.zhihu-feed-stream');
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' });
  } else {
    window.scrollTo({ top: 120, behavior: 'smooth' });
  }
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

  // 2. Keyword Filter
  if (searchKeyword.value.trim()) {
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
  if (currentSort.value === 'hot') {
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
      recordDeletedThreadId(post.id);
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
    title: isUpvoted ? '已赞同灵感' : '已取消赞同',
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
  postsList.value.unshift(newThread);
  activePost.value = newThread;
  currentViewMode.value = 'detail';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Top Bar Post Created Callback (从信息流顶部快速发布后，直接插入流顶部并更新视图)
function handleTopBarPublishSuccess(newThread) {
  // If user was filtering by a specific category that doesn't match, reset to ALL
  if (selectedCategoryCode.value !== 'ALL' && selectedCategoryCode.value !== newThread.category_code) {
    selectedCategoryCode.value = 'ALL';
  }
  // Automatically switch to 'new' sort so the newly created post is prominently at the very top
  currentSort.value = 'new';

  const existingIdx = postsList.value.findIndex((p) => String(p.id) === String(newThread.id));
  if (existingIdx === -1) {
    postsList.value.unshift(newThread);
  } else {
    postsList.value[existingIdx] = { ...postsList.value[existingIdx], ...newThread };
  }
  syncStoredInteractions(postsList.value);
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

// Lifecycle: Fetch from backend gateway with mandatory pagination (id + page + page_length)
onMounted(async () => {
  window.addEventListener('hashchange', onWindowHashChange);
  await fetchThreads(1, pageSize.value, selectedCategoryCode.value);
  checkUrlForPost();
});

onUnmounted(() => {
  window.removeEventListener('hashchange', onWindowHashChange);
});
</script>

<style scoped>
.forum-view-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  box-sizing: border-box;
}

.forum-main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  box-sizing: border-box;
}





/* Zhihu-style Feed Two-Column Layout */
.zhihu-feed-layout {
  display: flex;
  gap: 20px;
  width: 100%;
  align-items: flex-start;
  box-sizing: border-box;
}

.zhihu-feed-stream {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-sizing: border-box;
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 76px;
  align-self: flex-start;
  max-height: calc(100vh - 96px);
  overflow-y: auto;
  scrollbar-width: none;
  box-sizing: border-box;
}

.zhihu-feed-sidebar::-webkit-scrollbar {
  display: none;
}

.sidebar-card {
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
  color: var(--text-tertiary, #999);
}

.rank-1 {
  color: #ff3b30;
}

.rank-2 {
  color: #ff9500;
}

.rank-3 {
  color: #ffcc00;
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
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid rgba(239, 68, 68, 0.25);
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
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.22);
  border-radius: var(--radius-sm, 10px);
  padding: 10px 14px;
  margin-bottom: 22px;
  color: #ef4444;
  font-size: 12.5px;
  line-height: 1.5;
}

.delete-warning-text strong {
  font-weight: 700;
  color: #dc2626;
}

.delete-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: center;
}

.btn-confirm-delete {
  background: #ef4444 !important;
  color: #ffffff !important;
  border: none !important;
  font-weight: 600;
  padding: 8px 18px;
}

.btn-confirm-delete:hover:not(:disabled) {
  background: #dc2626 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.35);
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
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.3);
  color: #f87171;
}

[data-theme="dark"] .delete-warning-text strong {
  color: #fca5a5;
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
  gap: 8px;
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

/* ---------------- VisionOS Pagination Controls ---------------- */
.forum-pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  border-radius: var(--radius-md, 14px);
  margin-top: 16px;
  margin-bottom: 24px;
  gap: 14px;
  flex-wrap: wrap;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pagination-meta-pill {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent, #0071e3);
  background: rgba(0, 113, 227, 0.1);
  border: 1px solid rgba(0, 113, 227, 0.2);
  border-radius: var(--radius-full);
  padding: 2px 10px;
}

.pagination-total-text {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 6px;
}

.page-size-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.page-size-select {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
}

.pagination-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-page-nav {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.page-pills {
  display: flex;
  gap: 4px;
  align-items: center;
}

.page-number-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s;
}

.page-number-btn:hover:not(:disabled) {
  background: var(--glass-surface-subtle);
  color: var(--text-primary);
}

.page-number-btn.active {
  background: var(--accent, #0071e3);
  color: #fff;
  border-color: var(--accent, #0071e3);
  box-shadow: 0 2px 10px rgba(0, 113, 227, 0.35);
}

.page-number-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Dark mode adjustments for pagination */
[data-theme="dark"] .feed-filter-bar,
[data-theme="dark"] .forum-pagination-bar {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .page-size-select {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
  color: var(--text-primary);
}
</style>
