<template>
  <div class="gwrap">
    <!-- 左侧：可编排资产面板（算子 / 已发布子图） -->
    <div class="gpalette">
      <div class="gpalette-head">
        <span>{{ allowSubgraphs ? 'OPERATORS / SUBGRAPHS' : 'OPERATORS' }}</span>
        <span class="gpalette-count">{{ paletteItems.length }} 项</span>
      </div>
      <input v-model="filterText" class="glass-input gfilter" placeholder="按名称/域筛选" />
      <div class="gpalette-scroll">
        <template v-for="group in groupedPalette" :key="group.domain">
          <div class="gpalette-group">{{ group.domain }} · {{ group.items.length }}</div>
          <div
            v-for="item in group.items"
            :key="item.kind + item.key"
            class="gpalette-card"
            :class="{ addable: editable }"
            :title="editable ? `点击加入画布：${item.label}` : item.description"
            @click="addNode(item)"
          >
            <div class="gpalette-card-head">
              <span class="gpalette-name">{{ item.label }}</span>
              <span class="mono-tag" :class="item.kind === 'SUBGRAPH' ? 'tag-sub' : 'tag-op'">{{ item.kind === 'SUBGRAPH' ? '子图' : (item.tag || '算子') }}</span>
            </div>
            <div class="gpalette-desc">{{ item.description }}</div>
          </div>
        </template>
        <div v-if="paletteItems.length === 0" class="gempty">暂无可编排资产。</div>
      </div>
    </div>

    <!-- 中部：分层 DAG 画布 -->
    <div class="gcanvas-wrap">
      <div class="gcanvas-head">
        <span class="gcanvas-title">
          <template v-if="graph.nodes.length > 0">{{ graph.nodes.length }} 节点 · {{ graph.edges.length }} 边</template>
          <template v-else>画布为空</template>
        </span>
        <span v-if="editable" class="mono-tag gedit-tag">编辑中：点资产添加 · 点两节点连线 · 悬停删除</span>
      </div>
      <div class="gcanvas">
        <svg class="gsvg">
          <defs>
            <marker id="geditor-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)" />
            </marker>
          </defs>
          <line
            v-for="e in drawnEdges"
            :key="e.key"
            :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
            class="gedge"
            marker-end="url(#geditor-arrow)"
          />
        </svg>

        <div
          v-for="node in layoutNodes"
          :key="node.id"
          class="gnode-cell"
          :style="{ left: node.x + 'px', top: node.y + 'px', width: NODE_W + 'px' }"
        >
          <div
            class="gnode-box"
            :class="{
              selected: activeNodeId === node.id,
              linking: linkingFrom === node.id,
              entry: graph.entry_node === node.id,
              exit: graph.exit_node === node.id,
              sub: nodeKind(node) === 'SUBGRAPH',
            }"
            :title="nodeRefLabel(node)"
            @click="onNodeClick(node)"
          >
            <div class="gnode-meta">
              <span class="mono-tag">{{ nodeKind(node) === 'SUBGRAPH' ? 'SUBGRAPH' : node.type }}</span>
              <span class="gnode-badges">
                <span v-if="graph.entry_node === node.id" class="gbadge">ENTRY</span>
                <span v-if="graph.exit_node === node.id" class="gbadge exit">EXIT</span>
              </span>
            </div>
            <div class="gnode-name">{{ node.id }}</div>
            <div class="gnode-ref">{{ nodeRefLabel(node) }}</div>
          </div>
          <button v-if="editable" class="gnode-del" title="删除节点" @click.stop="removeNode(node.id)">×</button>
        </div>

        <div v-if="layoutNodes.length === 0" class="gempty gc-empty">
          {{ editable ? '从左侧点击算子/子图加入画布，先连成一条单向链路。' : '该版本暂无编排内容。' }}
        </div>
      </div>
    </div>

    <!-- 右侧：检视器 -->
    <div class="ginspector">
      <div class="ginspector-card" v-if="activeNode">
        <div class="glabel">选中节点</div>
        <div class="gvalue">{{ activeNode.id }}</div>
        <div class="gmono">{{ nodeRefLabel(activeNode) }}</div>
        <div class="gmono">类型: {{ nodeKind(activeNode) === 'SUBGRAPH' ? 'SUBGRAPH' : activeNode.type }}</div>
        <template v-if="editable">
          <div class="glabel" style="margin-top: 8px;">设为入口/出口</div>
          <div class="gbtn-row">
            <button class="btn-liquid-outline gmini" :class="{ on: graph.entry_node === activeNode.id }" @click="graph.entry_node = activeNode.id">ENTRY</button>
            <button class="btn-liquid-outline gmini" :class="{ on: graph.exit_node === activeNode.id }" @click="graph.exit_node = activeNode.id">EXIT</button>
          </div>
        </template>
      </div>
      <div class="ginspector-card" v-else>
        <div class="gempty" style="padding: 10px 0;">点击节点查看属性{{ editable ? '；依次点击两个节点可连线' : '' }}。</div>
      </div>

      <div class="ginspector-card">
        <div class="glabel">连线</div>
        <div v-for="(e, i) in graph.edges" :key="`${e.from_node}->${e.to_node}`" class="gedge-row">
          <span class="gmono">{{ e.from_node }} → {{ e.to_node }}</span>
          <button v-if="editable" class="gedge-del" title="删除此边" @click="graph.edges.splice(i, 1)">×</button>
        </div>
        <div v-if="graph.edges.length === 0" class="gempty" style="padding: 6px 0;">暂无边</div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 图编辑器：子图（编排算子）与场景（编排算子 + 子图）共用。
 * 通过原地修改 props.graph（响应式草稿）工作，父组件负责保存/发布。
 */
import { computed, ref } from 'vue';

const props = defineProps({
  graph: { type: Object, required: true }, // {entry_node, exit_node, nodes, edges}
  editable: { type: Boolean, default: false },
  allowSubgraphs: { type: Boolean, default: false },
  palette: { type: Array, default: () => [] }, // {kind, key, label, domain, description, tag}
});

const emit = defineEmits(['toast']);

const NODE_W = 190;
const NODE_H = 86;
const COL_GAP = 70;
const ROW_GAP = 26;
const PAD = 24;

const filterText = ref('');
const activeNodeId = ref('');
const linkingFrom = ref('');

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
  const id = uniqueId(item.key);
  const node =
    item.kind === 'SUBGRAPH'
      ? { id, kind: 'SUBGRAPH', subgraph: item.key, subgraph_version: '', type: 'SUBGRAPH', timeout_ms: 3000 }
      : { id, kind: 'OPERATOR', operator: item.key, operator_version: '', type: inferNodeType(item), timeout_ms: 3000 };
  props.graph.nodes.push(node);
  if (!props.graph.entry_node) props.graph.entry_node = id;
  // 首节点同时占位 entry/exit；链式追加时出口始终后移到最新节点
  if (props.graph.nodes.length > 1) props.graph.exit_node = id;
  activeNodeId.value = id;
  linkingFrom.value = '';
}

function onNodeClick(node) {
  if (!props.editable) {
    activeNodeId.value = node.id;
    return;
  }
  if (linkingFrom.value && linkingFrom.value !== node.id) {
    addEdge(linkingFrom.value, node.id);
    linkingFrom.value = '';
    return;
  }
  linkingFrom.value = linkingFrom.value === node.id ? '' : node.id;
  activeNodeId.value = node.id;
}

function addEdge(from, to) {
  if (from === to) return;
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
  props.graph.edges.push({ from_node: from, to_node: to });
}

function removeNode(id) {
  props.graph.nodes = props.graph.nodes.filter((n) => n.id !== id);
  props.graph.edges = props.graph.edges.filter((e) => e.from_node !== id && e.to_node !== id);
  if (props.graph.entry_node === id) props.graph.entry_node = props.graph.nodes[0]?.id || '';
  if (props.graph.exit_node === id) props.graph.exit_node = props.graph.nodes[props.graph.nodes.length - 1]?.id || '';
  if (activeNodeId.value === id) activeNodeId.value = '';
  if (linkingFrom.value === id) linkingFrom.value = '';
}

// Kahn 分层布局
const layoutNodes = computed(() => {
  const nodes = props.graph.nodes;
  const edges = props.graph.edges;
  if (nodes.length === 0) return [];
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
  while (queue.length && guard++ < 1000) {
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
    queue = next;
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
    colIds.forEach((id, i) => pos.set(id, { x: PAD + d * (NODE_W + COL_GAP), y: PAD + i * (NODE_H + ROW_GAP) }));
  }
  return nodes.map((n) => ({ ...n, x: pos.get(n.id).x, y: pos.get(n.id).y }));
});

const drawnEdges = computed(() => {
  const byId = new Map(layoutNodes.value.map((n) => [n.id, n]));
  return props.graph.edges
    .filter((e) => byId.has(e.from_node) && byId.has(e.to_node))
    .map((e) => {
      const a = byId.get(e.from_node);
      const b = byId.get(e.to_node);
      return { key: `${e.from_node}->${e.to_node}`, x1: a.x + NODE_W, y1: a.y + NODE_H / 2, x2: b.x, y2: b.y + NODE_H / 2 };
    });
});
</script>

<style scoped>
.gwrap { display: grid; grid-template-columns: 240px 1fr 260px; gap: 14px; align-items: start; }
@media (max-width: 1100px) { .gwrap { grid-template-columns: 1fr; } }

.gpalette, .ginspector { background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.gpalette-head { font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary); letter-spacing: 0.08em; display: flex; justify-content: space-between; }
.gpalette-count { color: var(--accent); }
.gfilter { font-size: 11.5px; padding: 5px 8px; }
.gpalette-scroll { max-height: 520px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.gpalette-group { font-size: 10.5px; color: var(--accent); font-weight: 700; font-family: var(--font-mono); margin-top: 6px; }
.gpalette-card { padding: 7px 9px; border-radius: var(--radius-sm); background: var(--glass-surface); border: 1px solid var(--glass-border); cursor: pointer; }
.gpalette-card.addable { box-shadow: inset 0 0 0 1px rgba(0, 113, 227, 0.25); }
.gpalette-card:hover { border-color: var(--accent); }
.gpalette-card-head { display: flex; justify-content: space-between; align-items: center; gap: 4px; }
.gpalette-name { font-weight: 600; font-size: 11.5px; word-break: break-all; }
.tag-op { font-size: 9px; padding: 1px 4px; }
.tag-sub { font-size: 9px; padding: 1px 4px; background: var(--status-warning-soft); color: var(--status-warning); }
.gpalette-desc { font-size: 10px; color: var(--text-tertiary); line-height: 1.4; margin-top: 2px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }

.gcanvas-wrap { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.gcanvas-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.gcanvas-title { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.gedit-tag { background: var(--status-warning-soft); color: var(--status-warning); }
.gcanvas { position: relative; min-height: 360px; max-height: 520px; overflow: auto; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-md); }
.gsvg { position: absolute; top: 0; left: 0; width: 2000px; height: 1200px; pointer-events: none; }
.gedge { stroke: var(--accent); stroke-width: 2; stroke-dasharray: 5 4; opacity: 0.75; }
.gnode-cell { position: absolute; }
.gnode-box { width: 190px; min-height: 86px; background: var(--glass-surface); border: 1px solid var(--glass-border); border-radius: 10px; padding: 9px 12px; cursor: pointer; transition: all 0.15s ease; box-sizing: border-box; }
.gnode-box:hover { border-color: var(--accent); }
.gnode-box.selected { border-color: var(--accent); background: var(--accent-glass); }
.gnode-box.linking { border-color: var(--status-success); box-shadow: 0 0 0 3px var(--status-success-soft); }
.gnode-box.entry { border-left: 3px solid var(--status-success); }
.gnode-box.exit { border-right: 3px solid var(--accent); }
.gnode-box.sub { border-style: dashed; background: var(--status-warning-soft); }
.gnode-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.gnode-badges { display: flex; gap: 3px; }
.gbadge { font-size: 8.5px; font-family: var(--font-mono); font-weight: 700; padding: 1px 4px; border-radius: 3px; background: var(--status-success-soft); color: var(--status-success); }
.gbadge.exit { background: var(--accent-glass); color: var(--accent); }
.gnode-name { font-weight: 600; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gnode-ref { font-size: 10px; font-family: var(--font-mono); color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
.gnode-del { position: absolute; top: -8px; right: -8px; width: 18px; height: 18px; border-radius: 50%; border: 1px solid var(--status-danger); background: var(--glass-surface); color: var(--status-danger); font-size: 11px; line-height: 1; cursor: pointer; display: none; }
.gnode-cell:hover .gnode-del { display: block; }

.ginspector-card { background: var(--glass-surface); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
.glabel { font-size: 11px; color: var(--text-tertiary); }
.gvalue { font-weight: 600; font-size: 14px; word-break: break-all; }
.gmono { font-family: var(--font-mono); font-size: 10.5px; color: var(--accent); word-break: break-all; }
.gbtn-row { display: flex; gap: 6px; }
.gmini { padding: 4px 10px; font-size: 10.5px; font-family: var(--font-mono); }
.gmini.on { background: var(--accent); color: #fff; border-color: var(--accent); }
.gedge-row { display: flex; justify-content: space-between; align-items: center; gap: 6px; }
.gedge-del { border: none; background: none; color: var(--status-danger); cursor: pointer; font-size: 13px; }
.gempty { padding: 12px; text-align: center; color: var(--text-tertiary); font-size: 12px; }
.gc-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
</style>
