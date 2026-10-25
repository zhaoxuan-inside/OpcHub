<template>
  <div class="opanel">
    <!-- 工具栏 -->
    <div class="opanel-toolbar">
      <button class="btn-liquid op-btn" @click="openCreate">新建算子</button>
      <button class="btn-liquid-outline op-btn" :disabled="isLoading || isReloading" @click="reloadAll">
        {{ isReloading ? '刷新中...' : '刷新目录' }}
      </button>
      <button class="btn-liquid-outline op-btn" :disabled="isReloading" @click="triggerHotReload" title="重新扫描并刷新系统预置算子">
        刷新预置算子
      </button>
      <span class="op-count mono-tag">{{ operators.length }} 个算子</span>
    </div>

    <!-- 新建算子表单 -->
    <div v-if="showCreate" class="op-create glass-box">
      <div class="op-create-title">新建自建算子</div>
      <div class="op-create-grid">
        <label class="op-field">
          <span>算子名 *</span>
          <input v-model="createForm.name" class="glass-input" placeholder="dynamic.my_operator" />
        </label>
        <label class="op-field">
          <span>显示名</span>
          <input v-model="createForm.display_name" class="glass-input" placeholder="我的算子" />
        </label>
        <label class="op-field">
          <span>所属域</span>
          <input v-model="createForm.domain" class="glass-input" placeholder="custom" />
        </label>
        <label class="op-field">
          <span>入口函数</span>
          <input v-model="createForm.entry_function" class="glass-input" placeholder="action_entry" />
        </label>
      </div>
      <label class="op-field">
        <span>描述</span>
        <input v-model="createForm.description" class="glass-input" placeholder="算子用途说明" />
      </label>
      <label class="op-field">
        <span>Python 脚本 *</span>
        <textarea v-model="createForm.code" class="glass-input op-code" rows="6" spellcheck="false" placeholder="async def action_entry(inputs, context):&#10;    return {'result': inputs.get('x', 0) * 2}"></textarea>
      </label>
      <div class="op-create-actions">
        <button class="btn-liquid op-btn" :disabled="!createForm.name.trim() || !createForm.code.trim() || isCreating" @click="submitCreate">
          {{ isCreating ? '创建中...' : '锁定并创建' }}
        </button>
        <button class="btn-liquid-outline op-btn" @click="showCreate = false">取消</button>
        <span class="op-hint">创建后将自动锁定该算子并进入草稿编辑；脚本经平台安全校验后方可发布。</span>
      </div>
    </div>

    <!-- 算子列表：真表格布局，列宽随内容自适应 -->
    <div class="op-list">
      <table class="cat-table">
        <thead>
          <tr>
            <th class="col-name">算子</th>
            <th>域</th>
            <th>来源</th>
            <th>当前版本</th>
            <th>调度</th>
            <th>版本</th>
            <th>使用状态</th>
            <th>锁定状态</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="op in operators"
            :key="op.name"
            :class="{ selected: op.name === selectedName }"
            @click="selectOperator(op)"
          >
            <td class="col-name" :title="op.description">{{ op.display_name || op.name }}</td>
            <td><span class="mono-tag">{{ op.domain }}</span></td>
            <td>
              <span class="mono-tag" :class="op.source === 'builtin' ? 'tag-builtin' : 'tag-custom'">{{ op.source === 'builtin' ? '预置' : '自建' }}</span>
            </td>
            <td><span class="mono-tag">{{ op.current_version || '—' }}</span></td>
            <td><span class="mono-tag">{{ op.runtime_mode === 'HTTP_REMOTE' ? 'HTTP' : op.runtime_mode || '—' }}</span></td>
            <td>{{ op.versions?.length || 0 }}</td>
            <td>
              <span
                class="mono-tag"
                :class="op.in_use ? 'tag-inuse' : 'tag-unused'"
                :title="op.in_use ? `被引用于：${(op.referenced_by || []).join('、')}` : '尚未被任何在用编排引用'"
              >
                {{ op.in_use ? '使用中' : '未使用' }}
              </span>
            </td>
            <td>
              <span v-if="op.lock_status" class="mono-tag tag-locked" :title="`锁定人：${op.lock_status.holder_name}（${op.lock_status.holder_id}）`">
                🔒 {{ op.lock_status.holder_name }}
              </span>
              <span v-else class="mono-tag tag-free">空闲</span>
            </td>
            <td class="col-actions">
              <template v-if="op.source === 'custom'">
                <button class="btn-liquid-outline op-mini" @click.stop="onEditClick(op)">编辑</button>
                <button class="btn-liquid-outline op-mini danger" @click.stop="onDelete(op)">删除</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="operators.length === 0 && !isLoading" class="op-empty">
        算子目录为空或加载失败，请点击「刷新目录」。
      </div>
    </div>

    <!-- 选中算子详情 / 编辑 -->
    <div v-if="detail" class="op-detail glass-box">
      <div class="op-detail-head">
        <div>
          <span class="op-detail-title">{{ detail.display_name || detail.name }}</span>
          <span class="mono-tag" style="margin-left: 8px;">{{ detail.name }}</span>
          <span class="mono-tag" :class="detail.source === 'builtin' ? 'tag-builtin' : 'tag-custom'" style="margin-left: 4px;">
            {{ detail.source === 'builtin' ? '预置算子' : '自建算子' }}
          </span>
        </div>
        <button class="btn-liquid-outline op-mini" @click="closeDetail">关闭</button>
      </div>

      <AssetLockBanner
        :held-by-me="heldByMe"
        :held-by-other="heldByOther"
        :holder-label="holderLabel"
        :remaining-seconds="remainingSeconds"
        :busy="isBusy"
        @acquire="acquire(detail.name)"
        @release="release()"
      />

      <p v-if="detail.source === 'builtin'" class="op-builtin-note">
        系统预置算子（{{ detail.domain }} 域），由平台统一维护，可直接编排引用；不支持创建、删除与版本管理。
      </p>

      <div class="op-usage">
        <span class="mono-tag" :class="detail.in_use ? 'tag-inuse' : 'tag-unused'">
          {{ detail.in_use ? '使用中' : '未使用' }}
        </span>
        <span v-if="detail.in_use" class="op-usage-detail">被引用于：{{ (detail.referenced_by || []).join('、') }}</span>
        <span v-else class="op-usage-detail">尚未被任何在用编排引用</span>
      </div>

      <div v-if="detail.description" class="op-desc">{{ detail.description }}</div>

      <!-- 自建算子：版本管理 -->
      <template v-if="detail.source === 'custom'">
        <div class="op-section-title">版本历史</div>
        <div class="op-versions">
          <div class="op-ver-row op-ver-head">
            <span>版本</span><span>状态</span><span>更新说明</span><span>发布</span><span></span>
          </div>
          <div v-for="v in detail.versions" :key="v.version" class="op-ver-row" :class="{ active: v.version === activeDraft?.version }">
            <span class="mono-tag">{{ v.version }}</span>
            <span>
              <span class="mono-tag" :class="verStatusClass(v.status)">{{ verStatusText(v.status) }}</span>
            </span>
            <span class="op-ver-log">{{ v.changelog }}</span>
            <span class="op-ver-time">{{ v.published_at || v.created_at || '' }}</span>
            <span>
              <button v-if="v.status === 'DRAFT'" class="btn-liquid op-mini" :disabled="!heldByMe || isPublishing" @click="publishVersion(v)">发布</button>
            </span>
          </div>
        </div>

        <!-- 草稿编辑 -->
        <template v-if="activeDraft">
          <div class="op-section-title">编辑草稿 {{ activeDraft.version }}<span v-if="!heldByMe" class="op-hint-inline">（需持有编辑锁）</span></div>
          <div class="op-create-grid">
            <label class="op-field">
              <span>显示名</span>
              <input v-model="draftForm.display_name" class="glass-input" :disabled="!heldByMe" />
            </label>
            <label class="op-field">
              <span>入口函数</span>
              <input v-model="draftForm.entry_function" class="glass-input" :disabled="!heldByMe" />
            </label>
          </div>
          <label class="op-field">
            <span>描述</span>
            <input v-model="draftForm.description" class="glass-input" :disabled="!heldByMe" />
          </label>
          <label class="op-field">
            <span>Python 脚本</span>
            <textarea v-model="draftForm.code" class="glass-input op-code" rows="8" spellcheck="false" :disabled="!heldByMe"></textarea>
          </label>
          <label class="op-field">
            <span>更新说明</span>
            <input v-model="draftForm.changelog" class="glass-input" :disabled="!heldByMe" placeholder="本次改动说明" />
          </label>
          <div class="op-create-actions">
            <button class="btn-liquid op-btn" :disabled="!heldByMe || isSaving" @click="saveDraft">{{ isSaving ? '保存中...' : '保存草稿' }}</button>
            <button class="btn-liquid-outline op-btn" :disabled="!heldByMe || isPublishing" @click="publishVersion(activeDraft)">发布此草稿</button>
            <button class="btn-liquid-outline op-btn" :disabled="!heldByMe || isSaving" @click="deriveNewDraft">基于最新新建草稿</button>
          </div>
        </template>
        <div v-else class="op-empty">暂无草稿版本；点击「基于最新新建草稿」开始下一版迭代。</div>
      </template>
    </div>
  </div>
</template>

<script setup>
/**
 * 算子管理面板：展示（内置 + 自建）/ 创建 / 删除 / 版本管理 / 发布。
 * 内置算子只读展示；自建算子全生命周期需持排他锁。
 */
import { computed, onMounted, ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import { catalogWrite, useAssetLock } from '@/components/orchestration/useAssetLock';
import AssetLockBanner from '@/components/orchestration/AssetLockBanner.vue';

const props = defineProps({
  userSession: { type: Object, default: null },
});
const emit = defineEmits(['toast', 'count']);

const operators = ref([]);
const isLoading = ref(false);
const isReloading = ref(false);
const selectedName = ref('');
const detail = ref(null);

const showCreate = ref(false);
const isCreating = ref(false);
const isSaving = ref(false);
const isPublishing = ref(false);

const createForm = ref({ name: '', display_name: '', domain: 'custom', description: '', code: '', entry_function: 'action_entry' });
const draftForm = ref({ display_name: '', description: '', code: '', entry_function: 'action_entry', changelog: '' });

const { heldByMe, heldByOther, holderLabel, remainingSeconds, isBusy, attach, acquire, release } = useAssetLock(
  props.userSession,
  'operator',
  emit,
);

const activeDraft = computed(() => detail.value?.versions?.find((v) => v.status === 'DRAFT') || null);

function verStatusText(status) {
  return { DRAFT: '草稿', PUBLISHED: '已发布', SUPERSEDED: '已取代' }[status] || status;
}
function verStatusClass(status) {
  return { DRAFT: 'tag-draft', PUBLISHED: 'tag-published', SUPERSEDED: 'tag-superseded' }[status] || '';
}

async function loadOperators() {
  const res = await dispatchGateway('orchestration.catalog.operators', {}, { silent: true });
  const data = res.data;
  operators.value = res.ok && Array.isArray(data?.operators) ? data.operators : [];
  emit('count', 'operators', operators.value.length);
}

async function reloadAll() {
  isLoading.value = true;
  isReloading.value = true;
  try {
    await loadOperators();
  } finally {
    isLoading.value = false;
    isReloading.value = false;
  }
}

async function triggerHotReload() {
  isReloading.value = true;
  try {
    const res = await dispatchGateway('framework.gateway.reload', {}, { silent: true });
    if (res.ok) {
      emit('toast', { title: '热加载完成', message: '已重新扫描代码算子并刷新路由表。', type: 'SUCCESS' });
      await loadOperators();
    } else {
      emit('toast', { title: '热加载失败', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } finally {
    isReloading.value = false;
  }
}

function openCreate() {
  showCreate.value = !showCreate.value;
  if (showCreate.value) {
    createForm.value = { name: '', display_name: '', domain: 'custom', description: '', code: '', entry_function: 'action_entry' };
  }
}

async function submitCreate() {
  const name = createForm.value.name.trim();
  if (!name || isCreating.value) return;
  isCreating.value = true;
  try {
    const locked = await acquire(name);
    if (!locked) return;
    const res = await catalogWrite('operators.create', { ...createForm.value, name });
    if (res.ok) {
      emit('toast', { title: '算子已创建', message: `${name} 已进入 v1.0.0 草稿，编辑脚本后可发布。`, type: 'SUCCESS' });
      showCreate.value = false;
      await loadOperators();
      await selectOperator({ name, lock_status: null });
    } else {
      emit('toast', { title: '创建失败', message: res.error || '请检查算子名与脚本。', type: 'ERROR' });
    }
  } finally {
    isCreating.value = false;
  }
}

async function selectOperator(row) {
  selectedName.value = row.name;
  const res = await dispatchGateway('orchestration.catalog.operator', { name: row.name }, { silent: true });
  if (!res.ok) {
    emit('toast', { title: '加载算子失败', message: res.error || '请稍后重试。', type: 'ERROR' });
    return;
  }
  detail.value = res.data;
  attach(row.name, res.data.lock_status || row.lock_status || null);
  const draft = detail.value.versions?.find((v) => v.status === 'DRAFT');
  if (draft) {
    draftForm.value = {
      display_name: detail.value.display_name,
      description: detail.value.description,
      code: draft.definition?.code || '',
      entry_function: draft.definition?.entry_function || 'action_entry',
      changelog: draft.changelog || '',
    };
  }
}

function onEditClick(op) {
  selectOperator(op);
}

function closeDetail() {
  detail.value = null;
  selectedName.value = '';
}

async function saveDraft() {
  if (!detail.value || !activeDraft.value || !heldByMe.value) return;
  isSaving.value = true;
  try {
    const res = await catalogWrite('operators.version.save', {
      name: detail.value.name,
      version: activeDraft.value.version,
      display_name: draftForm.value.display_name,
      description: draftForm.value.description,
      changelog: draftForm.value.changelog,
      definition: { code: draftForm.value.code, entry_function: draftForm.value.entry_function },
    });
    if (res.ok) {
      emit('toast', { title: '草稿已保存', message: `${detail.value.name}@${activeDraft.value.version} 已保存。`, type: 'SUCCESS' });
      await loadOperators();
      await selectOperator({ name: detail.value.name });
    } else {
      emit('toast', { title: '保存失败', message: res.error || '请检查脚本内容。', type: 'ERROR' });
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
  isSaving.value = true;
  try {
    const res = await catalogWrite('operators.version.save', {
      name: detail.value.name,
      version: next,
      changelog: `基于 ${latest?.version || '空'} 新建的草稿`,
    });
    if (res.ok) {
      emit('toast', { title: '新草稿已创建', message: `已创建 ${next} 草稿版本。`, type: 'SUCCESS' });
      await loadOperators();
      await selectOperator({ name: detail.value.name });
    } else {
      emit('toast', { title: '新建草稿失败', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } finally {
    isSaving.value = false;
  }
}

async function publishVersion(v) {
  if (!detail.value || !heldByMe.value || isPublishing.value) return;
  isPublishing.value = true;
  try {
    const res = await catalogWrite('operators.publish', { name: detail.value.name, version: v.version });
    if (res.ok) {
      emit('toast', { title: '算子版本已发布', message: `${detail.value.name}@${v.version} 已发布为可用算子，可被编排引用。`, type: 'SUCCESS' });
      await loadOperators();
      await selectOperator({ name: detail.value.name });
    } else {
      emit('toast', { title: '发布失败', message: res.error || '请先保存草稿后再试。', type: 'ERROR' });
    }
  } finally {
    isPublishing.value = false;
  }
}

async function onDelete(op) {
  if (isBusy.value) return;
  if (!window.confirm(`确认删除自建算子「${op.name}」？被已发布子图/场景引用时将被拒绝。`)) return;
  const locked = heldByMe.value || (await acquire(op.name));
  if (!locked) return;
  const res = await catalogWrite('operators.delete', { name: op.name });
  if (res.ok) {
    emit('toast', { title: '算子已删除', message: `${op.name} 已删除。`, type: 'SUCCESS' });
    if (detail.value?.name === op.name) closeDetail();
    await loadOperators();
  } else {
    emit('toast', { title: '删除被拒绝', message: res.error || '该算子可能仍被引用。', type: 'ERROR' });
  }
}

onMounted(loadOperators);
</script>

<style scoped>
.opanel { display: flex; flex-direction: column; gap: 14px; }
.opanel-toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.op-btn { padding: 7px 16px; font-size: 12.5px; }
.op-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.op-count { margin-left: auto; }
.op-mini { padding: 4px 10px; font-size: 11px; }
.op-mini.danger { color: var(--status-danger); border-color: var(--status-danger); }

.op-create { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.op-create-title { font-weight: 600; font-size: 13.5px; }
.op-create-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
.op-field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); }
.op-code { font-family: var(--font-mono); font-size: 12px; resize: vertical; }
.op-create-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.op-hint { font-size: 11.5px; color: var(--text-tertiary); }

.op-list { border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); overflow-x: auto; }
/* 真表格布局：列宽按内容自适应，超宽时容器内横向滚动 */
.cat-table { width: 100%; border-collapse: collapse; table-layout: auto; }
.cat-table th { text-align: left; font-size: 11px; font-weight: 500; color: var(--text-tertiary); padding: 9px 14px; white-space: nowrap; background: var(--glass-surface-subtle); }
.cat-table td { font-size: 12.5px; color: var(--text-secondary); padding: 9px 14px; white-space: nowrap; vertical-align: middle; }
.cat-table tbody tr:nth-child(2n) td { background: var(--glass-surface-subtle); }
.cat-table tbody tr:hover td { background: var(--accent-glass); cursor: pointer; }
.cat-table tbody tr.selected td { background: var(--accent-glass); box-shadow: inset 0 0 0 1px var(--accent); }
.cat-table td.col-name { font-weight: 600; color: var(--text-primary, inherit); white-space: normal; word-break: break-all; min-width: 140px; max-width: 320px; }
.cat-table .col-actions { text-align: right; white-space: nowrap; }
.cat-table td.col-actions .btn-liquid-outline + .btn-liquid-outline { margin-left: 6px; }
.tag-inuse { background: var(--status-success-soft); color: var(--status-success); }
.tag-unused { background: var(--glass-surface-subtle); color: var(--text-tertiary); }
.op-empty { padding: 18px 12px; text-align: center; color: var(--text-tertiary); font-size: 12.5px; }

.op-detail { padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
.op-detail-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.op-detail-title { font-size: 16px; font-weight: 700; }
.op-builtin-note { font-size: 12px; color: var(--text-tertiary); margin: 0; line-height: 1.6; }
.op-desc { font-size: 12.5px; color: var(--text-secondary); }
.op-usage { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.op-usage-detail { font-size: 12px; color: var(--text-tertiary); }
.op-section-title { font-size: 13px; font-weight: 600; margin-top: 4px; }
.op-hint-inline { font-size: 11px; color: var(--text-tertiary); font-weight: 400; margin-left: 6px; }
.op-versions { border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-sm); overflow: hidden; }
.op-ver-row { display: grid; grid-template-columns: 90px 90px 1fr 170px 70px; gap: 8px; align-items: center; padding: 7px 12px; font-size: 12px; color: var(--text-secondary); }
.op-ver-row:nth-child(2n) { background: var(--glass-surface-subtle); }
.op-ver-row.active { outline: 1px dashed var(--accent); }
.op-ver-head { color: var(--text-tertiary); font-size: 11px; }
.op-ver-log { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.op-ver-time { color: var(--text-tertiary); font-size: 11px; }

.tag-builtin { background: var(--glass-surface-subtle); color: var(--text-tertiary); }
.tag-custom { background: var(--accent-glass); color: var(--accent); }
.tag-locked { background: var(--status-warning-soft); color: var(--status-warning); }
.tag-free { background: var(--status-success-soft); color: var(--status-success); }
.tag-draft { background: var(--status-warning-soft); color: var(--status-warning); }
.tag-published { background: var(--status-success-soft); color: var(--status-success); }
.tag-superseded { background: var(--glass-surface-subtle); color: var(--text-tertiary); }
</style>
