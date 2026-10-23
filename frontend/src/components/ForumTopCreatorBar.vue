<template>
  <div
    class="zhihu-top-creator glass-box"
    :class="{ 'is-expanded': isExpanded }"
  >
    <!-- 1. Top Zhihu Action Tabs (发起探讨 / 分享实战 / 避坑微想法) -->
    <div class="creator-tabs-bar">
      <button
        type="button"
        class="creator-tab-btn"
        :class="{ active: activeMode === 'discuss' }"
        @click="handleSelectMode('discuss')"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <span>发起探讨</span>
      </button>

      <button
        type="button"
        class="creator-tab-btn"
        :class="{ active: activeMode === 'experience' }"
        @click="handleSelectMode('experience')"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M12 20h9"></path>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
        </svg>
        <span>分享实战</span>
      </button>

      <button
        type="button"
        class="creator-tab-btn"
        :class="{ active: activeMode === 'quick' }"
        @click="handleSelectMode('quick')"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
        <span>避坑微想法</span>
      </button>

      <div class="tabs-right-shortcut">
        <button
          type="button"
          class="btn-full-editor-link"
          @click="$emit('open-full-editor')"
          title="进入全屏沉浸式双栏排版工作台"
        >
          <span>全屏深度撰写</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
            <polyline points="15 3 21 3 21 9"></polyline>
            <polyline points="9 21 3 21 3 15"></polyline>
            <line x1="21" y1="3" x2="14" y2="10"></line>
            <line x1="3" y1="21" x2="10" y2="14"></line>
          </svg>
        </button>
      </div>
    </div>

    <!-- 2. Collapsed State: Zhihu-style Input Trigger Bar -->
    <div
      v-if="!isExpanded"
      class="creator-input-row"
      @click="expandComposer"
    >
      <div class="creator-avatar" :style="{ background: userAvatarBg }">
        {{ userInitial }}
      </div>

      <div class="creator-mock-input">
        <span class="mock-text">{{ placeholderText }}</span>
      </div>

      <div class="creator-quick-tools" @click.stop>
        <button
          type="button"
          class="btn-quick-tool"
          @click="expandWithTemplate"
          title="快速应用实战模板"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="9" y1="21" x2="9" y2="9"></line>
          </svg>
          <span class="tool-label">模板</span>
        </button>

        <button
          type="button"
          class="btn-quick-publish"
          @click="expandComposer"
        >
          <span>发布</span>
        </button>
      </div>
    </div>

    <!-- 3. Expanded State: In-Place High-Density Micro Composer -->
    <div
      v-else
      class="creator-expanded-panel"
    >
      <!-- 3.1 Category Selector Row -->
      <div class="expanded-category-row">
        <span class="cat-lead-label">领域分类:</span>
        <div class="cat-pills-list">
          <button
            v-for="cat in availableCategories"
            :key="cat.code"
            type="button"
            class="composer-cat-pill"
            :class="{ active: selectedCategoryCode === cat.code }"
            @click="selectedCategoryCode = cat.code"
          >
            <span>{{ cat.name }}</span>
          </button>
        </div>
      </div>

      <!-- 3.2 Title Input -->
      <div class="expanded-title-box">
        <input
          ref="titleInputRef"
          v-model="title"
          type="text"
          class="inline-title-input"
          :placeholder="titlePlaceholder"
          maxlength="100"
        />
        <span v-if="title.length > 70" class="title-counter">{{ title.length }}/100</span>
      </div>

      <!-- 3.3 Formatting Toolbar -->
      <div class="inline-format-bar">
        <div class="format-buttons-group">
          <button type="button" class="btn-fmt" @click="insertFormat('bold')" title="加粗 (Ctrl+B)">
            <strong>B</strong>
          </button>
          <button type="button" class="btn-fmt" @click="insertFormat('code')" title="行内代码或代码块">
            &lt;/&gt;
          </button>
          <button type="button" class="btn-fmt" @click="insertFormat('quote')" title="引用警示框">
            &ldquo;
          </button>
          <button type="button" class="btn-fmt" @click="insertFormat('list')" title="要点列表">
            • 列表
          </button>
          <button type="button" class="btn-fmt" @click="insertFormat('table')" title="核算对照表格">
            田 表格
          </button>

          <span class="fmt-sep">|</span>

          <!-- Templates Menu Dropdown -->
          <div class="templates-menu-anchor">
            <button
              type="button"
              class="btn-fmt-tpl"
              @click.stop="isTemplatesOpen = !isTemplatesOpen"
            >
              <span><OpcIcon name="clipboard" :size="13" /> 套用模板</span>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>

            <div v-if="isTemplatesOpen" class="inline-tpl-dropdown glass-box" @click.stop>
              <div class="tpl-dropdown-title">选择官方实战结构模板</div>
              <div
                v-for="tpl in FORUM_TEMPLATES"
                :key="tpl.id"
                class="inline-tpl-item"
                @click="applyTemplate(tpl)"
              >
                <div class="tpl-item-title">{{ tpl.title }}</div>
                <div class="tpl-item-tag">{{ getCategoryName(tpl.category) }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="format-right-tips">
          <span>支持完整 Markdown 语法</span>
        </div>
      </div>

      <!-- 3.4 Content Textarea -->
      <div class="expanded-textarea-wrap">
        <textarea
          ref="contentAreaRef"
          v-model="content"
          class="inline-content-textarea"
          :placeholder="contentPlaceholder"
          rows="5"
          @keydown="handleTextareaKeydown"
        ></textarea>
      </div>

      <!-- 3.5 Tag & Metric Chips Row -->
      <div class="expanded-tags-row">
        <div class="tags-cluster">
          <span class="tag-lead-hash">#</span>
          <input
            v-model="tagInputText"
            type="text"
            class="tag-input-mini"
            placeholder="添加标签 (回车确定，如: 出海合规, 算力补贴)"
            @keydown.enter.prevent="addTagFromInput"
            @keydown="handleTagKeydown"
          />
          <div class="chips-flex-wrap">
            <span
              v-for="(tag, idx) in tagsList"
              :key="tag"
              class="inline-tag-chip"
            >
              #{{ tag }}
              <span class="tag-remove" @click="removeTag(idx)">×</span>
            </span>
          </div>
        </div>
      </div>

      <!-- 3.6 Bottom Action Toolbar -->
      <div class="expanded-footer-bar">
        <div class="footer-stats">
          <span>{{ content.length }} 字</span>
          <span class="dot-sep">·</span>
          <span>预计阅读 {{ Math.max(1, Math.ceil(content.length / 300)) }} 分钟</span>
        </div>

        <div class="footer-buttons">
          <button
            type="button"
            class="btn-composer-cancel"
            @click="collapseComposer"
          >
            <span>收起</span>
          </button>

          <button
            type="button"
            class="btn-liquid btn-composer-publish"
            :disabled="!canPublish || isPublishing"
            @click="handlePublish"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
            <span>{{ isPublishing ? '发布中...' : '发布新风暴' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import { FORUM_TEMPLATES, stripMarkdown } from '@/utils/markdown';

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
  categories: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits([
  'publish-success',
  'open-full-editor',
  'open-register',
  'toast',
]);

// Modes: 'discuss' (探讨) | 'experience' (实战) | 'quick' (微想法)
const activeMode = ref('discuss');
const isExpanded = ref(false);
const isPublishing = ref(false);
const isTemplatesOpen = ref(false);

// Form Fields
const selectedCategoryCode = ref('TAX');
const title = ref('');
const content = ref('');
const tagsList = ref(['实战经验']);
const tagInputText = ref('');

// Refs
const titleInputRef = ref(null);
const contentAreaRef = ref(null);

// Available Categories (filter out ALL)
const availableCategories = computed(() => {
  if (!props.categories || props.categories.length === 0) {
    return [
      { code: 'TAX', name: '工商财税' },
      { code: 'BIZ', name: '独立出海' },
      { code: 'AGENTS', name: 'AI智能体' },
      { code: 'POLICY', name: '政策申报' },
      { code: 'DEV', name: '技术踩坑' },
    ];
  }
  return props.categories.filter((c) => c.code !== 'ALL');
});

function getCategoryName(code) {
  const found = availableCategories.value.find((c) => c.code === code);
  return found ? found.name : '技术踩坑';
}

// User Metadata
const userInitial = computed(() => {
  const name = props.userSession?.nickname || props.userSession?.username || '创';
  return name[0].toUpperCase();
});

const userAvatarBg = computed(() => {
  return 'linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%)';
});

// Placeholders based on mode
const placeholderText = computed(() => {
  if (activeMode.value === 'discuss') {
    return '有什么实战痛点、政策疑虑或技术选型想和创客们探讨？';
  } else if (activeMode.value === 'experience') {
    return '分享你的一人公司避坑经验、财税心得或架构设计... (支持 Markdown)';
  }
  return '记录今天踩到的一个坑或一条闪现的灵感...';
});

const titlePlaceholder = computed(() => {
  if (activeMode.value === 'discuss') {
    return '输入探讨标题（例：小规模纳税人电子税务局申报遇到系统报错怎么处理？）';
  } else if (activeMode.value === 'experience') {
    return '输入实战经验标题（例：从 0 到 1 拿到长三角智能算力补贴 12 万元的全周期复盘）';
  }
  return '输入微想法标题或核心论点（简明扼要）';
});

const contentPlaceholder = computed(() => {
  return `在此撰写详细内容...
• 背景与业务场景：
• 踩坑与阻断痛点：
• 破局方案与实操步骤：
• 量化指标（金额、耗时、对比数据）：`;
});

const canPublish = computed(() => {
  return title.value.trim().length >= 4 && content.value.trim().length >= 10;
});

// Mode Switching
function handleSelectMode(mode) {
  activeMode.value = mode;
  if (!isExpanded.value) {
    expandComposer();
  }
}

function expandComposer() {
  isExpanded.value = true;
  nextTick(() => {
    if (titleInputRef.value) {
      titleInputRef.value.focus();
    }
  });
}

function expandWithTemplate() {
  expandComposer();
  isTemplatesOpen.value = true;
}

function collapseComposer() {
  if (title.value || content.value) {
    if (!confirm('正在编辑的内容尚未发布，确定收起吗？')) return;
  }
  isExpanded.value = false;
  isTemplatesOpen.value = false;
  title.value = '';
  content.value = '';
}

// Format Actions
function insertFormat(type) {
  const textarea = contentAreaRef.value;
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const original = textarea.value;
  const selected = original.substring(start, end);

  let replacement = '';
  switch (type) {
    case 'bold':
      replacement = `**${selected || '加粗要点'}**`;
      break;
    case 'code':
      replacement = selected ? `\`${selected}\`` : '\n```python\n# 核心实战代码\n```\n';
      break;
    case 'quote':
      replacement = `\n> [!IMPORTANT]\n> ${selected || '关键避坑预警说明'}\n`;
      break;
    case 'list':
      replacement = `\n- ${selected || '实战要点一'}\n- 实战要点二\n`;
      break;
    case 'table':
      replacement = '\n| 项目指标 | 优化前 | 优化后 |\n|---|---|---|\n| 处理耗时 | 3 天 | 15 分钟 |\n| 综合税费 | ¥3,500 | ¥0 (免征) |\n';
      break;
  }

  content.value = original.substring(0, start) + replacement + original.substring(end);
  nextTick(() => {
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = start + replacement.length;
  });
}

// Apply Built-in Templates
function applyTemplate(tpl) {
  title.value = tpl.title;
  content.value = tpl.content;
  selectedCategoryCode.value = tpl.category || 'DEV';
  tagsList.value = [getCategoryName(tpl.category), '实战复盘', '避坑指南'];
  isTemplatesOpen.value = false;

  emit('toast', {
    title: '已套用官方模板',
    message: `已载入《${tpl.title}》结构框架，可根据您的真实情况修改数据！`,
    type: 'SUCCESS',
  });
}

// Tag Management
function addTagFromInput() {
  const val = tagInputText.value.trim().replace(/^#/, '');
  if (val && !tagsList.value.includes(val)) {
    tagsList.value.push(val);
  }
  tagInputText.value = '';
}

function handleTagKeydown(e) {
  if (e.key === ',' || e.key === '，') {
    e.preventDefault();
    addTagFromInput();
  }
}

function removeTag(idx) {
  tagsList.value.splice(idx, 1);
}

function handleTextareaKeydown(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    const textarea = e.target;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    content.value = textarea.value.substring(0, start) + '  ' + textarea.value.substring(end);
    nextTick(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 2;
    });
  }
}

// Close templates menu on document click
function handleDocClick() {
  isTemplatesOpen.value = false;
}

onMounted(() => {
  document.addEventListener('click', handleDocClick);
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocClick);
});

// Final Publish
async function handlePublish() {
  if (!canPublish.value || isPublishing.value) return;

  const sessionToken = localStorage.getItem('opchub_session_token');
  if (!sessionToken && !props.userSession) {
    emit('toast', {
      title: '需要登录',
      message: '请登录创客账号后再在风暴区发布探讨经验！',
      type: 'INFO',
    });
    emit('open-register');
    return;
  }

  isPublishing.value = true;
  const finalTitle = title.value.trim();
  const finalContent = content.value.trim();
  const authorName = props.userSession?.nickname || props.userSession?.username || '实战创客';
  const authorId = props.userSession?.uid || props.userSession?.id || props.userSession?.user?.id || props.userSession?.user?.uid || '';

  const threadPayload = {
    category_code: selectedCategoryCode.value,
    author_id: authorId,
    author_name: authorName,
    title: finalTitle,
    content: finalContent,
  };

  try {
    const res = await dispatchGateway('forum.threads.publish', {
      thread_payload: threadPayload,
    }, { silent: true });

    if (!res.ok) {
      emit('toast', {
        title: '发布未成功',
        message: res.error || '发布讨论帖未成功，请检查内容或稍后重试',
        type: 'ERROR',
      });
      return;
    }

    const nowIso = new Date().toISOString();
    const newThread = {
      id: res.data?.id || `local-thread-${Date.now()}`,
      category_code: selectedCategoryCode.value,
      category: getCategoryName(selectedCategoryCode.value),
      title: finalTitle,
      snippet: stripMarkdown(finalContent).slice(0, 140) + (finalContent.length > 140 ? '...' : ''),
      content: finalContent,
      author: res.data?.author_name || authorName,
      author_id: res.data?.author_id || authorId,
      ip_location: '来自 浙江',
      replies: 0,
      comment_count: 0,
      upvotes: 1,
      upvote_count: 1,
      is_upvoted: true,
      pinned: null,
      is_new: true,
      created_at: res.data?.created_at || nowIso,
      updated_at: '刚刚',
      tags: [...tagsList.value],
    };

    emit('toast', {
      title: '风暴帖发布成功！',
      message: `实战帖《${finalTitle}》已发布至广场文章流顶部！`,
      type: 'SUCCESS',
    });

    emit('publish-success', newThread);

    // Reset state
    title.value = '';
    content.value = '';
    isExpanded.value = false;
  } catch (err) {
    console.error('Publish error:', err);
    emit('toast', {
      title: '发布失败',
      message: err.message || '网络或网关响应异常，请稍后重试',
      type: 'ERROR',
    });
  } finally {
    isPublishing.value = false;
  }
}
</script>

<style scoped>
/* ========================================================
   Zhihu-Style Top Creator Bar Container
   ======================================================== */
.zhihu-top-creator {
  display: flex;
  flex-direction: column;
  padding: 12px 18px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface, rgba(255, 255, 255, 0.76));
  backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.88));
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  margin-bottom: 0;
  box-sizing: border-box;
  width: 100%;
}

.zhihu-top-creator:hover {
  border-color: rgba(0, 113, 227, 0.25);
  box-shadow: 0 6px 20px rgba(0, 113, 227, 0.06);
}

.zhihu-top-creator.is-expanded {
  padding: 16px 20px;
  border-color: rgba(0, 113, 227, 0.35);
  box-shadow: 0 8px 28px rgba(0, 113, 227, 0.1);
}

/* 1. Creator Tabs Bar */
.creator-tabs-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.05));
  margin-bottom: 10px;
}

.creator-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: none;
  padding: 6px 12px;
  border-radius: var(--radius-sm, 6px);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary, #4B4E56);
  cursor: pointer;
  transition: all 0.16s ease;
}

.creator-tab-btn:hover {
  color: var(--accent, #0071E3);
  background: rgba(0, 113, 227, 0.06);
}

.creator-tab-btn.active {
  color: var(--accent, #0071E3);
  background: rgba(0, 113, 227, 0.1);
  font-weight: 700;
}

.tabs-right-shortcut {
  display: flex;
  align-items: center;
}

.btn-full-editor-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent, #0071E3);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.16s ease;
}

.btn-full-editor-link:hover {
  background: rgba(0, 113, 227, 0.08);
  text-decoration: underline;
}

/* 2. Collapsed Input Row */
.creator-input-row {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.creator-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.creator-mock-input {
  flex: 1;
  background: var(--glass-surface-subtle, rgba(245, 247, 252, 0.7));
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.08));
  border-radius: 20px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  transition: all 0.18s ease;
}

.creator-input-row:hover .creator-mock-input {
  background: var(--glass-surface-hover);
  border-color: var(--accent, #0071E3);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.08);
}

.mock-text {
  font-size: 13px;
  color: var(--text-tertiary, #7D828D);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.creator-quick-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-quick-tool {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.08));
  color: var(--text-secondary, #4B4E56);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-quick-tool:hover {
  color: var(--accent, #0071E3);
  border-color: var(--accent, #0071E3);
  background: rgba(0, 113, 227, 0.05);
}

.btn-quick-publish {
  padding: 6px 16px;
  border-radius: 18px;
  background: var(--accent, #0071E3);
  color: #fff;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  box-shadow: 0 2px 8px rgba(0, 113, 227, 0.25);
}

.btn-quick-publish:hover {
  background: var(--accent, #0071E3);
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.35);
  transform: translateY(-1px);
}

/* 3. Expanded Panel */
.creator-expanded-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: expandFade 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes expandFade {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 3.1 Category Row */
.expanded-category-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cat-lead-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #4B4E56);
}

.cat-pills-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.composer-cat-pill {
  font-size: 11.5px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 6px;
  background: var(--glass-surface-subtle, rgba(0, 0, 0, 0.03));
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.08));
  color: var(--text-secondary, #4B4E56);
  cursor: pointer;
  transition: all 0.16s ease;
}

.composer-cat-pill:hover {
  border-color: var(--accent, #0071E3);
  color: var(--accent, #0071E3);
}

.composer-cat-pill.active {
  background: var(--accent, #0071E3);
  color: #fff;
  border-color: var(--accent, #0071E3);
  font-weight: 600;
}

/* 3.2 Title Input */
.expanded-title-box {
  position: relative;
  display: flex;
  align-items: center;
}

.inline-title-input {
  width: 100%;
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary, #121316);
  background: var(--glass-surface-solid, #ffffff);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.1));
  border-radius: var(--radius-sm, 8px);
  padding: 9px 65px 9px 12px;
  outline: none;
  transition: all 0.18s ease;
  box-sizing: border-box;
}

.inline-title-input:focus {
  border-color: var(--accent, #0071E3);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.1);
}

.title-counter {
  position: absolute;
  right: 12px;
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
}

/* 3.3 Formatting Toolbar */
.inline-format-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.05));
  border-radius: 6px;
  padding: 4px 8px;
}

.format-buttons-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-fmt {
  background: transparent;
  border: none;
  padding: 3px 7px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary, #4B4E56);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-fmt:hover {
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent, #0071E3);
}

.fmt-sep {
  opacity: 0.3;
  margin: 0 2px;
}

.templates-menu-anchor {
  position: relative;
}

.btn-fmt-tpl {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--accent, #0071E3);
  background: rgba(0, 113, 227, 0.08);
  border: 1px solid rgba(0, 113, 227, 0.16);
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-fmt-tpl:hover {
  background: rgba(0, 113, 227, 0.15);
}

.inline-tpl-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  width: 280px;
  background: var(--glass-surface-solid, #ffffff);
  border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.1));
  border-radius: var(--radius-sm, 8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 6px;
  z-index: 100;
}

.tpl-dropdown-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-tertiary, #7D828D);
  padding: 4px 8px 6px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  margin-bottom: 4px;
}

.inline-tpl-item {
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background 0.15s ease;
}

.inline-tpl-item:hover {
  background: rgba(0, 113, 227, 0.08);
}

.tpl-item-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #121316);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 190px;
}

.tpl-item-tag {
  font-size: 10px;
  color: var(--accent, #0071E3);
  background: rgba(0, 113, 227, 0.08);
  padding: 1px 4px;
  border-radius: 3px;
}

.format-right-tips {
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
}

/* 3.4 Textarea */
.expanded-textarea-wrap {
  width: 100%;
}

.inline-content-textarea {
  width: 100%;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text-primary, #121316);
  background: var(--glass-surface-solid, #ffffff);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.1));
  border-radius: var(--radius-sm, 8px);
  padding: 10px 12px;
  outline: none;
  resize: vertical;
  min-height: 100px;
  box-sizing: border-box;
  font-family: inherit;
  transition: all 0.18s ease;
}

.inline-content-textarea:focus {
  border-color: var(--accent, #0071E3);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.1);
}

/* 3.5 Tags Row */
.expanded-tags-row {
  display: flex;
  align-items: center;
}

.tags-cluster {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  width: 100%;
}

.tag-lead-hash {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent, #0071E3);
}

.tag-input-mini {
  font-size: 12px;
  border: 1px dashed var(--glass-border-subtle, rgba(0, 0, 0, 0.12));
  border-radius: 4px;
  padding: 4px 8px;
  background: transparent;
  outline: none;
  min-width: 220px;
  color: var(--text-primary, #121316);
}

.tag-input-mini:focus {
  border-color: var(--accent, #0071E3);
  border-style: solid;
}

.chips-flex-wrap {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.inline-tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent, #0071E3);
}

.tag-remove {
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  opacity: 0.7;
}

.tag-remove:hover {
  opacity: 1;
}

/* 3.6 Footer Bar */
.expanded-footer-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.05));
}

.footer-stats {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--text-tertiary, #7D828D);
}

.dot-sep {
  opacity: 0.5;
}

.footer-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-composer-cancel {
  padding: 6px 14px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.1));
  color: var(--text-secondary, #4B4E56);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-composer-cancel:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-primary, #121316);
}

.btn-composer-publish {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 18px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
}

/* Dark Mode Adjustments */
[data-theme="dark"] .zhihu-top-creator {
  background: rgba(26, 29, 36, 0.78);
  border-color: rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .creator-mock-input {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

[data-theme="dark"] .inline-title-input,
[data-theme="dark"] .inline-content-textarea {
  background: rgba(18, 20, 26, 0.8);
  border-color: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

[data-theme="dark"] .inline-tpl-dropdown {
  background: var(--glass-surface-solid);
  border-color: rgba(255, 255, 255, 0.12);
}
</style>
