import { io, type Socket } from "socket.io-client";

interface SelectionPayload {
  nodes: string[];
  edges: string[];
}

type SelectionListener = (payload: SelectionPayload) => void;
type ConnectionListener = (connected: boolean) => void;
type GraphUpdateListener = (payload: any) => void;

export function useRealtime() {
  let defaultUrl = "http://localhost:8080";
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const backendPort = import.meta.env.VITE_BACKEND_PORT ? Number(import.meta.env.VITE_BACKEND_PORT) : 8080;
    defaultUrl = `http://${host}:${backendPort}`;
  }

  const socketUrl = (import.meta.env.VITE_WS_URL || defaultUrl).replace(/\/$/, "");
  const namespace = "/ws";
  let socket: Socket | null = null;

  const selectionListeners: SelectionListener[] = [];
  const connectionListeners: ConnectionListener[] = [];
  const graphListeners: GraphUpdateListener[] = [];

  function connect() {
    if (socket) {
      socket.disconnect();
    }

    socket = io(`${socketUrl}${namespace}`, {
      path: "/socket.io",
      transports: ["websocket"],
      autoConnect: true,
    });

    socket.on("connect", () => {
      connectionListeners.forEach((listener) => listener(true));
      subscribeToChannels(["graph_updates", "selection_updates"]);
    });

    socket.on("disconnect", () => {
      connectionListeners.forEach((listener) => listener(false));
    });

    socket.on("event", (payload: any) => {
      if (!payload) {
        return;
      }
      if (payload.type === "hello") {
        requestSelection();
      }
      if (payload.type === "selected_nodes" && payload.data) {
        selectionListeners.forEach((listener) => listener(payload.data));
      }
      if (payload.type === "graph_updated" && payload.data) {
        graphListeners.forEach((listener) => listener(payload.data));
      }
    });

    socket.on("connect_error", (error) => {
      console.error("Socket.IO connection error", error.message);
    });
  }

  function send(message: unknown) {
    if (!socket || !socket.connected) {
      console.warn("Socket.IO client is not connected");
      return;
    }
    socket.emit("client_event", message);
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

  function onGraphUpdate(listener: GraphUpdateListener) {
    graphListeners.push(listener);
  }

  return {
    connect,
    requestSelection,
    pushSelection,
    onSelection,
    onConnectionChange,
    onGraphUpdate,
  };
}
