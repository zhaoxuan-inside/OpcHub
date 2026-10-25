<template>
  <div class="sop-doc-page">
    <!-- ============ Shared header ============ -->
    <div class="glass-box sop-doc-header">
      <div class="sop-doc-header-left">
        <button class="sop-doc-back" @click="$emit('back')" title="返回流程文书">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
        </button>

        <div class="sop-doc-heading">
          <h2 class="sop-doc-title">{{ crumbTitle }}</h2>
          <div class="sop-doc-meta">
            <template v-if="isEditorMode">
              <span class="sop-doc-category-pill" :class="{ new: !draft }">{{ draft ? '编辑草稿' : '新文书' }}</span>
              <span class="sop-doc-dot">·</span>
              <span>{{ draftStats }}</span>
            </template>
            <template v-else-if="node && node.kind === 'subgraph'">
              <span class="sop-doc-category-pill">复合子图</span>
              <span class="sop-doc-dot">·</span>
              <span>包含 {{ (children || []).length }} 份文书</span>
            </template>
            <template v-else-if="node">
              <span class="sop-doc-category-pill">{{ categoryLabel(node.category) }}</span>
              <span class="sop-doc-stage">阶段 {{ String(node.stage || 0).padStart(2, '0') }}</span>
              <span class="sop-doc-dot">·</span>
              <span>{{ (node.required_fields || []).length }} 个待填要素</span>
            </template>
            <template v-else>
              <span class="sop-doc-category-pill new">新文书</span>
              <span class="sop-doc-dot">·</span>
              <span>从右侧模板库选择 {{ catalog.length }} 份标准文书开始填写</span>
            </template>
          </div>
        </div>
      </div>

      <!-- Editor mode actions: save to 我的文书, then publish to 标准文书库 -->
      <div v-if="isEditorMode" class="sop-doc-header-actions">
        <button type="button" class="btn-liquid-outline sop-doc-action" @click="copyRendered" title="复制编辑器中的全文">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span>复制全文</span>
        </button>
        <button type="button" class="btn-liquid-outline sop-doc-action" :disabled="exporting" @click="exportPdf">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          <span>{{ exporting ? '生成中...' : '生成 PDF' }}</span>
        </button>
        <button type="button" class="btn-liquid-outline sop-doc-action" :disabled="saving || publishing" @click="saveDraft" title="保存到「我的文书」">
          <svg v-if="!saving" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          <span v-else class="loading-spinner"></span>
          <span>{{ saving ? '保存中...' : '保存文书' }}</span>
        </button>
        <button type="button" class="btn-liquid sop-doc-action sop-doc-save" :disabled="saving || publishing" @click="saveAndPublish" title="保存并提交审核，通过后发布至标准文书库">
          <svg v-if="!publishing" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
          <span v-else class="loading-spinner"></span>
          <span>{{ publishing ? '发布中...' : '保存并发布' }}</span>
        </button>
      </div>

      <!-- Standard document mode actions (unchanged field-fill experience) -->
      <div v-else-if="node && node.kind !== 'subgraph'" class="sop-doc-header-actions">
        <button type="button" class="btn-liquid sop-doc-action sop-doc-save" :disabled="saving" @click="saveDocument" title="保存文书至我的文书">
          <svg v-if="!saving" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          <span v-else class="loading-spinner"></span>
          <span>{{ saving ? '保存中...' : '保存文书' }}</span>
        </button>
        <button type="button" class="btn-liquid-outline sop-doc-action" @click="copyRendered" title="复制文书全文">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span>复制全文</span>
        </button>
        <button type="button" class="btn-liquid sop-doc-action" :disabled="exporting" @click="exportPdf">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          <span>{{ exporting ? '生成中...' : '生成 PDF 文书' }}</span>
        </button>

        <!-- Manual fallback: always available once a PDF has been produced -->
        <a
          v-if="fallbackUrl"
          class="btn-liquid-outline sop-doc-action sop-doc-fallback-link"
          :href="fallbackUrl"
          :download="fallbackName"
          title="若未自动下载，点击此处另存为 PDF"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          <span>另存为 PDF</span>
        </a>
      </div>
    </div>

    <!-- ============ Body ============ -->
    <div
      class="sop-doc-body"
      :class="{
        'sop-doc-body-single': !isEditorMode && node && node.kind === 'subgraph',
        'sop-doc-body-creation': isEditorMode,
      }"
    >
      <!-- ============ Creation: unified rich-text editor ============ -->
      <template v-if="isEditorMode">
        <section class="sop-doc-main-col">
          <div class="sop-doc-editor">
            <PublishNotice />
            <input
              v-model="draftTitle"
              type="text"
              class="sop-doc-title-input"
              maxlength="120"
              placeholder="未命名文书"
              aria-label="文书标题"
            />
            <!-- 统一发布体验：富文本 + Markdown 双模式编辑器 -->
            <RichEditor
              v-model="draftContent"
              :min-height="420"
              placeholder="在此撰写文书正文，或从右侧选择一个模板开始起草……&#10;模板中的【要素】是待填写提示，可直接替换为你的真实信息。支持标题、列表与高亮提示框。"
            />
            <div class="sop-doc-editor-footer">
              <span>{{ draftStats }}</span>
              <span class="sop-doc-editor-hint">内容仅自己可见 · 保存后可在「我的文书」继续编辑或发布</span>
            </div>
          </div>
        </section>

        <!-- Right-side template library: click to seed the editor -->
        <aside class="sop-doc-template-panel">
          <div class="sop-doc-pane-label">
            常见模板
            <span class="sop-doc-panel-count">{{ filteredCatalog.length }} 份</span>
          </div>

          <div class="sop-doc-picker">
            <button
              v-for="cat in categories"
              :key="cat.key"
              type="button"
              :class="['sop-doc-picker-cat', { active: activeCategory === cat.key }]"
              @click="activeCategory = cat.key"
            >
              {{ cat.label }}
            </button>
          </div>

          <div class="sop-doc-panel-list">
            <button
              type="button"
              class="sop-doc-panel-card sop-doc-panel-empty-card"
              :class="{ active: !selectedTemplateId }"
              @click="startBlank"
            >
              <span class="sop-doc-panel-name">空白文书</span>
              <span class="sop-doc-panel-meta">从零开始自由撰写</span>
            </button>

            <button
              v-for="doc in filteredCatalog"
              :key="doc.id"
              type="button"
              class="sop-doc-panel-card"
              :class="{ active: selectedTemplateId === doc.id }"
              :title="templateTooltip(doc)"
              @click="applyTemplate(doc)"
            >
              <span class="sop-doc-panel-name">{{ doc.name }}</span>
              <span class="sop-doc-panel-meta">
                {{ categoryLabel(doc.category) }} · {{ (doc.required_fields || []).length }} 个待填要素
              </span>
            </button>
            <div v-if="!filteredCatalog.length" class="sop-doc-panel-empty">该分类暂无可用模板。</div>
          </div>

          <p class="sop-doc-panel-tip">选择模板会把正文载入左侧编辑器，你可以自由增删修改后再保存。</p>
        </aside>
      </template>

      <!-- ============ Standard document: field-fill writer ============ -->
      <template v-else-if="node && node.kind !== 'subgraph'">
        <section class="sop-doc-main-col">
          <div class="sop-doc-writer-grid">
            <section class="sop-doc-form-pane">
              <div class="sop-doc-pane-label">待填要素</div>

              <div v-if="node.description" class="sop-doc-intro">{{ node.description }}</div>

              <ContentInteractionBar
                target-type="SOP_DOCUMENT"
                :target-id="node.id"
                :target-title="node.name"
                auto-load
                :authenticated="authenticated"
                @require-login="$emit('require-login')"
                @toast="$emit('toast', $event)"
              />

              <div class="sop-doc-fields">
                <SopFieldForm
                  v-for="field in (node.required_fields || [])"
                  :key="field.key"
                  :field="field"
                  :model-value="formData[field.key] ?? ''"
                  :show-error="submitted && isFieldMissing(field)"
                  @update:model-value="(v) => onFieldInput(field.key, v)"
                />
              </div>
            </section>

            <section class="sop-doc-preview-pane">
              <div class="sop-doc-pane-label">
                文书正文
                <span v-if="serial" class="sop-doc-serial">流水号 {{ serial }}</span>
              </div>

              <div ref="paperRef" class="sop-doc-paper">
                <pre class="sop-doc-paper-content">{{ renderedContent || '填写左侧要素后，此处实时生成标准文书正文。' }}</pre>
              </div>

              <div v-if="node.outcome" class="sop-doc-outcome">
                <span class="sop-doc-outcome-label">完成后你会得到</span>
                <span>{{ node.outcome }}</span>
              </div>
              <div v-if="node.next_hint" class="sop-doc-next-hint">
                <span class="sop-doc-outcome-label">接下来建议</span>
                <span>{{ node.next_hint }}</span>
              </div>

              <!-- 展示页面免责声明 -->
              <ContentDisclaimer type="sop" />
            </section>
          </div>
        </section>
      </template>

      <!-- ============ Subgraph composition ============ -->
      <template v-else-if="node && node.kind === 'subgraph'">
        <section class="sop-doc-form-pane">
          <div class="sop-doc-pane-label">子图构成</div>

          <div v-if="node.description" class="sop-doc-intro">{{ node.description }}</div>

          <div v-if="node.outcome" class="sop-doc-outcome">
            <span class="sop-doc-outcome-label">完成这整个子图，你会得到</span>
            <span>{{ node.outcome }}</span>
          </div>

          <div class="sop-doc-child-list">
            <button
              v-for="(child, idx) in (children || [])"
              :key="child.id"
              type="button"
              class="sop-doc-child"
              @click="$emit('pick', child)"
            >
              <span class="sop-doc-child-order">{{ idx + 1 }}</span>
              <div class="sop-doc-child-body">
                <div class="sop-doc-child-name">{{ child.name }}</div>
                <div class="sop-doc-child-meta">
                  {{ (child.required_fields || []).length }} 个待填要素
                  <span class="sop-doc-dot">·</span>
                  {{ child.description }}
                </div>
              </div>
              <span class="sop-doc-child-go">撰写 ›</span>
            </button>
          </div>
        </section>
      </template>

      <!-- ============ Fallback empty state ============ -->
      <template v-else>
        <div class="sop-doc-empty-writer">
          <div class="sop-doc-empty-icon">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
          </div>
          <h3 class="sop-doc-empty-title">开始起草新文书</h3>
          <p class="sop-doc-empty-desc">
            直接在上方编辑器撰写正文，或从右侧模板库选择一份标准文书作为起点，再自由修改。
          </p>
        </div>
      </template>
    </div>

    <!-- Off-screen paper used only to rasterise the editor content into a PDF -->
    <div ref="printRef" class="sop-doc-print-surface" aria-hidden="true">
      <h2 class="sop-doc-print-title">{{ draftTitle || '未命名文书' }}</h2>
      <!-- 正文为统一富文本编辑器产出的 Markdown，导出前渲染为排版 HTML -->
      <div class="sop-doc-print-body markdown-rendered-content" v-html="printBodyHtml"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, onUnmounted } from 'vue';
import SopFieldForm from '@/components/sop/SopFieldForm.vue';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
import ContentDisclaimer from '@/components/ContentDisclaimer.vue';
import PublishNotice from '@/components/PublishNotice.vue';
import RichEditor from '@/components/editor/RichEditor.vue';
import { renderMarkdown } from '@/utils/markdown';
import { buildPdfFileName, exportElementToPdf } from '@/utils/sopPdf';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  node: { type: Object, default: null },
  catalog: { type: Array, default: () => [] },
  children: { type: Array, default: () => [] },
  authenticated: { type: Boolean, default: false },
  // Authoritative maker uid resolved by the parent workspace, so saving always
  // attributes the document to the logged-in user without re-parsing storage.
  userId: { type: String, default: '' },
  // Creation entry (创建文书 / 发布新文档): open the free-form text editor with
  // the template library as a right-side panel. This is the true drafting path:
  // the maker writes the body, optionally seeded from a template.
  creationMode: { type: Boolean, default: false },
  // An existing private draft to reopen in the editor (编辑草稿). When present
  // the editor is prefilled and saving updates the same document in place.
  draft: { type: Object, default: null },
});

const emit = defineEmits(['back', 'pick', 'saved', 'toast', 'require-login']);

const CATEGORY_LABELS = {
  ENTITY: '主体登记',
  TAX: '税务合规',
  LEGAL: '法律文书',
  BANK: '银行账户',
  IP: '知识产权',
  CROSS_BORDER: '跨境出海',
  FINANCE: '财务票据',
};

/* --------------------------------------------------------------------------
 * Shared state
 * ------------------------------------------------------------------------ */
const exporting = ref(false);
const paperRef = ref(null);
const printRef = ref(null);
// Manual "另存为" fallback: the object URL of the last generated PDF.
const fallbackUrl = ref('');
const fallbackName = ref('');

/* --------------------------------------------------------------------------
 * Creation mode: free-form editor + template library
 * ------------------------------------------------------------------------ */
const isEditorMode = computed(() => props.creationMode);

const draftTitle = ref('');
const draftContent = ref('');
const selectedTemplateId = ref('');
const selectedCategory = ref('');
// The content last seeded by a template. Used to detect whether the maker has
// typed anything worth protecting before a template switch / blank reset.
const seededContent = ref('');

const activeCategory = ref('ALL');

const categories = computed(() => {
  const used = new Set(props.catalog.map((n) => n.category));
  const list = [{ key: 'ALL', label: '全部' }];
  for (const [key, label] of Object.entries(CATEGORY_LABELS)) {
    if (used.has(key)) list.push({ key, label });
  }
  return list;
});

const filteredCatalog = computed(() =>
  props.catalog.filter(
    (n) => activeCategory.value === 'ALL' || n.category === activeCategory.value
  )
);

const draftStats = computed(() => {
  const text = draftContent.value || '';
  const chars = text.replace(/\s/g, '').length;
  const lines = text ? text.split('\n').length : 0;
  return `${chars} 字 · ${lines} 行`;
});

// PDF 导出面：Markdown 渲染为排版 HTML 后由 html2canvas 光栅化
const printBodyHtml = computed(() => renderMarkdown(draftContent.value || ''));

function resetEditor() {
  draftTitle.value = '';
  draftContent.value = '';
  selectedTemplateId.value = '';
  selectedCategory.value = '';
  seededContent.value = '';
}

/** Is there unsaved manual typing that a template switch would discard? */
function hasUnsavedTyping() {
  const current = draftContent.value.trim();
  if (!current) return false;
  return current !== (seededContent.value || '').trim();
}

/**
 * Turn a template body into an editable starting point.
 * Field placeholders `{key}` become readable 【label】 prompts so the maker can
 * replace them in place instead of filling a separate form.
 */
function buildEditableContent(template) {
  let text = template?.template_content || '';
  for (const field of template?.required_fields || []) {
    text = text.split(`{${field.key}}`).join(`【${field.label}】`);
  }
  // Any leftover unknown placeholder still gets a readable presentation.
  text = text.replace(/\{([a-zA-Z0-9_]+)\}/g, '【$1】');
  return text;
}

function templateTooltip(template) {
  const fields = (template.required_fields || []).map((f) => f.label);
  return fields.length ? `载入后可替换：${fields.join('、')}` : '载入模板正文后自由修改';
}

/** Seed the editor from a template card (or node). */
async function applyTemplate(card) {
  if (!card) return;
  if (hasUnsavedTyping() && !window.confirm(`应用模板「${card.name}」将替换当前编辑内容，是否继续？`)) {
    return;
  }

  // The workspace catalog already carries the full node (template_content +
  // required_fields). Fall back to a node lookup if a lean card is passed in.
  let template = card;
  if (!template.template_content) {
    const res = await dispatchGateway('sop.node', { node_id: card.id }, { silent: true });
    if (res.ok && res.data?.node) template = { ...card, ...res.data.node };
  }

  const body = buildEditableContent(template);
  draftTitle.value = template.name || '';
  draftContent.value = body;
  selectedTemplateId.value = template.id || '';
  selectedCategory.value = template.category || '';
  seededContent.value = body;
  emit('toast', {
    title: '模板已载入',
    message: `《${template.name}》已载入编辑器，替换【要素】后即可保存。`,
    type: 'INFO',
  });
}

/** Clear the editor and start from a blank document. */
function startBlank() {
  if (hasUnsavedTyping() && !window.confirm('清空当前编辑内容，开始一份空白文书？')) {
    return;
  }
  resetEditor();
}

// A different creation session always starts clean, unless an existing private
// draft is being reopened for editing.
watch(
  () => [props.creationMode, props.node?.id, props.draft?.id],
  ([creationMode]) => {
    if (!creationMode) return;
    if (props.draft) {
      draftTitle.value = props.draft.document_title || '';
      draftContent.value = props.draft.rendered_content || '';
      selectedTemplateId.value = props.draft.template_id || '';
      selectedCategory.value = props.draft.category || '';
      seededContent.value = draftContent.value;
    } else {
      resetEditor();
    }
  },
  { immediate: true }
);

/* --------------------------------------------------------------------------
 * Standard document mode: field-fill writer (unchanged)
 * ------------------------------------------------------------------------ */
const formData = reactive({});
const submitted = ref(false);

// Reset the form whenever a different document is opened.
watch(
  () => props.node?.id,
  () => {
    for (const key of Object.keys(formData)) {
      delete formData[key];
    }
    for (const field of props.node?.required_fields || []) {
      formData[field.key] = field.default ?? '';
    }
    submitted.value = false;
    // The previous document's PDF no longer applies.
    revokeFallbackUrl();
  },
  { immediate: true }
);

function categoryLabel(category) {
  return CATEGORY_LABELS[category] || category || '标准文书';
}

// Header breadcrumb title: the live draft title in the editor, otherwise the
// active document's name.
const crumbTitle = computed(() => {
  if (isEditorMode.value) return draftTitle.value.trim() || '起草新文书';
  if (!props.node) return '起草新文书';
  return props.node.name;
});

const renderedContent = computed(() => {
  const node = props.node;
  if (!node) return '';
  let content = node.template_content || '';
  for (const field of node.required_fields || []) {
    const value = formData[field.key];
    const display =
      value === undefined || value === null || value === '' ? `（待填写${field.label}）` : value;
    content = content.split(`{${field.key}}`).join(String(display));
  }
  return content;
});

const serial = computed(() => {
  const seedSource = isEditorMode.value
    ? `${draftTitle.value}|${draftContent.value}`
    : `${props.node?.id || ''}|${JSON.stringify(formData)}`;
  if (!seedSource) return '';
  const seed = seedSource.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  return `VER-${seed.toString(16).toUpperCase().padStart(8, '0').slice(0, 8)}`;
});

function onFieldInput(key, value) {
  formData[key] = value;
}

function isFieldMissing(field) {
  if (!field.required) return false;
  const value = formData[field.key];
  return value === undefined || value === null || String(value).trim() === '';
}

/* --------------------------------------------------------------------------
 * Persistence
 * ------------------------------------------------------------------------ */
const saving = ref(false);
const publishing = ref(false);

/**
 * Resolve the current maker uid. Prefers the authoritative `userId` prop passed
 * by the workspace; falls back to the localStorage session for resilience.
 */
function currentUserUid() {
  if (props.userId) return props.userId;
  try {
    const raw = localStorage.getItem('opchub_user_session');
    const session = raw ? JSON.parse(raw) : null;
    return session?.uid || session?.id || '';
  } catch (e) {
    return '';
  }
}

/**
 * Save the edited draft (no user-facing events). Returns the persisted document
 * so callers can chain a publish step without navigating away mid-flight.
 */
async function persistDraft() {
  if (!props.authenticated) {
    emit('require-login');
    return null;
  }
  const content = draftContent.value.trim();
  if (!content) {
    emit('toast', { title: '正文为空', message: '请先撰写正文，或从右侧选择一个模板开始。', type: 'WARN' });
    return null;
  }

  saving.value = true;
  try {
    const res = await dispatchGateway('sop.document.draft', {
      doc_id: props.draft?.id || undefined,
      title: draftTitle.value.trim(),
      content: draftContent.value,
      template_id: selectedTemplateId.value || '',
      category: selectedCategory.value || '',
      user_id: currentUserUid(),
    });
    if (res.ok && res.data) {
      seededContent.value = draftContent.value;
      return res.data;
    }
    emit('toast', { title: '保存受阻', message: res.error || '文书保存未成功，请稍后重试。', type: 'ERROR' });
    return null;
  } catch (e) {
    emit('toast', { title: '保存异常', message: e?.message || '文书保存服务暂时不可用，请稍后重试。', type: 'ERROR' });
    return null;
  } finally {
    saving.value = false;
  }
}

/** 保存文书 → 我的文书 */
async function saveDraft() {
  const doc = await persistDraft();
  if (!doc) return;
  emit('saved', doc);
  emit('toast', {
    title: '文书已保存',
    message: `《${doc.document_title || '未命名文书'}》已保存到「我的文书」。`,
    type: 'SUCCESS',
  });
}

/** 保存并发布 → 保存后立即提交审核（通过后进入标准文书库） */
async function saveAndPublish() {
  const doc = await persistDraft();
  if (!doc) return;
  publishing.value = true;
  try {
    const res = await dispatchGateway('sop.document.publish', { doc_id: doc.id });
    if (res.ok && res.data) {
      emit('saved', { ...doc, status: res.data.status || 'PENDING_REVIEW' });
      emit('toast', {
        title: '已提交发布',
        message: `《${doc.document_title || '未命名文书'}》已提交审核，通过后将发布至标准文书库。`,
        type: 'SUCCESS',
      });
    } else {
      emit('saved', doc);
      emit('toast', { title: '发布未完成', message: res.error || '文书已保存，但提交审核未成功。', type: 'ERROR' });
    }
  } catch (e) {
    emit('saved', doc);
    emit('toast', { title: '发布异常', message: e?.message || '文书已保存，但发布服务暂时不可用。', type: 'ERROR' });
  } finally {
    publishing.value = false;
  }
}

/**
 * Standard-document field-fill save: render the template with the maker's form
 * data and persist it to「我的文书」via the microkernel DAG pipeline.
 */
async function saveDocument() {
  const node = props.node;
  if (!node || node.kind === 'subgraph') {
    emit('toast', { title: '暂无可保存文书', message: '请先从模板库选择一份标准文书。', type: 'WARN' });
    return;
  }
  if (!props.authenticated) {
    emit('require-login');
    return;
  }

  const missing = (node.required_fields || []).filter((f) => f.required && isFieldMissing(f));
  if (missing.length) {
    submitted.value = true;
    emit('toast', {
      title: '信息不全',
      message: `还有 ${missing.length} 项必填要素未完成：${missing.map((f) => f.label).join('、')}。`,
      type: 'WARN',
    });
    return;
  }

  saving.value = true;
  try {
    const res = await dispatchGateway('sop.document.render', {
      template_id: node.id,
      user_id: currentUserUid(),
      form_data: { ...formData },
    });
    if (res.ok && res.data) {
      emit('saved', res.data);
      emit('toast', {
        title: '文书已保存',
        message: `《${res.data.document_title || node.name}》已保存到「我的文书」。`,
        type: 'SUCCESS',
      });
    } else {
      emit('toast', { title: '保存受阻', message: res.error || '文书保存未成功，请稍后重试。', type: 'WARN' });
    }
  } catch (e) {
    emit('toast', { title: '保存异常', message: e?.message || '文书保存服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    saving.value = false;
  }
}

/* --------------------------------------------------------------------------
 * PDF export / clipboard
 * ------------------------------------------------------------------------ */
async function exportPdf() {
  if (isEditorMode.value) {
    if (!draftContent.value.trim()) {
      emit('toast', { title: '正文为空', message: '请先撰写正文后再生成 PDF。', type: 'WARN' });
      return;
    }
  } else {
    const missing = (props.node?.required_fields || []).filter((f) => f.required && isFieldMissing(f));
    if (missing.length) {
      submitted.value = true;
      emit('toast', {
        title: '信息不全',
        message: `还有 ${missing.length} 项必填要素未完成：${missing.map((f) => f.label).join('、')}。`,
        type: 'WARN',
      });
      return;
    }
  }

  const element = isEditorMode.value ? printRef.value : paperRef.value;
  if (!element) {
    emit('toast', { title: '导出受阻', message: '未找到文书正文，无法生成 PDF。', type: 'ERROR' });
    return;
  }

  exporting.value = true;
  try {
    const title = isEditorMode.value ? (draftTitle.value.trim() || '未命名文书') : props.node?.name;
    const fileName = buildPdfFileName(title, serial.value);
    const { pages, blob } = await exportElementToPdf(element, fileName);

    // Keep a manual fallback: if the browser blocked the automatic download,
    // the maker can still save the file with a single click on the link.
    revokeFallbackUrl();
    fallbackUrl.value = URL.createObjectURL(blob);
    fallbackName.value = fileName;

    emit('toast', {
      title: 'PDF 已生成',
      message: `已导出为 ${pages} 页 PDF，文件未上传至服务器。若未自动下载，请点击页面上的「另存为 PDF」。`,
      type: 'SUCCESS',
    });
  } catch (e) {
    emit('toast', {
      title: '导出失败',
      message: e?.message || 'PDF 生成失败，请稍后重试。',
      type: 'ERROR',
    });
  } finally {
    exporting.value = false;
  }
}

function revokeFallbackUrl() {
  if (fallbackUrl.value) {
    URL.revokeObjectURL(fallbackUrl.value);
    fallbackUrl.value = '';
  }
}

async function copyRendered() {
  const text = isEditorMode.value ? draftContent.value : renderedContent.value;
  if (!text || !text.trim()) {
    emit('toast', { title: '暂无可复制内容', message: '请先撰写或生成文书正文。', type: 'INFO' });
    return;
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    emit('toast', { title: '复制成功', message: '文书全文已复制到剪贴板。', type: 'SUCCESS' });
  } catch (e) {
    emit('toast', { title: '复制失败', message: '当前浏览器未授予剪贴板权限，请手动选择复制。', type: 'WARN' });
  }
}

onUnmounted(() => {
  revokeFallbackUrl();
});
</script>

<style scoped>
.sop-doc-page {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.sop-doc-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 22px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.sop-doc-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.sop-doc-back {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.sop-doc-back:hover {
  border-color: rgba(0, 113, 227, 0.35);
  color: var(--accent);
}

.sop-doc-heading {
  min-width: 0;
}

.sop-doc-title {
  margin: 0 0 3px;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sop-doc-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  color: var(--text-tertiary);
  flex-wrap: wrap;
}

.sop-doc-category-pill {
  font-size: 11px;
  font-weight: 500;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent, #0071e3);
  border: 1px solid rgba(0, 113, 227, 0.18);
}

.sop-doc-dot {
  opacity: 0.6;
}

.sop-doc-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.sop-doc-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: var(--radius-full);
}

.sop-doc-save {
  background: var(--accent);
  color: #fff;
  border: none;
}

.sop-doc-save:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px var(--accent-glow);
}

.sop-doc-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.sop-doc-save .loading-spinner {
  width: 12px;
  height: 12px;
  border-width: 2px;
  border-color: rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: sopDocSpin 0.8s linear infinite;
}

@keyframes sopDocSpin {
  to { transform: rotate(360deg); }
}

.sop-doc-fallback-link {
  text-decoration: none;
  white-space: nowrap;
}

.sop-doc-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  overflow: hidden;
}

.sop-doc-body-single {
  grid-template-columns: 1fr;
}

/* Creation entry: main editor column + right-side template panel */
.sop-doc-body-creation {
  grid-template-columns: minmax(0, 1fr) 300px;
}

.sop-doc-main-col {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sop-doc-main-col > .sop-doc-form-pane {
  flex: 1;
}

/* ---------------------------------------------------------------- Editor */
.sop-doc-editor {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px 22px;
  border-radius: var(--radius-lg, 16px);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
}

.sop-doc-title-input {
  flex-shrink: 0;
  width: 100%;
  padding: 0 0 12px;
  border: none;
  border-bottom: 1px solid var(--glass-border);
  background: transparent;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
  outline: none;
  box-sizing: border-box;
}

.sop-doc-title-input::placeholder {
  color: var(--text-tertiary);
  font-weight: 500;
}

.sop-doc-editor-footer {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
  flex-wrap: wrap;
}

.sop-doc-editor-hint {
  opacity: 0.85;
}

/* The form + preview pair, inside the main column */
.sop-doc-writer-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  overflow: hidden;
}

/* Empty writing surface shown before a template is picked */
.sop-doc-empty-writer {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 24px;
  text-align: center;
  border-radius: var(--radius-lg, 16px);
  background: var(--glass-surface);
  border: 1px dashed var(--glass-border);
}

.sop-doc-empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--glass-surface-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.sop-doc-empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.sop-doc-empty-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  max-width: 380px;
  line-height: 1.6;
  margin: 0;
}

/* ---------------------------------------------------- Right-side templates */
.sop-doc-template-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 16px;
  border-radius: var(--radius-lg, 16px);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  overflow: hidden;
}

.sop-doc-panel-count {
  color: var(--accent);
}

.sop-doc-panel-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  scrollbar-width: none;
}

.sop-doc-panel-list::-webkit-scrollbar {
  display: none;
}

.sop-doc-panel-card {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 11px 13px;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.sop-doc-panel-card:hover {
  border-color: rgba(0, 113, 227, 0.35);
  transform: translateY(-1px);
}

.sop-doc-panel-card.active {
  border-color: rgba(0, 113, 227, 0.5);
  background: rgba(0, 113, 227, 0.1);
}

.sop-doc-panel-empty-card {
  border-style: dashed;
}

.sop-doc-panel-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}

.sop-doc-panel-meta {
  font-size: 10.5px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.sop-doc-panel-empty {
  font-size: 12px;
  color: var(--text-tertiary);
  padding: 14px 4px;
}

.sop-doc-panel-tip {
  flex-shrink: 0;
  margin: 0;
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-tertiary);
}

.sop-doc-category-pill.new {
  background: var(--status-warning-soft);
  color: var(--status-warning);
  border-color: var(--status-warning-soft);
}

.sop-doc-form-pane,
.sop-doc-preview-pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 22px;
  border-radius: var(--radius-lg, 16px);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  scrollbar-width: none;
}

.sop-doc-form-pane::-webkit-scrollbar,
.sop-doc-preview-pane::-webkit-scrollbar {
  display: none;
}

.sop-doc-pane-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-shrink: 0;
}

.sop-doc-serial {
  color: var(--accent);
}

.sop-doc-intro {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-secondary);
  padding: 11px 13px;
  border-radius: 9px;
  background: var(--glass-surface-subtle);
}

.sop-doc-fields {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.sop-doc-paper {
  flex: 1;
  min-height: 240px;
  overflow-y: auto;
  background: var(--glass-surface-solid);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  padding: 24px;
  box-shadow: var(--glass-shadow);
}

.sop-doc-paper-content {
  margin: 0;
  font-family: var(--font-mono, monospace);
  font-size: 12.5px;
  line-height: 1.95;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.sop-doc-outcome,
.sop-doc-next-hint {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px 13px;
  border-radius: 9px;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-primary);
  flex-shrink: 0;
}

.sop-doc-outcome {
  background: var(--status-success-soft);
  border: 1px solid var(--status-success-soft);
}

.sop-doc-next-hint {
  background: var(--status-warning-soft);
  border: 1px solid var(--status-warning-soft);
}

.sop-doc-outcome-label {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary);
}

/* Subgraph composition list */
.sop-doc-child-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sop-doc-child {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.sop-doc-child:hover {
  border-color: rgba(0, 113, 227, 0.35);
  transform: translateY(-1px);
}

.sop-doc-child-order {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono, monospace);
  background: rgba(0, 113, 227, 0.12);
  color: var(--accent);
  border: 1px solid rgba(0, 113, 227, 0.25);
}

.sop-doc-child-body {
  flex: 1;
  min-width: 0;
}

.sop-doc-child-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.sop-doc-child-meta {
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sop-doc-child-go {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  flex-shrink: 0;
}

/* Template picker categories */
.sop-doc-picker {
  flex-shrink: 0;
  display: flex;
  gap: 6px;
  margin-bottom: 2px;
  flex-wrap: wrap;
}

.sop-doc-picker-cat {
  padding: 5px 14px;
  font-size: 12.5px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  background: var(--glass-surface-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s ease;
}

.sop-doc-picker-cat.active {
  background: rgba(0, 113, 227, 0.1);
  border-color: rgba(0, 113, 227, 0.25);
  color: var(--accent);
  font-weight: 600;
}

/* Hidden print surface: rasterised by html2canvas when exporting a PDF. */
.sop-doc-print-surface {
  position: fixed;
  left: -10000px;
  top: 0;
  width: 760px;
  padding: 40px 48px;
  background: #ffffff;
  color: #111111;
  z-index: -1;
}

.sop-doc-print-title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 700;
  text-align: center;
}

.sop-doc-print-body {
  margin: 0;
  font-family: var(--font-mono, monospace);
  font-size: 13px;
  line-height: 1.95;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 960px) {
  .sop-doc-body {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
  .sop-doc-body-creation {
    grid-template-columns: 1fr;
  }
  .sop-doc-main-col {
    overflow: visible;
  }
  .sop-doc-writer-grid {
    grid-template-columns: 1fr;
    overflow: visible;
  }
  .sop-doc-form-pane,
  .sop-doc-preview-pane {
    overflow: visible;
  }
  .sop-doc-template-panel {
    max-height: 320px;
  }
}

[data-theme="dark"] .sop-doc-form-pane,
[data-theme="dark"] .sop-doc-preview-pane,
[data-theme="dark"] .sop-doc-template-panel,
[data-theme="dark"] .sop-doc-empty-writer,
[data-theme="dark"] .sop-doc-editor {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}
</style>
