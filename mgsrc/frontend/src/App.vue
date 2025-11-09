<template>
  <div class="app-shell">
    <aside class="sidebar">
      <header>
        <h1>fedoc multigraph</h1>
        <p class="subtitle">Frontend Dashboard</p>
      </header>
      <nav>
        <button class="nav-button" @click="refreshData">Обновить данные</button>
        <button class="nav-button" :disabled="!canUndo" @click="undo">Отменить</button>
        <button class="nav-button" :disabled="!canRedo" @click="redo">Повторить</button>
        <button class="nav-button" @click="requestSelection">Получить выделение</button>
      </nav>
      <section class="status-panel">
        <h2>Состояние</h2>
        <ul>
          <li>API: <span :class="{ ok: apiStatus === 'ok', fail: apiStatus !== 'ok' }">{{ apiStatusLabel }}</span></li>
          <li>WS: <span :class="{ ok: wsConnected, fail: !wsConnected }">{{ wsConnected ? 'подключено' : 'нет соединения' }}</span></li>
          <li v-if="activeProjectId !== null">Проект: <span>{{ activeProjectName }}</span></li>
          <li>Снимков: <span>{{ historyLabel }}</span></li>
        </ul>
      </section>
    </aside>
    <main class="workspace">
      <GraphCanvas
        :nodes="activeNodes"
        :edges="activeEdges"
        :selected-nodes="selection.nodes"
        @select="handleGraphSelect"
      />
    </main>
    <section class="details-panel">
      <SelectionPanel :selection="selection" />
    </section>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from "vue";
import GraphCanvas from "./components/GraphCanvas.vue";
import SelectionPanel from "./components/SelectionPanel.vue";
import { useApi } from "./services/api";
import { useRealtime } from "./services/realtime";
import { useGraphHistory } from "./stores/graphHistory";

const api = useApi();
const realtime = useRealtime();
const history = useGraphHistory();

const apiStatus = ref("unknown");
const wsConnected = ref(false);

const activeSnapshot = history.activeSnapshot;
const selection = history.selection;
const canUndo = computed(() => history.canUndo.value);
const canRedo = computed(() => history.canRedo.value);
const historyDepth = history.depth;
const historyPointer = history.pointer;
const historyLabel = computed(() => {
  const depth = historyDepth.value;
  const pointer = historyPointer.value;
  if (!depth || pointer < 0) {
    return "0/0";
  }
  return `${pointer + 1}/${depth}`;
});
const activeProjectId = ref<number | null>(null);
const activeProjectName = ref<string>("");

const activeNodes = computed(() => activeSnapshot.value.nodes);
const activeEdges = computed(() => activeSnapshot.value.edges);

const apiStatusLabel = computed(() => {
  switch (apiStatus.value) {
    case "ok":
      return "доступно";
    case "error":
      return "ошибка";
    default:
      return "неизвестно";
  }
});

async function refreshData() {
  if (activeProjectId.value === null) {
    const projects = await api.listProjects();
    if (!projects.length) {
      throw new Error("No projects available");
    }
    activeProjectId.value = projects[0].id;
    activeProjectName.value = projects[0].name;
  }

  const raw = await api.getProjectGraph(activeProjectId.value || 53);
  history.pushState(normalizeGraph(raw));
}

function requestSelection() {
  realtime.requestSelection();
}

function pushSelection(payload: { nodes: string[]; edges: string[] }) {
  realtime.pushSelection(payload);
}

function handleGraphSelect(payload: { nodes: string[]; edges: string[] }) {
  history.setSelection(payload);
  pushSelection(payload);
}

function undo() {
  if (history.undo()) {
    pushSelection(history.selection.value);
  }
}

function redo() {
  if (history.redo()) {
    pushSelection(history.selection.value);
  }
}

function normalizeGraph(raw: any) {
  const graph = raw?.graph ?? raw ?? {};

  const blockNodes = (graph.blocks || []).map((block: any) => ({
    id: String(block.id ?? block.raw_id),
    label: block.properties?.name || block.label || String(block.id ?? "block"),
    group: "block",
  }));

  const designNodes = (graph.designs || []).map((design: any) => ({
    id: String(design.id ?? design.raw_id),
    label: design.properties?.name || design.label || String(design.id ?? "design"),
    group: "design",
    blockId: design.block_id ? String(design.block_id) : undefined,
  }));

  const designEdges = (graph.design_edges || []).map((edge: any) => ({
    id: String(edge.id ?? edge.edge_id ?? `${edge.start_id}-${edge.end_id}`),
    from: String(edge.start_id ?? edge.source ?? edge.from),
    to: String(edge.end_id ?? edge.target ?? edge.to),
    label: edge.properties?.relation_type || edge.label,
  }));

  const blockLinks = designNodes
    .filter((node: any) => node.blockId)
    .map((node: any) => ({
      id: `block:${node.blockId}->design:${node.id}`,
      from: node.blockId,
      to: node.id,
      label: "contains",
    }));

  const seenIds = new Set<string>();
  const nodes = [...blockNodes, ...designNodes].filter((node) => {
    if (seenIds.has(node.id)) {
      return false;
    }
    seenIds.add(node.id);
    return true;
  });

  const edges = [...designEdges, ...blockLinks];

  return { nodes, edges };
}

onMounted(async () => {
  apiStatus.value = (await api.healthCheck()) ? "ok" : "error";

  realtime.onSelection((payload) => {
    history.setSelection(payload);
  });
  realtime.onConnectionChange((connected) => {
    wsConnected.value = connected;
  });
  realtime.onGraphUpdate(() => {
    refreshData();
  });

  realtime.connect();
  await refreshData();
});
</script>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  grid-template-rows: 100vh;
}

.sidebar {
  padding: 1.5rem;
  background: #111827;
  color: #f9fafb;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar h1 {
  margin: 0;
  font-size: 1.4rem;
}

.subtitle {
  margin: 0;
  color: #9ca3af;
}

.nav-button {
  width: 100%;
  margin-bottom: 0.5rem;
  padding: 0.6rem 1rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.nav-button:disabled {
  opacity: 0.4;
  cursor: default;
}

.nav-button:hover:enabled {
  background: #1d4ed8;
}

.status-panel ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.status-panel li {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.3rem;
}

.status-panel .ok {
  color: #22c55e;
}

.status-panel .fail {
  color: #ef4444;
}

.workspace {
  background: white;
  padding: 1rem;
}

.details-panel {
  background: #f3f4f6;
  padding: 1rem;
  border-left: 1px solid #e5e7eb;
}
</style>
