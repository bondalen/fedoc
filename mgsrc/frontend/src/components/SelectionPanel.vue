<template>
  <div class="selection-panel">
    <h2>Выделение</h2>
    <section>
      <h3>Узлы</h3>
      <p v-if="!selection.nodes.length">Нет выделенных узлов.</p>
      <ul v-else>
        <li v-for="node in selection.nodes" :key="node">{{ node }}</li>
      </ul>
    </section>
    <section>
      <h3>Рёбра</h3>
      <p v-if="!selection.edges.length">Нет выделенных рёбер.</p>
      <ul v-else>
        <li v-for="edge in selection.edges" :key="edge">{{ edge }}</li>
      </ul>
    </section>
  </div>
</template>

<script lang="ts" setup>
defineProps<{
  selection: { nodes: string[]; edges: string[] };
}>();
</script>

<style scoped>
.selection-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.selection-panel h2 {
  margin: 0;
}

.selection-panel ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
</style>
