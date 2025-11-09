<template>
  <div class="graph-canvas">
    <div ref="networkContainer" class="network"></div>
  </div>
</template>

<script lang="ts" setup>
import { Network, type Node, type Edge } from "vis-network";
import { DataSet } from "vis-data/peer/esm/vis-data";
import { onMounted, onBeforeUnmount, ref, watch } from "vue";

interface GraphNode {
  id: string;
  label?: string;
}

interface GraphEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
}

const props = defineProps<{
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodes?: string[];
}>();

const emit = defineEmits<{
  (event: "select", payload: { nodes: string[]; edges: string[] }): void;
}>();

const networkContainer = ref<HTMLDivElement | null>(null);
let network: Network | null = null;
let dataNodes: DataSet<Node> | null = null;
let dataEdges: DataSet<Edge> | null = null;

function initNetwork() {
  if (!networkContainer.value) {
    return;
  }

  dataNodes = new DataSet<Node>();
  dataEdges = new DataSet<Edge>();

  network = new Network(
    networkContainer.value,
    { nodes: dataNodes, edges: dataEdges },
    {
      autoResize: true,
      layout: {
        improvedLayout: true,
        hierarchical: false,
      },
      physics: {
        enabled: true,
        stabilization: {
          iterations: 200,
        },
      },
      nodes: {
        shape: "dot",
        size: 14,
        font: {
          size: 14,
          color: "#111827",
        },
        borderWidth: 2,
        color: {
          background: "#93c5fd",
          border: "#3b82f6",
          highlight: {
            background: "#2563eb",
            border: "#1d4ed8",
          },
        },
      },
      edges: {
        arrows: {
          to: { enabled: true, type: "arrow" },
        },
        smooth: {
          type: "dynamic",
        },
        color: {
          color: "#94a3b8",
          highlight: "#2563eb",
        },
        font: {
          size: 12,
          color: "#475569",
        },
      },
    }
  );

  network.on("select", ({ nodes, edges }) => {
    emit("select", { nodes: nodes as string[], edges: edges as string[] });
  });

  updateData();
}

function updateData() {
  if (!network || !dataNodes || !dataEdges) {
    return;
  }

  const nodes = props.nodes.map((n) => ({ id: n.id, label: n.label || n.id }));
  const edges = props.edges.map((e) => ({ id: e.id, from: (e as any).source || e.from, to: (e as any).target || e.to, label: e.label }));

  dataNodes.clear();
  dataNodes.add(nodes);

  dataEdges.clear();
  dataEdges.add(edges);

  if (props.selectedNodes && props.selectedNodes.length) {
    network.selectNodes(props.selectedNodes, false);
  }
}

onMounted(() => {
  initNetwork();
});

onBeforeUnmount(() => {
  if (network) {
    network.destroy();
    network = null;
  }
});

watch(
  () => [props.nodes, props.edges],
  () => {
    updateData();
  },
  { deep: true }
);

watch(
  () => props.selectedNodes,
  (nodes) => {
    if (!network) return;
    if (nodes && nodes.length) {
      network.selectNodes(nodes, false);
      network.focus(nodes[0], { scale: 1.2, animation: true });
    } else {
      network.unselectAll();
    }
  },
  { deep: true }
);
</script>

<style scoped>
.graph-canvas {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  height: 100%;
  display: flex;
}

.network {
  flex: 1;
  height: calc(100vh - 2rem);
}
</style>
