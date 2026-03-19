import { dispatch } from "./handlers";

export type ConnectionState = "disconnected" | "connecting" | "authenticating" | "connected" | "error";

export interface RelayCallbacks {
  onStateChange: (state: ConnectionState, error?: string) => void;
}

let ws: WebSocket | null = null;
let currentState: ConnectionState = "disconnected";
let callbacks: RelayCallbacks | null = null;
let intentionalDisconnect = false;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempt = 0;
let lastServerUrl = "";
let lastToken = "";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

function setState(state: ConnectionState, error?: string) {
  currentState = state;
  callbacks?.onStateChange(state, error);
}

export function getState(): ConnectionState {
  return currentState;
}

function clearReconnectTimer() {
  if (reconnectTimer !== null) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function scheduleReconnect() {
  if (intentionalDisconnect || !lastServerUrl) return;

  const delay = Math.min(
    RECONNECT_BASE_MS * Math.pow(2, reconnectAttempt),
    RECONNECT_MAX_MS
  );
  reconnectAttempt++;

  console.log(`[relay] Reconnecting in ${delay}ms (attempt ${reconnectAttempt})`);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (!intentionalDisconnect && callbacks) {
      connect(lastServerUrl, lastToken, callbacks);
    }
  }, delay);
}

export function connect(serverUrl: string, token: string, cb: RelayCallbacks) {
  callbacks = cb;
  intentionalDisconnect = false;
  clearReconnectTimer();

  lastServerUrl = serverUrl;
  lastToken = token;

  if (ws) {
    ws.close();
    ws = null;
  }

  setState("connecting");

  try {
    ws = new WebSocket(serverUrl);
  } catch (err) {
    setState("error", `Failed to connect: ${err}`);
    scheduleReconnect();
    return;
  }

  ws.addEventListener("open", () => {
    setState("authenticating");
    ws!.send(JSON.stringify({ type: "auth", token }));
  });

  ws.addEventListener("message", async (event) => {
    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(typeof event.data === "string" ? event.data : await event.data.text());
    } catch {
      console.error("[relay] Failed to parse message:", event.data);
      return;
    }

    if (msg.type === "auth-ok") {
      reconnectAttempt = 0;
      setState("connected");
      return;
    }

    if (msg.type === "request") {
      const requestId = msg.requestId as string;
      const method = msg.method as string;
      const params = (msg.params as Record<string, unknown>) ?? {};

      try {
        const data = await dispatch(method, params);
        ws?.send(
          JSON.stringify({
            type: "response",
            requestId,
            success: true,
            data,
          })
        );
      } catch (err) {
        ws?.send(
          JSON.stringify({
            type: "response",
            requestId,
            success: false,
            error:
              err instanceof Error
                ? err.message
                : typeof err === "string"
                  ? err
                  : JSON.stringify(err),
          })
        );
      }
    }
  });

  ws.addEventListener("close", (event) => {
    ws = null;
    if (event.code === 4001) {
      setState("error", "Authentication failed");
      // Don't reconnect on auth failure
    } else if (intentionalDisconnect) {
      setState("disconnected");
    } else {
      setState("disconnected");
      scheduleReconnect();
    }
  });

  ws.addEventListener("error", () => {
    setState("error", "WebSocket connection error");
  });
}

export function disconnect() {
  intentionalDisconnect = true;
  clearReconnectTimer();
  reconnectAttempt = 0;
  if (ws) {
    ws.close();
    ws = null;
  }
  setState("disconnected");
}
