<template>
  <!--
    A layered flow diagram of a resolved plan (goal reverse lookup or a saved flow).

    Nodes are laid out in dependency layers: a node sits one column right of its
    prerequisites. Every node is clickable — a single click selects it (and the
    parent shows its detail), the fill button jumps straight into the document form.
  -->
  <div class="sop-graph" :class="{ 'sop-graph-empty': !nodes.length }">
    <!-- Loading -->
    <div v-if="loading" class="sop-graph-loading">
      <span class="loading-spinner"></span>
      <span>正在装配流程图谱...</span>
    </div>

    <!-- Empty -->
    <div v-else-if="!nodes.length" class="sop-graph-empty-box">
      <span class="sop-graph-empty-text">该流程暂无可展示的节点</span>
    </div>

    <!-- Graph -->
    <div
      v-else
      class="sop-graph-canvas"
      ref="canvasRef"
      :style="{ height: `${svgHeight}px`, minWidth: `${svgWidth}px` }"
    >
      <svg class="sop-graph-svg" :width="svgWidth" :height="svgHeight" :viewBox="`0 0 ${svgWidth} ${svgHeight}`">
        <defs>
          <marker id="sop-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-tertiary)" />
          </marker>
          <marker id="sop-arrow-active" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)" />
          </marker>
        </defs>

        <!-- Edges -->
        <g class="sop-graph-edges">
          <path
            v-for="edge in renderedEdges"
            :key="`${edge.from}-${edge.to}`"
            :d="edge.path"
            class="sop-graph-edge"
            :class="{ active: edge.active }"
            :marker-end="edge.active ? 'url(#sop-arrow-active)' : 'url(#sop-arrow)'"
          />
        </g>
      </svg>

      <!-- Nodes are HTML so text stays crisp and accessible -->
      <button
        v-for="node in positionedNodes"
        :key="node.node_id"
        type="button"
        class="sop-graph-node"
        :class="[
          node.kind === 'subgraph' ? 'is-subgraph' : 'is-document',
          { active: node.node_id === selectedId, optional: !node.required },
        ]"
        :style="node.style"
        :title="node.description"
        @click="$emit('select-node', node)"
      >
        <span class="sop-graph-node-head">
          <span class="sop-graph-node-stage">{{ String(node.stage).padStart(2, '0') }}</span>
          <span v-if="node.kind === 'subgraph'" class="sop-graph-node-kind">子图</span>
        </span>
        <span class="sop-graph-node-name">{{ node.name }}</span>
        <span class="sop-graph-node-foot">
          <span class="sop-graph-node-fields">
            {{ node.kind === 'subgraph' ? '含子文书' : `${(node.required_fields || []).length} 项待填` }}
          </span>
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
});

defineEmits(['select-node', 'open-node']);

const canvasRef = ref(null);

const NODE_W = 152;
const NODE_H = 86;
const GAP_X = 46;
const GAP_Y = 18;
const PAD = 14;

/**
 * Assign each node a column equal to its longest distance from a root, so a
 * prerequisite always sits to the left of the node that depends on it.
 */
const layeredNodes = computed(() => {
  const ids = props.nodes.map((n) => n.node_id);
  const idSet = new Set(ids);

  const incoming = new Map(ids.map((id) => [id, []]));
  for (const edge of props.edges || []) {
    if (idSet.has(edge.from_node) && idSet.has(edge.to_node)) {
      incoming.get(edge.to_node).push(edge.from_node);
    }
  }

  const depth = new Map(ids.map((id) => [id, 0]));
  // Iterate to a fixed point; the graph is small and the bound prevents cycles
  // from looping forever.
  for (let pass = 0; pass < ids.length; pass++) {
    let changed = false;
    for (const id of ids) {
      for (const parent of incoming.get(id)) {
        const candidate = (depth.get(parent) ?? 0) + 1;
        if (candidate > depth.get(id)) {
          depth.set(id, candidate);
          changed = true;
        }
      }
    }
    if (!changed) break;
  }

  const columns = new Map();
  for (const node of props.nodes) {
    const col = depth.get(node.node_id) ?? 0;
    if (!columns.has(col)) columns.set(col, []);
    columns.get(col).push(node);
  }
  return { depth, columns };
});

const positionedNodes = computed(() => {
  const { depth, columns } = layeredNodes.value;
  const out = [];
  let maxRows = 0;
  for (const [col, list] of columns) {
    maxRows = Math.max(maxRows, list.length);
    list.forEach((node, row) => {
      out.push({
        ...node,
        _col: col,
        _row: row,
        style: {
          left: `${PAD + col * (NODE_W + GAP_X)}px`,
          top: `${PAD + row * (NODE_H + GAP_Y)}px`,
          width: `${NODE_W}px`,
          height: `${NODE_H}px`,
        },
      });
    });
  }
  return out;
});

const svgWidth = computed(() => {
  const { columns } = layeredNodes.value;
  const colCount = Math.max(columns.size, 1);
  return PAD * 2 + colCount * NODE_W + (colCount - 1) * GAP_X;
});

const svgHeight = computed(() => {
  const { columns } = layeredNodes.value;
  const maxRows = Math.max(
    ...Array.from(columns.values()).map((list) => list.length),
    1
  );
  return PAD * 2 + maxRows * NODE_H + (maxRows - 1) * GAP_Y;
});

/**
 * Orthogonal (right-angle) edge routing.
 *
 * Each edge leaves its source on the right edge, runs horizontally into the
 * vertical gutter that separates the two columns, turns 90 degrees there, and
 * enters the target on its left edge. The gutter is shared, so parallel edges
 * between the same pair of columns are offset vertically to avoid overlapping.
 * A small rounded corner keeps the right-angle reading without sharp joins.
 */
const renderedEdges = computed(() => {
  const byId = new Map(positionedNodes.value.map((n) => [n.node_id, n]));
  const out = [];

  // Group edges by the column pair so each can get its own lane in the gutter.
  const laneUsage = new Map();
  const edges = props.edges || [];

  for (const edge of edges) {
    const from = byId.get(edge.from_node);
    const to = byId.get(edge.to_node);
    if (!from || !to) continue;

    const x1 = PAD + from._col * (NODE_W + GAP_X) + NODE_W;
    const y1 = PAD + from._row * (NODE_H + GAP_Y) + NODE_H / 2;
    const x2 = PAD + to._col * (NODE_W + GAP_X);
    const y2 = PAD + to._row * (NODE_H + GAP_Y) + NODE_H / 2;

    const pairKey = `${from._col}-${to._col}`;
    const lane = laneUsage.get(pairKey) || 0;
    laneUsage.set(pairKey, lane + 1);

    // The vertical run happens in the gutter between the two columns. When the
    // target sits in the same column (or to the left) we route out to a gutter
    // further right so the line never cuts through a node box.
    const gutterX =
      to._col > from._col
        ? x1 + GAP_X * 0.5
        : x1 + GAP_X * 0.75 + lane * 10;

    // Offset the horizontal run slightly per lane so parallel edges stay apart.
    const offset = lane * 7;
    const startY = y1 + offset;
    const endY = y2 + offset;

    const radius = 8;
    const dirX = gutterX > x1 ? 1 : -1;
    const r = Math.min(radius, Math.abs(gutterX - x1) / 2, Math.abs(endY - startY) / 2);

    // Horizontal from source to the corner, vertical to the target row, then
    // horizontal into the target. Each turn is a 90 degree bend.
    const corner1X = gutterX - dirX * r;
    const corner2X = gutterX + dirX * r;

    const path = [
      `M ${x1} ${startY}`,
      `L ${corner1X} ${startY}`,
      `Q ${gutterX} ${startY} ${gutterX} ${startY + r * Math.sign(endY - startY || 1)}`,
      `L ${gutterX} ${endY - r * Math.sign(endY - startY || 1)}`,
      `Q ${gutterX} ${endY} ${corner2X} ${endY}`,
      `L ${x2} ${endY}`,
    ].join(' ');

    out.push({
      from: edge.from_node,
      to: edge.to_node,
      path,
      active:
        props.selectedId === edge.from_node || props.selectedId === edge.to_node,
    });
  }
  return out;
});
</script>

<style scoped>
.sop-graph {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.sop-graph-canvas {
  position: relative;
  overflow: auto;
  padding-bottom: 8px;
  scrollbar-width: thin;
}

.sop-graph-svg {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  overflow: visible;
  /* Edges render below the node cards so a line never paints over a node. */
  z-index: 1;
}

.sop-graph-edge {
  fill: none;
  stroke: var(--text-tertiary);
  stroke-width: 1.4;
  opacity: 0.45;
  transition: stroke 0.2s ease, opacity 0.2s ease;
}

.sop-graph-edge.active {
  stroke: var(--accent);
  opacity: 0.9;
  stroke-width: 1.8;
}

.sop-graph-node {
  position: absolute;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s ease, box-shadow 0.18s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  /* Node cards sit above the connector layer. */
  z-index: 2;
}

.sop-graph-node:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 113, 227, 0.4);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.sop-graph-node.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.18);
}

.sop-graph-node.is-subgraph {
  border-style: solid;
  border-color: var(--accent-glow);
  background: linear-gradient(150deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
}

.sop-graph-node.optional {
  opacity: 0.72;
  border-style: dashed;
}

.sop-graph-node-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-shrink: 0;
}

.sop-graph-node-stage {
  font-family: var(--font-mono, monospace);
  font-size: 9.5px;
  color: var(--text-tertiary);
}

.sop-graph-node-kind {
  font-size: 9px;
  font-weight: 700;
  padding: 0 5px;
  border-radius: 4px;
  background: var(--accent-glass);
  color: var(--accent);
}

.sop-graph-node-name {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
  flex: 1;
  min-height: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sop-graph-node-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-shrink: 0;
  margin-top: auto;
}

.sop-graph-node-fields {
  font-size: 10px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.sop-graph-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 28px 20px;
  font-size: 12.5px;
  color: var(--text-tertiary);
}

.sop-graph-empty-box {
  padding: 28px 20px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-tertiary);
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 113, 227, 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

[data-theme="dark"] .sop-graph-node {
  background: rgba(26, 29, 36, 0.75);
  border-color: rgba(255, 255, 255, 0.1);
}
</style>
