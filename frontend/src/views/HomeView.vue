<template>
  <div class="view-panel active home-view">
    <HomeAnnouncementBar @explore="handleExploreAction" />

    <HomeHeroSection
      :user-session="userSession"
      :overview="homeOverview"
      @open-login="$emit('open-login')"
      @open-register="$emit('open-register')"
      @switch-tab="(tab) => $emit('switch-tab', tab)"
    />

    <HomePillarsBento
      :hot-products="hotProducts"
      :hot-policies="hotPolicies"
      :hot-demands="hotDemands"
      :sop-templates="sopTemplates"
      @card-click="handleCardClick"
    />

    <HomeExhibitionFeed
      :items="exhibitionData"
      @exhibit-click="handleExhibitClick"
    />

    <HomeJourneySection />

    <HomeCtaBanner
      :user-session="userSession"
      @open-login="$emit('open-login')"
      @open-register="$emit('open-register')"
      @switch-tab="(tab) => $emit('switch-tab', tab)"
    />

    <HomeSiteFooter @footer-nav="handleFooterNav" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import HomeAnnouncementBar from '../components/home/HomeAnnouncementBar.vue';
import HomeHeroSection from '../components/home/HomeHeroSection.vue';
import HomePillarsBento from '../components/home/HomePillarsBento.vue';
import HomeExhibitionFeed from '../components/home/HomeExhibitionFeed.vue';
import HomeJourneySection from '../components/home/HomeJourneySection.vue';
import HomeCtaBanner from '../components/home/HomeCtaBanner.vue';
import HomeSiteFooter from '../components/home/HomeSiteFooter.vue';

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

const homeOverview = ref(null);
const hotProducts = ref([]);
const hotPolicies = ref([]);
const hotForums = ref([]);
const hotPerks = ref([]);
const hotDemands = ref([]);
const sopTemplates = ref([]);

async function loadHomeOverview() {
  try {
    const res = await dispatchGateway('home.overview', {});
    if (res.ok && res.data) {
      homeOverview.value = res.data;
    }
  } catch (e) {
    // 首页指标聚合读取失败不阻塞页面，指标条整体隐藏
  }
}

async function loadHomeProducts() {
  try {
    const res = await dispatchGateway('products.list', {});
    if (res.ok && res.data) {
      hotProducts.value = Array.isArray(res.data) ? res.data : (res.data.items || []);
    }
  } catch (e) {
    // 首页公开展览读取失败不阻塞页面
  }
}

async function loadHomePolicies() {
  try {
    const res = await dispatchGateway('policies.list', {});
    if (res.ok && res.data) {
      hotPolicies.value = Array.isArray(res.data) ? res.data : (res.data.items || []);
    }
  } catch (e) {
    // 首页公开展览读取失败不阻塞页面
  }
}

async function loadHomeForums() {
  try {
    const res = await dispatchGateway('forum.feed.stream', {
      category_code: 'ALL', cursor: 0, limit: 4, sort_by: 'hot',
    });
    if (res.ok && res.data && Array.isArray(res.data.items)) {
      hotForums.value = res.data.items;
    }
  } catch (e) {
    // 首页公开展览读取失败不阻塞页面
  }
}

async function loadHomePerks() {
  try {
    const res = await dispatchGateway('perks.list', {});
    if (res.ok && res.data) {
      const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
      hotPerks.value = items.filter((perk) => (perk.status || 'PUBLISHED') === 'PUBLISHED');
    }
  } catch (e) {
    // 首页公开展览读取失败不阻塞页面
  }
}

async function loadHomeDemands() {
  try {
    const res = await dispatchGateway('demands.list', {});
    if (res.ok && res.data) {
      const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
      hotDemands.value = items.filter((d) => (d.status || 'OPEN') === 'OPEN');
    }
  } catch (e) {
    // 首页公开展览读取失败不阻塞页面
  }
}

async function loadSopTemplates() {
  try {
    const res = await dispatchGateway('sop.flow.templates', {});
    if (res.ok && res.data) {
      sopTemplates.value = Array.isArray(res.data) ? res.data : (res.data.items || []);
    }
  } catch (e) {
    // 首页公开展览读取失败不阻塞页面
  }
}

// Computed dynamic exhibition showcase: every item is derived from backend data
const exhibitionData = computed(() => {
  const dynamicProdList = hotProducts.value.slice(0, 4).map((p) => ({
    id: `ex-product-${p.id}`,
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

  const dynamicPolicyList = hotPolicies.value.slice(0, 2).map((p) => ({
    id: `ex-policy-${p.id || p.code}`,
    type: 'policy',
    categoryTag: `${p.category === 'TAX' ? '税收减免' : '重点扶持'} · 政策中心`,
    badgeColor: 'var(--status-success)',
    title: p.title,
    summary: p.summary,
    authorOrSource: `${p.region || '全国'}${p.code ? ` · ${p.code}` : ''}`,
    metricLabel: p.subsidy_amount_max > 0 ? `最高 ¥${Number(p.subsidy_amount_max).toLocaleString()}` : (p.category === 'TAX' ? '税优减免' : '专项扶持'),
    actionLabel: p.action_text || '研判申报资格',
    targetTab: 'policy',
  }));

  const dynamicForumList = hotForums.value.slice(0, 2).map((t) => ({
    id: `ex-forum-${t.id}`,
    type: 'forum',
    categoryTag: '实战复盘 · 头脑风暴',
    badgeColor: 'var(--status-warning)',
    title: t.title,
    summary: (t.content || '').replace(/[#*`>\[\]]/g, '').slice(0, 90) + ((t.content || '').length > 90 ? '...' : ''),
    authorOrSource: `${t.author_name || '@创客'} · 风暴议题`,
    metricLabel: `${t.upvote_count ?? 0} 赞同`,
    actionLabel: '参与风暴探讨',
    targetTab: 'forum',
  }));

  const dynamicPerkList = hotPerks.value.slice(0, 2).map((perk) => ({
    id: `ex-perk-${perk.id}`,
    type: 'perk',
    categoryTag: '生态优惠 · 公告速递',
    badgeColor: 'var(--text-secondary)',
    title: perk.name,
    summary: perk.summary,
    authorOrSource: perk.provider || perk.author_name || '生态联盟伙伴',
    metricLabel: perk.value_cny > 0 ? `价值 ¥${Number(perk.value_cny).toLocaleString()}` : '专项优惠',
    actionLabel: '查看生态优惠',
    targetTab: 'perks',
  }));

  return [...dynamicProdList, ...dynamicPolicyList, ...dynamicForumList, ...dynamicPerkList];
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

onMounted(() => {
  loadHomeOverview();
  loadHomeProducts();
  loadHomePolicies();
  loadHomeForums();
  loadHomePerks();
  loadHomeDemands();
  loadSopTemplates();
});
</script>

<style scoped>
.home-view {
  position: relative;
}
</style>
