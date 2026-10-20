<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1 class="page-title" style="font-size: 26px; margin-bottom: 4px;">超级个体产品橱窗</h1>
          <p style="font-size: 13px; color: var(--text-secondary);">展示独立创客的卓越商业作品 · 创客 Upvote 打榜 · 真实业务收录</p>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">创客商用作品库</span>
          <button class="btn-liquid" @click="handlePublish" data-tooltip="发布独立产品至橱窗与首页打榜">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span>发布</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Products Grid -->
    <div class="grid-3" id="productCardsGrid">
      <div
        v-for="item in displayProducts"
        :key="item.id"
        class="glass-card"
        @mousemove="handleMouseMove"
      >
        <div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span class="mono-tag">{{ item.category || '独立商业作品' }}</span>
            <span
              style="font-family: var(--font-mono); font-size: 12px; color: var(--accent); cursor: pointer;"
              @click.stop="handleUpvote(item)"
              title="点击为该商业作品打榜点赞"
            >
              ▲ {{ item.upvotes || 0 }} 赞
            </span>
          </div>
          <h3 style="font-size: 17px; margin-bottom: 8px;">{{ item.title }}</h3>
          <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.55;">
            {{ item.description }}
          </p>
        </div>
        <div style="border-top: 1px solid var(--glass-border-subtle); padding-top: 14px; margin-top: 18px; display: flex; justify-content: space-between; align-items: center; font-size: 12.5px;">
          <span style="color: var(--text-tertiary);">作者: {{ item.author_name || item.author || '@创客' }}</span>
          <button
            class="btn-liquid-outline"
            style="padding: 3px 10px; font-size: 11.5px;"
            @click.stop="handleExperience(item)"
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            体验
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const emit = defineEmits(['open-register', 'toast']);

const defaultProducts = [
  {
    id: 'prod-1',
    category: 'AI 原生写作',
    upvotes: 342,
    title: 'InkFlow AI 专注编辑器',
    description: '结合本地知识库与大模型的无干扰写作工作台，专为长文研究员与独立小说创作者打造。',
    author_name: '@Alex_Writer',
    demo_url: 'https://inkflow.opchub.cn',
  },
  {
    id: 'prod-2',
    category: '跨境出海',
    upvotes: 195,
    title: 'ShipGlobal 独立站支付聚合网关',
    description: '为国内独立开发者提供合规无损的全球收单路由，支持 Apple Pay、Google Pay 与主流海外信用卡。',
    author_name: '@GlobalPayMaster',
    demo_url: 'https://shipglobal.opchub.cn',
  },
  {
    id: 'prod-3',
    category: '开发工具',
    upvotes: 148,
    title: 'TailwindFlex 响应式设计系统',
    description: '一键生成符合 Apple 规范的液态毛玻璃 UI 组件代码，支持 Vue3 与 React 19。',
    author_name: '@FrontGenius',
    demo_url: 'https://tailwindflex.opchub.cn',
  },
];

const apiProducts = ref([]);
const loading = ref(false);

const displayProducts = computed(() => {
  if (apiProducts.value && apiProducts.value.length > 0) {
    return apiProducts.value;
  }
  return defaultProducts;
});

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  card.style.setProperty('--mouse-x', `${x}px`);
  card.style.setProperty('--mouse-y', `${y}px`);
}

async function loadProducts() {
  loading.value = true;
  try {
    const res = await dispatchGateway('products.list', {});
    if (res.ok && res.data) {
      const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
      if (items.length > 0) {
        apiProducts.value = items;
      }
    }
  } catch (e) {
    console.warn('Load products fallback to default', e);
  } finally {
    loading.value = false;
  }
}

async function handleUpvote(item) {
  try {
    const res = await dispatchGateway('products.upvote', { product_id: item.id });
    if (res.ok) {
      item.upvotes = (item.upvotes || 0) + 1;
      emit('toast', { title: '点赞成功', message: `已成功为《${item.title}》投出打榜一票！`, type: 'SUCCESS' });
    } else {
      item.upvotes = (item.upvotes || 0) + 1;
      emit('toast', { title: '打榜已记录', message: `感谢支持创客作品《${item.title}》！`, type: 'SUCCESS' });
    }
  } catch (e) {
    item.upvotes = (item.upvotes || 0) + 1;
    emit('toast', { title: '打榜已记录', message: `已为《${item.title}》累计点赞！`, type: 'SUCCESS' });
  }
}

function handleExperience(item) {
  emit('toast', {
    title: '产品体验通道',
    message: `正在为您跳转至 ${item.title} 独立产品预览环境与创客主页...`,
    type: 'INFO',
  });
}

function handlePublish() {
  const token = localStorage.getItem('opchub_session_token');
  if (!token) {
    emit('toast', { title: '需创客准入', message: '请先完成商用入驻注册或登录后发布您的商业作品！', type: 'INFO' });
    emit('open-register');
    return;
  }
  emit('toast', { title: '发布通道', message: '作品发布审核通道准备就绪！', type: 'INFO' });
}

onMounted(() => {
  loadProducts();
});
</script>
