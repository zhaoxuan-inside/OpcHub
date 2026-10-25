<template>
  <div class="sgpanel">
    <!-- 工具栏 -->
    <div class="sgpanel-toolbar">
      <button class="btn-liquid sg-btn" @click="openCreate">新建子图</button>
      <button class="btn-liquid-outline sg-btn" :disabled="isLoading" @click="loadSubgraphs">刷新目录</button>
      <span class="mono-tag sg-count">{{ subgraphs.length }} 个子图</span>
    </div>

    <!-- 新建子图表单 -->
    <div v-if="showCreate" class="glass-box sg-create">
      <div class="sg-create-title">新建子图（算子编排子流水线 · DRAFT 起步）</div>
      <div class="sg-create-grid">
        <label class="sg-field">
          <span>子图编码 *</span>
          <input v-model="createForm.code" class="glass-input" placeholder="SG_MY_GUARD" />
        </label>
        <label class="sg-field">
          <span>显示名</span>
          <input v-model="createForm.display_name" class="glass-input" placeholder="我的校验子图" />
        </label>
      </div>
      <label class="sg-field">
        <span>描述</span>
        <input v-model="createForm.description" class="glass-input" placeholder="子图用途说明" />
      </label>
      <div class="sg-create-actions">
        <button class="btn-liquid sg-btn" :disabled="!createForm.code.trim() || isCreating" @click="submitCreate">
          {{ isCreating ? '创建中...' : '锁定并创建' }}
        </button>
        <button class="btn-liquid-outline sg-btn" @click="showCreate = false">取消</button>
        <span class="sg-hint">创建后将自动锁定该子图，随后即可编排算子节点。</span>
      </div>
    </div>

    <!-- 子图列表：真表格布局，列宽随内容自适应 -->
    <div class="sg-list">
      <table class="cat-table">
        <thead>
          <tr>
            <th class="col-name">子图</th>
            <th>当前版本</th>
            <th>版本</th>
            <th>节点</th>
            <th>锁定状态</th>
            <th>更新时间</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="sg in subgraphs"
            :key="sg.code"
            :class="{ selected: sg.code === selectedCode }"
            @click="selectSubgraph(sg)"
          >
            <td class="col-name" :title="sg.description">{{ sg.display_name || sg.code }}<em class="sg-code">{{ sg.code }}</em></td>
            <td><span class="mono-tag">{{ sg.current_version || '未发布' }}</span></td>
            <td>{{ sg.versions?.length || 0 }}</td>
            <td>{{ latestGraphOf(sg)?.nodes?.length || 0 }}</td>
            <td>
              <span v-if="sg.lock_status" class="mono-tag tag-locked" :title="`锁定人：${sg.lock_status.holder_name}（${sg.lock_status.holder_id}）`">
                🔒 {{ sg.lock_status.holder_name }}
              </span>
              <span v-else class="mono-tag tag-free">空闲</span>
            </td>
            <td class="sg-time">{{ (sg.updated_at || '').slice(0, 16).replace('T', ' ') }}</td>
            <td class="col-actions">
              <button class="btn-liquid-outline sg-mini" @click.stop="selectSubgraph(sg)">编排</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="subgraphs.length === 0 && !isLoading" class="sg-empty">
        暂无子图。子图由算子编排而成，可作为整体被场景引用。
      </div>
    </div>

    <!-- 选中子图：锁 + 版本 + 图编辑 -->
    <div v-if="detail" class="sg-detail glass-box">
      <div class="sg-detail-head">
        <div>
          <span class="sg-detail-title">{{ detail.display_name || detail.code }}</span>
          <span class="mono-tag" style="margin-left: 8px;">{{ detail.code }}</span>
          <span class="mono-tag tag-published" style="margin-left: 4px;">当前 {{ detail.current_version || '未发布' }}</span>
        </div>
        <button class="btn-liquid-outline sg-mini" @click="closeDetail">关闭</button>
      </div>

      <AssetLockBanner
        :held-by-me="heldByMe"
        :held-by-other="heldByOther"
        :holder-label="holderLabel"
        :remaining-seconds="remainingSeconds"
        :busy="isBusy"
        @acquire="acquire(detail.code)"
        @release="release()"
      />

      <!-- 版本切换 + 发布 -->
      <div class="sg-verbar">
        <span class="sg-verlabel">版本：</span>
        <select v-model="selectedVersion" class="glass-select sg-versel" @change="loadVersionGraph">
          <option v-for="v in detail.versions" :key="v.version" :value="v.version">
            {{ v.version }} · {{ verStatusText(v.status) }}
          </option>
        </select>
        <button v-if="editingDraft" class="btn-liquid sg-btn" :disabled="isSaving" @click="saveDraft">{{ isSaving ? '保存中...' : '保存草稿' }}</button>
        <button v-if="editingDraft" class="btn-liquid sg-btn" :disabled="isPublishing" @click="publishDraft">{{ isPublishing ? '发布中...' : '发布此草稿' }}</button>
        <button v-if="heldByMe" class="btn-liquid-outline sg-btn" :disabled="isSaving" @click="deriveNewDraft">基于最新新建草稿</button>
        <span v-if="versionNote" class="sg-note" :class="{ ok: noteOk }">{{ versionNote }}</span>
      </div>

      <!-- 图编辑器：编排算子 -->
      <GraphEditor
        :graph="draftGraph"
        :editable="editingDraft && heldByMe"
        :allow-subgraphs="false"
        :palette="operatorPalette"
        @toast="(t) => emit('toast', t)"
      />
      <p class="sg-tip">发布前需确保引用的算子均已成可用版本，且编排为一条完整的单向链路；已发布版本不可再修改。</p>
    </div>
  </div>
</template>

<script setup>
/**
 * 子图管理面板：展示 / 创建 / 编排算子 / 版本管理 / 发布。
 */
import { computed, onMounted, ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import { catalogWrite, useAssetLock } from '@/components/orchestration/useAssetLock';
import AssetLockBanner from '@/components/orchestration/AssetLockBanner.vue';
import GraphEditor from '@/components/orchestration/GraphEditor.vue';

const props = defineProps({
  userSession: { type: Object, default: null },
});
const emit = defineEmits(['toast', 'count']);

const subgraphs = ref([]);
const operators = ref([]);
const isLoading = ref(false);
const isCreating = ref(false);
const isSaving = ref(false);
const isPublishing = ref(false);

const showCreate = ref(false);
const createForm = ref({ code: '', display_name: '', description: '' });

const selectedCode = ref('');
const detail = ref(null);
const selectedVersion = ref('');
const versionNote = ref('');
const noteOk = ref(false);

const draftGraph = ref({ entry_node: '', exit_node: '', nodes: [], edges: [] });

const { heldByMe, heldByOther, holderLabel, remainingSeconds, isBusy, attach, acquire, release } = useAssetLock(
  props.userSession,
  'subgraph',
  emit,
);

const selectedVersionRow = computed(() => detail.value?.versions?.find((v) => v.version === selectedVersion.value) || null);
const editingDraft = computed(() => selectedVersionRow.value?.status === 'DRAFT');

const operatorPalette = computed(() =>
  operators.value
    .filter((o) => o.source === 'builtin' || o.current_version)
    .map((o) => ({
      kind: 'OPERATOR',
      key: o.name,
      label: o.name,
      domain: o.domain,
      description: o.source === 'builtin' ? o.description : `${o.description || '自建算子'} · ${o.current_version}`,
      tag: o.source === 'builtin' ? '预置' : '自建',
    })),
);

function latestGraphOf(sg) {
  const versions = sg.versions || [];
  return versions[versions.length - 1]?.graph || null;
}

function verStatusText(status) {
  return { DRAFT: '草稿', PUBLISHED: '已发布', SUPERSEDED: '已取代' }[status] || status;
}

async function loadSubgraphs() {
  isLoading.value = true;
  try {
    const res = await dispatchGateway('orchestration.catalog.subgraphs', {}, { silent: true });
    subgraphs.value = res.ok && Array.isArray(res.data?.subgraphs) ? res.data.subgraphs : [];
    emit('count', 'subgraphs', subgraphs.value.length);
  } finally {
    isLoading.value = false;
  }
}

async function loadOperators() {
  const res = await dispatchGateway('orchestration.catalog.operators', {}, { silent: true });
  operators.value = res.ok && Array.isArray(res.data?.operators) ? res.data.operators : [];
}

function openCreate() {
  showCreate.value = !showCreate.value;
  if (showCreate.value) createForm.value = { code: '', display_name: '', description: '' };
}

async function submitCreate() {
  const code = createForm.value.code.trim();
  if (!code || isCreating.value) return;
  isCreating.value = true;
  try {
    const locked = await acquire(code);
    if (!locked) return;
    const res = await catalogWrite('subgraphs.create', { ...createForm.value, code });
    if (res.ok) {
      emit('toast', { title: '子图已创建', message: `${code} 已进入 v1.0.0 草稿，开始编排算子。`, type: 'SUCCESS' });
      showCreate.value = false;
      await loadSubgraphs();
      await selectSubgraph({ code, lock_status: null });
    } else {
      emit('toast', { title: '创建失败', message: res.error || '请检查子图编码。', type: 'ERROR' });
    }
  } finally {
    isCreating.value = false;
  }
}

async function selectSubgraph(row) {
  selectedCode.value = row.code;
  // 刷新算子清单（算子可能在算子面板刚发布），保证编排面板与目录同步
  loadOperators();
  const res = await dispatchGateway('orchestration.catalog.subgraph', { code: row.code }, { silent: true });
  if (!res.ok) {
    emit('toast', { title: '加载子图失败', message: res.error || '请稍后重试。', type: 'ERROR' });
    return;
  }
  detail.value = res.data;
  attach(row.code, res.data.lock_status || row.lock_status || null);
  const versions = detail.value.versions || [];
  const draft = versions.find((v) => v.status === 'DRAFT');
  selectedVersion.value = (draft || versions[versions.length - 1] || {}).version || '';
  loadVersionGraph();
}

function loadVersionGraph() {
  const row = selectedVersionRow.value;
  versionNote.value = '';
  if (!row) {
    draftGraph.value = { entry_node: '', exit_node: '', nodes: [], edges: [] };
    return;
  }
  const g = row.graph || {};
  draftGraph.value = {
    entry_node: g.entry_node || '',
    exit_node: g.exit_node || '',
    nodes: JSON.parse(JSON.stringify(g.nodes || [])),
    edges: JSON.parse(JSON.stringify(g.edges || [])),
  };
}

function closeDetail() {
  detail.value = null;
  selectedCode.value = '';
}

async function saveDraft() {
  if (!detail.value || !editingDraft.value || !heldByMe.value) return;
  isSaving.value = true;
  try {
    const res = await catalogWrite('subgraphs.version.save', {
      code: detail.value.code,
      version: selectedVersion.value,
      graph: draftGraph.value,
    });
    if (res.ok) {
      versionNote.value = `草稿 ${selectedVersion.value} 已保存`;
      noteOk.value = true;
      emit('toast', { title: '草稿已保存', message: `${detail.value.code}@${selectedVersion.value} 编排已保存。`, type: 'SUCCESS' });
      await loadSubgraphs();
    } else {
      versionNote.value = res.error || '保存失败';
      noteOk.value = false;
    }
  } finally {
    isSaving.value = false;
  }
}

async function deriveNewDraft() {
  if (!detail.value || !heldByMe.value) return;
  const versions = detail.value.versions || [];
  const latest = versions[versions.length - 1];
  let next = 'v1.0.0';
  const m = latest?.version?.match(/^v(\d+)\.(\d+)\.(\d+)$/);
  if (m) next = `v${m[1]}.${m[2]}.${Number(m[3]) + 1}`;
  const res = await catalogWrite('subgraphs.version.save', {
    code: detail.value.code,
    version: next,
    changelog: `基于 ${latest?.version || '空'} 新建的草稿`,
    graph: latest?.graph || draftGraph.value,
  });
  if (res.ok) {
    emit('toast', { title: '新草稿已创建', message: `已创建 ${next} 草稿（继承上一版编排）。`, type: 'SUCCESS' });
    await loadSubgraphs();
    await selectSubgraph({ code: detail.value.code });
  } else {
    emit('toast', { title: '新建草稿失败', message: res.error || '请稍后重试。', type: 'ERROR' });
  }
}

async function publishDraft() {
  if (!detail.value || !editingDraft.value || !heldByMe.value) return;
  isPublishing.value = true;
  try {
    const res = await catalogWrite('subgraphs.publish', { code: detail.value.code, version: selectedVersion.value });
    if (res.ok) {
      versionNote.value = `版本 ${selectedVersion.value} 已发布`;
      noteOk.value = true;
      emit('toast', { title: '子图已发布', message: `${detail.value.code}@${selectedVersion.value} 已发布，可被场景编排引用。`, type: 'SUCCESS' });
      await loadSubgraphs();
      await selectSubgraph({ code: detail.value.code });
    } else {
      versionNote.value = res.error || '发布失败';
      noteOk.value = false;
      emit('toast', { title: '发布未通过', message: res.error || '请检查编排连线与算子引用。', type: 'ERROR' });
    }
  } finally {
    isPublishing.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadSubgraphs(), loadOperators()]);
});
</script>

<style scoped>
.sgpanel { display: flex; flex-direction: column; gap: 14px; }
.sgpanel-toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sg-btn { padding: 7px 16px; font-size: 12.5px; }
.sg-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.sg-count { margin-left: auto; }
.sg-mini { padding: 4px 10px; font-size: 11px; }

.sg-create { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.sg-create-title { font-weight: 600; font-size: 13.5px; }
.sg-create-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.sg-field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); }
.sg-create-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sg-hint { font-size: 11.5px; color: var(--text-tertiary); }

.sg-list { border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); overflow-x: auto; }
/* 真表格布局：列宽按内容自适应，超宽时容器内横向滚动 */
.cat-table { width: 100%; border-collapse: collapse; table-layout: auto; }
.cat-table th { text-align: left; font-size: 11px; font-weight: 500; color: var(--text-tertiary); padding: 9px 14px; white-space: nowrap; background: var(--glass-surface-subtle); }
.cat-table td { font-size: 12.5px; color: var(--text-secondary); padding: 9px 14px; white-space: nowrap; vertical-align: middle; }
.cat-table tbody tr:nth-child(2n) td { background: var(--glass-surface-subtle); }
.cat-table tbody tr:hover td { background: var(--accent-glass); cursor: pointer; }
.cat-table tbody tr.selected td { background: var(--accent-glass); box-shadow: inset 0 0 0 1px var(--accent); }
.cat-table td.col-name { font-weight: 600; white-space: normal; word-break: break-all; min-width: 140px; max-width: 320px; }
.cat-table .col-actions { text-align: right; white-space: nowrap; }
.sg-code { font-style: normal; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-tertiary); margin-left: 6px; }
.sg-time { color: var(--text-tertiary); font-size: 11px; }
.sg-empty { padding: 18px 12px; text-align: center; color: var(--text-tertiary); font-size: 12.5px; }

.sg-detail { padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
.sg-detail-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.sg-detail-title { font-size: 16px; font-weight: 700; }
.sg-verbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sg-verlabel { font-size: 12px; color: var(--text-tertiary); }
.sg-versel { padding: 4px 8px; font-size: 11.5px; border: 1px solid var(--glass-border-subtle); border-radius: 6px; background: transparent; }
.sg-note { font-size: 12px; color: var(--status-danger); }
.sg-note.ok { color: var(--status-success); }
.sg-tip { font-size: 11.5px; color: var(--text-tertiary); margin: 0; }

.tag-locked { background: var(--status-warning-soft); color: var(--status-warning); }
.tag-free { background: var(--status-success-soft); color: var(--status-success); }
.tag-published { background: var(--status-success-soft); color: var(--status-success); }
</style>
