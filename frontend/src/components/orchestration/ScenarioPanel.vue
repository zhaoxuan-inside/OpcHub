<template>
  <div class="scpanel">
    <!-- 工具栏 -->
    <div class="scpanel-toolbar">
      <button class="btn-liquid sc-btn" @click="openCreate">新建场景</button>
      <button class="btn-liquid-outline sc-btn" :disabled="isLoading" @click="loadScenarios">刷新目录</button>
      <span class="mono-tag sc-count">{{ scenarios.length }} 个场景</span>
    </div>

    <!-- 新建场景表单 -->
    <div v-if="showCreate" class="glass-box sc-create">
      <div class="sc-create-title">新建场景（算子与子图混合编排 · DRAFT 起步）</div>
      <div class="sc-create-grid">
        <label class="sc-field">
          <span>场景编码 *</span>
          <input v-model="createForm.code" class="glass-input" placeholder="OPC_MY_FLOW" />
        </label>
        <label class="sc-field">
          <span>显示名</span>
          <input v-model="createForm.display_name" class="glass-input" placeholder="我的业务流程" />
        </label>
      </div>
      <label class="sc-field">
        <span>描述</span>
        <input v-model="createForm.description" class="glass-input" placeholder="场景用途说明" />
      </label>
      <div class="sc-create-actions">
        <button class="btn-liquid sc-btn" :disabled="!createForm.code.trim() || isCreating" @click="submitCreate">
          {{ isCreating ? '创建中...' : '锁定并创建' }}
        </button>
        <button class="btn-liquid-outline sc-btn" @click="showCreate = false">取消</button>
        <span class="sc-hint">创建后将自动锁定该场景；发布后即可执行。</span>
      </div>
    </div>

    <!-- 场景列表：管理场景 + 系统预置流程；真表格布局，列宽随内容自适应 -->
    <div class="sc-list">
      <table class="cat-table">
        <thead>
          <tr>
            <th class="col-name">场景</th>
            <th>来源</th>
            <th>当前版本</th>
            <th>版本</th>
            <th>锁定状态</th>
            <th>更新时间</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="sc in scenarios"
            :key="sc.code"
            :class="{ selected: sc.code === selectedCode }"
            @click="selectScenario(sc)"
          >
            <td class="col-name" :title="sc.description">{{ sc.display_name || sc.code }}<em class="sc-code">{{ sc.code }}</em></td>
            <td>
              <span class="mono-tag" :class="sc.source === 'managed' ? 'tag-managed' : 'tag-runtime'">
                {{ sc.source === 'managed' ? '管理' : '系统预置' }}
              </span>
            </td>
            <td><span class="mono-tag">{{ sc.current_version || (sc.runtime_status === 'ACTIVE' ? '使用中' : '未发布') }}</span></td>
            <td>{{ sc.versions?.length || 0 }}</td>
            <td>
              <span v-if="sc.lock_status" class="mono-tag tag-locked" :title="`锁定人：${sc.lock_status.holder_name}（${sc.lock_status.holder_id}）`">
                🔒 {{ sc.lock_status.holder_name }}
              </span>
              <span v-else class="mono-tag tag-free">空闲</span>
            </td>
            <td class="sc-time">{{ (sc.updated_at || '').slice(0, 16).replace('T', ' ') }}</td>
            <td class="col-actions">
              <template v-if="sc.source === 'managed'">
                <button class="btn-liquid-outline sc-mini" @click.stop="selectScenario(sc)">编排</button>
                <button class="btn-liquid-outline sc-mini danger" @click.stop="onDelete(sc)">删除</button>
              </template>
              <button v-else class="btn-liquid-outline sc-mini" @click.stop="selectScenario(sc)">查看</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="scenarios.length === 0 && !isLoading" class="sc-empty">暂无场景记录。</div>
    </div>

    <!-- 选中场景 -->
    <div v-if="detail" class="sc-detail glass-box">
      <div class="sc-detail-head">
        <div>
          <span class="sc-detail-title">{{ detail.display_name || detail.code }}</span>
          <span class="mono-tag" style="margin-left: 8px;">{{ detail.code }}</span>
          <span class="mono-tag" :class="detail.source === 'managed' ? 'tag-managed' : 'tag-runtime'" style="margin-left: 4px;">
            {{ detail.source === 'managed' ? `管理 · 当前 ${detail.current_version || '未发布'}` : '系统预置 · 只读' }}
          </span>
        </div>
        <button class="btn-liquid-outline sc-mini" @click="closeDetail">关闭</button>
      </div>

      <AssetLockBanner
        v-if="detail.source === 'managed'"
        :held-by-me="heldByMe"
        :held-by-other="heldByOther"
        :holder-label="holderLabel"
        :remaining-seconds="remainingSeconds"
        :busy="isBusy"
        @acquire="acquire(detail.code)"
        @release="release()"
      />

      <p v-if="detail.source === 'runtime'" class="sc-runtime-note">
        系统预置流程，由平台统一维护，仅支持查看与执行。
      </p>

      <!-- 管理场景：版本 + 图编辑 -->
      <template v-if="detail.source === 'managed'">
        <div class="sc-verbar">
          <span class="sc-verlabel">版本：</span>
          <select v-model="selectedVersion" class="glass-select sc-versel" @change="loadVersionGraph">
            <option v-for="v in detail.versions" :key="v.version" :value="v.version">
              {{ v.version }} · {{ verStatusText(v.status) }}
            </option>
          </select>
          <label v-if="editingDraft" class="sc-saga">
            <input v-model="draftGraph.enable_saga_compensation" type="checkbox" />
            <span>失败时自动回滚已执行步骤</span>
          </label>
          <button v-if="editingDraft" class="btn-liquid sc-btn" :disabled="isSaving" @click="saveDraft">{{ isSaving ? '保存中...' : '保存草稿' }}</button>
          <button v-if="editingDraft" class="btn-liquid sc-btn" :disabled="isPublishing" @click="publishDraft">{{ isPublishing ? '发布中...' : '发布' }}</button>
          <button v-if="heldByMe" class="btn-liquid-outline sc-btn" :disabled="isSaving" @click="deriveNewDraft">基于最新新建草稿</button>
          <span v-if="versionNote" class="sc-note" :class="{ ok: noteOk }">{{ versionNote }}</span>
        </div>

        <GraphEditor
          :graph="draftGraph"
          :editable="editingDraft && heldByMe"
          :allow-subgraphs="true"
          :palette="mixedPalette"
          @toast="(t) => emit('toast', t)"
        />
        <p class="sc-tip">发布时子图将自动展开为算子步骤并即时生效；引用的算子与子图须已成可用版本。</p>
      </template>

      <!-- 运行面板 -->
      <div class="sc-run">
        <div class="sc-run-left">
          <span class="sc-verlabel">执行入参 (JSON)</span>
          <textarea v-model="inputsJson" class="glass-input sc-inputs" rows="2" spellcheck="false"></textarea>
          <span v-if="inputsError" class="sc-inputs-err">{{ inputsError }}</span>
        </div>
        <button class="btn-liquid sc-run-btn" :disabled="isExecuting || !!inputsError || !canRun" @click="runScenario">
          {{ isExecuting ? '执行中...' : '执行场景' }}
        </button>
      </div>

      <div v-if="runResult" class="sc-result">
        <div class="sc-result-head">
          <span>执行结果 · {{ runResult.scenario_code }}</span>
          <span class="mono-tag" :class="runResult.status === 'SUCCESS' ? 'ok-tag' : 'bad-tag'">
            {{ runResult.status }} · {{ runResult.execution_time_ms }}ms
          </span>
        </div>
        <div class="sc-trace">
          <div class="sc-trace-row head"><span>节点</span><span>算子</span><span>状态</span><span>耗时</span></div>
          <div v-for="tr in runResult.node_traces" :key="tr.node_id" class="sc-trace-row">
            <span class="sc-trace-node">{{ tr.node_id }}</span>
            <span class="sc-trace-handler">{{ tr.action_handler }}</span>
            <span :class="tr.status === 'SUCCESS' ? 'ok-tag' : 'bad-tag'">{{ tr.status }}</span>
            <span>{{ tr.duration_ms }}ms</span>
          </div>
        </div>
        <details class="sc-final">
          <summary>final_output</summary>
          <pre>{{ JSON.stringify(runResult.final_output, null, 2) }}</pre>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 场景管理面板：展示（管理场景 + 运行时内置管线）/ 创建 / 删除 /
 * 版本管理 / 算子与子图混合编排 / 发布部署 / 执行。
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

const scenarios = ref([]);
const operators = ref([]);
const subgraphs = ref([]);
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

const draftGraph = ref({ entry_node: '', exit_node: '', nodes: [], edges: [], enable_saga_compensation: true });

const inputsJson = ref('{}');
const isExecuting = ref(false);
const runResult = ref(null);

const { heldByMe, heldByOther, holderLabel, remainingSeconds, isBusy, attach, acquire, release } = useAssetLock(
  props.userSession,
  'scenario',
  emit,
);

const selectedVersionRow = computed(() => detail.value?.versions?.find((v) => v.version === selectedVersion.value) || null);
const editingDraft = computed(() => selectedVersionRow.value?.status === 'DRAFT');
const canRun = computed(() => {
  if (!detail.value) return false;
  if (detail.value.source === 'runtime') return detail.value.runtime_status === 'ACTIVE';
  return !!detail.value.current_version;
});

const inputsError = computed(() => {
  try {
    const v = JSON.parse(inputsJson.value || '{}');
    return v && typeof v === 'object' && !Array.isArray(v) ? '' : '入参必须为 JSON 对象';
  } catch (e) {
    return 'JSON 格式错误: ' + e.message;
  }
});

const mixedPalette = computed(() => {
  const opItems = operators.value
    .filter((o) => o.source === 'builtin' || o.current_version)
    .map((o) => ({
      kind: 'OPERATOR',
      key: o.name,
      label: o.name,
      domain: o.domain,
      description: o.source === 'builtin' ? o.description : `${o.description || '自建算子'} · ${o.current_version}`,
      tag: o.source === 'builtin' ? '预置' : '自建',
    }));
  const sgItems = subgraphs.value
    .filter((s) => s.current_version)
    .map((s) => ({
      kind: 'SUBGRAPH',
      key: s.code,
      label: s.code,
      domain: '子图',
      description: `${s.description || s.display_name || '子流水线'} · ${s.current_version}（发布时自动展开）`,
      tag: s.current_version,
    }));
  return [...sgItems, ...opItems];
});

function verStatusText(status) {
  return { DRAFT: '草稿', PUBLISHED: '已发布', SUPERSEDED: '已取代' }[status] || status;
}

async function loadScenarios() {
  isLoading.value = true;
  try {
    const res = await dispatchGateway('orchestration.catalog.scenarios', {}, { silent: true });
    scenarios.value = res.ok && Array.isArray(res.data?.scenarios) ? res.data.scenarios : [];
    emit('count', 'scenarios', scenarios.value.length);
  } finally {
    isLoading.value = false;
  }
}

async function loadPaletteMeta() {
  const [opsRes, sgsRes] = await Promise.all([
    dispatchGateway('orchestration.catalog.operators', {}, { silent: true }),
    dispatchGateway('orchestration.catalog.subgraphs', {}, { silent: true }),
  ]);
  operators.value = opsRes.ok && Array.isArray(opsRes.data?.operators) ? opsRes.data.operators : [];
  subgraphs.value = sgsRes.ok && Array.isArray(sgsRes.data?.subgraphs) ? sgsRes.data.subgraphs : [];
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
    const res = await catalogWrite('scenarios.create', { ...createForm.value, code });
    if (res.ok) {
      emit('toast', { title: '场景已创建', message: `${code} 已进入 v1.0.0 草稿，开始编排算子与子图。`, type: 'SUCCESS' });
      showCreate.value = false;
      await loadScenarios();
      await selectScenario({ code, lock_status: null });
    } else {
      emit('toast', { title: '创建失败', message: res.error || '请检查场景编码。', type: 'ERROR' });
    }
  } finally {
    isCreating.value = false;
  }
}

async function selectScenario(row) {
  selectedCode.value = row.code;
  runResult.value = null;
  // 刷新可编排资产（算子/子图可能在其他面板刚发布），保证面板与目录同步
  loadPaletteMeta();
  const res = await dispatchGateway('orchestration.catalog.scenario', { code: row.code }, { silent: true });
  if (!res.ok) {
    emit('toast', { title: '加载场景失败', message: res.error || '请稍后重试。', type: 'ERROR' });
    return;
  }
  detail.value = res.data;
  if (detail.value.source === 'managed') {
    attach(row.code, detail.value.lock_status || row.lock_status || null);
    const versions = detail.value.versions || [];
    const draft = versions.find((v) => v.status === 'DRAFT');
    selectedVersion.value = (draft || versions[versions.length - 1] || {}).version || '';
    loadVersionGraph();
    inputsJson.value = /TAX|tax|VAT/i.test(row.code) ? '{"quarterly_income": 260000}' : '{}';
  } else {
    attach('', null);
    inputsJson.value = /TAX|tax|VAT/i.test(row.code) ? '{"quarterly_income": 260000}' : '{}';
  }
}

function loadVersionGraph() {
  const row = selectedVersionRow.value;
  versionNote.value = '';
  if (!row) {
    draftGraph.value = { entry_node: '', exit_node: '', nodes: [], edges: [], enable_saga_compensation: true };
    return;
  }
  const g = row.graph || {};
  draftGraph.value = {
    entry_node: g.entry_node || '',
    exit_node: g.exit_node || '',
    nodes: JSON.parse(JSON.stringify(g.nodes || [])),
    edges: JSON.parse(JSON.stringify(g.edges || [])),
    enable_saga_compensation: g.enable_saga_compensation !== false,
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
    const res = await catalogWrite('scenarios.version.save', {
      code: detail.value.code,
      version: selectedVersion.value,
      graph: draftGraph.value,
    });
    if (res.ok) {
      versionNote.value = `草稿 ${selectedVersion.value} 已保存`;
      noteOk.value = true;
      emit('toast', { title: '草稿已保存', message: `${detail.value.code}@${selectedVersion.value} 编排已保存。`, type: 'SUCCESS' });
      await loadScenarios();
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
  const res = await catalogWrite('scenarios.version.save', {
    code: detail.value.code,
    version: next,
    changelog: `基于 ${latest?.version || '空'} 新建的草稿`,
    graph: latest?.graph || draftGraph.value,
  });
  if (res.ok) {
    emit('toast', { title: '新草稿已创建', message: `已创建 ${next} 草稿（继承上一版编排）。`, type: 'SUCCESS' });
    await loadScenarios();
    await selectScenario({ code: detail.value.code });
  } else {
    emit('toast', { title: '新建草稿失败', message: res.error || '请稍后重试。', type: 'ERROR' });
  }
}

async function publishDraft() {
  if (!detail.value || !editingDraft.value || !heldByMe.value) return;
  isPublishing.value = true;
  try {
    const res = await catalogWrite('scenarios.publish', { code: detail.value.code, version: selectedVersion.value });
    if (res.ok) {
      versionNote.value = `版本 ${selectedVersion.value} 已发布`;
      noteOk.value = true;
      emit('toast', { title: '场景已发布', message: `${detail.value.code}@${selectedVersion.value} 已发布并即时生效。`, type: 'SUCCESS' });
      await loadScenarios();
      await selectScenario({ code: detail.value.code });
    } else {
      versionNote.value = res.error || '发布失败';
      noteOk.value = false;
      emit('toast', { title: '发布未通过', message: res.error || '请检查编排连线与算子、子图引用。', type: 'ERROR' });
    }
  } finally {
    isPublishing.value = false;
  }
}

async function onDelete(sc) {
  if (isBusy.value) return;
  if (!window.confirm(`确认删除场景「${sc.code}」？其全部已发布版本将一并移除。`)) return;
  const locked = heldByMe.value || (await acquire(sc.code));
  if (!locked) return;
  const res = await catalogWrite('scenarios.delete', { code: sc.code });
  if (res.ok) {
    const removed = res.data?.removed_runtime_versions?.join('、') || '无';
    emit('toast', { title: '场景已删除', message: `${sc.code} 已删除（移除已发布版本：${removed}）。`, type: 'SUCCESS' });
    if (detail.value?.code === sc.code) closeDetail();
    await loadScenarios();
  } else {
    emit('toast', { title: '删除失败', message: res.error || '请稍后重试。', type: 'ERROR' });
  }
}

async function runScenario() {
  if (isExecuting.value || !detail.value || inputsError.value) return;
  isExecuting.value = true;
  runResult.value = null;
  try {
    const res = await dispatchGateway(
      'orchestration.scenarios.execute',
      { scenario_code: detail.value.code, inputs: JSON.parse(inputsJson.value || '{}') },
      { silent: true },
    );
    if (res.ok) {
      runResult.value = res.data;
    } else {
      emit('toast', { title: '场景执行失败', message: res.error || '请检查编排配置。', type: 'ERROR' });
    }
  } finally {
    isExecuting.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadScenarios(), loadPaletteMeta()]);
});
</script>

<style scoped>
.scpanel { display: flex; flex-direction: column; gap: 14px; }
.scpanel-toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sc-btn { padding: 7px 16px; font-size: 12.5px; }
.sc-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.sc-count { margin-left: auto; }
.sc-mini { padding: 4px 10px; font-size: 11px; }
.sc-mini.danger { color: var(--status-danger); border-color: var(--status-danger); }

.sc-create { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.sc-create-title { font-weight: 600; font-size: 13.5px; }
.sc-create-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.sc-field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); }
.sc-create-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sc-hint { font-size: 11.5px; color: var(--text-tertiary); }

.sc-list { border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); overflow-x: auto; }
/* 真表格布局：列宽按内容自适应，超宽时容器内横向滚动 */
.cat-table { width: 100%; border-collapse: collapse; table-layout: auto; }
.cat-table th { text-align: left; font-size: 11px; font-weight: 500; color: var(--text-tertiary); padding: 9px 14px; white-space: nowrap; background: var(--glass-surface-subtle); }
.cat-table td { font-size: 12.5px; color: var(--text-secondary); padding: 9px 14px; white-space: nowrap; vertical-align: middle; }
.cat-table tbody tr:nth-child(2n) td { background: var(--glass-surface-subtle); }
.cat-table tbody tr:hover td { background: var(--accent-glass); cursor: pointer; }
.cat-table tbody tr.selected td { background: var(--accent-glass); box-shadow: inset 0 0 0 1px var(--accent); }
.cat-table td.col-name { font-weight: 600; white-space: normal; word-break: break-all; min-width: 160px; max-width: 360px; }
.cat-table .col-actions { text-align: right; white-space: nowrap; }
.cat-table td.col-actions .btn-liquid-outline + .btn-liquid-outline { margin-left: 6px; }
.sc-code { font-style: normal; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-tertiary); margin-left: 6px; }
.sc-time { color: var(--text-tertiary); font-size: 11px; }
.sc-empty { padding: 18px 12px; text-align: center; color: var(--text-tertiary); font-size: 12.5px; }

.sc-detail { padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
.sc-detail-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.sc-detail-title { font-size: 16px; font-weight: 700; }
.sc-runtime-note { font-size: 12px; color: var(--text-tertiary); margin: 0; }
.sc-verbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sc-verlabel { font-size: 12px; color: var(--text-tertiary); }
.sc-versel { padding: 4px 8px; font-size: 11.5px; border: 1px solid var(--glass-border-subtle); border-radius: 6px; background: transparent; }
.sc-saga { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-secondary); }
.sc-note { font-size: 12px; color: var(--status-danger); }
.sc-note.ok { color: var(--status-success); }
.sc-tip { font-size: 11.5px; color: var(--text-tertiary); margin: 0; }

.sc-run { display: flex; gap: 12px; align-items: flex-end; padding: 10px 14px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-sm); flex-wrap: wrap; }
.sc-run-left { flex: 1; min-width: 240px; display: flex; flex-direction: column; gap: 4px; }
.sc-inputs { font-family: var(--font-mono); font-size: 12px; resize: vertical; }
.sc-inputs-err { font-size: 11px; color: var(--status-danger); }
.sc-run-btn { font-size: 12.5px; padding: 8px 18px; }
.sc-run-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.sc-result { border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-sm); padding: 10px 14px; display: flex; flex-direction: column; gap: 8px; }
.sc-result-head { display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; font-weight: 600; }
.ok-tag { background: var(--status-success-soft); color: var(--status-success); }
.bad-tag { background: var(--status-danger-soft); color: var(--status-danger); }
.sc-trace { display: flex; flex-direction: column; gap: 3px; font-size: 12px; }
.sc-trace-row { display: grid; grid-template-columns: 1.2fr 1.6fr 90px 70px; gap: 8px; padding: 4px 8px; border-radius: 6px; color: var(--text-secondary); align-items: center; }
.sc-trace-row.head { color: var(--text-tertiary); font-size: 11px; }
.sc-trace-row:nth-child(2n) { background: var(--glass-surface-subtle); }
.sc-trace-node { font-family: var(--font-mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sc-trace-handler { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sc-final summary { cursor: pointer; font-size: 12px; color: var(--text-tertiary); }
.sc-final pre { font-size: 11px; font-family: var(--font-mono); max-height: 200px; overflow: auto; background: var(--glass-surface-subtle); border-radius: 6px; padding: 8px; margin: 6px 0 0; }

.tag-managed { background: var(--accent-glass); color: var(--accent); }
.tag-runtime { background: var(--glass-surface-subtle); color: var(--text-tertiary); }
.tag-locked { background: var(--status-warning-soft); color: var(--status-warning); }
.tag-free { background: var(--status-success-soft); color: var(--status-success); }
</style>
