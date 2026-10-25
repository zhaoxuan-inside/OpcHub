<template>
  <div class="view-panel active">
    <div class="glass-box fo-header-card">
      <div class="fo-header-row">
        <div>
          <div class="fo-title-row">
            <h1 class="page-title fo-title">前端页面编排 · 24 栅格布局工作台</h1>
            <span class="mono-tag fo-live-tag">LAYOUT STUDIO</span>
          </div>
          <p class="fo-desc">
            低代码页面布局编排：布局与组件清单实时读取自平台配置，支持添加/调整/删除组件并保存部署，保存后全平台生效。
          </p>
        </div>
        <div class="fo-toolbar">
          <button class="btn-liquid-outline fo-tool-btn" :disabled="isLoading" @click="loadLayout">重新读取</button>
          <button class="btn-liquid fo-tool-btn" :disabled="isSaving || widgets.length === 0" @click="saveLayout">
            {{ isSaving ? '保存中...' : '保存部署' }}
          </button>
        </div>
      </div>

      <div class="fo-meta-row">
        <span class="fo-meta">布局: <strong>{{ layoutName }}</strong></span>
        <span class="fo-meta">版本: <input v-model="layoutVersion" class="glass-input fo-version-input" /></span>
        <span class="fo-meta">栅格: {{ columns }} 列 · 间距 {{ colGap }}px</span>
        <span v-if="saveMsg" class="fo-save-msg" :class="{ ok: saveOk }">{{ saveMsg }}</span>
      </div>

      <div class="fo-grid-workspace">
        <!-- Column 1: widget library -->
        <div class="fo-col-lib">
          <div class="fo-col-head"><span>WIDGET LIBRARY</span></div>
          <div class="fo-lib-note">点击组件加入画布：</div>
          <div
            v-for="t in widgetTypes"
            :key="t.type"
            class="sitemap-card fo-lib-card"
            @click="addWidget(t.type)"
          >
            <div class="fo-lib-head">
              <span class="fo-lib-name">{{ t.label }}</span>
              <span class="mono-tag fo-lib-tag">{{ t.defaultSpan }} 列</span>
            </div>
            <div class="fo-lib-desc">{{ t.desc }}</div>
          </div>
        </div>

        <!-- Column 2: canvas -->
        <div class="fo-canvas-wrap">
          <div class="fo-canvas-head">
            <span class="fo-canvas-title">当前编排（{{ widgets.length }} 个组件 · 已占 {{ usedSpan }}/{{ columns }} 列每行自适应换行）</span>
          </div>
          <div class="fo-canvas" :style="{ gridTemplateColumns: `repeat(${columns}, 1fr)`, gap: `${rowGap}px ${colGap}px` }">
            <div
              v-for="w in widgets"
              :key="w.id"
              class="fo-widget"
              :class="{ selected: selectedWidgetId === w.id }"
              :style="{ gridColumn: `span ${clampSpan(w.span)}` }"
              @click="selectedWidgetId = w.id"
            >
              <div class="fo-widget-head">
                <span class="mono-tag fo-widget-type">{{ typeLabel(w.type) }}</span>
                <button class="fo-widget-del" title="移除组件" @click.stop="removeWidget(w.id)">×</button>
              </div>
              <div class="fo-widget-title">{{ w.title || '未命名组件' }}</div>
              <div class="fo-widget-value">{{ w.value || '（数值由业务数据绑定）' }}</div>
              <div class="fo-widget-span">{{ clampSpan(w.span) }} 列</div>
            </div>
            <div v-if="widgets.length === 0" class="fo-empty">暂无组件。从左侧组件库点击添加，或在下方属性面板配置。</div>
          </div>
        </div>

        <!-- Column 3: property panel -->
        <div class="fo-col-prop">
          <div class="fo-col-head"><span>WIDGET INSPECTOR</span></div>
          <template v-if="selectedWidget">
            <div class="fo-prop-card">
              <div class="fo-prop-label">组件标识</div>
              <div class="fo-prop-value mono">{{ selectedWidget.id }}</div>
            </div>
            <div class="fo-prop-card">
              <div class="fo-prop-label">标题</div>
              <input v-model="selectedWidget.title" class="glass-input fo-prop-input" placeholder="组件展示标题" />
              <div class="fo-prop-label" style="margin-top: 8px;">展示数值 / 说明（选填）</div>
              <input v-model="selectedWidget.value" class="glass-input fo-prop-input" placeholder="由业务数据绑定，可留空" />
              <div class="fo-prop-label" style="margin-top: 8px;">占列宽（1-{{ columns }}）</div>
              <div class="fo-span-row">
                <input v-model.number="selectedWidget.span" type="number" min="1" :max="columns" class="glass-input fo-prop-input fo-span-input" />
                <span class="fo-span-presets">
                  <button v-for="s in spanPresets" :key="s" class="btn-liquid-outline fo-span-preset" :class="{ on: clampSpan(selectedWidget.span) === s }" @click="selectedWidget.span = s">{{ s }}列</button>
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
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const emit = defineEmits(['toast']);

// 组件类型库：低代码编辑器可放置的组件种类（编辑器素材，非业务数据）
const widgetTypes = [
  { type: 'stat', label: '统计指标卡', defaultSpan: 6, desc: '展示单一核心指标数值' },
  { type: 'form', label: '业务表单', defaultSpan: 12, desc: '业务填报与申报入口' },
  { type: 'chart', label: '图表', defaultSpan: 12, desc: '趋势图 / 对比图区域' },
  { type: 'table', label: '数据列表', defaultSpan: 12, desc: '列表型数据展示' },
  { type: 'list', label: '动态流', defaultSpan: 8, desc: '公告 / 动态信息流' },
  { type: 'banner', label: '横幅', defaultSpan: 24, desc: '通栏横幅与公告位' },
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
const selectedWidgetId = ref('');
const saveMsg = ref('');
const saveOk = ref(false);

const columns = computed(() => Number(gridSchema.value.columns) || 24);
const rowGap = computed(() => Number(gridSchema.value.row_gap) || 16);
const colGap = computed(() => Number(gridSchema.value.col_gap) || 16);
const usedSpan = computed(() => widgets.value.reduce((s, w) => s + clampSpan(w.span), 0));
const selectedWidget = computed(() => widgets.value.find((w) => w.id === selectedWidgetId.value) || null);
const spanPresets = computed(() => [6, 8, 12, 24].filter((s) => s <= columns.value));

const layoutJson = computed(() =>
  JSON.stringify({ grid_schema: gridSchema.value, widgets: widgets.value }, null, 2)
);

function clampSpan(span) {
  const n = Number(span) || 6;
  return Math.max(1, Math.min(n, columns.value));
}

function typeLabel(type) {
  return widgetTypes.find((t) => t.type === type)?.label || type;
}

function uniqueWidgetId(type) {
  let i = widgets.value.length + 1;
  let id = `w_${type}_${Date.now().toString(36)}`;
  while (widgets.value.some((w) => w.id === id)) id += '_';
  void i;
  return id;
}

function addWidget(type) {
  const t = widgetTypes.find((x) => x.type === type);
  if (!t) return;
  const w = { id: uniqueWidgetId(type), type, span: t.defaultSpan, title: t.label, value: '' };
  widgets.value.push(w);
  selectedWidgetId.value = w.id;
  saveMsg.value = '';
}

function removeWidget(id) {
  widgets.value = widgets.value.filter((w) => w.id !== id);
  if (selectedWidgetId.value === id) selectedWidgetId.value = '';
  saveMsg.value = '';
}

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
      grid_schema: gridSchema.value,
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

onMounted(() => {
  loadLayout();
});
</script>

<style scoped>
.fo-header-card { padding: 24px 28px 20px; }
.fo-header-row { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
.fo-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.fo-title { font-size: 24px; margin: 0; }
.fo-live-tag { background: var(--accent-glass); color: var(--accent); }
.fo-desc { font-size: 13px; color: var(--text-secondary); max-width: 620px; }
.fo-toolbar { display: flex; gap: 8px; }
.fo-tool-btn { padding: 7px 16px; font-size: 12.5px; }
.fo-tool-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.fo-meta-row { display: flex; align-items: center; gap: 14px; flex-wrap: nowrap; overflow-x: auto; margin-top: 14px; padding: 9px 14px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); font-size: 12px; color: var(--text-secondary); }
.fo-meta strong { color: var(--text-primary); font-family: var(--font-mono); }
.fo-version-input { width: 90px; padding: 3px 8px; font-size: 11.5px; font-family: var(--font-mono); }
.fo-save-msg { margin-left: auto; color: var(--status-danger); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.fo-save-msg.ok { color: var(--status-success); }

.fo-grid-workspace { display: grid; grid-template-columns: 230px 1fr 260px; gap: 16px; margin-top: 16px; align-items: start; }
@media (max-width: 1100px) { .fo-grid-workspace { grid-template-columns: 1fr; } }

.fo-col-lib, .fo-col-prop { background: var(--glass-surface-subtle); padding: 12px; border-radius: var(--radius-md); border: 1px solid var(--glass-border-subtle); display: flex; flex-direction: column; gap: 8px; }
.fo-col-head { font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary); letter-spacing: 0.08em; }
.fo-lib-note { font-size: 11.5px; color: var(--text-secondary); }
.fo-lib-card { padding: 8px 10px; cursor: pointer; }
.fo-lib-card:hover { border-color: var(--accent); }
.fo-lib-head { display: flex; justify-content: space-between; align-items: center; }
.fo-lib-name { font-weight: 600; font-size: 12.5px; }
.fo-lib-tag { font-size: 9.5px; padding: 1px 4px; }
.fo-lib-desc { font-size: 10.5px; color: var(--text-tertiary); margin-top: 2px; }

.fo-canvas-wrap { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.fo-canvas-head { display: flex; justify-content: space-between; }
.fo-canvas-title { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.fo-canvas { display: grid; background: var(--glass-surface-subtle); border: 1px dashed var(--glass-border); border-radius: var(--radius-md); padding: 16px; min-height: 320px; background-image: repeating-linear-gradient(90deg, transparent, transparent calc(100% / 24 - 1px), var(--glass-border-subtle) calc(100% / 24 - 1px), var(--glass-border-subtle) calc(100% / 24)); }

.fo-widget { position: relative; background: var(--glass-surface); border: 1px solid var(--glass-border); border-radius: 10px; padding: 10px 12px; min-height: 92px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; transition: all 0.15s ease; }
.fo-widget:hover { border-color: var(--accent); }
.fo-widget.selected { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glass); }
.fo-widget-head { display: flex; justify-content: space-between; align-items: center; }
.fo-widget-type { font-size: 9px; padding: 1px 5px; }
.fo-widget-del { position: absolute; top: -8px; right: -8px; width: 18px; height: 18px; border-radius: 50%; border: 1px solid var(--status-danger); background: var(--glass-surface); color: var(--status-danger); font-size: 11px; line-height: 1; cursor: pointer; display: none; }
.fo-widget:hover .fo-widget-del { display: block; }
.fo-widget-title { font-weight: 600; font-size: 13px; color: var(--text-primary); }
.fo-widget-value { font-size: 11px; color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fo-widget-span { margin-top: auto; font-size: 10px; font-family: var(--font-mono); color: var(--accent); align-self: flex-end; }

.fo-empty { grid-column: 1 / -1; padding: 40px 12px; text-align: center; color: var(--text-tertiary); font-size: 12.5px; }
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
</style>
