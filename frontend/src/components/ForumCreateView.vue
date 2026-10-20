<template>
  <div class="forum-create-page-wrapper">
    <!-- Top Fluid Navigation & Actions Header -->
    <div class="glass-box create-page-header">
      <div class="header-left-cluster">
        <button class="btn-back-square" @click="handleBack" title="返回风暴广场 (不保存可放弃)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
        </button>

        <div class="page-title-cluster">
          <div class="breadcrumb-row">
            <span class="crumb-link" @click="handleBack">头脑风暴广场</span>
            <span class="crumb-separator">/</span>
            <span class="crumb-current">发起新风暴</span>
          </div>
          <h1 class="page-main-title">发起创客头脑风暴</h1>
        </div>
      </div>

      <!-- Center Auto-save Status & Stats -->
      <div class="header-center-info">
        <div class="save-status-pill" :class="{ 'is-saving': isAutoSaving }">
          <span class="status-dot"></span>
          <span class="status-text">{{ saveStatusText }}</span>
        </div>
        <div class="meta-stats-text">
          <span>{{ wordCount }} 字</span>
          <span class="stat-divider">·</span>
          <span>约需阅读 {{ estimatedReadTime }} 分钟</span>
        </div>
      </div>

      <!-- Right Action Controls -->
      <div class="header-actions-cluster">
        <!-- Templates Dropdown -->
        <div class="templates-menu-wrap">
          <button
            type="button"
            class="btn-header-secondary"
            @click="isTemplateMenuOpen = !isTemplateMenuOpen"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="3" y1="9" x2="21" y2="9"></line>
              <line x1="9" y1="21" x2="9" y2="9"></line>
            </svg>
            <span>实战模板</span>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          <!-- Template Popup Menu -->
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

        <!-- Discard / Clear Button -->
        <button
          type="button"
          class="btn-header-ghost"
          @click="handleClearDraft"
          title="清空当前内容"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          <span>清空</span>
        </button>

        <!-- Save Draft Button -->
        <button
          type="button"
          class="btn-header-secondary"
          @click="handleSaveDraftManual"
        >
          <span>暂存草稿</span>
        </button>

        <!-- Submit Button -->
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
          <span>{{ isSubmitting ? '正在发布...' : '立即发布风暴帖' }}</span>
        </button>
      </div>
    </div>

    <!-- Main Workspace Container -->
    <div class="glass-box create-workspace-box">
      <!-- 1. Category Selection Row -->
      <div class="form-row category-selector-row">
        <label class="section-label">
          <span>风暴主题分区</span>
          <span class="required-star">*</span>
        </label>
        <div class="categories-pill-row">
          <button
            v-for="cat in categoryOptions"
            :key="cat.code"
            type="button"
            class="cat-select-btn"
            :class="{ active: selectedCategory === cat.code }"
            @click="selectedCategory = cat.code"
          >
            <span class="cat-dot" :style="{ background: cat.color }"></span>
            <span class="cat-name">{{ cat.label }}</span>
            <span class="cat-desc">{{ cat.desc }}</span>
          </button>
        </div>
      </div>

      <!-- 2. Post Title Input -->
      <div class="form-row title-input-row">
        <div class="title-label-row">
          <label class="section-label">
            <span>风暴帖标题</span>
            <span class="required-star">*</span>
          </label>
          <span class="char-counter" :class="{ 'is-limit': title.length > 90 }">
            {{ title.length }} / 100
          </span>
        </div>
        <div class="title-input-wrapper">
          <input
            v-model="title"
            type="text"
            class="glass-input title-large-input"
            placeholder="一句话清晰描述您的实战主题或核心痛点（如：独立开发者 Stripe 绑定万里汇香港对公户结汇避坑实录）"
            maxlength="100"
          />
          <button
            v-if="title"
            type="button"
            class="btn-clear-input"
            @click="title = ''"
          >
            ×
          </button>
        </div>
      </div>

      <!-- 3. Tags Input & Recommendations -->
      <div class="form-row tags-input-row">
        <div class="tags-label-row">
          <label class="section-label">
            <span>话题标签 (回车或逗号分隔)</span>
          </label>
          <span class="tags-hint">已添加 {{ tagsList.length }} 个标签</span>
        </div>

        <div class="tags-interactive-field">
          <!-- Active Tags Badges -->
          <span
            v-for="(tag, idx) in tagsList"
            :key="idx"
            class="active-tag-chip"
          >
            <span class="tag-hash">#</span>
            <span class="tag-text">{{ tag }}</span>
            <button type="button" class="tag-del-btn" @click="removeTag(idx)">×</button>
          </span>

          <!-- Tag Input -->
          <input
            v-model="tagInputText"
            type="text"
            class="tag-inline-input"
            placeholder="输入标签并按回车..."
            @keydown.enter.prevent="addTagFromInput"
            @keydown="handleTagInputKeydown"
          />
        </div>

        <!-- Quick Tag Suggestions -->
        <div class="quick-tags-cluster">
          <span class="quick-tags-title">推荐灵感标签：</span>
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
      </div>

      <!-- 4. Universal Toolbar: Mode Switcher & Syntax Buttons -->
      <div class="editor-universal-toolbar">
        <!-- Left: Formatting & Syntax Buttons -->
        <div class="toolbar-buttons-cluster">
          <!-- Undo / Redo -->
          <div class="btn-group">
            <button
              type="button"
              class="tool-btn"
              title="撤销 (Ctrl+Z)"
              @click="handleUndo"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 7v6h6"></path>
                <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="重做 (Ctrl+Y)"
              @click="handleRedo"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 7v6h-6"></path>
                <path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3L21 13"></path>
              </svg>
            </button>
          </div>

          <div class="tool-divider"></div>

          <!-- Headings -->
          <div class="btn-group">
            <button
              type="button"
              class="tool-btn"
              title="一级标题 (# 标题)"
              @click="applyFormat('h1')"
            >
              <b>H1</b>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="二级标题 (## 标题)"
              @click="applyFormat('h2')"
            >
              <b>H2</b>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="三级标题 (### 标题)"
              @click="applyFormat('h3')"
            >
              <b>H3</b>
            </button>
          </div>

          <div class="tool-divider"></div>

          <!-- Text Styles -->
          <div class="btn-group">
            <button
              type="button"
              class="tool-btn"
              title="加粗 (**粗体** / Ctrl+B)"
              @click="applyFormat('bold')"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"></path>
                <path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="斜体 (*斜体* / Ctrl+I)"
              @click="applyFormat('italic')"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="19" y1="4" x2="10" y2="4"></line>
                <line x1="14" y1="20" x2="5" y2="20"></line>
                <line x1="15" y1="4" x2="9" y2="20"></line>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="下划线 (<u>文本</u> / Ctrl+U)"
              @click="applyFormat('underline')"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3"></path>
                <line x1="4" y1="21" x2="20" y2="21"></line>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="删除线 (~~文本~~)"
              @click="applyFormat('strikethrough')"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <path d="M16 6C16 4 14 3 12 3C9 3 8 5 8 7C8 13 16 11 16 17C16 19 14 21 12 21C9 21 8 20 8 18"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="行内代码 (`code`)"
              @click="applyFormat('inlineCode')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <polyline points="16 18 22 12 16 6"></polyline>
                <polyline points="8 6 2 12 8 18"></polyline>
              </svg>
            </button>
          </div>

          <div class="tool-divider"></div>

          <!-- Lists & Blocks -->
          <div class="btn-group">
            <button
              type="button"
              class="tool-btn"
              title="无序列表 (- 列表项)"
              @click="applyFormat('ul')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="有序列表 (1. 列表项)"
              @click="applyFormat('ol')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="10" y1="6" x2="21" y2="6"></line>
                <line x1="10" y1="12" x2="21" y2="12"></line>
                <line x1="10" y1="18" x2="21" y2="18"></line>
                <path d="M4 6h1v4"></path>
                <path d="M4 10h2"></path>
                <path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="待办任务清单 (- [ ] 待办项)"
              @click="applyFormat('tasklist')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 11 12 14 22 4"></polyline>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="引用块 (> 引用文本)"
              @click="applyFormat('quote')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"></path>
                <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="分割线 (---)"
              @click="applyFormat('hr')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="12" x2="21" y2="12"></line>
              </svg>
            </button>
          </div>

          <div class="tool-divider"></div>

          <!-- Advanced Inserts -->
          <div class="btn-group">
            <button
              type="button"
              class="tool-btn"
              title="插入多行代码块 (```代码```)"
              @click="applyFormat('codeblock')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="4" width="20" height="16" rx="2"></rect>
                <path d="m10 10-2 2 2 2"></path>
                <path d="m14 14 2-2-2-2"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="插入超链接 ([文字](URL))"
              @click="insertLinkPrompt"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="插入图片链接 (![描述](URL))"
              @click="insertImagePrompt"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn"
              title="插入表格 (| 标题1 | 标题2 |)"
              @click="insertTable"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"></rect>
                <path d="M3 9h18"></path>
                <path d="M3 15h18"></path>
                <path d="M9 3v18"></path>
                <path d="M15 3v18"></path>
              </svg>
            </button>
            <button
              type="button"
              class="tool-btn tool-btn-highlight"
              title="插入避坑预警 / 关键提示框 (> [!WARNING] 或 > [!TIP])"
              @click="insertCalloutPrompt"
            >
              <span class="callout-icon-mini">💡</span>
              <span class="btn-txt-mini">提示框</span>
            </button>
          </div>
        </div>

        <!-- Right: View Modes Switcher -->
        <div class="view-modes-segmented-control">
          <button
            type="button"
            class="mode-btn"
            :class="{ active: editorMode === 'markdown' }"
            @click="switchEditorMode('markdown')"
          >
            <span>Markdown 模式</span>
          </button>
          <button
            type="button"
            class="mode-btn"
            :class="{ active: editorMode === 'wysiwyg' }"
            @click="switchEditorMode('wysiwyg')"
          >
            <span>富文本模式</span>
          </button>
          <button
            type="button"
            class="mode-btn"
            :class="{ active: editorMode === 'split' }"
            @click="switchEditorMode('split')"
          >
            <span>双栏分屏</span>
          </button>
          <button
            type="button"
            class="mode-btn"
            :class="{ active: editorMode === 'preview' }"
            @click="switchEditorMode('preview')"
          >
            <span>全页效果预览</span>
          </button>
        </div>
      </div>

      <!-- 5. Active Editor Canvas -->
      <div class="editor-canvas-container" :class="`mode-${editorMode}`">
        <!-- A. Pure Markdown Mode -->
        <div v-show="editorMode === 'markdown'" class="pane-markdown-canvas">
          <textarea
            ref="markdownTextareaRef"
            v-model="markdownContent"
            class="code-textarea markdown-raw-editor"
            placeholder="在此以 Markdown 语法畅快书写您的复盘思考、技术避坑或商业实操... 支持标题、加粗、代码块、数学逻辑、表格与高亮预警盒！"
            @keydown="handleTextareaKeydown"
            @input="handleContentInput"
          ></textarea>
        </div>

        <!-- B. WYSIWYG Rich Text Mode -->
        <div v-show="editorMode === 'wysiwyg'" class="pane-wysiwyg-canvas">
          <div
            ref="wysiwygEditorRef"
            class="wysiwyg-editable-surface"
            contenteditable="true"
            placeholder="在此直接输入或粘贴富文本内容，支持使用上方工具栏按钮进行可视化排版..."
            @input="handleWysiwygInput"
            @blur="syncWysiwygToMarkdown"
          ></div>
        </div>

        <!-- C. Split Screen Mode (Side by Side) -->
        <div v-show="editorMode === 'split'" class="pane-split-container">
          <div class="split-col split-left">
            <div class="split-header">
              <span class="split-title">Markdown 源码编辑</span>
              <span class="split-badge">实时双向同步</span>
            </div>
            <textarea
              ref="splitTextareaRef"
              v-model="markdownContent"
              class="code-textarea split-textarea"
              placeholder="在此输入 Markdown 源码，右侧将实时渲染排版..."
              @keydown="handleTextareaKeydown"
              @input="handleContentInput"
            ></textarea>
          </div>

          <div class="split-divider-line"></div>

          <div class="split-col split-right">
            <div class="split-header">
              <span class="split-title">富文本实时渲染预览</span>
              <span class="split-badge highlight">所见即所得</span>
            </div>
            <div
              class="split-preview-surface markdown-rendered-content"
              v-html="renderedHtml"
            ></div>
          </div>
        </div>

        <!-- D. Full Preview Mode (Simulated Forum Reading View) -->
        <div v-show="editorMode === 'preview'" class="pane-full-preview">
          <div class="preview-card-wrap">
            <div class="preview-header-meta">
              <span class="category-pill-preview" :style="{ background: currentCategoryColor }">
                {{ currentCategoryName }}
              </span>
              <span class="preview-ip">来自 浙江</span>
              <span class="preview-time">刚刚</span>
            </div>

            <h1 class="preview-post-title">{{ title || '（尚未输入标题）' }}</h1>

            <div class="preview-author-bar">
              <div class="author-circle">{{ authorName[0]?.toUpperCase() || '创' }}</div>
              <div>
                <div class="author-name-text">{{ authorName }} <span class="badge-maker">认证超级个体</span></div>
                <div class="author-sub-desc">头脑风暴区实战贴</div>
              </div>
            </div>

            <!-- Tags in preview -->
            <div v-if="tagsList.length > 0" class="preview-tags-row">
              <span v-for="tag in tagsList" :key="tag" class="preview-tag-pill">#{{ tag }}</span>
            </div>

            <div class="preview-divider"></div>

            <div
              class="preview-article-body markdown-rendered-content"
              v-html="renderedHtml || '<p style=\'color: var(--text-tertiary); font-style: italic;\'>正文内容为空...</p>'"
            ></div>
          </div>
        </div>
      </div>

      <!-- 6. Bottom Status & Compliance Bar -->
      <div class="create-page-footer">
        <div class="footer-left-notes">
          <div class="compliance-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
            <span>创客社区合规守护：发帖遵循《平台自律倡议》，系统自动经过敏感词审查并加注创客实名防线</span>
          </div>
        </div>

        <div class="footer-actions-cluster">
          <button type="button" class="btn-footer-cancel" @click="handleBack">
            返回广场
          </button>
          <button
            type="button"
            class="btn-liquid btn-footer-publish"
            :disabled="!isFormValid || isSubmitting"
            @click="handleSubmit"
          >
            <svg v-if="!isSubmitting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
            <span v-else class="spinner-icon"></span>
            <span>{{ isSubmitting ? '正在发布...' : '立即发布风暴帖' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import {
  renderMarkdown,
  htmlToMarkdown,
  stripMarkdown,
  FORUM_TEMPLATES,
} from '@/utils/markdown';

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['back', 'success', 'toast']);

// Categories Configuration
const categoryOptions = [
  { code: 'DEV', label: '技术踩坑', color: '#0071E3', desc: '全栈架构 · 数据库选型 · 异步流水线' },
  { code: 'BIZ', label: '独立出海', color: '#00c6ff', desc: 'Stripe结汇 · 境外企业 · 单元经济' },
  { code: 'TAX', label: '工商财税', color: '#e67e22', desc: '小规模免税 · 电子税务局 · 年报合规' },
  { code: 'AGENTS', label: 'AI智能体', color: '#a855f7', desc: 'RAG知识库 · 提示词流水线 · 算力优化' },
  { code: 'POLICY', label: '政策申报', color: '#10b981', desc: '算力补贴 · 科技型中小企业 · 软著申请' },
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
const editorMode = ref('split'); // 'markdown' | 'wysiwyg' | 'split' | 'preview'
const isSubmitting = ref(false);
const isAutoSaving = ref(false);
const lastSavedTime = ref('');
const isTemplateMenuOpen = ref(false);

// Refs for DOM Elements
const markdownTextareaRef = ref(null);
const splitTextareaRef = ref(null);
const wysiwygEditorRef = ref(null);

// History stack for Undo / Redo in Markdown mode
const historyStack = ref([]);
const historyIndex = ref(-1);

// Computed Properties
const authorName = computed(() => {
  return props.userSession?.nickname || props.userSession?.username || '认证创客';
});

const authorId = computed(() => {
  return props.userSession?.uid || props.userSession?.id || props.userSession?.user?.id || props.userSession?.user?.uid || '';
});

const wordCount = computed(() => {
  const clean = stripMarkdown(markdownContent.value);
  return clean.replace(/\s+/g, '').length;
});

const estimatedReadTime = computed(() => {
  const mins = Math.ceil(wordCount.value / 300);
  return mins < 1 ? 1 : mins;
});

const isFormValid = computed(() => {
  return title.value.trim().length >= 4 && markdownContent.value.trim().length >= 10;
});

const renderedHtml = computed(() => {
  return renderMarkdown(markdownContent.value);
});

const currentCategoryName = computed(() => {
  return categoryOptions.find(c => c.code === selectedCategory.value)?.label || '实战风暴';
});

const currentCategoryColor = computed(() => {
  return categoryOptions.find(c => c.code === selectedCategory.value)?.color || '#0071E3';
});

const saveStatusText = computed(() => {
  if (isAutoSaving.value) return '正在暂存...';
  if (lastSavedTime.value) return `草稿已于 ${lastSavedTime.value} 自动暂存`;
  return '实时自动暂存就绪';
});

function getCategoryName(code) {
  return categoryOptions.find(c => c.code === code)?.label || code;
}

// History stack management
function recordHistory() {
  if (historyStack.value[historyIndex.value] === markdownContent.value) return;
  // Truncate redo tree if we made changes in the past
  historyStack.value = historyStack.value.slice(0, historyIndex.value + 1);
  historyStack.value.push(markdownContent.value);
  historyIndex.value = historyStack.value.length - 1;
}

function handleUndo() {
  if (editorMode.value === 'wysiwyg') {
    document.execCommand('undo', false, null);
    syncWysiwygToMarkdown();
    return;
  }
  if (historyIndex.value > 0) {
    historyIndex.value--;
    markdownContent.value = historyStack.value[historyIndex.value];
    nextTick(() => syncMarkdownToWysiwyg());
  }
}

function handleRedo() {
  if (editorMode.value === 'wysiwyg') {
    document.execCommand('redo', false, null);
    syncWysiwygToMarkdown();
    return;
  }
  if (historyIndex.value < historyStack.value.length - 1) {
    historyIndex.value++;
    markdownContent.value = historyStack.value[historyIndex.value];
    nextTick(() => syncMarkdownToWysiwyg());
  }
}

// Mode Switching & Synchronization
function switchEditorMode(newMode) {
  if (editorMode.value === newMode) return;

  if (editorMode.value === 'wysiwyg') {
    syncWysiwygToMarkdown();
  }

  editorMode.value = newMode;

  nextTick(() => {
    if (newMode === 'wysiwyg') {
      syncMarkdownToWysiwyg();
    }
  });
}

function syncMarkdownToWysiwyg() {
  if (wysiwygEditorRef.value) {
    wysiwygEditorRef.value.innerHTML = renderMarkdown(markdownContent.value);
  }
}

function syncWysiwygToMarkdown() {
  if (wysiwygEditorRef.value) {
    const md = htmlToMarkdown(wysiwygEditorRef.value.innerHTML);
    if (md !== markdownContent.value) {
      markdownContent.value = md;
      recordHistory();
    }
  }
}

function handleWysiwygInput() {
  syncWysiwygToMarkdown();
  triggerAutoSave();
}

function handleContentInput() {
  recordHistory();
  triggerAutoSave();
}

// Active Textarea Reference
function getActiveTextarea() {
  if (editorMode.value === 'split') {
    return splitTextareaRef.value;
  }
  return markdownTextareaRef.value;
}

// Toolbar Formatting Engine
function applyFormat(type) {
  if (editorMode.value === 'wysiwyg') {
    applyWysiwygCommand(type);
    return;
  }

  const textarea = getActiveTextarea();
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const originalText = textarea.value;
  const selectedText = originalText.substring(start, end);

  let replacement = '';
  let cursorOffset = 0;

  switch (type) {
    case 'bold':
      replacement = `**${selectedText || '粗体文本'}**`;
      cursorOffset = selectedText ? replacement.length : 2;
      break;
    case 'italic':
      replacement = `*${selectedText || '斜体文本'}*`;
      cursorOffset = selectedText ? replacement.length : 1;
      break;
    case 'underline':
      replacement = `<u>${selectedText || '下划线文本'}</u>`;
      cursorOffset = selectedText ? replacement.length : 3;
      break;
    case 'strikethrough':
      replacement = `~~${selectedText || '删除线文本'}~~`;
      cursorOffset = selectedText ? replacement.length : 2;
      break;
    case 'inlineCode':
      replacement = `\`${selectedText || 'code'}\``;
      cursorOffset = selectedText ? replacement.length : 1;
      break;
    case 'h1':
      replacement = `\n# ${selectedText || '一级标题'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'h2':
      replacement = `\n## ${selectedText || '二级标题'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'h3':
      replacement = `\n### ${selectedText || '三级标题'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'ul':
      replacement = `\n- ${selectedText || '列表项'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'ol':
      replacement = `\n1. ${selectedText || '有序列表项'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'tasklist':
      replacement = `\n- [ ] ${selectedText || '待办任务事项'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'quote':
      replacement = `\n> ${selectedText || '引用内容'}\n`;
      cursorOffset = replacement.length;
      break;
    case 'hr':
      replacement = `\n\n---\n\n`;
      cursorOffset = replacement.length;
      break;
    case 'codeblock':
      replacement = `\n\`\`\`typescript\n${selectedText || '// 在此编写代码或实操配置'}\n\`\`\`\n`;
      cursorOffset = replacement.length;
      break;
    default:
      return;
  }

  markdownContent.value =
    originalText.substring(0, start) + replacement + originalText.substring(end);

  recordHistory();
  triggerAutoSave();

  nextTick(() => {
    textarea.focus();
    textarea.setSelectionRange(start + cursorOffset, start + cursorOffset);
    if (wysiwygEditorRef.value) {
      syncMarkdownToWysiwyg();
    }
  });
}

function applyWysiwygCommand(type) {
  const commands = {
    bold: 'bold',
    italic: 'italic',
    underline: 'underline',
    strikethrough: 'strikeThrough',
    ul: 'insertUnorderedList',
    ol: 'insertOrderedList',
  };

  if (commands[type]) {
    document.execCommand(commands[type], false, null);
  } else if (type === 'h1' || type === 'h2' || type === 'h3') {
    document.execCommand('formatBlock', false, `<${type}>`);
  } else if (type === 'quote') {
    document.execCommand('formatBlock', false, '<blockquote>');
  } else if (type === 'hr') {
    document.execCommand('insertHorizontalRule', false, null);
  } else if (type === 'inlineCode') {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    const range = selection.getRangeAt(0);
    const codeElem = document.createElement('code');
    codeElem.innerText = selection.toString() || 'code';
    range.deleteContents();
    range.insertNode(codeElem);
  } else if (type === 'codeblock') {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    const range = selection.getRangeAt(0);
    const preElem = document.createElement('pre');
    const codeElem = document.createElement('code');
    codeElem.innerText = selection.toString() || '// 代码块';
    preElem.appendChild(codeElem);
    range.deleteContents();
    range.insertNode(preElem);
  }

  syncWysiwygToMarkdown();
  triggerAutoSave();
}

// Special Inserts: Link, Image, Table, Callout
function insertLinkPrompt() {
  const url = prompt('请输入链接目标地址 (URL):', 'https://');
  if (!url) return;
  const text = prompt('请输入链接显示的文本 (可选):', '参考链接') || url;

  if (editorMode.value === 'wysiwyg') {
    document.execCommand('createLink', false, url);
    syncWysiwygToMarkdown();
    return;
  }

  const textarea = getActiveTextarea();
  const start = textarea?.selectionStart || markdownContent.value.length;
  const linkMd = `[${text}](${url})`;

  markdownContent.value =
    markdownContent.value.substring(0, start) +
    linkMd +
    markdownContent.value.substring(start);

  recordHistory();
  triggerAutoSave();
}

function insertImagePrompt() {
  const url = prompt('请输入图片网络地址 (URL):', 'https://');
  if (!url) return;
  const alt = prompt('请输入图片说明文字 (Alt):', '实战配图') || '图片';

  if (editorMode.value === 'wysiwyg') {
    document.execCommand('insertImage', false, url);
    syncWysiwygToMarkdown();
    return;
  }

  const textarea = getActiveTextarea();
  const start = textarea?.selectionStart || markdownContent.value.length;
  const imgMd = `\n![${alt}](${url})\n`;

  markdownContent.value =
    markdownContent.value.substring(0, start) +
    imgMd +
    markdownContent.value.substring(start);

  recordHistory();
  triggerAutoSave();
}

function insertTable() {
  const tableMd = `\n\n| 对比维度 / 方案 | 优化前状况 | 规范后实测收益 |\n|---|---|---|\n| 支付结算时效 | T+7 天（易风控拦截） | T+1 天自动结汇通道 |\n| 资金损耗率 | 4.8% 综合损耗 | 1.8% 合规完税成本 |\n| 风险控制表现 | 触发人工稽查警告 | 100% 具备完税凭证 |\n\n`;

  if (editorMode.value === 'wysiwyg') {
    document.execCommand('insertHTML', false, renderMarkdown(tableMd));
    syncWysiwygToMarkdown();
    return;
  }

  const textarea = getActiveTextarea();
  const start = textarea?.selectionStart || markdownContent.value.length;
  markdownContent.value =
    markdownContent.value.substring(0, start) +
    tableMd +
    markdownContent.value.substring(start);

  recordHistory();
  triggerAutoSave();
}

function insertCalloutPrompt() {
  const types = ['TIP (经验诀窍)', 'WARNING (避坑预警)', 'NOTE (提示说明)', 'IMPORTANT (关键要点)'];
  const chosen = prompt(`请选择提示框类型 (输入序号 1-4):\n1. 经验诀窍 (TIP)\n2. 避坑预警 (WARNING)\n3. 提示说明 (NOTE)\n4. 关键要点 (IMPORTANT)`, '2');

  let typeKey = 'WARNING';
  if (chosen === '1') typeKey = 'TIP';
  else if (chosen === '2') typeKey = 'WARNING';
  else if (chosen === '3') typeKey = 'NOTE';
  else if (chosen === '4') typeKey = 'IMPORTANT';

  const defaultMsg = '此处展开关键避坑步骤或核心合规注意事项，高亮提醒其他创客注意风险！';
  const calloutMd = `\n\n> [!${typeKey}]\n> ${defaultMsg}\n\n`;

  if (editorMode.value === 'wysiwyg') {
    document.execCommand('insertHTML', false, renderMarkdown(calloutMd));
    syncWysiwygToMarkdown();
    return;
  }

  const textarea = getActiveTextarea();
  const start = textarea?.selectionStart || markdownContent.value.length;
  markdownContent.value =
    markdownContent.value.substring(0, start) +
    calloutMd +
    markdownContent.value.substring(start);

  recordHistory();
  triggerAutoSave();
}

// Textarea Smart Key Handling (Tab indent, shortcuts)
function handleTextareaKeydown(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    const textarea = e.target;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    markdownContent.value =
      textarea.value.substring(0, start) + '  ' + textarea.value.substring(end);

    nextTick(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 2;
    });
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
    e.preventDefault();
    applyFormat('bold');
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'i') {
    e.preventDefault();
    applyFormat('italic');
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'u') {
    e.preventDefault();
    applyFormat('underline');
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.shiftKey) {
    e.preventDefault();
    handleUndo();
  } else if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey))) {
    e.preventDefault();
    handleRedo();
  }
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
  recordHistory();
  triggerAutoSave();

  emit('toast', {
    title: '已载入实战模板',
    message: `成功载入《${tpl.title}》，请根据您的真实情况修改细节！`,
    type: 'SUCCESS',
  });

  nextTick(() => {
    if (editorMode.value === 'wysiwyg') {
      syncMarkdownToWysiwyg();
    }
  });
}

// Local Draft Persistence (localStorage)
const DRAFT_STORAGE_KEY = 'opchub_forum_create_draft';
let autoSaveTimer = null;

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

function handleSaveDraftManual() {
  saveDraftLocal();
  emit('toast', {
    title: '草稿已暂存',
    message: '您的风暴帖草稿已安全保存在本地存储中，随时可恢复继续撰写。',
    type: 'INFO',
  });
}

function handleClearDraft() {
  if (!confirm('确定要清空当前所有内容吗？清空后草稿将被删除。')) return;
  title.value = '';
  markdownContent.value = '';
  tagsList.value = [];
  tagInputText.value = '';
  localStorage.removeItem(DRAFT_STORAGE_KEY);
  lastSavedTime.value = '';
  historyStack.value = [];
  historyIndex.value = -1;

  if (wysiwygEditorRef.value) {
    wysiwygEditorRef.value.innerHTML = '';
  }

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
      recordHistory();

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

  if (editorMode.value === 'wysiwyg') {
    syncWysiwygToMarkdown();
  }

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
        message: res.error || '网络或网关异常，请稍后重试',
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
      ip_location: '来自 浙江',
      replies: 0,
      upvotes: 1,
      is_upvoted: true,
      pinned: null,
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
      message: err.message || '网络或网关异常，请稍后重试',
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
  if (markdownContent.value) {
    recordHistory();
    syncMarkdownToWysiwyg();
  }
  window.addEventListener('click', handleGlobalClick);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', handleGlobalClick);
  clearTimeout(autoSaveTimer);
});
</script>

<style scoped>
.forum-create-page-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Header Bar */
.create-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.header-left-cluster {
  display: flex;
  align-items: center;
  gap: 14px;
}

.btn-back-square {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-back-square:hover {
  background: var(--glass-surface-hover);
  color: var(--accent);
  transform: translateX(-2px);
}

.page-title-cluster {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.breadcrumb-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.crumb-link {
  cursor: pointer;
  transition: color 0.2s ease;
}

.crumb-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.crumb-separator {
  opacity: 0.5;
}

.crumb-current {
  color: var(--text-primary);
  font-weight: 500;
}

.page-main-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin: 0;
}

/* Center Status */
.header-center-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.save-status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: rgba(52, 199, 89, 0.08);
  border: 1px solid rgba(52, 199, 89, 0.25);
  font-size: 11.5px;
  color: #34c759;
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

.meta-stats-text {
  font-size: 11px;
  color: var(--text-tertiary);
  display: flex;
  gap: 6px;
}

.stat-divider {
  opacity: 0.4;
}

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
  gap: 5px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-tertiary);
  font-size: 12px;
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-header-ghost:hover {
  background: rgba(255, 59, 48, 0.08);
  color: #ff3b30;
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

/* Main Workspace Box */
.create-workspace-box {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Form Rows */
.form-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.required-star {
  color: #ff3b30;
}

/* Category Pills Row */
.categories-pill-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.cat-select-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  cursor: pointer;
  transition: var(--transition-liquid);
  text-align: left;
}

.cat-select-btn:hover {
  background: var(--glass-surface-hover);
  border-color: var(--accent);
}

.cat-select-btn.active {
  background: var(--glass-surface-solid);
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent), var(--glass-shadow);
}

.cat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-bottom: 6px;
}

.cat-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.cat-desc {
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.3;
}

/* Title Input */
.title-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.char-counter {
  font-size: 11.5px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.char-counter.is-limit {
  color: #ff9500;
}

.title-input-wrapper {
  position: relative;
  width: 100%;
}

.title-large-input {
  width: 100%;
  font-size: 16px;
  font-weight: 600;
  padding: 12px 36px 12px 16px;
  border-radius: var(--radius-md);
}

.btn-clear-input {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  color: var(--text-tertiary);
  cursor: pointer;
  line-height: 1;
}

/* Tags Field */
.tags-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tags-hint {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.tags-interactive-field {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  min-height: 44px;
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
  margin-top: 4px;
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

/* Universal Editor Toolbar */
.editor-universal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  flex-wrap: wrap;
}

.toolbar-buttons-cluster {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.btn-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 30px;
  padding: 0 6px;
  border-radius: var(--radius-xs);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.tool-btn:hover {
  background: var(--glass-surface-hover);
  color: var(--text-primary);
  border-color: var(--glass-border);
}

.tool-btn-highlight {
  background: rgba(255, 149, 0, 0.1);
  color: #ff9500;
  border-color: rgba(255, 149, 0, 0.25);
  gap: 4px;
  padding: 0 8px;
}

.tool-btn-highlight:hover {
  background: rgba(255, 149, 0, 0.18);
  color: #ff9500;
  border-color: #ff9500;
}

.callout-icon-mini {
  font-size: 13px;
}

.btn-txt-mini {
  font-size: 11px;
  font-weight: 600;
}

.tool-divider {
  width: 1px;
  height: 18px;
  background: var(--glass-border);
  margin: 0 4px;
}

/* View Modes Segmented Control */
.view-modes-segmented-control {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.05);
  padding: 3px;
  border-radius: var(--radius-sm);
  gap: 2px;
}

[data-theme="dark"] .view-modes-segmented-control {
  background: rgba(255, 255, 255, 0.06);
}

.mode-btn {
  padding: 4px 10px;
  border-radius: var(--radius-xs);
  background: transparent;
  border: none;
  font-size: 11.5px;
  color: var(--text-tertiary);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn.active {
  background: var(--glass-surface-solid);
  color: var(--accent);
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

/* Editor Canvas Container */
.editor-canvas-container {
  width: 100%;
  min-height: 480px;
  border-radius: var(--radius-md);
  border: 1px solid var(--glass-border);
  background: var(--glass-surface-subtle);
  overflow: hidden;
  display: flex;
}

/* Markdown Textarea Canvas */
.pane-markdown-canvas {
  width: 100%;
  height: 100%;
  min-height: 480px;
}

.code-textarea {
  width: 100%;
  height: 100%;
  min-height: 480px;
  padding: 18px;
  font-family: var(--font-mono);
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--text-primary);
  background: transparent;
  border: none;
  outline: none;
  resize: vertical;
}

/* WYSIWYG Editable Surface */
.pane-wysiwyg-canvas {
  width: 100%;
  min-height: 480px;
  padding: 24px;
  overflow-y: auto;
}

.wysiwyg-editable-surface {
  min-height: 440px;
  outline: none;
  color: var(--text-primary);
  font-size: 14.5px;
  line-height: 1.75;
}

.wysiwyg-editable-surface:empty::before {
  content: attr(placeholder);
  color: var(--text-tertiary);
  font-style: italic;
  pointer-events: none;
}

/* Split Screen Mode */
.pane-split-container {
  display: flex;
  width: 100%;
  min-height: 520px;
}

.split-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.split-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.02);
  border-bottom: 1px solid var(--glass-border);
  font-size: 11.5px;
  color: var(--text-tertiary);
}

[data-theme="dark"] .split-header {
  background: rgba(255, 255, 255, 0.02);
}

.split-badge {
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
}

.split-badge.highlight {
  color: var(--accent);
  background: var(--accent-glass);
}

.split-textarea {
  flex: 1;
  min-height: 480px;
  padding: 16px;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.65;
  background: transparent;
  color: var(--text-primary);
}

.split-divider-line {
  width: 1px;
  background: var(--glass-border);
}

.split-preview-surface {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  min-height: 480px;
  max-height: 700px;
}

/* Full Preview Mode */
.pane-full-preview {
  width: 100%;
  padding: 28px;
  overflow-y: auto;
}

.preview-card-wrap {
  width: 100%;
}

.preview-header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.category-pill-preview {
  font-size: 11.5px;
  font-weight: 600;
  color: #fff;
  padding: 3px 9px;
  border-radius: var(--radius-full);
}

.preview-ip,
.preview-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.preview-post-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.35;
  margin-bottom: 18px;
}

.preview-author-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.author-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.author-name-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge-maker {
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background: rgba(52, 199, 89, 0.12);
  color: #34c759;
  border: 1px solid rgba(52, 199, 89, 0.3);
}

.author-sub-desc {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.preview-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.preview-tag-pill {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--accent);
}

.preview-divider {
  height: 1px;
  background: var(--glass-border);
  margin: 18px 0;
}

/* Footer & Compliance Bar */
.create-page-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding-top: 8px;
  border-top: 1px solid var(--glass-border-subtle);
}

.footer-left-notes {
  display: flex;
  align-items: center;
}

.compliance-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.footer-actions-cluster {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-footer-cancel {
  padding: 9px 18px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-footer-cancel:hover {
  background: var(--glass-surface-hover);
  color: var(--text-primary);
}

.btn-footer-publish {
  padding: 9px 24px;
  border-radius: var(--radius-md);
  font-size: 13.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-footer-publish:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

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
</style>
