<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1 class="page-title" style="font-size: 26px; margin-bottom: 4px;">头脑风暴</h1>
          <p style="font-size: 13px; color: var(--text-secondary);">超级个体灵感碰撞 · 独立出海答疑 · 经验踩坑互助</p>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">实战交流讨论区</span>
          <button class="btn-liquid" @click="openPostModal">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            <span>发帖</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Forum Layout -->
    <div class="forum-container">
      <!-- Left: Brainstorm Categories -->
      <div class="glass-box" style="padding: 20px;">
        <div style="font-size: 12px; font-family: var(--font-mono); color: var(--text-tertiary); margin-bottom: 12px;">
          BRAINSTORM THEMES
        </div>
        <div
          v-for="cat in categories"
          :key="cat.name"
          class="bar-list-item"
          :class="{ active: selectedCategory === cat.name }"
          @click="selectedCategory = cat.name"
        >
          <span>{{ cat.name }}</span>
          <span>{{ cat.count }}</span>
        </div>
      </div>

      <!-- Right: Brainstorm Posts List -->
      <div class="glass-box" style="padding: 20px 28px;" id="forumPostsContainer">
        <!-- RAG Community AI Q&A Box -->
        <div style="background: rgba(0, 113, 227, 0.05); border: 1px solid var(--accent-glass); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 13.5px; color: var(--accent);">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
              <span>创客问答</span>
            </div>
            <span class="mono-tag" style="font-size: 11px;">RAG: Vector Search + LLM</span>
          </div>
          <div style="display: flex; gap: 8px;">
            <input
              v-model="ragQuery"
              type="text"
              class="glass-input input-liquid"
              placeholder="输入您的一人公司经营疑问（如：注册地址如何选？银行开户如何防风控？）..."
              style="flex: 1; padding: 8px 12px; font-size: 13px;"
              @keydown.enter="handleRagAsk"
            />
            <button
              class="btn-liquid"
              @click="handleRagAsk"
              :disabled="ragLoading"
              style="padding: 8px 16px; font-size: 12.5px; white-space: nowrap;"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span>{{ ragLoading ? '分析中...' : '智能问答' }}</span>
            </button>
          </div>

          <!-- RAG Result Display -->
          <div
            v-if="ragAnswer"
            style="margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--glass-border-subtle);"
          >
            <div style="font-weight: 600; font-size: 13px; color: var(--text-primary); margin-bottom: 6px;">
              AI 顾问解答：
            </div>
            <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6; white-space: pre-wrap; margin-bottom: 10px;">
              {{ ragAnswer }}
            </p>
            <div style="font-size: 11.5px; color: var(--text-tertiary);">
              参考来源: 《一人公司财税合规实务手册》、《网络安全法与数据隐私指引》
            </div>
          </div>
        </div>

        <!-- Posts List -->
        <div
          v-for="post in filteredPosts"
          :key="post.id"
          class="post-card"
          @click="viewPost(post)"
        >
          <div class="post-title">
            <span v-if="post.pinned" class="post-pinned">{{ post.pinned }}</span>
            <span>{{ post.title }}</span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">
            {{ post.snippet }}
          </p>
          <div style="display: flex; gap: 16px; font-size: 11.5px; color: var(--text-tertiary); font-family: var(--font-mono);">
            <span>作者: {{ post.author }}</span>
            <span>回复: {{ post.replies }}</span>
            <span>最后更新: {{ post.updated_at }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const emit = defineEmits(['open-register', 'toast']);

const categories = [
  { name: '全部风暴区', count: '1,280' },
  { name: '工商财税', count: '420' },
  { name: '独立出海', count: '365' },
  { name: 'AI智能体', count: '290' },
  { name: '政策申报', count: '114' },
  { name: '技术踩坑', count: '91' },
];

const selectedCategory = ref('全部风暴区');

const samplePosts = [
  {
    id: 1,
    pinned: '置顶',
    category: '工商财税',
    title: '【必读】2026 一人公司工商年报与增值税免征额度最新操作细则',
    snippet: '针对季度营收 30 万以下免税政策的电子税务局申报实录，附常见报错与退税处理流程...',
    author: '平台管家',
    replies: 89,
    updated_at: '10 分钟前',
  },
  {
    id: 2,
    pinned: '精选',
    category: '政策申报',
    title: '从 0 到 1 拿到长三角智能算力补贴 12 万元的全周期复盘 (附审批材料格式)',
    snippet: '很多朋友以为个体户申报不了算力券，其实只要软著+科技型中小企业入库登记即可破局...',
    author: 'CodeNomad',
    replies: 42,
    updated_at: '35 分钟前',
  },
  {
    id: 3,
    pinned: null,
    category: '独立出海',
    title: '独立开发者 Stripe 绑定万里汇香港对公户结汇流程避坑指南',
    snippet: '最近很多人遇到银行合规风控抽检要求提供发票与服务履约截图，这里分享一份标准回复模版...',
    author: 'SoloDev_Z',
    replies: 19,
    updated_at: '2 小时前',
  },
  {
    id: 4,
    pinned: null,
    category: 'AI智能体',
    title: '基于 PostgreSQL + pgvector 打造垂直知识库 Agent 的成本优化与延迟实测',
    snippet: '分享我们团队在生产环境将余弦检索延迟从 120ms 降至 18ms 的索引调优实战...',
    author: 'VectorPilot',
    replies: 31,
    updated_at: '3 小时前',
  },
];

const filteredPosts = computed(() => {
  if (selectedCategory.value === '全部风暴区') {
    return samplePosts;
  }
  return samplePosts.filter((p) => p.category === selectedCategory.value);
});

const ragQuery = ref('');
const ragLoading = ref(false);
const ragAnswer = ref('');

function handleRagAsk() {
  if (!ragQuery.value.trim()) return;
  ragLoading.value = true;
  setTimeout(() => {
    ragAnswer.value = `针对“${ragQuery.value}”的问题分析：
1. 建议先确认一人公司法人/经营者主体性质（个体工商户 vs 个人独资 vs 一人有限责任公司）；
2. 财税层面享受季度 30 万元免征额（财税〔2023〕12号延续政策）；
3. 银行开户首选支持小微企业简易开户的商业银行网点，避免一次性高频大额转账触发反洗钱规则。`;
    ragLoading.value = false;
  }, 600);
}

function openPostModal() {
  const token = localStorage.getItem('opchub_session_token');
  if (!token) {
    emit('toast', { title: '需要登录', message: '请先登录创客账号后再在风暴区发帖交流！', type: 'INFO' });
    emit('open-register');
    return;
  }
  emit('toast', { title: '发帖通道', message: '风暴区发帖编辑器已就绪！', type: 'INFO' });
}

function viewPost(post) {
  emit('toast', { title: '查看帖子', message: `正在加载《${post.title}》全文与最新回帖...`, type: 'INFO' });
}
</script>
