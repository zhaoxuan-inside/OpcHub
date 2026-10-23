<template>
  <div class="view-panel active home-view">
    <!-- 1. Top Announcement Pill -->
    <div class="announcement-wrapper">
      <div class="announcement-pill" @click="handleExploreAction('perks')">
        <span class="pulse-dot"></span>
        <span class="announcement-tag">OPC 2.0 正式上线</span>
        <span class="announcement-text">专为一人公司打造的商业操作系统 · 首月入驻立享全域政策研判与生态特权</span>
        <span class="announcement-arrow">›</span>
      </div>
    </div>

    <!-- 2. Hero Showcase Section -->
    <section class="hero-section glass-box">
      <div class="hero-content">
        <div class="hero-badge">
          <span class="mono-code">OPC_COMMERCIAL_OS // 2026</span>
          <span class="badge-separator">·</span>
          <span>一人公司 · 商业全周期赋能</span>
        </div>

        <h1 class="hero-headline">
          一人公司，<span class="text-gradient">千军万马</span>。<br />
          超级个体的下一代商业操作系统
        </h1>

        <p class="hero-subtitle">
          深度集成政策中心、智能申报文书、独立作品高光橱窗与超级个体需求集市。<br class="desktop-break" />
          告别繁杂孤立的工商、报税与流量焦虑，让单兵作战拥有集团级的商业势能与合规保障。
        </p>

        <!-- Dynamic Action Buttons -->
        <div class="hero-actions">
          <template v-if="!userSession">
            <button class="btn-liquid hero-btn-primary" @click="$emit('open-register')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="8.5" cy="7" r="4"/>
                <line x1="20" y1="8" x2="20" y2="14"/>
                <line x1="23" y1="11" x2="17" y2="11"/>
              </svg>
              <span>立即入驻 · 开启一人公司</span>
            </button>
            <button class="btn-liquid-outline hero-btn-secondary" @click="$emit('open-login')">
              <span>创客登录</span>
            </button>
          </template>
          <template v-else>
            <button class="btn-liquid hero-btn-primary" @click="$emit('switch-tab', 'forum')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span>进入创客工作台</span>
            </button>
            <button class="btn-liquid-outline hero-btn-secondary" @click="$emit('switch-tab', 'product')">
              <span>浏览产品橱窗</span>
            </button>
          </template>

          <a href="#showcaseBento" class="scroll-explore-link">
            <span>浏览平台宣传与精选成果</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M19 12l-7 7-7-7"/>
            </svg>
          </a>
        </div>

        <!-- Metrics Ticker -->
        <div class="hero-metrics-grid">
          <div class="metric-item">
            <div class="metric-value">8,400<span class="metric-plus">+</span></div>
            <div class="metric-label">认证一人公司与独立创客</div>
          </div>
          <div class="metric-divider"></div>
          <div class="metric-item">
            <div class="metric-value">36<span class="metric-plus">+</span></div>
            <div class="metric-label">核心城市扶持政策库</div>
          </div>
          <div class="metric-divider"></div>
          <div class="metric-item">
            <div class="metric-value">¥1,280<span class="metric-unit">万+</span></div>
            <div class="metric-label">辅助申报专项扶持资金</div>
          </div>
          <div class="metric-divider"></div>
          <div class="metric-item">
            <div class="metric-value">99.8<span class="metric-unit">%</span></div>
            <div class="metric-label">AI 申报材料初审通过率</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. Core Capabilities Bento Grid (便当盒展示矩阵) -->
    <section id="showcaseBento" class="section-container">
      <div class="section-header">
        <div class="mono-tag">01 // PLATFORM PILLARS</div>
        <h2 class="section-title">四大核心支柱 · 解构超级个体的商业全景</h2>
        <p class="section-desc">
          我们为一人公司定制了从找政策、备文书，到拓市场、求合作的完整能力链路。
        </p>
      </div>

      <div class="bento-grid">
        <!-- Bento 1: 政策中心 (Large) -->
        <div class="bento-card bento-span-2" @mousemove="handleMouseMove" @click="handleCardClick('policy')">
          <div class="bento-content">
            <div class="card-top-meta">
              <span class="mono-tag accent-tag">POL-RADAR // 实时聚合</span>
              <span class="card-status-badge">全域覆盖</span>
            </div>
            <h3 class="bento-title">政策中心 · 精准洞悉各省市一人公司专项扶持</h3>
            <p class="bento-text">
              打破信息不对称与晦涩公文壁垒。独家收录深圳、上海、杭州、成都等城市针对 OPC、独立开发者的无偿资助、税收减免与算力免租政策，AI 智能评估匹配度。
            </p>

            <div class="bento-preview-pills">
              <div class="policy-chip">
                <span class="city-dot"></span>
                <span class="city-name">深圳南山</span>
                <span class="policy-amount">最高 ¥500,000</span>
                <span class="policy-brief">算力补贴 & 研发直补</span>
              </div>
              <div class="policy-chip">
                <span class="city-dot"></span>
                <span class="city-name">上海张江</span>
                <span class="policy-amount">税收减半</span>
                <span class="policy-brief">初创创客税收优惠</span>
              </div>
              <div class="policy-chip">
                <span class="city-dot"></span>
                <span class="city-name">成都高新</span>
                <span class="policy-amount">¥100,000 创新券</span>
                <span class="policy-brief">一人工作室入驻减免</span>
              </div>
            </div>
          </div>
          <div class="bento-action-row">
            <span class="action-text">查看全部政策中心数据库</span>
            <span class="action-arrow">→</span>
          </div>
        </div>

        <!-- Bento 2: 产品橱窗 (Vertical) -->
        <div class="bento-card" @mousemove="handleMouseMove" @click="handleCardClick('product')">
          <div class="bento-content">
            <div class="card-top-meta">
              <span class="mono-tag">SHOWCASE // 独立作品秀场</span>
              <span class="card-status-badge hot">HOT 榜单</span>
            </div>
            <h3 class="bento-title">产品橱窗 · 独立作品高光舞台</h3>
            <p class="bento-text">
              打造超级个体的 Product Hunt。优秀商业产品打榜 Upvote，全站置顶曝光与公测获客直达。
            </p>
            <div class="mini-showcase-box">
              <template v-if="hotProducts.length > 0">
                <div
                  v-for="(p, pIdx) in hotProducts.slice(0, 2)"
                  :key="p.id"
                  class="mini-product-item"
                >
                  <div class="mini-prod-avatar" :class="{ alt: pIdx > 0 }">
                    <img v-if="p.icon_url" :src="p.icon_url" :alt="p.title" style="width: 100%; height: 100%; object-fit: contain; padding: 2px;" />
                    <span v-else>{{ getInitials(p.title) }}</span>
                  </div>
                  <div class="mini-prod-info">
                    <div class="mini-prod-title">{{ p.title }}</div>
                    <div class="mini-prod-sub">{{ p.tagline || p.description }}</div>
                  </div>
                  <div class="mini-upvote"><OpcIcon name="like" :size="11" /> {{ p.upvote_count ?? p.upvotes ?? 0 }}</div>
                </div>
              </template>
              <div v-else class="mini-product-item" style="justify-content: center; color: var(--text-tertiary); font-size: 12px; padding: 12px 0;">
                <span>暂无上架作品 · 点击探索首发</span>
              </div>
            </div>
          </div>
          <div class="bento-action-row">
            <span class="action-text">探索创客产品打榜</span>
            <span class="action-arrow">→</span>
          </div>
        </div>

        <!-- Bento 3: AI 文书与 SOP (Vertical) -->
        <div class="bento-card" @mousemove="handleMouseMove" @click="handleCardClick('sop')">
          <div class="bento-content">
            <div class="card-top-meta">
              <span class="mono-tag">SOP-DOC // 智能公函与文书</span>
              <span class="card-status-badge ai">AI 增强</span>
            </div>
            <h3 class="bento-title">流程文书 · 标准化法商合规</h3>
            <p class="bento-text">
              无需聘请昂贵法务与中介。工商设立公函、银行开户指引、财务零申报 SOP 一键生成。
            </p>
            <div class="sop-mini-stepper">
              <div class="stepper-node done">
                <div class="step-num">01</div>
                <div class="step-desc">工商核名设立</div>
              </div>
              <div class="stepper-line"></div>
              <div class="stepper-node active">
                <div class="step-num">02</div>
                <div class="step-desc">银行开户指导</div>
              </div>
              <div class="stepper-line"></div>
              <div class="stepper-node">
                <div class="step-num">03</div>
                <div class="step-desc">零申报财务合规</div>
              </div>
            </div>
          </div>
          <div class="bento-action-row">
            <span class="action-text">生成标准化合规文书</span>
            <span class="action-arrow">→</span>
          </div>
        </div>

        <!-- Bento 4: 需求集市与撮合 (Large) -->
        <div class="bento-card bento-span-2" @mousemove="handleMouseMove" @click="handleCardClick('demand')">
          <div class="bento-content">
            <div class="card-top-meta">
              <span class="mono-tag">MARKET // 技能交易撮合</span>
              <span class="card-status-badge">即时对接</span>
            </div>
            <h3 class="bento-title">需求集市 · 超级个体的分布式协同网络</h3>
            <p class="bento-text">
              一个人办公司，不代表单打独斗。当需要出海海外支付集成、UI 品牌设计或跨境法务支持时，在集市一键发布需求，与平台 8,400+ 专业创客快速联名撮合。
            </p>
            <div class="demands-mini-stream">
              <div class="demand-pill">
                <span class="demand-type">技术外包</span>
                <span class="demand-title">微SaaS出海 Stripe & LemonSqueezy 路由对接</span>
                <span class="demand-budget">¥15,000</span>
              </div>
              <div class="demand-pill">
                <span class="demand-type">视觉设计</span>
                <span class="demand-title">一人公司 VisionOS 液态毛玻璃风格官网与套件</span>
                <span class="demand-budget">¥8,500</span>
              </div>
            </div>
          </div>
          <div class="bento-action-row">
            <span class="action-text">浏览需求撮合与商机</span>
            <span class="action-arrow">→</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 4. Interactive Editorial Content Feed (内容展示平台式筛选展示) -->
    <section class="section-container">
      <div class="section-header">
        <div class="mono-tag">02 // CURATED EXHIBITION</div>
        <h2 class="section-title">精选展厅 · 浏览创客作品与扶持精粹</h2>
        <p class="section-desc">
          探索「晨昏线外」实时沉淀的真实作品、深度政策与经验手记。
        </p>

        <!-- Content Filter Tabs -->
        <div class="filter-tabs-bar">
          <button
            class="filter-tab-pill"
            :class="{ active: currentContentFilter === 'all' }"
            @click="currentContentFilter = 'all'"
          >
            全部精选推荐
          </button>
          <button
            class="filter-tab-pill"
            :class="{ active: currentContentFilter === 'product' }"
            @click="currentContentFilter = 'product'"
          >
            <OpcIcon name="flame" :size="13" /> 卓越商业作品
          </button>
          <button
            class="filter-tab-pill"
            :class="{ active: currentContentFilter === 'policy' }"
            @click="currentContentFilter = 'policy'"
          >
            <OpcIcon name="landmark" :size="13" /> 重点扶持政策
          </button>
          <button
            class="filter-tab-pill"
            :class="{ active: currentContentFilter === 'forum' }"
            @click="currentContentFilter = 'forum'"
          >
            <OpcIcon name="bulb" :size="13" /> 创客思想手记
          </button>
          <button
            class="filter-tab-pill"
            :class="{ active: currentContentFilter === 'perk' }"
            @click="currentContentFilter = 'perk'"
          >
            <OpcIcon name="gift" :size="13" /> 独家生态特权
          </button>
        </div>
      </div>

      <!-- Display Grid -->
      <div class="grid-3 exhibition-grid">
        <div
          v-for="item in filteredContentList"
          :key="item.id"
          class="glass-card exhibition-card"
          @mousemove="handleMouseMove"
          @click="handleExhibitClick(item)"
        >
          <div>
            <div class="exhibit-header">
              <span class="mono-tag" :style="{ color: item.badgeColor || 'var(--text-secondary)' }">
                {{ item.categoryTag }}
              </span>
              <span class="exhibit-metric">{{ item.metricLabel }}</span>
            </div>

            <h3 class="exhibit-title">{{ item.title }}</h3>
            <p class="exhibit-summary">{{ item.summary }}</p>
          </div>

          <div class="exhibit-footer">
            <div class="exhibit-author">
              <div class="author-dot"></div>
              <span>{{ item.authorOrSource }}</span>
            </div>
            <div class="exhibit-cta">
              <span>{{ item.actionLabel }}</span>
              <span class="cta-arrow">›</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 5. The OPC Journey (一人公司的全生命周期图景) -->
    <section class="section-container">
      <div class="section-header">
        <div class="mono-tag">03 // JOURNEY & EVOLUTION</div>
        <h2 class="section-title">一人公司演进路径 · 从单点萌芽到自主商业实体</h2>
        <p class="section-desc">
          「晨昏线外」伴随超级个体成长的四个核心阶段，提供不同周期的关键基础设施。
        </p>
      </div>

      <div class="journey-grid">
        <div class="journey-card glass-card" @mousemove="handleMouseMove">
          <div class="journey-step-num">PHASE 01</div>
          <h4 class="journey-card-title">立项与政策锁定</h4>
          <p class="journey-card-desc">
            借助政策中心测算全国优惠税率与落地园区，筛选最契合主营赛道的落地城市与初创免租扶持。
          </p>
          <div class="journey-feature-tag">政策中心 · 城市匹配</div>
        </div>

        <div class="journey-card glass-card" @mousemove="handleMouseMove">
          <div class="journey-step-num">PHASE 02</div>
          <h4 class="journey-card-title">合规注册与设立</h4>
          <p class="journey-card-desc">
            AI 辅助生成标准化公司章程与工商设立公函，指导银行基本户设立与首年合规税务零申报。
          </p>
          <div class="journey-feature-tag">流程文书 · AI 公函生成</div>
        </div>

        <div class="journey-card glass-card" @mousemove="handleMouseMove">
          <div class="journey-step-num">PHASE 03</div>
          <h4 class="journey-card-title">产品发布与商业化</h4>
          <p class="journey-card-desc">
            作品上架超级个体橱窗，通过全网创客打榜获取早期种子种子用户，验证产品商业变现模型。
          </p>
          <div class="journey-feature-tag">产品橱窗 · Upvote 打榜</div>
        </div>

        <div class="journey-card glass-card" @mousemove="handleMouseMove">
          <div class="journey-step-num">PHASE 04</div>
          <h4 class="journey-card-title">生态协同与规模化</h4>
          <p class="journey-card-desc">
            在需求集市撮合外部专家弥补能力短板，领取平台专属云服务器、AI 算力与财税折扣券。
          </p>
          <div class="journey-feature-tag">需求集市 · 生态特权</div>
        </div>
      </div>
    </section>

    <!-- 6. Maker Testimonials (创客心声与社会认同) -->
    <section class="section-container">
      <div class="section-header">
        <div class="mono-tag">04 // MAKER VOICES</div>
        <h2 class="section-title">听听来自前线创客的真实声音</h2>
        <p class="section-desc">
          数千位独立工程师、设计师、研究员与内容创作者正在「晨昏线外」经营他们的一人商业帝国。
        </p>
      </div>

      <div class="grid-3">
        <div class="glass-card testimonial-card" @mousemove="handleMouseMove">
          <p class="testimonial-quote">
            “以前最恐惧的就是工商注册与繁复的税务报表，找中介每次都要好几千。在「晨昏线外」跟着 SOP 走，配合政策中心，顺利拿到了首批创业孵化直补，省下大笔开销。”
          </p>
          <div class="testimonial-author-row">
            <div class="testimonial-avatar">LT</div>
            <div>
              <div class="author-name">@Leon_Tech</div>
              <div class="author-role">独立微SaaS全栈创客 · 深圳</div>
            </div>
          </div>
        </div>

        <div class="glass-card testimonial-card" @mousemove="handleMouseMove">
          <p class="testimonial-quote">
            “把我的 AI 写作工具放到产品橱窗后，第一周就获得了 300+ 试用用户和 12 个年度订阅。更棒的是在需求集市找到了长期合作的出海支付工程师，一人公司也能快速拼装能力。”
          </p>
          <div class="testimonial-author-row">
            <div class="testimonial-avatar alt">SD</div>
            <div>
              <div class="author-name">@Sophia_Design</div>
              <div class="author-role">AI 创意工具独立开发者 · 杭州</div>
            </div>
          </div>
        </div>

        <div class="glass-card testimonial-card" @mousemove="handleMouseMove">
          <p class="testimonial-quote">
            “政策中心的白话解读是真神。传统政府公文几十页又长又晦涩，这里的关键资格和材料清单一目了然，一人创业的时间终于能 100% 聚焦在核心产品打磨上。”
          </p>
          <div class="testimonial-author-row">
            <div class="testimonial-avatar mono">DC</div>
            <div>
              <div class="author-name">@David_CFO</div>
              <div class="author-role">独立财务战略顾问 · 上海</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 7. Bottom Conversion Banner (底部转化大卡片) -->
    <section class="section-container">
      <div class="glass-box bottom-cta-box" @mousemove="handleMouseMove">
        <div class="bottom-cta-orb"></div>
        <div class="bottom-cta-inner">
          <div class="mono-tag" style="background: var(--accent-glass); color: var(--accent); margin-bottom: 16px;">
            JOIN THE OPC REVOLUTION
          </div>
          <h2 class="bottom-cta-title">
            今天，正式开启你的一人公司之旅
          </h2>
          <p class="bottom-cta-desc">
            无论你是一名全栈工程师、产品设计师、内容专家还是独立顾问，「晨昏线外」为你提供全方位的商业后盾与成长生态。
          </p>
          <div class="bottom-cta-actions">
            <button
              v-if="!userSession"
              class="btn-liquid bottom-btn-primary"
              @click="$emit('open-register')"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="8.5" cy="7" r="4"/>
                <line x1="20" y1="8" x2="20" y2="14"/>
                <line x1="23" y1="11" x2="17" y2="11"/>
              </svg>
              <span>免费注册入驻平台</span>
            </button>
            <button
              v-if="!userSession"
              class="btn-liquid-outline bottom-btn-secondary"
              @click="$emit('open-login')"
            >
              <span>已有账号？立即登录</span>
            </button>
            <button
              v-else
              class="btn-liquid bottom-btn-primary"
              @click="$emit('switch-tab', 'forum')"
            >
              <span>进入创客工作台 ›</span>
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 8. Editorial Footer (平台页脚) -->
    <footer class="editorial-footer">
      <div class="footer-inner">
        <div class="footer-brand-col">
          <div class="footer-brand-title">
            <BrandLogo :size="24" />
            <span>晨昏线外</span>
            <span class="footer-brand-ver">Beyond the Line</span>
          </div>
          <p class="footer-brand-text">
            全国领先的面向超级个体与一人公司 (One Person Company) 的全周期商业操作系统。于晨昏线外，赋能每一份独立创造的商业势能。
          </p>
        </div>

        <div class="footer-links-col">
          <div class="footer-col-heading">平台四大支柱</div>
          <ul class="footer-links-list">
            <li><a @click.prevent="handleFooterNav('policy')">政策中心与城市招商</a></li>
            <li><a @click.prevent="handleFooterNav('sop')">合规文书与流程 SOP</a></li>
            <li><a @click.prevent="handleFooterNav('product')">超级个体产品橱窗</a></li>
            <li><a @click.prevent="handleFooterNav('demand')">创客需求集市撮合</a></li>
          </ul>
        </div>

        <div class="footer-links-col">
          <div class="footer-col-heading">创客成长生态</div>
          <ul class="footer-links-list">
            <li><a @click.prevent="handleFooterNav('forum')">头脑风暴社区</a></li>
            <li><a @click.prevent="handleFooterNav('perks')">生态伙伴优惠公告</a></li>
            <li><a @click.prevent="handleFooterNav('compliance')">合规法务指南</a></li>
          </ul>
        </div>

        <div class="footer-links-col">
          <div class="footer-col-heading">平台治理与信任</div>
          <ul class="footer-links-list">
            <li><span>用户服务协议</span></li>
            <li><span>隐私合规保护</span></li>
            <li><span>PostgreSQL 18 存证保障</span></li>
            <li><span>电信级审计与数据加密</span></li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom-bar">
        <div>© 2026 晨昏线外 Beyond Terminator. All Rights Reserved.</div>
        <div class="footer-bottom-meta">
          <span>Apple VisionOS Liquid Glass Spec</span>
          <span>·</span>
          <span>iA Writer Editorial Rhythm</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import BrandLogo from '../components/BrandLogo.vue';

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits([
  'open-login',
  'open-register',
  'switch-tab',
  'toast',
]);

const currentContentFilter = ref('all');
const hotProducts = ref([]);
const hotPolicies = ref([]);

async function loadHomeProducts() {
  try {
    const res = await dispatchGateway('products.list', {});
    if (res.ok && res.data) {
      hotProducts.value = Array.isArray(res.data) ? res.data : (res.data.items || []);
    }
  } catch (e) {
    console.error('Failed to load home products:', e);
  }
}

async function loadHomePolicies() {
  try {
    const res = await dispatchGateway('policies.list', {});
    if (res.ok && res.data) {
      hotPolicies.value = Array.isArray(res.data) ? res.data : (res.data.items || []);
    }
  } catch (e) {
    console.error('Failed to load home policies:', e);
  }
}

function getInitials(name) {
  if (!name) return 'OP';
  const clean = name.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
  return clean.slice(0, 2).toUpperCase() || 'OP';
}

// Static baseline resources for other tabs (policy / forum / perk)
const staticBaselineExhibits = [
  {
    id: 'ex-pol-1',
    type: 'policy',
    categoryTag: '重点扶持 · 政策中心',
    badgeColor: 'var(--status-success)',
    title: '深圳市南山区一人公司算力与租金直达资助',
    summary: '面向人工智能、独立软件开发领域的 OPC 实体，提供首年办公空间免租及最高 50 万元的公有云与智算算力补贴。',
    authorOrSource: '深圳市科技创新局 · POL-2026-088',
    metricLabel: '最高 ¥500,000',
    actionLabel: '研判申报资格',
    targetTab: 'policy',
  },
  {
    id: 'ex-forum-1',
    type: 'forum',
    categoryTag: '实战复盘 · 头脑风暴',
    badgeColor: 'var(--status-warning)',
    title: '一人公司如何实现首年收支平衡？3000 字全链路拆解',
    summary: '涵盖公司设立、零申报财务避坑、海外 Stripe 注册以及首批 100 个种子客户获客的真实实战心得。',
    authorOrSource: '@Master_Maker · 深度长文',
    metricLabel: '1,420 次阅读',
    actionLabel: '阅读经验全文',
    targetTab: 'forum',
  },
  {
    id: 'ex-pol-2',
    type: 'policy',
    categoryTag: '税收减免 · 政策中心',
    badgeColor: 'var(--status-success)',
    title: '上海张江创客工作室小微所得税减免细则',
    summary: '针对独立设计师与个人咨询工作室，享受应纳税所得额 100 万元以内减免 20% 专项税优政策，全流程在线填报。',
    authorOrSource: '张江综合保税区管理局 · POL-2026-042',
    metricLabel: '税优减免 20%',
    actionLabel: '研判申报资格',
    targetTab: 'policy',
  },
  {
    id: 'ex-perk-1',
    type: 'perk',
    categoryTag: '生态优惠 · 公告速递',
    badgeColor: 'var(--text-secondary)',
    title: '生态伙伴云服务器与 Token 优惠上新',
    summary: '汇集云厂商 Token 抵扣券、服务器折扣与 SaaS 服务特惠的一站式优惠公告板，直达领取权益落地技术架构。',
    authorOrSource: '晨昏线外 生态联盟伙伴',
    metricLabel: '多类优惠持续上新',
    actionLabel: '查看生态优惠',
    targetTab: 'perks',
  },
];

// Computed dynamic exhibition showcase data: dynamically derives products & policies from backend
const exhibitionData = computed(() => {
  const dynamicProdList = hotProducts.value.map((p) => ({
    id: `ex-${p.id}`,
    type: 'product',
    categoryTag: `${p.category || '独立作品'} · 橱窗收录`,
    badgeColor: 'var(--accent)',
    title: p.title,
    summary: p.tagline || p.description,
    authorOrSource: `${p.author_name || '@创客'} · 创客出品`,
    metricLabel: `${p.upvote_count ?? p.upvotes ?? 0} 赞`,
    actionLabel: '查看产品详情',
    targetTab: 'product',
  }));

  const dynamicPolicyList = hotPolicies.value.length > 0
    ? hotPolicies.value.slice(0, 2).map((p) => ({
        id: `ex-pol-${p.id || p.code}`,
        type: 'policy',
        categoryTag: `${p.category === 'TAX' ? '税收减免' : '重点扶持'} · 政策中心`,
        badgeColor: 'var(--status-success)',
        title: p.title,
        summary: p.summary,
        authorOrSource: `${p.region || '全国'} · ${p.code || 'POL-2026'}`,
        metricLabel: p.subsidy_amount_max > 0 ? `最高 ¥${Number(p.subsidy_amount_max).toLocaleString()}` : (p.category === 'TAX' ? '税优减免' : '专项扶持'),
        actionLabel: p.action_text || '研判申报资格',
        targetTab: 'policy',
      }))
    : staticBaselineExhibits.filter((e) => e.type === 'policy');

  const otherExhibits = staticBaselineExhibits.filter((e) => e.type !== 'policy');

  return [...dynamicProdList, ...dynamicPolicyList, ...otherExhibits];
});

const filteredContentList = computed(() => {
  if (currentContentFilter.value === 'all') {
    return exhibitionData.value;
  }
  return exhibitionData.value.filter((item) => item.type === currentContentFilter.value);
});

function handleExploreAction(tab) {
  if (!props.userSession) {
    emit('open-login');
  } else {
    emit('switch-tab', tab);
  }
}

function handleCardClick(tab) {
  if (!props.userSession) {
    emit('toast', {
      title: '创客工作台权限提示',
      message: '当前板块需登录后使用。请登录或免费入驻成为平台认证创客。',
      type: 'INFO',
    });
    emit('open-login');
  } else {
    emit('switch-tab', tab);
  }
}

function handleExhibitClick(item) {
  if (!props.userSession) {
    emit('toast', {
      title: '欢迎体验「晨昏线外」',
      message: `【${item.title}】的完整详情与交互能力仅对认证创客开放，请先登录或入驻。`,
      type: 'INFO',
    });
    emit('open-login');
  } else {
    emit('switch-tab', item.targetTab);
  }
}

function handleFooterNav(tab) {
  handleCardClick(tab);
}

// Fluid mouse spotlight helper
function handleMouseMove(e) {
  const rect = e.currentTarget.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  e.currentTarget.style.setProperty('--mouse-x', `${x}px`);
  e.currentTarget.style.setProperty('--mouse-y', `${y}px`);
}

onMounted(() => {
  loadHomeProducts();
  loadHomePolicies();
});
</script>

<style scoped>
.home-view {
  position: relative;
}

/* Announcement Pill */
.announcement-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.announcement-pill {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow), var(--glass-specular);
  backdrop-filter: var(--blur-strength);
  -webkit-backdrop-filter: var(--blur-strength);
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-liquid);
  user-select: none;
}

.announcement-pill:hover {
  background: var(--glass-surface-hover);
  border-color: var(--glass-border-hover);
  box-shadow: var(--glass-glow-halo);
  color: var(--text-primary);
  transform: translateY(-1px);
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-success);
  box-shadow: 0 0 8px var(--status-success-soft);
  flex-shrink: 0;
  animation: pulse 2s infinite ease-in-out;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.announcement-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.announcement-text {
  font-weight: 500;
}

.announcement-arrow {
  font-size: 14px;
  color: var(--text-tertiary);
  transition: transform 0.2s ease;
}

.announcement-pill:hover .announcement-arrow {
  transform: translateX(3px);
  color: var(--accent);
}

/* Hero Section */
.hero-section {
  padding: 64px 48px 52px;
  text-align: center;
  margin-bottom: 56px;
  position: relative;
  overflow: hidden;
}

.hero-content {
  max-width: 900px;
  margin: 0 auto;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 20px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.badge-separator {
  opacity: 0.4;
}

.mono-code {
  font-family: var(--font-mono);
  color: var(--accent);
  letter-spacing: 0.05em;
}

.hero-headline {
  font-family: var(--font-display);
  font-size: 48px;
  font-weight: 700;
  line-height: 1.18;
  letter-spacing: -0.04em;
  color: var(--text-primary);
  margin-bottom: 22px;
}

.text-gradient {
  color: var(--accent);
}

.hero-subtitle {
  font-size: 17px;
  line-height: 1.65;
  color: var(--text-secondary);
  margin-bottom: 38px;
  font-weight: 400;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 52px;
}

.hero-btn-primary {
  padding: 12px 28px;
  font-size: 14.5px;
  font-weight: 600;
  box-shadow: 0 4px 20px rgba(0, 113, 227, 0.28);
}

.hero-btn-secondary {
  padding: 12px 24px;
  font-size: 14.5px;
}

.scroll-explore-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: var(--text-tertiary);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: var(--radius-full);
  transition: var(--transition-liquid);
}

.scroll-explore-link:hover {
  color: var(--accent);
  transform: translateY(1px);
}

/* Metrics Grid */
.hero-metrics-grid {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 24px 0 0;
  border-top: 1px solid var(--glass-border-subtle);
  flex-wrap: wrap;
  gap: 16px;
}

.metric-item {
  text-align: center;
  flex: 1;
  min-width: 140px;
}

.metric-value {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1.1;
  margin-bottom: 4px;
}

.metric-plus, .metric-unit {
  color: var(--accent);
  font-weight: 600;
  font-size: 24px;
}

.metric-label {
  font-size: 12.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.metric-divider {
  width: 1px;
  height: 36px;
  background: var(--glass-border-subtle);
}

/* Sections Common */
.section-container {
  margin-bottom: 72px;
}

.section-header {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 36px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin-top: 8px;
  margin-bottom: 10px;
}

.section-desc {
  font-size: 14.5px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Bento Grid */
.bento-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.bento-span-2 {
  grid-column: span 2;
}

.bento-card {
  background: var(--glass-surface);
  backdrop-filter: var(--blur-strength);
  -webkit-backdrop-filter: var(--blur-strength);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow), var(--glass-specular);
  padding: 30px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--transition-liquid);
}

.bento-card:hover {
  background: var(--glass-surface-hover);
  border-color: var(--glass-border-hover);
  box-shadow: var(--glass-shadow-hover), var(--glass-glow-halo);
  transform: translateY(-4px) scale(1.006);
}

.card-top-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.accent-tag {
  background: var(--accent-glass);
  color: var(--accent);
  border-color: rgba(0, 113, 227, 0.2);
}

.card-status-badge {
  font-size: 11px;
  font-family: var(--font-mono);
  padding: 2px 7px;
  border-radius: var(--radius-xs);
  background: var(--status-success-soft);
  color: var(--status-success);
}

.card-status-badge.hot {
  background: var(--status-warning-soft);
  color: var(--status-warning);
}

.card-status-badge.ai {
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
}

.bento-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.bento-text {
  font-size: 13.5px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 22px;
}

.bento-preview-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.policy-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.city-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

.city-name {
  font-weight: 600;
  color: var(--text-primary);
}

.policy-amount {
  font-family: var(--font-mono);
  color: var(--text-secondary);
  font-weight: 600;
}

.policy-brief {
  color: var(--text-tertiary);
}

.mini-showcase-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.mini-product-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-sm);
}

.mini-prod-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.mini-prod-avatar.alt {
  background: var(--accent);
}

.mini-prod-info {
  flex: 1;
  min-width: 0;
}

.mini-prod-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mini-prod-sub {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mini-upvote {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
}

.sop-mini-stepper {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
}

.stepper-node {
  flex: 1;
  padding: 8px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  text-align: center;
}

.stepper-node.active {
  background: var(--accent-glass);
  border-color: var(--accent);
}

.stepper-node .step-num {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
  margin-bottom: 2px;
}

.stepper-node.active .step-num {
  color: var(--accent);
  font-weight: 700;
}

.stepper-node .step-desc {
  font-size: 11px;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
}

.stepper-line {
  width: 12px;
  height: 1px;
  background: var(--glass-border-subtle);
  flex-shrink: 0;
}

.demands-mini-stream {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.demand-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.demand-type {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--glass-surface);
  color: var(--text-secondary);
}

.demand-title {
  flex: 1;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.demand-budget {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
}

.bento-action-row {
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12.5px;
  color: var(--accent);
  font-weight: 500;
}

.bento-card:hover .action-arrow {
  transform: translateX(4px);
}

.action-arrow {
  transition: transform 0.2s ease;
}

/* Filter Tabs Bar */
.filter-tabs-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 24px;
}

.filter-tab-pill {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-liquid);
  user-select: none;
}

.filter-tab-pill:hover {
  color: var(--text-primary);
  background: var(--glass-surface-hover);
}

.filter-tab-pill.active {
  color: #fff;
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 2px 10px rgba(0, 113, 227, 0.35);
}

/* Exhibition Cards */
.exhibition-grid {
  margin-top: 20px;
}

.exhibition-card {
  min-height: 220px;
}

.exhibit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.exhibit-metric {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
}

.exhibit-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  line-height: 1.35;
}

.exhibit-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.55;
  margin-bottom: 18px;
}

.exhibit-footer {
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.exhibit-author {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-tertiary);
}

.author-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

.exhibit-cta {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--accent);
  font-weight: 600;
}

.cta-arrow {
  font-size: 14px;
  transition: transform 0.2s ease;
}

.exhibition-card:hover .cta-arrow {
  transform: translateX(3px);
}

/* Journey Grid */
.journey-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.journey-card {
  padding: 24px 20px;
}

.journey-step-num {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.journey-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.journey-card-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.55;
  margin-bottom: 14px;
}

.journey-feature-tag {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-tertiary);
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 10px;
}

/* Testimonial Cards */
.testimonial-card {
  padding: 24px;
}

.testimonial-quote {
  font-size: 13.5px;
  color: var(--text-secondary);
  line-height: 1.65;
  margin-bottom: 20px;
  font-style: italic;
}

.testimonial-author-row {
  display: flex;
  align-items: center;
  gap: 12px;
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 14px;
}

.testimonial-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.testimonial-avatar.alt {
  background: var(--accent);
}

.testimonial-avatar.mono {
  background: var(--accent);
}

.author-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.author-role {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

/* Bottom CTA Banner */
.bottom-cta-box {
  padding: 56px 40px;
  text-align: center;
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-lg);
  margin-top: 32px;
}

.bottom-cta-orb {
  position: absolute;
  top: -50%;
  left: 30%;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
  pointer-events: none;
  filter: blur(40px);
}

.bottom-cta-inner {
  position: relative;
  z-index: 1;
  max-width: 640px;
  margin: 0 auto;
}

.bottom-cta-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin-bottom: 14px;
}

.bottom-cta-desc {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 28px;
}

.bottom-cta-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
}

.bottom-btn-primary {
  padding: 12px 28px;
  font-size: 14px;
  font-weight: 600;
}

.bottom-btn-secondary {
  padding: 12px 24px;
  font-size: 14px;
}

/* Editorial Footer */
.editorial-footer {
  margin-top: 80px;
  border-top: 1px solid var(--glass-border-subtle);
  padding: 56px 0 32px;
}

.footer-inner {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 32px;
  margin-bottom: 40px;
}

.footer-brand-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.footer-brand-mark {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  background: var(--accent);
}

.footer-brand-ver {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 400;
}

.footer-brand-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 320px;
}

.footer-col-heading {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 14px;
}

.footer-links-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12.5px;
}

.footer-links-list a {
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s ease;
}

.footer-links-list a:hover {
  color: var(--accent);
}

.footer-links-list span {
  color: var(--text-tertiary);
}

.footer-bottom-bar {
  border-top: 1px solid var(--glass-border-subtle);
  padding-top: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-tertiary);
  flex-wrap: wrap;
  gap: 12px;
}

.footer-bottom-meta {
  display: flex;
  gap: 8px;
}

/* Responsive Breakpoints */
@media (max-width: 1024px) {
  .hero-headline {
    font-size: 38px;
  }
  .bento-grid {
    grid-template-columns: 1fr;
  }
  .bento-span-2 {
    grid-column: span 1;
  }
  .journey-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .footer-inner {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 680px) {
  .hero-section {
    padding: 36px 20px 32px;
  }
  .hero-headline {
    font-size: 28px;
  }
  .hero-subtitle {
    font-size: 14px;
  }
  .desktop-break {
    display: none;
  }
  .hero-metrics-grid {
    gap: 20px;
  }
  .metric-divider {
    display: none;
  }
  .journey-grid {
    grid-template-columns: 1fr;
  }
  .footer-inner {
    grid-template-columns: 1fr;
  }
}
</style>
