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
          <div class="sop-doc-breadcrumb">
            <span class="sop-doc-crumb-link" @click="$emit('back')">流程文书</span>
            <span class="sop-doc-crumb-sep">/</span>
            <span class="sop-doc-crumb-current">{{ crumbTitle }}</span>
          </div>
          <div class="sop-doc-meta">
            <template v-if="node && node.kind === 'subgraph'">
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

      <div v-if="node && node.kind !== 'subgraph'" class="sop-doc-header-actions">
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
        'sop-doc-body-single': !creationMode && node && node.kind === 'subgraph',
        'sop-doc-body-creation': creationMode,
      }"
    >
      <section class="sop-doc-main-col">
        <!-- Document writer (form + preview) -->
        <template v-if="node && node.kind !== 'subgraph'">
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
            </section>
          </div>
        </template>

        <!-- Subgraph composition -->
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

        <!-- Creation entry with no template yet: keep the writing area open -->
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
              创建文书不需要先选模板。从右侧模板库挑选一份标准文书后即可填写要素并生成正文，编写区始终保留在此处。
            </p>
          </div>
        </template>
      </section>

      <!-- Right-side template panel (creation entry only) -->
      <aside v-if="creationMode" class="sop-doc-template-panel">
        <div class="sop-doc-pane-label">
          模板选择
          <span class="sop-doc-panel-count">{{ catalog.length }} 份</span>
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
            v-for="doc in filteredCatalog"
            :key="doc.id"
            type="button"
            class="sop-doc-panel-card"
            @click="$emit('pick', doc)"
          >
            <span class="sop-doc-panel-name">{{ doc.name }}</span>
            <span class="sop-doc-panel-meta">
              {{ categoryLabel(doc.category) }} · {{ (doc.required_fields || []).length }} 个待填要素
            </span>
          </button>
          <div v-if="!filteredCatalog.length" class="sop-doc-panel-empty">该分类暂无可用模板。</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, onUnmounted } from 'vue';
import SopFieldForm from '@/components/sop/SopFieldForm.vue';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
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
  // Creation entry (创建文书 / 发布新文档): keeps the writing area open and
  // shows the template library as a right-side panel instead of a full-page
  // picker takeover.
  creationMode: { type: Boolean, default: false },
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

const formData = reactive({});
const submitted = ref(false);
const activeCategory = ref('ALL');
const exporting = ref(false);
const paperRef = ref(null);
// Manual "另存为" fallback: the object URL of the last generated PDF.
const fallbackUrl = ref('');
const fallbackName = ref('');

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

function categoryLabel(category) {
  return CATEGORY_LABELS[category] || category || '标准文书';
}

// Header breadcrumb title: a fresh creation shows "起草新文书", otherwise the
// active document's name.
const crumbTitle = computed(() => {
  if (!props.node) return '起草新文书';
  return props.node.name;
});

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

onUnmounted(() => {
  revokeFallbackUrl();
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
  const node = props.node;
  if (!node) return '';
  const seed = (node.id + JSON.stringify(formData))
    .split('')
    .reduce((a, c) => a + c.charCodeAt(0), 0);
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

/**
 * 保存文书到「我的文书」。
 *
 * 调用后端 sop.document.render（微内核 DAG 编排：渲染模板 + 持久化到
 * PostgreSQL），保存成功后 emit('saved') 由父组件刷新我的文书列表。
 */
const saving = ref(false);

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

/**
 * Generate the document as a PDF and download it.
 *
 * The whole pipeline runs in the browser: the body text is already
 * interpolated into the live preview, so we rasterise that paper and wrap it
 * into an A4 PDF. Nothing is persisted on the server.
 */
async function exportPdf() {
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

  if (!paperRef.value) {
    emit('toast', { title: '导出受阻', message: '未找到文书正文，无法生成 PDF。', type: 'ERROR' });
    return;
  }

  exporting.value = true;
  try {
    const fileName = buildPdfFileName(props.node?.name, serial.value);
    const { pages, blob } = await exportElementToPdf(paperRef.value, fileName);

    // Keep a manual fallback: if the browser blocked the automatic download,
    // the maker can still save the file with a single click on the link.
    revokeFallbackUrl();
    fallbackUrl.value = URL.createObjectURL(blob);
    fallbackName.value = fileName;

    emit('toast', {
      title: 'PDF 已生成',
      message: `《${props.node?.name}》已导出为 ${pages} 页 PDF，文件未上传至服务器。若未自动下载，请点击页面上的「另存为 PDF」。`,
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
  const text = renderedContent.value;
  if (!text) {
    emit('toast', { title: '暂无可复制内容', message: '请先填写要素生成文书。', type: 'INFO' });
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

.sop-doc-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  margin-bottom: 3px;
}

.sop-doc-crumb-link {
  color: var(--text-secondary);
  cursor: pointer;
}

.sop-doc-crumb-link:hover {
  color: var(--accent);
}

.sop-doc-crumb-sep {
  color: var(--text-tertiary);
}

.sop-doc-crumb-current {
  color: var(--text-primary);
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

/* Creation entry: main writing column + right-side template panel */
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

/* Right-side template library */
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

/* Template picker */
.sop-doc-picker {
  flex-shrink: 0;
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
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
[data-theme="dark"] .sop-doc-empty-writer {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
}
</style>
