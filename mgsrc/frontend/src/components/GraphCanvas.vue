<template>
  <div class="graph-canvas">
    <p v-if="!nodes.length">Граф пока пуст — загрузите данные.</p>
    <div v-else>
      <h2>Граф проекта</h2>
      <ul>
        <li v-for="node in nodes" :key="node.id">
          {{ node.name || node.id }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script lang="ts" setup>
interface GraphNode {
  id: string;
  name?: string;
}

interface GraphEdge {
  id: string;
  source?: string;
  target?: string;
}

defineProps<{
  nodes: GraphNode[];
  edges: GraphEdge[];
}>();
</script>

<style scoped>
.graph-canvas {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
  overflow: auto;
}

.graph-canvas ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
</style>
