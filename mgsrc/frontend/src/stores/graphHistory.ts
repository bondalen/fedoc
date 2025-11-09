import { computed, reactive } from "vue";

type GraphSnapshot = {
  nodes: Array<{ id: string; label?: string }>;
  edges: Array<{ id: string; from: string; to: string; label?: string }>;
  createdAt: number;
};

type Selection = {
  nodes: string[];
  edges: string[];
};

const EMPTY_SNAPSHOT: GraphSnapshot = {
  nodes: [],
  edges: [],
  createdAt: 0,
};

const state = reactive({
  history: [] as GraphSnapshot[],
  pointer: -1,
  selection: { nodes: [] as string[], edges: [] as string[] } as Selection,
  limit: 10,
});

function cloneSnapshot(snapshot: { nodes: any[]; edges: any[] }): GraphSnapshot {
  return {
    nodes: snapshot.nodes.map((node) => ({ ...node })),
    edges: snapshot.edges.map((edge) => ({ ...edge })),
    createdAt: Date.now(),
  };
}

function snapshotsEqual(a: GraphSnapshot, b: GraphSnapshot): boolean {
  if (!a || !b) return false;
  if (a.nodes.length !== b.nodes.length || a.edges.length !== b.edges.length) {
    return false;
  }
  const nodeIdsA = a.nodes.map((n) => n.id).join("|");
  const nodeIdsB = b.nodes.map((n) => n.id).join("|");
  const edgeIdsA = a.edges.map((e) => e.id).join("|");
  const edgeIdsB = b.edges.map((e) => e.id).join("|");
  return nodeIdsA === nodeIdsB && edgeIdsA === edgeIdsB;
}

export function useGraphHistory() {
  const activeSnapshot = computed(() => {
    if (state.pointer >= 0 && state.pointer < state.history.length) {
      return state.history[state.pointer];
    }
    return EMPTY_SNAPSHOT;
  });

  const selection = computed(() => state.selection);

  const canUndo = computed(() => state.pointer > 0);
  const canRedo = computed(() => state.pointer >= 0 && state.pointer < state.history.length - 1);
  const depth = computed(() => state.history.length);
  const pointer = computed(() => state.pointer);

  function pushState(snapshot: { nodes: any[]; edges: any[] }): boolean {
    const cloned = cloneSnapshot(snapshot);

    const current = state.pointer >= 0 ? state.history[state.pointer] : null;
    if (current && snapshotsEqual(current, cloned)) {
      return false;
    }

    if (state.pointer < state.history.length - 1) {
      state.history.splice(state.pointer + 1);
    }

    state.history.push(cloned);

    if (state.history.length > state.limit) {
      state.history.shift();
      state.pointer = state.history.length - 1;
    } else {
      state.pointer = state.history.length - 1;
    }

    state.selection = { nodes: [], edges: [] };
    return true;
  }

  function undo(): boolean {
    if (!canUndo.value) {
      return false;
    }
    state.pointer -= 1;
    return true;
  }

  function redo(): boolean {
    if (!canRedo.value) {
      return false;
    }
    state.pointer += 1;
    return true;
  }

  function setSelection(payload: Selection) {
    state.selection = {
      nodes: [...(payload.nodes || [])],
      edges: [...(payload.edges || [])],
    };
  }

  function clear() {
    state.history = [];
    state.pointer = -1;
    state.selection = { nodes: [], edges: [] };
  }

  return {
    activeSnapshot,
    selection,
    canUndo,
    canRedo,
    depth,
    pointer,
    pushState,
    undo,
    redo,
    setSelection,
    clear,
  };
}
