import { dispatch } from "./handlers";

export type ConnectionState = "disconnected" | "connecting" | "authenticating" | "connected" | "error";

export interface RelayCallbacks {
  onStateChange: (state: ConnectionState, error?: string) => void;
}

let ws: WebSocket | null = null;
let currentState: ConnectionState = "disconnected";
let callbacks: RelayCallbacks | null = null;

function setState(state: ConnectionState, error?: string) {
  currentState = state;
  callbacks?.onStateChange(state, error);
}

export function getState(): ConnectionState {
  return currentState;
}

export function connect(serverUrl: string, token: string, cb: RelayCallbacks) {
  callbacks = cb;

  if (ws) {
    ws.close();
    ws = null;
  }

  setState("connecting");

  try {
    ws = new WebSocket(serverUrl);
  } catch (err) {
    setState("error", `Failed to connect: ${err}`);
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
            error: err instanceof Error ? err.message : String(err),
          })
        );
      }
    }
  });

  ws.addEventListener("close", (event) => {
    ws = null;
    if (event.code === 4001) {
      setState("error", "Authentication failed");
    } else if (currentState !== "disconnected") {
      setState("disconnected");
    }
  });

  ws.addEventListener("error", () => {
    setState("error", "WebSocket connection error");
  });
}

export function disconnect() {
  if (ws) {
    ws.close();
    ws = null;
  }
  setState("disconnected");
}
