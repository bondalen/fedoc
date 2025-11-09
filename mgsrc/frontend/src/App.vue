<template>
  <div class="app-shell">
    <aside class="sidebar">
      <header>
        <h1>fedoc multigraph</h1>
        <p class="subtitle">Frontend Dashboard</p>
      </header>
      <nav>
        <button class="nav-button" @click="refreshData">Обновить данные</button>
        <button class="nav-button" @click="requestSelection">Получить выделение</button>
      </nav>
      <section class="status-panel">
        <h2>Состояние</h2>
        <ul>
          <li>API: <span :class="{ ok: apiStatus === 'ok', fail: apiStatus !== 'ok' }">{{ apiStatusLabel }}</span></li>
          <li>WS: <span :class="{ ok: wsConnected, fail: !wsConnected }">{{ wsConnected ? 'подключено' : 'нет соединения' }}</span></li>
        </ul>
      </section>
    </aside>
    <main class="workspace">
      <GraphCanvas :nodes="graph.nodes" :edges="graph.edges" />
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

const api = useApi();
const realtime = useRealtime();

const apiStatus = ref("unknown");
const wsConnected = ref(false);
const graph = ref({ nodes: [], edges: [] } as { nodes: any[]; edges: any[] });
const selection = ref({ nodes: [], edges: [] } as { nodes: any[]; edges: any[] });

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

function refreshData() {
  api.getProjectGraph().then((data) => {
    graph.value = data;
  });
}

function requestSelection() {
  realtime.requestSelection();
}

onMounted(async () => {
  apiStatus.value = (await api.healthCheck()) ? "ok" : "error";
  realtime.onSelection((payload) => {
    selection.value = payload;
  });
  realtime.onConnectionChange((connected) => {
    wsConnected.value = connected;
  });
  realtime.connect();
  refreshData();
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

.nav-button:hover {
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
