import { type ConnectionState, connect, disconnect, getState } from "./relay";

const STATUS_COLORS: Record<ConnectionState, string> = {
  disconnected: "#888",
  connecting: "#f0ad4e",
  authenticating: "#f0ad4e",
  connected: "#5cb85c",
  error: "#d9534f",
};

const STATUS_LABELS: Record<ConnectionState, string> = {
  disconnected: "Disconnected",
  connecting: "Connecting...",
  authenticating: "Authenticating...",
  connected: "Connected",
  error: "Error",
};

export function renderUI(root: HTMLElement) {
  root.innerHTML = `
    <div style="padding: 12px; font-family: system-ui, sans-serif; font-size: 13px; color: #e0e0e0;">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
        <span id="status-dot" style="width: 10px; height: 10px; border-radius: 50%; background: #888; flex-shrink: 0;"></span>
        <span id="status-label">Disconnected</span>
      </div>
      <div id="error-msg" style="color: #d9534f; margin-bottom: 8px; display: none;"></div>
      <label style="display: block; margin-bottom: 4px;">Server</label>
      <input id="server-url" type="text" value="wss://localhost:9876"
        style="width: 100%; box-sizing: border-box; margin-bottom: 8px; padding: 4px 6px; background: #2a2a2a; color: #e0e0e0; border: 1px solid #555; border-radius: 3px;" />
      <label style="display: block; margin-bottom: 4px;">Token</label>
      <input id="auth-token" type="password"
        style="width: 100%; box-sizing: border-box; margin-bottom: 12px; padding: 4px 6px; background: #2a2a2a; color: #e0e0e0; border: 1px solid #555; border-radius: 3px;" />
      <button id="connect-btn"
        style="width: 100%; padding: 6px; cursor: pointer; background: #4a9eff; color: white; border: none; border-radius: 3px; font-size: 13px;">
        Connect
      </button>
    </div>
  `;

  const btn = root.querySelector("#connect-btn") as HTMLButtonElement;
  const serverInput = root.querySelector("#server-url") as HTMLInputElement;
  const tokenInput = root.querySelector("#auth-token") as HTMLInputElement;

  btn.addEventListener("click", () => {
    const state = getState();
    if (state === "connected" || state === "connecting" || state === "authenticating") {
      disconnect();
    } else {
      const url = serverInput.value.trim();
      const token = tokenInput.value.trim();
      if (!url) return;
      if (!token) {
        updateError("Token is required");
        return;
      }
      connect(url, token, { onStateChange: updateStatus });
    }
  });
}

function updateStatus(state: ConnectionState, error?: string) {
  const dot = document.getElementById("status-dot");
  const label = document.getElementById("status-label");
  const btn = document.getElementById("connect-btn") as HTMLButtonElement | null;
  const serverInput = document.getElementById("server-url") as HTMLInputElement | null;
  const tokenInput = document.getElementById("auth-token") as HTMLInputElement | null;

  if (dot) dot.style.background = STATUS_COLORS[state];
  if (label) label.textContent = STATUS_LABELS[state];

  if (btn) {
    const isActive = state === "connected" || state === "connecting" || state === "authenticating";
    btn.textContent = isActive ? "Disconnect" : "Connect";
    btn.style.background = isActive ? "#d9534f" : "#4a9eff";
  }

  const inputsDisabled = state === "connected" || state === "connecting" || state === "authenticating";
  if (serverInput) serverInput.disabled = inputsDisabled;
  if (tokenInput) tokenInput.disabled = inputsDisabled;

  if (error) {
    updateError(error);
  } else {
    updateError(null);
  }
}

function updateError(msg: string | null) {
  const el = document.getElementById("error-msg");
  if (!el) return;
  if (msg) {
    el.textContent = msg;
    el.style.display = "block";
  } else {
    el.style.display = "none";
  }
}
