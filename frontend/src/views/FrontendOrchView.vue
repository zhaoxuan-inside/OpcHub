<template>
  <div class="view-panel active">
    <div class="glass-box fo-header-card">
      <div class="fo-header-row">
        <div>
          <div class="fo-title-row">
            <h1 class="page-title fo-title">前端页面编排 · 栅格布局工作台</h1>
            <span class="mono-tag fo-live-tag">LAYOUT STUDIO</span>
          </div>
          <p class="fo-desc">
            拖拽 / 缩放 / 撤销 / 三档预览。布局与组件清单实时读取自平台配置，保存后全平台生效。
          </p>
        </div>
        <div class="fo-toolbar">
          <button class="btn-liquid-outline fo-tool-btn" :disabled="isLoading" @click="loadLayout">重新读取</button>
          <button class="btn-liquid-outline fo-tool-btn" :disabled="!canUndo" @click="undo">撤销</button>
          <button class="btn-liquid-outline fo-tool-btn" :disabled="!canRedo" @click="redo">重做</button>
          <button class="btn-liquid-outline fo-tool-btn" @click="previewMode = !previewMode">
            {{ previewMode ? '退出预览' : '预览' }}
          </button>
          <button class="btn-liquid fo-tool-btn" :disabled="isSaving || widgets.length === 0" @click="saveLayout">
            {{ isSaving ? '保存中...' : '保存部署' }}
          </button>
        </div>
      </div>

      <div class="fo-meta-row">
        <span class="fo-meta">布局: <strong>{{ layoutName }}</strong></span>
        <span class="fo-meta">版本: <input v-model="layoutVersion" class="glass-input fo-version-input" /></span>
        <span class="fo-meta">栅格: {{ columns }} 列</span>
        <span class="fo-meta">组件: {{ widgets.length }}</span>
        <span v-if="saveMsg" class="fo-save-msg" :class="{ ok: saveOk }">{{ saveMsg }}</span>
        <span class="fo-preview-switch">
          <button
            v-for="bp in breakpoints"
            :key="bp.key"
            type="button"
            class="fo-bp-btn"
            :class="{ on: previewBreakpoint === bp.key }"
            @click="previewBreakpoint = bp.key"
          >{{ bp.label }}</button>
        </span>
      </div>

      <div class="fo-grid-workspace">
        <!-- Column 1: widget library -->
        <aside class="fo-col-lib">
          <div class="fo-col-head"><span>WIDGET LIBRARY</span></div>
          <div class="fo-lib-note">拖入画布，或点击加入：</div>
          <button
            v-for="t in widgetTypes"
            :key="t.type"
            type="button"
            class="sitemap-card fo-lib-card"
            draggable="true"
            @dragstart="onLibraryDragStart($event, t.type)"
            @click="addWidget(t.type)"
          >
            <span class="fo-lib-head">
              <span class="fo-lib-name">{{ t.label }}</span>
              <span class="mono-tag fo-lib-tag">{{ t.defaultSpan }} 列</span>
            </span>
            <span class="fo-lib-desc">{{ t.desc }}</span>
          </button>
        </aside>

        <!-- Column 2: canvas -->
        <section class="fo-canvas-wrap">
          <div class="fo-canvas-head">
            <span class="fo-canvas-title">
              当前编排 · {{ widgets.length }} 个组件 · 预览 {{ currentBreakpoint.label }}
            </span>
            <span v-if="previewMode" class="fo-preview-tag">PREVIEW</span>
          </div>

          <div
            class="fo-device-frame"
            :class="{ 'is-preview': previewMode }"
            :style="{ maxWidth: currentBreakpoint.width }"
            @dragover.prevent
            @drop="onCanvasDrop"
          >
            <GridLayout
              v-model:layout="layout"
              :col-num="columns"
              :row-height="28"
              :margin="[colGap, rowGap]"
              :is-draggable="!previewMode"
              :is-resizable="!previewMode"
              :vertical-compact="true"
              :use-css-transforms="true"
              :auto-size="true"
              :prevent-collision="false"
              @layout-updated="onLayoutUpdated"
            >
              <GridItem
                v-for="item in layout"
                :key="item.i"
                :i="item.i"
                :x="item.x"
                :y="item.y"
                :w="item.w"
                :h="item.h"
                :min-w="2"
                :min-h="2"
                drag-allow-from=".fo-widget-head"
                drag-ignore-from=".fo-widget-del, .fo-widget-action"
              >
                <div
                  class="fo-widget"
                  :class="{ selected: selectedWidgetId === item.i }"
                  @click="selectedWidgetId = String(item.i)"
                >
                  <div class="fo-widget-head">
                    <span class="mono-tag fo-widget-type">{{ typeLabel(widgetFor(item.i)?.type) }}</span>
                    <span class="fo-widget-head-right">
                      <span class="fo-widget-span">{{ item.w }} 列</span>
                      <button
                        v-if="!previewMode"
                        class="fo-widget-del"
                        title="移除组件"
                        @click.stop="removeWidget(item.i)"
                      >×</button>
                    </span>
                  </div>
                  <div class="fo-widget-body">
                    <div class="fo-widget-title">{{ widgetFor(item.i)?.title || '未命名组件' }}</div>
                    <div class="fo-widget-value">{{ widgetFor(item.i)?.value || '（数值由业务数据绑定）' }}</div>
                  </div>
                  <div v-if="widgetFor(item.i)?.type === 'chart'" class="fo-widget-chart" aria-hidden="true">
                    <span v-for="n in 7" :key="n" :style="{ height: `${28 + ((n * 13) % 52)}%` }"></span>
                  </div>
                  <div v-else-if="widgetFor(item.i)?.type === 'stat'" class="fo-widget-stat" aria-hidden="true">
                    {{ widgetFor(item.i)?.value || '0' }}
                  </div>
                  <div v-if="previewMode" class="fo-widget-resize-hint">拖动标题栏移动 · 右下角缩放</div>
                </div>
              </GridItem>
            </GridLayout>

            <div v-if="widgets.length === 0" class="fo-empty">
              暂无组件。从左侧拖入或点击组件加入画布。
            </div>
          </div>
          <p class="fo-canvas-tip">
            {{ previewMode ? '预览模式下布局只读。' : '拖动组件标题栏移动，拖动右下角缩放；删除后可用顶部「撤销」恢复。' }}
          </p>
        </section>

        <!-- Column 3: property panel -->
        <aside class="fo-col-prop">
          <div class="fo-col-head"><span>WIDGET INSPECTOR</span></div>
          <template v-if="selectedWidget">
            <div class="fo-prop-card">
              <div class="fo-prop-label">组件标识</div>
              <div class="fo-prop-value mono">{{ selectedWidget.id }}</div>
            </div>
            <div class="fo-prop-card">
              <div class="fo-prop-label">标题</div>
              <input v-model="selectedWidget.title" class="glass-input fo-prop-input" placeholder="组件展示标题" @input="markDirty" />
              <div class="fo-prop-label" style="margin-top: 8px;">展示数值 / 说明（选填）</div>
              <input v-model="selectedWidget.value" class="glass-input fo-prop-input" placeholder="由业务数据绑定，可留空" @input="markDirty" />
              <div class="fo-prop-label" style="margin-top: 8px;">占列宽（1-{{ columns }}）</div>
              <div class="fo-span-row">
                <input v-model.number="selectedWidget.span" type="number" min="1" :max="columns" class="glass-input fo-prop-input fo-span-input" @change="syncSpanFromInspector" />
                <span class="fo-span-presets">
                  <button
                    v-for="s in spanPresets"
                    :key="s"
                    class="btn-liquid-outline fo-span-preset"
                    :class="{ on: clampSpan(selectedWidget.span) === s }"
                    @click="setSelectedSpan(s)"
                  >{{ s }}列</button>
                </span>
              </div>
            </div>
            <button class="btn-liquid-outline fo-remove-btn" @click="removeWidget(selectedWidget.id)">移除此组件</button>
          </template>
          <div v-else class="fo-empty">点击画布中的组件编辑属性。</div>

          <div class="fo-prop-card">
            <div class="fo-prop-label">当前编排 JSON</div>
            <details class="fo-json">
              <summary>查看 grid_schema + widgets</summary>
              <pre>{{ layoutJson }}</pre>
            </details>
          </div>

          <div class="fo-prop-card">
            <div class="fo-prop-label">操作提示</div>
            <div class="fo-shortcuts">
              <span><kbd>拖动</kbd> 标题栏移动</span>
              <span><kbd>拖动</kbd> 右下角缩放</span>
              <span><kbd>⌘Z</kbd> 撤销</span>
              <span><kbd>Del</kbd> 删除选中</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { GridLayout, GridItem } from 'grid-layout-plus';
import { dispatchGateway } from '@/api/gateway';

const emit = defineEmits(['toast']);

// 组件类型库：低代码编辑器可放置的组件种类（编辑器素材，非业务数据）
const widgetTypes = [
  { type: 'stat', label: '统计指标卡', defaultSpan: 6, height: 3, desc: '展示单一核心指标数值' },
  { type: 'form', label: '业务表单', defaultSpan: 12, height: 6, desc: '业务填报与申报入口' },
  { type: 'chart', label: '图表', defaultSpan: 12, height: 6, desc: '趋势图 / 对比图区域' },
  { type: 'table', label: '数据列表', defaultSpan: 12, height: 6, desc: '列表型数据展示' },
  { type: 'list', label: '动态流', defaultSpan: 8, height: 5, desc: '公告 / 动态信息流' },
  { type: 'banner', label: '横幅', defaultSpan: 24, height: 3, desc: '通栏横幅与公告位' },
];

const BREAKPOINTS = [
  { key: 'desktop', label: '桌面', width: '100%' },
  { key: 'tablet', label: '平板', width: '820px' },
  { key: 'mobile', label: '手机', width: '420px' },
];

const DEFAULT_LAYOUT = {
  layout_name: 'main_console_layout',
  version: 'v1.0.1',
  grid_schema: { columns: 24, row_gap: 16, col_gap: 16 },
  widgets: [],
};

const isLoading = ref(false);
const isSaving = ref(false);
const layoutName = ref(DEFAULT_LAYOUT.layout_name);
const layoutVersion = ref(DEFAULT_LAYOUT.version);
const gridSchema = ref({ ...DEFAULT_LAYOUT.grid_schema });
const widgets = ref([]);
const layout = ref([]);
const selectedWidgetId = ref('');
const saveMsg = ref('');
const saveOk = ref(false);
const previewMode = ref(false);
const previewBreakpoint = ref('desktop');
const draggingType = ref('');
const history = ref([]);
const redoStack = ref([]);
const dirty = ref(false);

const columns = computed(() => Number(gridSchema.value.columns) || 24);
const rowGap = computed(() => Number(gridSchema.value.row_gap) || 16);
const colGap = computed(() => Number(gridSchema.value.col_gap) || 16);
const selectedWidget = computed(() => widgets.value.find((w) => w.id === selectedWidgetId.value) || null);
const spanPresets = computed(() => [6, 8, 12, 24].filter((s) => s <= columns.value));
const breakpoints = BREAKPOINTS;
const currentBreakpoint = computed(() => BREAKPOINTS.find((b) => b.key === previewBreakpoint.value) || BREAKPOINTS[0]);
const canUndo = computed(() => history.value.length > 0);
const canRedo = computed(() => redoStack.value.length > 0);

const layoutJson = computed(() =>
  JSON.stringify({
    grid_schema: { columns: columns.value, row_gap: rowGap.value, col_gap: colGap.value },
    widgets: widgets.value.map((w) => ({ id: w.id, type: w.type, span: w.span, title: w.title, value: w.value })),
    positions: layout.value.map(({ i, x, y, w, h }) => ({ id: i, x, y, w, h })),
  }, null, 2)
);

function clampSpan(span) {
  const n = Number(span) || 6;
  return Math.max(1, Math.min(n, columns.value));
}

function typeLabel(type) {
  return widgetTypes.find((t) => t.type === type)?.label || type;
}

function typeHeight(type) {
  return widgetTypes.find((t) => t.type === type)?.height || 4;
}

function uniqueWidgetId(type) {
  let id = `w_${type}_${Date.now().toString(36)}`;
  while (widgets.value.some((w) => w.id === id)) id += '_';
  return id;
}

function widgetFor(id) {
  return widgets.value.find((w) => String(w.id) === String(id));
}

/* ------------------------------------------------------------------ */
/* Layout <-> widgets                                                  */
/* ------------------------------------------------------------------ */

function snapshots() {
  return JSON.parse(JSON.stringify({
    widgets: widgets.value,
    layout: layout.value,
    version: layoutVersion.value,
  }));
}

function pushHistory() {
  history.value.push(snapshots());
  if (history.value.length > 50) history.value.shift();
  redoStack.value = [];
  markDirty();
}

function restore(snap) {
  widgets.value = JSON.parse(JSON.stringify(snap.widgets));
  layout.value = JSON.parse(JSON.stringify(snap.layout));
  layoutVersion.value = snap.version;
  dirty.value = true;
}

function undo() {
  if (!history.value.length) return;
  redoStack.value.push(snapshots());
  restore(history.value.pop());
}

function redo() {
  if (!redoStack.value.length) return;
  history.value.push(snapshots());
  restore(redoStack.value.pop());
}

function markDirty() {
  dirty.value = true;
  saveMsg.value = '';
}

function rebuildLayoutFromWidgets() {
  let cursorX = 0;
  let cursorY = 0;
  let rowHeight = 0;
  const next = [];
  for (const widget of widgets.value) {
    const w = clampSpan(widget.span);
    const h = typeHeight(widget.type);
    if (cursorX + w > columns.value) {
      cursorX = 0;
      cursorY += rowHeight;
      rowHeight = 0;
    }
    next.push({ i: String(widget.id), x: cursorX, y: cursorY, w, h });
    cursorX += w;
    rowHeight = Math.max(rowHeight, h);
  }
  layout.value = next;
}

function onLayoutUpdated(nextLayout) {
  if (!Array.isArray(nextLayout) || !nextLayout.length) return;
  let changed = false;
  for (const item of nextLayout) {
    const widget = widgetFor(item.i);
    if (widget && Number(widget.span) !== Number(item.w)) {
      widget.span = Number(item.w);
      changed = true;
    }
  }

  // Grid drag reorders visually; persist that order in the widgets array too.
  const ordered = [...nextLayout]
    .sort((a, b) => (a.y - b.y) || (a.x - b.x))
    .map((item) => widgetFor(item.i))
    .filter(Boolean);
  if (ordered.length === widgets.value.length) {
    const ids = ordered.map((w) => w.id).join('|');
    if (ids !== widgets.value.map((w) => w.id).join('|')) {
      widgets.value = ordered;
      changed = true;
    }
  }

  if (changed) markDirty();
}

/* ------------------------------------------------------------------ */
/* Add / remove / resize                                               */
/* ------------------------------------------------------------------ */

function addWidget(type, dropPosition = null) {
  const t = widgetTypes.find((x) => x.type === type);
  if (!t) return;
  pushHistory();
  const widget = {
    id: uniqueWidgetId(type),
    type,
    span: t.defaultSpan,
    title: t.label,
    value: '',
  };
  widgets.value.push(widget);
  selectedWidgetId.value = widget.id;

  if (dropPosition) {
    const h = typeHeight(type);
    layout.value.push({
      i: String(widget.id),
      x: Math.max(0, Math.min(columns.value - clampSpan(t.defaultSpan), dropPosition.x)),
      y: Math.max(0, dropPosition.y),
      w: clampSpan(t.defaultSpan),
      h,
    });
  } else {
    rebuildLayoutFromWidgets();
  }
  nextTick(() => {
    selectedWidgetId.value = widget.id;
  });
}

function removeWidget(id) {
  pushHistory();
  widgets.value = widgets.value.filter((w) => String(w.id) !== String(id));
  layout.value = layout.value.filter((item) => String(item.i) !== String(id));
  if (String(selectedWidgetId.value) === String(id)) selectedWidgetId.value = '';
}

function setSelectedSpan(span) {
  if (!selectedWidget.value) return;
  pushHistory();
  selectedWidget.value.span = clampSpan(span);
  const item = layout.value.find((entry) => String(entry.i) === String(selectedWidget.value.id));
  if (item) item.w = selectedWidget.value.span;
}

function syncSpanFromInspector() {
  if (!selectedWidget.value) return;
  selectedWidget.value.span = clampSpan(selectedWidget.value.span);
  const item = layout.value.find((entry) => String(entry.i) === String(selectedWidget.value.id));
  if (item) item.w = selectedWidget.value.span;
  markDirty();
}

function onLibraryDragStart(event, type) {
  draggingType.value = type;
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData('text/plain', type);
  }
}

function onCanvasDrop(event) {
  event.preventDefault();
  const type = event.dataTransfer?.getData('text/plain') || draggingType.value;
  if (!type) return;
  // Approximate grid position from pointer; vertical compact will settle it.
  const rect = event.currentTarget.getBoundingClientRect();
  const cellWidth = rect.width / columns.value;
  const x = Math.floor((event.clientX - rect.left) / cellWidth);
  const y = Math.max(0, Math.floor((event.clientY - rect.top) / 48));
  addWidget(type, { x, y });
  draggingType.value = '';
}

/* ------------------------------------------------------------------ */
/* Load / save                                                         */
/* ------------------------------------------------------------------ */

async function loadLayout() {
  isLoading.value = true;
  saveMsg.value = '';
  try {
    const res = await dispatchGateway('frontend.layouts.get', { layout_name: layoutName.value }, { silent: true });
    if (res.ok && res.data) {
      layoutVersion.value = res.data.version || 'v1.0.0';
      gridSchema.value = res.data.grid_schema || { ...DEFAULT_LAYOUT.grid_schema };
      widgets.value = Array.isArray(res.data.widgets) ? JSON.parse(JSON.stringify(res.data.widgets)) : [];
      selectedWidgetId.value = '';
      history.value = [];
      redoStack.value = [];
      dirty.value = false;
      rebuildLayoutFromWidgets();
      emit('toast', { title: '布局已读取', message: `已载入 ${layoutName.value} @ ${res.data.version}（${widgets.value.length} 个组件）。`, type: 'SUCCESS' });
    } else {
      emit('toast', { title: '读取失败', message: res.error || '布局配置暂不可用。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '读取异常', message: '布局服务暂时不可用。', type: 'ERROR' });
  } finally {
    isLoading.value = false;
  }
}

function bumpVersion(v) {
  const m = String(v).match(/^v(\d+)\.(\d+)\.(\d+)$/);
  if (!m) return 'v1.0.1';
  return `v${m[1]}.${m[2]}.${Number(m[3]) + 1}`;
}

async function saveLayout() {
  if (isSaving.value || widgets.value.length === 0) return;
  isSaving.value = true;
  saveMsg.value = '';
  const version = layoutVersion.value.trim() || bumpVersion(layoutVersion.value);
  try {
    const res = await dispatchGateway('frontend.layouts.save', {
      layout_name: layoutName.value,
      version,
      grid_schema: {
        columns: columns.value,
        row_gap: rowGap.value,
        col_gap: colGap.value,
      },
      widgets: widgets.value.map((w) => ({
        id: w.id,
        type: w.type,
        span: clampSpan(w.span),
        title: String(w.title || '').slice(0, 60),
        ...(w.value ? { value: String(w.value).slice(0, 120) } : {}),
      })),
    });
    if (res.ok && res.data) {
      layoutVersion.value = res.data.version;
      saveMsg.value = `已保存部署：${layoutName.value}@${res.data.version}`;
      saveOk.value = true;
      dirty.value = false;
      history.value = [];
      redoStack.value = [];
      emit('toast', { title: '布局已保存', message: `前端布局 ${version} 已保存并生效（${res.data.widgets.length} 个组件）。`, type: 'SUCCESS' });
    } else {
      saveMsg.value = res.error || '保存失败';
      saveOk.value = false;
      emit('toast', { title: '保存失败', message: res.error || '请检查组件配置后重试。', type: 'ERROR' });
    }
  } catch (e) {
    saveMsg.value = '保存异常';
    saveOk.value = false;
    emit('toast', { title: '保存异常', message: '布局服务暂时不可用。', type: 'ERROR' });
  } finally {
    isSaving.value = false;
  }
}

function onGlobalKeydown(event) {
  const target = event.target;
  const editing = target && (
    ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
    || target.isContentEditable
  );
  if (editing) return;
  const key = String(event.key || '').toLowerCase();
  if ((event.metaKey || event.ctrlKey) && key === 'z') {
    event.preventDefault();
    if (event.shiftKey) redo();
    else undo();
  }
  if (event.key === 'Delete' && selectedWidgetId.value && !previewMode.value) {
    removeWidget(selectedWidgetId.value);
  }
}

onMounted(() => {
  loadLayout();
  window.addEventListener('keydown', onGlobalKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown);
});

watch(widgets, () => {
  if (!widgets.value.length) layout.value = [];
}, { deep: true });
</script>

<style scoped>
.fo-header-card { padding: 24px 28px 20px; }
.fo-header-row { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
.fo-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.fo-title { font-size: 24px; margin: 0; }
.fo-live-tag { background: var(--accent-glass); color: var(--accent); }
.fo-desc { font-size: 13px; color: var(--text-secondary); max-width: 620px; }
.fo-toolbar { display: flex; gap: 6px; flex-wrap: wrap; }
.fo-tool-btn { padding: 7px 13px; font-size: 12px; }
.fo-tool-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.fo-meta-row { display: flex; align-items: center; gap: 12px; flex-wrap: nowrap; overflow-x: auto; margin-top: 14px; padding: 9px 14px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); font-size: 12px; color: var(--text-secondary); }
.fo-meta strong { color: var(--text-primary); font-family: var(--font-mono); }
.fo-version-input { width: 90px; padding: 3px 8px; font-size: 11.5px; font-family: var(--font-mono); }
.fo-save-msg { margin-left: auto; color: var(--status-danger); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.fo-save-msg.ok { color: var(--status-success); }
.fo-preview-switch { display: flex; gap: 2px; margin-left: auto; flex-shrink: 0; }
.fo-bp-btn { border: 1px solid var(--glass-border-subtle); background: var(--glass-surface); color: var(--text-tertiary); border-radius: 999px; padding: 3px 9px; font-size: 10.5px; cursor: pointer; }
.fo-bp-btn.on { color: var(--accent); background: var(--accent-glass); border-color: rgba(0, 113, 227, 0.24); }

.fo-grid-workspace { display: grid; grid-template-columns: 220px minmax(0, 1fr) 250px; gap: 14px; margin-top: 16px; align-items: start; }
@media (max-width: 1100px) { .fo-grid-workspace { grid-template-columns: 1fr; } }

.fo-col-lib, .fo-col-prop { background: var(--glass-surface-subtle); padding: 12px; border-radius: var(--radius-md); border: 1px solid var(--glass-border-subtle); display: flex; flex-direction: column; gap: 8px; }
.fo-col-head { font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary); letter-spacing: 0.08em; }
.fo-lib-note { font-size: 11.5px; color: var(--text-secondary); }
.fo-lib-card { padding: 8px 10px; cursor: grab; text-align: left; display: flex; flex-direction: column; gap: 2px; width: 100%; }
.fo-lib-card:active { cursor: grabbing; }
.fo-lib-card:hover { border-color: var(--accent); }
.fo-lib-head { display: flex; justify-content: space-between; align-items: center; }
.fo-lib-name { font-weight: 600; font-size: 12.5px; }
.fo-lib-tag { font-size: 9.5px; padding: 1px 4px; }
.fo-lib-desc { font-size: 10.5px; color: var(--text-tertiary); margin-top: 2px; }

.fo-canvas-wrap { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.fo-canvas-head { display: flex; justify-content: space-between; align-items: center; }
.fo-canvas-title { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.fo-preview-tag { font-family: var(--font-mono); font-size: 9px; color: var(--status-success); background: var(--status-success-soft); padding: 2px 6px; border-radius: 999px; }

.fo-device-frame {
  width: 100%;
  margin: 0 auto;
  min-height: 380px;
  background: var(--glass-surface-subtle);
  border: 1px dashed var(--glass-border);
  border-radius: var(--radius-md);
  padding: 12px;
  transition: max-width 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  background-image: repeating-linear-gradient(90deg, transparent, transparent calc(100% / 24 - 1px), var(--glass-border-subtle) calc(100% / 24 - 1px), var(--glass-border-subtle) calc(100% / 24));
}
.fo-device-frame.is-preview { background-image: none; border-style: solid; }

.fo-canvas-tip { font-size: 10.5px; color: var(--text-tertiary); }

.fo-widget {
  height: 100%;
  box-sizing: border-box;
  position: relative;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.96));
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.fo-widget:hover { border-color: var(--accent); }
.fo-widget.selected { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glass, rgba(0, 113, 227, 0.14)); }
.fo-widget-head { display: flex; justify-content: space-between; align-items: center; cursor: grab; }
.fo-widget-head:active { cursor: grabbing; }
.fo-widget-head-right { display: flex; align-items: center; gap: 6px; }
.fo-widget-type { font-size: 9px; padding: 1px 5px; }
.fo-widget-span { font-size: 9.5px; font-family: var(--font-mono); color: var(--accent); }
.fo-widget-del { width: 18px; height: 18px; border-radius: 50%; border: 1px solid var(--status-danger); background: var(--glass-surface); color: var(--status-danger); font-size: 11px; line-height: 1; cursor: pointer; }
.fo-widget-title { font-weight: 600; font-size: 13px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fo-widget-value { font-size: 10.5px; color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fo-widget-body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 2px; }
.fo-widget-chart { flex: 1; min-height: 24px; display: flex; align-items: flex-end; gap: 3px; padding-top: 4px; }
.fo-widget-chart span { flex: 1; border-radius: 2px 2px 0 0; background: var(--accent-glass); }
.fo-widget-stat { font-size: 22px; font-weight: 700; letter-spacing: -0.03em; color: var(--accent); }
.fo-widget-resize-hint { position: absolute; bottom: 2px; right: 5px; font-size: 8.5px; color: var(--text-tertiary); }

.fo-empty { padding: 48px 12px; text-align: center; color: var(--text-tertiary); font-size: 12.5px; }
.fo-col-prop .fo-empty { padding: 20px 8px; }

.fo-prop-card { background: var(--glass-surface); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
.fo-prop-label { font-size: 11px; color: var(--text-tertiary); }
.fo-prop-value { font-weight: 600; font-size: 13px; word-break: break-all; }
.fo-prop-value.mono { font-family: var(--font-mono); font-size: 11px; }
.fo-prop-input { font-size: 12.5px; padding: 6px 10px; }
.fo-span-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fo-span-input { width: 70px; }
.fo-span-presets { display: flex; gap: 4px; flex-wrap: wrap; }
.fo-span-preset { padding: 3px 8px; font-size: 10.5px; }
.fo-span-preset.on { background: var(--accent); color: #fff; border-color: var(--accent); }
.fo-remove-btn { font-size: 11.5px; padding: 6px 10px; color: var(--status-danger); border-color: var(--status-danger-soft); }
.fo-json summary { cursor: pointer; font-size: 11.5px; color: var(--text-tertiary); }
.fo-json pre { font-size: 10.5px; font-family: var(--font-mono); max-height: 220px; overflow: auto; background: var(--glass-surface-subtle); border-radius: 6px; padding: 8px; margin-top: 6px; }
.fo-shortcuts { display: flex; flex-direction: column; gap: 4px; font-size: 10.5px; color: var(--text-tertiary); }
.fo-shortcuts kbd { font-family: var(--font-mono); font-size: 9px; padding: 1px 5px; border-radius: 4px; border: 1px solid var(--glass-border-subtle); background: var(--glass-surface); }
</style>
