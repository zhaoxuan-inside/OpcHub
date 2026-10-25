<template>
  <CreatePageLayout
    title="发起创客头脑风暴"
    back-label="头脑风暴"
    plain-body
    @back="handleBack"
  >
    <template #meta>
      <div class="save-status-pill" :class="{ 'is-saving': isAutoSaving }">
        <span class="status-dot"></span>
        <span class="status-text">{{ saveStatusText }}</span>
      </div>
    </template>

    <template #actions>
      <div class="header-actions-cluster">
        <!-- Templates Dropdown -->
        <div class="templates-menu-wrap">
          <button type="button" class="btn-header-secondary" @click="isTemplateMenuOpen = !isTemplateMenuOpen">
            <OpcIcon name="scroll" :size="14" />
            <span>模板</span>
          </button>

          <div v-if="isTemplateMenuOpen" class="templates-dropdown-panel glass-box" @click.stop>
            <div class="dropdown-header">选择官方高赞实战模板</div>
            <div
              v-for="tpl in FORUM_TEMPLATES"
              :key="tpl.id"
              class="tpl-menu-item"
              @click="applyTemplate(tpl)"
            >
              <div class="tpl-title">{{ tpl.title }}</div>
              <div class="tpl-cat-badge">{{ getCategoryName(tpl.category) }}</div>
            </div>
          </div>
        </div>

        <!-- Discard / Clear (icon-only) -->
        <button type="button" class="btn-header-ghost" title="清空当前内容" @click="handleClearDraft">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>

        <!-- Submit -->
        <button
          type="button"
          class="btn-liquid btn-primary-publish"
          :disabled="!isFormValid || isSubmitting"
          @click="handleSubmit"
        >
          <svg v-if="!isSubmitting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
          <span v-else class="spinner-icon"></span>
          <span>{{ isSubmitting ? '发布中…' : '发布' }}</span>
        </button>
      </div>
    </template>

    <!-- Main Workspace: content-first -->
    <div class="glass-box create-workspace-box">
      <PublishNotice />

      <!-- 1. Title -->
      <input
        v-model="title"
        type="text"
        class="glass-input title-large-input"
        placeholder="一句话清晰描述您的实战主题或核心痛点（如：独立开发者 Stripe 绑定万里汇香港对公户结汇避坑实录）"
        maxlength="100"
      />

      <!-- 2. Compact meta row: section dropdown + tags -->
      <div class="meta-row">
        <select v-model="selectedCategory" class="glass-input glass-select category-select" title="风暴主题分区">
          <option v-for="cat in categoryOptions" :key="cat.code" :value="cat.code">
            {{ cat.label }} · {{ cat.desc }}
          </option>
        </select>

        <div class="tags-interactive-field">
          <span
            v-for="(tag, idx) in tagsList"
            :key="idx"
            class="active-tag-chip"
          >
            <span class="tag-hash">#</span>
            <span class="tag-text">{{ tag }}</span>
            <button type="button" class="tag-del-btn" @click="removeTag(idx)">×</button>
          </span>
          <input
            v-model="tagInputText"
            type="text"
            class="tag-inline-input"
            placeholder="话题标签，回车添加…"
            @keydown.enter.prevent="addTagFromInput"
            @keydown="handleTagInputKeydown"
          />
        </div>
      </div>

      <div v-if="suggestedTags.length" class="quick-tags-cluster">
        <span class="quick-tags-title">灵感标签</span>
        <button
          v-for="suggest in suggestedTags"
          :key="suggest"
          type="button"
          class="btn-suggest-tag"
          :class="{ selected: tagsList.includes(suggest) }"
          @click="toggleSuggestedTag(suggest)"
        >
          + {{ suggest }}
        </button>
      </div>

      <!-- 3. Unified content editor -->
      <RichEditor
        v-model="markdownContent"
        :min-height="440"
        placeholder="在此以富文本或 Markdown 畅快书写您的复盘思考、技术避坑或商业实操……支持标题、列表、代码块、表格与高亮预警盒。"
      />
      <div class="editor-word-count">
        <span>{{ markdownContent.length }} 字</span>
      </div>
    </div>
  </CreatePageLayout>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import PublishNotice from '@/components/PublishNotice.vue';
import CreatePageLayout from '@/components/CreatePageLayout.vue';
import RichEditor from '@/components/editor/RichEditor.vue';
import { stripMarkdown, FORUM_TEMPLATES } from '@/utils/markdown';

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['back', 'success', 'toast']);

// Categories Configuration
const categoryOptions = [
  { code: 'DEV', label: '技术踩坑', desc: '全栈架构 · 数据库选型 · 异步流水线' },
  { code: 'BIZ', label: '独立出海', desc: 'Stripe结汇 · 境外企业 · 单元经济' },
  { code: 'TAX', label: '工商财税', desc: '小规模免税 · 电子税务局 · 年报合规' },
  { code: 'AGENTS', label: 'AI智能体', desc: 'RAG知识库 · 提示词流水线 · 算力优化' },
  { code: 'POLICY', label: '政策申报', desc: '算力补贴 · 科技型中小企业 · 软著申请' },
];

// Suggested Tags
const suggestedTags = [
  'Stripe',
  '独立出海',
  '结汇避坑',
  '一人公司',
  'FastAPI',
  'Vue3',
  'PostgreSQL',
  '算力补贴',
  '电子税务局',
  '小规模免税',
  'AI智能体',
  'pgvector',
];

// State
const selectedCategory = ref('DEV');
const title = ref('');
const markdownContent = ref('');
const tagsList = ref(['独立开发']);
const tagInputText = ref('');
const isSubmitting = ref(false);
const isAutoSaving = ref(false);
const lastSavedTime = ref('');
const isTemplateMenuOpen = ref(false);

// Computed Properties
const authorName = computed(() => {
  return props.userSession?.nickname || props.userSession?.username || '我';
});

const authorId = computed(() => {
  return props.userSession?.uid || props.userSession?.id || props.userSession?.user?.id || props.userSession?.user?.uid || '';
});

const isFormValid = computed(() => {
  return title.value.trim().length >= 4 && markdownContent.value.trim().length >= 10;
});

const currentCategoryName = computed(() => {
  return categoryOptions.find(c => c.code === selectedCategory.value)?.label || '实战风暴';
});

const saveStatusText = computed(() => {
  if (isAutoSaving.value) return '正在暂存...';
  if (lastSavedTime.value) return `草稿已于 ${lastSavedTime.value} 自动暂存`;
  return '实时自动暂存就绪';
});

function getCategoryName(code) {
  return categoryOptions.find(c => c.code === code)?.label || code;
}

// Tags Management
function addTagFromInput() {
  const val = tagInputText.value.trim().replace(/^#/, '');
  if (val && !tagsList.value.includes(val)) {
    tagsList.value.push(val);
  }
  tagInputText.value = '';
  triggerAutoSave();
}

function handleTagInputKeydown(e) {
  if (e.key === ',' || e.key === '，') {
    e.preventDefault();
    addTagFromInput();
  } else if (e.key === 'Backspace' && !tagInputText.value && tagsList.value.length > 0) {
    tagsList.value.pop();
    triggerAutoSave();
  }
}

function removeTag(idx) {
  tagsList.value.splice(idx, 1);
  triggerAutoSave();
}

function toggleSuggestedTag(tag) {
  const idx = tagsList.value.indexOf(tag);
  if (idx > -1) {
    tagsList.value.splice(idx, 1);
  } else {
    tagsList.value.push(tag);
  }
  triggerAutoSave();
}

// Apply Built-in Templates
function applyTemplate(tpl) {
  if (
    markdownContent.value.trim().length > 10 &&
    !confirm('应用新模板将替换当前编辑器内容，是否继续？')
  ) {
    return;
  }

  selectedCategory.value = tpl.category;
  title.value = tpl.title;
  markdownContent.value = tpl.content;
  tagsList.value = [getCategoryName(tpl.category), '实战复盘', '超级个体'];

  isTemplateMenuOpen.value = false;
  triggerAutoSave();

  emit('toast', {
    title: '已载入实战模板',
    message: `成功载入《${tpl.title}》，请根据您的真实情况修改细节！`,
    type: 'SUCCESS',
  });
}

// Local Draft Persistence (localStorage)
const DRAFT_STORAGE_KEY = 'opchub_forum_create_draft';
let autoSaveTimer = null;

// Content edits (rich text or markdown) debounce into the local draft.
watch(markdownContent, () => triggerAutoSave());
watch(title, () => triggerAutoSave());

function triggerAutoSave() {
  clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(() => {
    saveDraftLocal();
  }, 1000);
}

function saveDraftLocal() {
  if (!title.value && !markdownContent.value) return;

  isAutoSaving.value = true;
  const draftData = {
    category: selectedCategory.value,
    title: title.value,
    content: markdownContent.value,
    tags: tagsList.value,
    savedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };

  try {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draftData));
    lastSavedTime.value = draftData.savedAt;
  } catch (e) {
    // ignore
  } finally {
    setTimeout(() => {
      isAutoSaving.value = false;
    }, 400);
  }
}

function handleClearDraft() {
  if (!confirm('确定要清空当前所有内容吗？清空后草稿将被删除。')) return;
  title.value = '';
  markdownContent.value = '';
  tagsList.value = [];
  tagInputText.value = '';
  localStorage.removeItem(DRAFT_STORAGE_KEY);
  lastSavedTime.value = '';

  emit('toast', {
    title: '已清空草稿',
    message: '编辑器已重置为初始状态。',
    type: 'INFO',
  });
}

function restoreDraftIfPresent() {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data.title || data.content) {
      selectedCategory.value = data.category || 'DEV';
      title.value = data.title || '';
      markdownContent.value = data.content || '';
      tagsList.value = Array.isArray(data.tags) ? data.tags : [];
      lastSavedTime.value = data.savedAt || '刚才';

      emit('toast', {
        title: '已自动恢复草稿',
        message: `为您恢复了暂存的《${data.title || '风暴帖'}》草稿。`,
        type: 'INFO',
      });
    }
  } catch (e) {
    // ignore
  }
}

// Back to list
function handleBack() {
  if (
    isFormValid.value &&
    !confirm('正在编辑的内容已自动暂存到草稿箱。确定返回风暴广场吗？')
  ) {
    return;
  }
  emit('back');
}

// Final Submit
async function handleSubmit() {
  if (!isFormValid.value || isSubmitting.value) return;

  isSubmitting.value = true;

  const finalContent = markdownContent.value.trim();
  const finalTitle = title.value.trim();

  const threadPayload = {
    category_code: selectedCategory.value,
    author_id: authorId.value,
    author_name: authorName.value,
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
        message: res.error || '网络异常，请稍后重试',
        type: 'ERROR',
      });
      return;
    }

    const nowIso = new Date().toISOString();
    const newThread = {
      id: res.data?.id || `local-thread-${Date.now()}`,
      category_code: selectedCategory.value,
      category: currentCategoryName.value,
      title: finalTitle,
      snippet: stripMarkdown(finalContent).slice(0, 120) + (finalContent.length > 120 ? '...' : ''),
      content: finalContent,
      author: res.data?.author_name || authorName.value,
      author_id: res.data?.author_id || authorId.value,
      comment_count: res.data?.comment_count ?? 0,
      answer_count: res.data?.answer_count ?? 0,
      upvote_count: res.data?.upvote_count ?? 0,
      downvote_count: res.data?.downvote_count ?? 0,
      user_vote: res.data?.user_vote || null,
      pinned: res.data?.is_pinned ? '置顶' : null,
      created_at: res.data?.created_at || nowIso,
      updated_at: '刚刚',
      tags: [...tagsList.value],
    };

    // Clear local draft on success
    localStorage.removeItem(DRAFT_STORAGE_KEY);

    emit('toast', {
      title: '风暴帖发布成功！',
      message: `您的实战帖《${finalTitle}》已发布至创客社区广场！`,
      type: 'SUCCESS',
    });

    emit('success', newThread);
  } catch (err) {
    console.error('Submit thread error:', err);
    emit('toast', {
      title: '发布失败',
      message: err.message || '网络异常，请稍后重试',
      type: 'ERROR',
    });
  } finally {
    isSubmitting.value = false;
  }
}

// Close template menu on click outside
function handleGlobalClick(e) {
  if (!e.target.closest('.templates-menu-wrap')) {
    isTemplateMenuOpen.value = false;
  }
}

onMounted(() => {
  restoreDraftIfPresent();
  window.addEventListener('click', handleGlobalClick);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', handleGlobalClick);
  clearTimeout(autoSaveTimer);
});
</script>

<style scoped>
/* Right Actions */
.header-actions-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-header-secondary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-header-secondary:hover {
  background: var(--glass-surface-hover);
  border-color: var(--accent);
  color: var(--accent);
}

.btn-header-ghost {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-header-ghost:hover {
  background: var(--status-danger-soft);
  color: var(--status-danger);
}

.btn-primary-publish {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-md);
}

.btn-primary-publish:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  filter: grayscale(0.6);
}

/* Templates Dropdown Menu */
.templates-menu-wrap {
  position: relative;
}

.templates-dropdown-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  padding: 12px;
  z-index: 100;
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow-hover);
  display: flex;
  flex-direction: column;
  gap: 6px;
  animation: fadeIn 0.18s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 6px;
}

.tpl-menu-item {
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  cursor: pointer;
  transition: all 0.2s ease;
}

.tpl-menu-item:hover {
  background: var(--glass-surface-hover);
  border-color: var(--accent);
  transform: translateX(2px);
}

.tpl-title {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 3px;
}

.tpl-cat-badge {
  display: inline-block;
  font-size: 10.5px;
  color: var(--accent);
  font-weight: 500;
}

/* Save Status Pill */
.save-status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--status-success-soft);
  border: 1px solid var(--status-success);
  font-size: 11.5px;
  color: var(--status-success);
  transition: all 0.25s ease;
}

.save-status-pill.is-saving {
  background: rgba(0, 113, 227, 0.08);
  border-color: rgba(0, 113, 227, 0.3);
  color: var(--accent);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}

/* Main Workspace Box */
.create-workspace-box {
  padding: 22px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.title-large-input {
  width: 100%;
  font-size: 16px;
  font-weight: 600;
  padding: 12px 16px;
  border-radius: var(--radius-md);
}

/* Compact meta row: section dropdown + tags */
.meta-row {
  display: flex;
  align-items: stretch;
  gap: 10px;
  flex-wrap: wrap;
}

.category-select {
  flex: 0 0 auto;
  width: 320px;
  max-width: 100%;
  font-size: 13px;
}

.tags-interactive-field {
  flex: 1;
  min-width: 240px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  min-height: 42px;
  box-sizing: border-box;
}

.active-tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background: var(--accent-glass);
  border: 1px solid rgba(0, 113, 227, 0.2);
  color: var(--accent);
  font-size: 12px;
  font-weight: 500;
}

.tag-hash {
  opacity: 0.6;
}

.tag-del-btn {
  background: none;
  border: none;
  color: inherit;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  margin-left: 2px;
}

.tag-inline-input {
  flex: 1;
  min-width: 140px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}

.quick-tags-cluster {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: -4px;
}

.quick-tags-title {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.btn-suggest-tag {
  background: transparent;
  border: 1px dashed var(--glass-border);
  border-radius: var(--radius-full);
  padding: 2px 9px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-suggest-tag:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-glass);
}

.btn-suggest-tag.selected {
  border-style: solid;
  border-color: var(--accent);
  background: var(--accent-glass);
  color: var(--accent);
}

/* Submit spinner */
.spinner-icon {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 720px) {
  .category-select {
    width: 100%;
  }
}
</style>
