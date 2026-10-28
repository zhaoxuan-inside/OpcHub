<template>
  <div class="gwrap">
    <!-- 左侧：可编排资产面板（算子 / 已发布子图） -->
    <aside class="gpalette">
      <div class="gpalette-head">
        <span>{{ allowSubgraphs ? 'OPERATORS / SUBGRAPHS' : 'OPERATORS' }}</span>
        <span class="gpalette-count">{{ paletteItems.length }} 项</span>
      </div>
      <input v-model="filterText" class="glass-input gfilter" placeholder="按名称/域筛选" />
      <div class="gpalette-scroll">
        <template v-for="group in groupedPalette" :key="group.domain">
          <div class="gpalette-group">{{ group.domain }} · {{ group.items.length }}</div>
          <button
            v-for="item in group.items"
            :key="item.kind + item.key"
            type="button"
            class="gpalette-card"
            :class="{ addable: editable }"
            :title="editable ? `点击加入画布：${item.label}` : item.description"
            :disabled="!editable"
            @click="addNode(item)"
          >
            <span class="gpalette-card-head">
              <span class="gpalette-name">{{ item.label }}</span>
              <span class="mono-tag" :class="item.kind === 'SUBGRAPH' ? 'tag-sub' : 'tag-op'">{{ item.kind === 'SUBGRAPH' ? '子图' : (item.tag || '算子') }}</span>
            </span>
            <span class="gpalette-desc">{{ item.description }}</span>
          </button>
        </template>
        <div v-if="paletteItems.length === 0" class="gempty">暂无可编排资产。</div>
      </div>
    </aside>

    <!-- 中部：真正的流程图画布（Vue Flow：拖拽 / 缩放 / 小地图 / 端口连线） -->
    <section class="gcanvas-wrap">
      <div class="gcanvas-head">
        <span class="gcanvas-title">
          <template v-if="graph.nodes.length > 0">{{ graph.nodes.length }} 节点 · {{ graph.edges.length }} 边</template>
          <template v-else>画布为空</template>
        </span>
        <div class="gtools">
          <button type="button" class="gtool" title="缩小" @click="zoomOut()">−</button>
          <button type="button" class="gtool" title="放大" @click="zoomIn()">+</button>
          <button type="button" class="gtool gtool-text" title="适应画布" @click="fitView({ padding: 0.2 })">适应</button>
          <span class="gtool-divider"></span>
          <button type="button" class="gtool gtool-text" :disabled="!editable || !canUndo" title="撤销" @click="undo">撤销</button>
          <button type="button" class="gtool gtool-text" :disabled="!editable || !canRedo" title="重做" @click="redo">重做</button>
        </div>
      </div>

      <div class="gcanvas" :class="{ 'is-editable': editable }">
        <VueFlow
          id="opc-graph"
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :nodes-draggable="editable"
          :nodes-connectable="editable"
          :elements-selectable="true"
          :edges-updatable="editable"
          :delete-key-code="editable ? 'Delete' : null"
          :min-zoom="0.25"
          :max-zoom="1.8"
          :default-viewport="{ x: 24, y: 24, zoom: 0.9 }"
          fit-view-on-init
          @connect="onConnect"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @pane-click="activeNodeId = ''"
          @nodes-delete="onNodesDelete"
          @edges-delete="onEdgesDelete"
        >
          <Background :gap="18" pattern-color="var(--glass-border-subtle)" />
          <Controls position="bottom-left" />
          <MiniMap pannable zoomable position="bottom-right" />

          <template #node-opc="nodeProps">
            <div
              class="gnode-box"
              :class="{
                selected: activeNodeId === nodeProps.id,
                entry: graph.entry_node === nodeProps.id,
                exit: graph.exit_node === nodeProps.id,
                sub: nodeProps.data.kind === 'SUBGRAPH',
              }"
              :title="nodeRefLabel(nodeProps.data)"
            >
              <Handle type="target" :position="Position.Left" />
              <Handle type="source" :position="Position.Right" />
              <div class="gnode-meta">
                <span class="mono-tag">{{ nodeProps.data.kind === 'SUBGRAPH' ? 'SUBGRAPH' : nodeProps.data.type }}</span>
                <span class="gnode-badges">
                  <span v-if="graph.entry_node === nodeProps.id" class="gbadge">ENTRY</span>
                  <span v-if="graph.exit_node === nodeProps.id" class="gbadge exit">EXIT</span>
                </span>
              </div>
              <div class="gnode-name">{{ nodeProps.id }}</div>
              <div class="gnode-ref">{{ nodeRefLabel(nodeProps.data) }}</div>
            </div>
          </template>
        </VueFlow>

        <div v-if="graph.nodes.length === 0" class="gc-empty">
          {{ editable ? '从左侧点击算子/子图加入画布，再拖拽端口连成一条单向链路。' : '该版本暂无编排内容。' }}
        </div>
      </div>

      <div class="ghint">
        <span v-if="editable">拖拽节点移动 · 从节点右侧端口拖到目标节点连线 · 滚轮缩放 · 选中后 Delete 删除</span>
        <span v-else>只读模式：查看拓扑与入口/出口，切换到编辑模式后可拖拽编排。</span>
      </div>
    </section>

    <!-- 右侧：检视器 -->
    <aside class="ginspector">
      <div class="ginspector-card" v-if="activeNode">
        <div class="glabel">选中节点</div>
        <div class="gvalue">{{ activeNode.id }}</div>
        <div class="gmono">{{ nodeRefLabel(activeNode) }}</div>
        <div class="gmono">类型: {{ nodeKind(activeNode) === 'SUBGRAPH' ? 'SUBGRAPH' : activeNode.type }}</div>
        <template v-if="editable">
          <div class="glabel" style="margin-top: 8px;">设为入口/出口</div>
          <div class="gbtn-row">
            <button class="btn-liquid-outline gmini" :class="{ on: graph.entry_node === activeNode.id }" @click="setEntry(activeNode.id)">ENTRY</button>
            <button class="btn-liquid-outline gmini" :class="{ on: graph.exit_node === activeNode.id }" @click="setExit(activeNode.id)">EXIT</button>
          </div>
          <button class="btn-liquid-outline gmini gdanger" @click="removeNode(activeNode.id)">移除节点</button>
        </template>
      </div>
      <div class="ginspector-card" v-else>
        <div class="gempty" style="padding: 10px 0;">点击画布中的节点查看属性。</div>
      </div>

      <div class="ginspector-card">
        <div class="glabel">连线（{{ graph.edges.length }}）</div>
        <div v-for="(e, i) in graph.edges" :key="`${e.from_node}->${e.to_node}`" class="gedge-row">
          <span class="gmono">{{ e.from_node }} → {{ e.to_node }}</span>
          <button v-if="editable" class="gedge-del" title="删除此边" @click="removeEdge(i)">×</button>
        </div>
        <div v-if="graph.edges.length === 0" class="gempty" style="padding: 6px 0;">暂无边</div>
      </div>

      <div class="ginspector-card">
        <div class="glabel">快捷键</div>
        <div class="gshortcut"><kbd>Del</kbd><span>删除选中节点/连线</span></div>
        <div class="gshortcut"><kbd>⌘</kbd><kbd>Z</kbd><span>撤销</span></div>
        <div class="gshortcut"><kbd>滚轮</kbd><span>缩放画布</span></div>
      </div>
    </aside>
  </div>
</template>

<script setup>
/**
 * 图编辑器：子图（编排算子）与场景（编排算子 + 子图）共用。
 *
 * 使用 Vue Flow 提供 pan/zoom、拖拽节点、端口连线、框选、小地图与删除；
 * 底层数据仍原地修改 props.graph（响应式草稿），父组件负责保存/发布。
 */
import { computed, nextTick, ref, watch } from 'vue';
import { VueFlow, useVueFlow, MarkerType, Handle, Position } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import { MiniMap } from '@vue-flow/minimap';
import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/controls/dist/style.css';
import '@vue-flow/minimap/dist/style.css';

const props = defineProps({
  graph: { type: Object, required: true }, // {entry_node, exit_node, nodes, edges}
  editable: { type: Boolean, default: false },
  allowSubgraphs: { type: Boolean, default: false },
  palette: { type: Array, default: () => [] }, // {kind, key, label, domain, description, tag}
});

const emit = defineEmits(['toast']);

const { fitView, zoomIn, zoomOut, updateNodeInternals } = useVueFlow({ id: 'opc-graph' });

const NODE_W = 190;
const NODE_H = 86;
const COL_GAP = 70;
const ROW_GAP = 30;
const PAD = 28;

const filterText = ref('');
const activeNodeId = ref('');
const flowNodes = ref([]);
const flowEdges = ref([]);

const paletteItems = computed(() => props.palette);

const groupedPalette = computed(() => {
  const q = filterText.value.trim().toLowerCase();
  const map = new Map();
  for (const item of props.palette) {
    if (q && !item.label.toLowerCase().includes(q) && !String(item.domain).toLowerCase().includes(q)) continue;
    const d = item.domain || '其他';
    if (!map.has(d)) map.set(d, []);
    map.get(d).push(item);
  }
  return [...map.entries()].map(([domain, items]) => ({ domain, items }));
});

const activeNode = computed(() => props.graph.nodes.find((n) => n.id === activeNodeId.value) || null);

/* ------------------------------------------------------------------ */
/* Layout + graph ↔ Vue Flow sync                                      */
/* ------------------------------------------------------------------ */

function calcLayout(nodes, edges) {
  if (!nodes.length) return new Map();
  const ids = nodes.map((n) => n.id);
  const idSet = new Set(ids);
  const inDeg = new Map(ids.map((id) => [id, 0]));
  const adj = new Map(ids.map((id) => [id, []]));
  for (const e of edges) {
    if (!idSet.has(e.from_node) || !idSet.has(e.to_node)) continue;
    adj.get(e.from_node).push(e.to_node);
    inDeg.set(e.to_node, (inDeg.get(e.to_node) || 0) + 1);
  }
  const depth = new Map();
  let queue = ids.filter((id) => (inDeg.get(id) || 0) === 0);
  queue.forEach((id) => depth.set(id, 0));
  let guard = 0;
  while (queue.length && guard++ < 2000) {
    const next = [];
    for (const id of queue) {
      const d = depth.get(id);
      for (const t of adj.get(id) || []) {
        if (!depth.has(t) || d + 1 > depth.get(t)) {
          depth.set(t, d + 1);
          next.push(t);
        }
      }
    }
    queue = [...new Set(next)];
  }
  ids.forEach((id) => { if (!depth.has(id)) depth.set(id, 0); });

  const cols = new Map();
  for (const id of ids) {
    const d = depth.get(id);
    if (!cols.has(d)) cols.set(d, []);
    cols.get(d).push(id);
  }
  const pos = new Map();
  for (const [d, colIds] of cols) {
    colIds.forEach((id, i) => pos.set(id, {
      x: PAD + d * (NODE_W + COL_GAP),
      y: PAD + i * (NODE_H + ROW_GAP),
    }));
  }
  return pos;
}

function syncFromGraph({ keepPositions = true } = {}) {
  const layout = calcLayout(props.graph.nodes, props.graph.edges);
  const previous = new Map(flowNodes.value.map((n) => [n.id, n.position]));
  flowNodes.value = props.graph.nodes.map((node) => ({
    id: node.id,
    type: 'opc',
    width: NODE_W,
    height: NODE_H,
    position: keepPositions && previous.has(node.id)
      ? previous.get(node.id)
      : (layout.get(node.id) || { x: PAD, y: PAD }),
    data: { ...node },
  }));
  flowEdges.value = props.graph.edges.map((edge) => ({
    id: `${edge.from_node}->${edge.to_node}`,
    source: edge.from_node,
    target: edge.to_node,
    type: 'smoothstep',
    animated: false,
    markerEnd: MarkerType.ArrowClosed,
    style: { stroke: 'var(--accent)', strokeWidth: 1.6 },
  }));
  nextTick(() => {
    updateNodeInternals();
  });
}

watch(
  () => [
    props.graph.nodes.map((n) => n.id).join('|'),
    props.graph.edges.map((e) => `${e.from_node}->${e.to_node}`).join('|'),
    props.graph.entry_node,
    props.graph.exit_node,
  ],
  () => syncFromGraph(),
  { immediate: true }
);

watch(
  flowNodes,
  (nodes) => {
    // Persist the dragged position on the underlying node object so a later
    // sync (entry/exit change, add/remove) does not snap it back to auto-layout.
    for (const node of nodes) {
      const target = props.graph.nodes.find((n) => n.id === node.id);
      if (target) {
        target._x = node.position?.x ?? 0;
        target._y = node.position?.y ?? 0;
      }
    }
  },
  { deep: true }
);

/* ------------------------------------------------------------------ */
/* History                                                             */
/* ------------------------------------------------------------------ */

const history = ref([]);
const redoStack = ref([]);
const canUndo = computed(() => history.value.length > 0);
const canRedo = computed(() => redoStack.value.length > 0);

function snapshot() {
  return JSON.parse(JSON.stringify({
    nodes: props.graph.nodes,
    edges: props.graph.edges,
    entry_node: props.graph.entry_node,
    exit_node: props.graph.exit_node,
  }));
}

function applySnapshot(snap) {
  props.graph.nodes = JSON.parse(JSON.stringify(snap.nodes));
  props.graph.edges = JSON.parse(JSON.stringify(snap.edges));
  props.graph.entry_node = snap.entry_node;
  props.graph.exit_node = snap.exit_node;
  syncFromGraph({ keepPositions: false });
}

function pushHistory() {
  history.value.push(snapshot());
  if (history.value.length > 50) history.value.shift();
  redoStack.value = [];
}

function undo() {
  if (!history.value.length) return;
  redoStack.value.push(snapshot());
  const snap = history.value.pop();
  applySnapshot(snap);
}

function redo() {
  if (!redoStack.value.length) return;
  history.value.push(snapshot());
  const snap = redoStack.value.pop();
  applySnapshot(snap);
}

/* ------------------------------------------------------------------ */
/* Graph mutations                                                     */
/* ------------------------------------------------------------------ */

function nodeKind(node) {
  return node.kind === 'SUBGRAPH' ? 'SUBGRAPH' : 'OPERATOR';
}

function nodeRefLabel(node) {
  return node.kind === 'SUBGRAPH' ? `子图: ${node.subgraph}` : node.operator;
}

function inferNodeType(item) {
  if (item.kind === 'SUBGRAPH') return 'GUARD';
  const name = item.key || '';
  if (/guard|validate|check/.test(name)) return 'GUARD';
  if (/persist|save|store|delete|upsert/.test(name)) return 'STORAGE';
  if (/cache/.test(name)) return 'CACHE';
  return 'BIZ';
}

function uniqueId(base) {
  let id = base;
  let i = 2;
  while (props.graph.nodes.some((n) => n.id === id)) id = `${base}_${i++}`;
  return id;
}

function addNode(item) {
  if (!props.editable) return;
  pushHistory();
  const id = uniqueId(item.key);
  const node = item.kind === 'SUBGRAPH'
    ? { id, kind: 'SUBGRAPH', subgraph: item.key, subgraph_version: '', type: 'SUBGRAPH', timeout_ms: 3000 }
    : { id, kind: 'OPERATOR', operator: item.key, operator_version: '', type: inferNodeType(item), timeout_ms: 3000 };

  const maxX = props.graph.nodes.reduce((m, n) => Math.max(m, Number(n._x) || 0), 0);
  node._x = maxX ? maxX + NODE_W + COL_GAP : PAD;
  node._y = PAD + (props.graph.nodes.length % 4) * (NODE_H + ROW_GAP);

  props.graph.nodes.push(node);
  if (!props.graph.entry_node) props.graph.entry_node = id;
  if (props.graph.nodes.length > 1) props.graph.exit_node = id;
  activeNodeId.value = id;
  syncFromGraph({ keepPositions: false });
  nextTick(() => fitView({ padding: 0.25, duration: 220 }));
}

function removeNode(id) {
  if (!props.editable) return;
  pushHistory();
  props.graph.nodes = props.graph.nodes.filter((n) => n.id !== id);
  props.graph.edges = props.graph.edges.filter((e) => e.from_node !== id && e.to_node !== id);
  if (props.graph.entry_node === id) props.graph.entry_node = props.graph.nodes[0]?.id || '';
  if (props.graph.exit_node === id) props.graph.exit_node = props.graph.nodes[props.graph.nodes.length - 1]?.id || '';
  if (activeNodeId.value === id) activeNodeId.value = '';
  syncFromGraph({ keepPositions: false });
}

function removeEdge(index) {
  if (!props.editable) return;
  pushHistory();
  props.graph.edges.splice(index, 1);
  syncFromGraph();
}

function setEntry(id) {
  if (!props.editable) return;
  pushHistory();
  props.graph.entry_node = id;
  syncFromGraph();
}

function setExit(id) {
  if (!props.editable) return;
  pushHistory();
  props.graph.exit_node = id;
  syncFromGraph();
}

function onNodeClick({ node }) {
  activeNodeId.value = node.id;
}

function onEdgeClick() {
  activeNodeId.value = '';
}

function onNodesDelete(nodes) {
  if (!props.editable || !nodes?.length) return;
  pushHistory();
  const ids = new Set(nodes.map((n) => n.id));
  props.graph.nodes = props.graph.nodes.filter((n) => !ids.has(n.id));
  props.graph.edges = props.graph.edges.filter((e) => !ids.has(e.from_node) && !ids.has(e.to_node));
  if (ids.has(props.graph.entry_node)) props.graph.entry_node = props.graph.nodes[0]?.id || '';
  if (ids.has(props.graph.exit_node)) props.graph.exit_node = props.graph.nodes[props.graph.nodes.length - 1]?.id || '';
  syncFromGraph({ keepPositions: false });
}

function onEdgesDelete(edges) {
  if (!props.editable || !edges?.length) return;
  pushHistory();
  const keys = new Set(edges.map((e) => `${e.source}->${e.target}`));
  props.graph.edges = props.graph.edges.filter((e) => !keys.has(`${e.from_node}->${e.to_node}`));
  syncFromGraph();
}

function onConnect(params) {
  if (!props.editable) return;
  const from = params.source;
  const to = params.target;
  if (!from || !to) return;
  if (from === to) {
    emit('toast', { title: '不能自连', message: '节点不能连接到自身。', type: 'WARN' });
    return;
  }
  if (props.graph.edges.some((e) => e.from_node === from && e.to_node === to)) {
    emit('toast', { title: '连线已存在', message: `${from} → ${to} 已在编排中。`, type: 'INFO' });
    return;
  }
  // 环路防御：to 可达 from 时拒绝
  const adj = new Map();
  props.graph.edges.forEach((e) => {
    if (!adj.has(e.from_node)) adj.set(e.from_node, []);
    adj.get(e.from_node).push(e.to_node);
  });
  const seen = new Set();
  const stack = [to];
  while (stack.length) {
    const cur = stack.pop();
    if (cur === from) {
      emit('toast', { title: '不允许成环', message: `${to} 可达 ${from}，添加该边会构成环路。`, type: 'ERROR' });
      return;
    }
    if (seen.has(cur)) continue;
    seen.add(cur);
    (adj.get(cur) || []).forEach((n) => stack.push(n));
  }
  pushHistory();
  props.graph.edges.push({ from_node: from, to_node: to });
  syncFromGraph();
}
</script>

<style scoped>
.gwrap {
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr) 250px;
  gap: 12px;
  align-items: start;
}

@media (max-width: 1100px) {
  .gwrap { grid-template-columns: 1fr; }
}

.gpalette,
.ginspector {
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gpalette-head {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-tertiary);
  letter-spacing: 0.08em;
  display: flex;
  justify-content: space-between;
}

.gpalette-count { color: var(--accent); }
.gfilter { font-size: 11.5px; padding: 5px 8px; }
.gpalette-scroll { max-height: 560px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.gpalette-group { font-size: 10.5px; color: var(--accent); font-weight: 700; font-family: var(--font-mono); margin-top: 6px; }

.gpalette-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding: 7px 9px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  cursor: pointer;
  text-align: left;
  color: var(--text-primary);
  font-family: inherit;
}

.gpalette-card.addable { box-shadow: inset 0 0 0 1px rgba(0, 113, 227, 0.22); }
.gpalette-card:hover:not(:disabled) { border-color: var(--accent); }
.gpalette-card:disabled { cursor: default; opacity: 0.7; }
.gpalette-card-head { display: flex; justify-content: space-between; align-items: center; gap: 4px; }
.gpalette-name { font-weight: 600; font-size: 11.5px; word-break: break-all; }
.tag-op { font-size: 9px; padding: 1px 4px; }
.tag-sub { font-size: 9px; padding: 1px 4px; background: var(--status-warning-soft); color: var(--status-warning); }
.gpalette-desc { font-size: 10px; color: var(--text-tertiary); line-height: 1.4; margin-top: 2px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }

.gcanvas-wrap { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.gcanvas-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.gcanvas-title { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }

.gtools { display: flex; align-items: center; gap: 4px; }
.gtool {
  min-width: 26px;
  height: 26px;
  padding: 0 7px;
  border-radius: 7px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
}
.gtool:hover:not(:disabled) { color: var(--accent); border-color: rgba(0, 113, 227, 0.3); }
.gtool:disabled { opacity: 0.4; cursor: default; }
.gtool-text { font-size: 10.5px; font-weight: 600; }
.gtool-divider { width: 1px; height: 14px; background: var(--glass-border-subtle); margin: 0 2px; }

.gcanvas {
  position: relative;
  height: 500px;
  min-height: 360px;
  overflow: hidden;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  border-radius: var(--radius-md);
}

.gcanvas :deep(.vue-flow) {
  width: 100%;
  height: 100%;
  background: transparent;
}

.gcanvas :deep(.vue-flow__node) {
  width: 190px;
  padding: 0;
  border: none;
  background: transparent;
  font-family: inherit;
}

.gcanvas :deep(.vue-flow__handle) {
  width: 8px;
  height: 8px;
  border: 1px solid var(--accent);
  background: var(--glass-surface-solid, #fff);
}

.gcanvas :deep(.vue-flow__controls) {
  border-radius: 9px;
  overflow: hidden;
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
}

.gcanvas :deep(.vue-flow__minimap) {
  border-radius: 9px;
  overflow: hidden;
  border: 1px solid var(--glass-border);
  background: var(--glass-surface);
}

.gnode-box {
  width: 190px;
  min-height: 86px;
  background: var(--glass-surface-solid, rgba(255, 255, 255, 0.96));
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 9px 12px;
  cursor: grab;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  box-sizing: border-box;
}

.gnode-box:active { cursor: grabbing; }
.gnode-box:hover { border-color: var(--accent); }
.gnode-box.selected { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glass, rgba(0, 113, 227, 0.14)); }
.gnode-box.entry { border-left: 3px solid var(--status-success); }
.gnode-box.exit { border-right: 3px solid var(--accent); }
.gnode-box.sub { border-style: dashed; background: var(--status-warning-soft); }
.gnode-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.gnode-badges { display: flex; gap: 3px; }
.gbadge { font-size: 8.5px; font-family: var(--font-mono); font-weight: 700; padding: 1px 4px; border-radius: 3px; background: var(--status-success-soft); color: var(--status-success); }
.gbadge.exit { background: var(--accent-glass); color: var(--accent); }
.gnode-name { font-weight: 600; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gnode-ref { font-size: 10px; font-family: var(--font-mono); color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }

.gc-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px;
  color: var(--text-tertiary);
  font-size: 12px;
  pointer-events: none;
}

.ghint {
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--text-tertiary);
}

.ginspector-card { background: var(--glass-surface); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
.glabel { font-size: 11px; color: var(--text-tertiary); }
.gvalue { font-weight: 600; font-size: 14px; word-break: break-all; }
.gmono { font-family: var(--font-mono); font-size: 10.5px; color: var(--accent); word-break: break-all; }
.gbtn-row { display: flex; gap: 6px; }
.gmini { padding: 4px 10px; font-size: 10.5px; font-family: var(--font-mono); }
.gmini.on { background: var(--accent); color: #fff; border-color: var(--accent); }
.gdanger { margin-top: 4px; color: var(--status-danger); border-color: rgba(192, 57, 43, 0.3); }
.gedge-row { display: flex; justify-content: space-between; align-items: center; gap: 6px; }
.gedge-del { border: none; background: none; color: var(--status-danger); cursor: pointer; font-size: 13px; }
.gempty { padding: 12px; text-align: center; color: var(--text-tertiary); font-size: 12px; }
.gshortcut { display: flex; align-items: center; gap: 5px; font-size: 10.5px; color: var(--text-tertiary); }
.gshortcut kbd { font-family: var(--font-mono); font-size: 9px; padding: 1px 5px; border-radius: 4px; border: 1px solid var(--glass-border-subtle); background: var(--glass-surface); }
</style>
