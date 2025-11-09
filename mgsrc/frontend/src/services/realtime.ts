import { ref } from "vue";

interface SelectionPayload {
  nodes: string[];
  edges: string[];
}

type SelectionListener = (payload: SelectionPayload) => void;
type ConnectionListener = (connected: boolean) => void;

export function useRealtime() {
  const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8080/ws";
  let socket: WebSocket | null = null;

  const selectionListeners: SelectionListener[] = [];
  const connectionListeners: ConnectionListener[] = [];

  function connect() {
    if (socket) {
      socket.close();
    }

    socket = new WebSocket(wsUrl);

    socket.addEventListener("open", () => {
      connectionListeners.forEach((listener) => listener(true));
      subscribeToChannels(["graph_updates", "selection_updates"]);
    });

    socket.addEventListener("close", () => {
      connectionListeners.forEach((listener) => listener(false));
    });

    socket.addEventListener("message", (event) => {
      const payload = JSON.parse(event.data ?? "{}");
      if (payload.type === "selected_nodes" && payload.data) {
        selectionListeners.forEach((listener) => listener(payload.data));
      }
    });
  }

  function send(message: unknown) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn("WebSocket is not ready");
      return;
    }
    socket.send(JSON.stringify(message));
  }

  function subscribeToChannels(channels: string[]) {
    channels.forEach((channel) =>
      send({
        type: "subscribe",
        channel,
      }),
    );
  }

  function requestSelection() {
    send({ type: "get_selected_nodes" });
  }

  function pushSelection(payload: SelectionPayload) {
    send({
      type: "push_selection",
      data: payload,
    });
  }

  function onSelection(listener: SelectionListener) {
    selectionListeners.push(listener);
  }

  function onConnectionChange(listener: ConnectionListener) {
    connectionListeners.push(listener);
  }

  return {
    connect,
    requestSelection,
    pushSelection,
    onSelection,
    onConnectionChange,
  };
}
