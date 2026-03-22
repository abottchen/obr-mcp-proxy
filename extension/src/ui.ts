import OBR, { type Item, type Metadata } from "@owlbear-rodeo/sdk";
import { type ConnectionState, connect, disconnect, getState } from "./relay";

const EXPORT_VERSION = 1;

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

const btnStyle = `width: 48%; padding: 6px; cursor: pointer; color: white; border: none; border-radius: 3px; font-size: 13px;`;

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
      <hr style="border: none; border-top: 1px solid #444; margin: 12px 0;" />
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
        <button id="export-btn" disabled
          style="${btnStyle} background: #5cb85c; opacity: 0.5;">
          Export Scene
        </button>
        <button id="import-btn" disabled
          style="${btnStyle} background: #f0ad4e; opacity: 0.5;">
          Import Scene
        </button>
      </div>
      <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
        <input id="import-room-meta" type="checkbox" style="cursor: pointer;" />
        <span>Include room metadata on import</span>
      </label>
      <input id="import-file" type="file" accept=".json" style="display: none;" />
    </div>
  `;

  const btn = root.querySelector("#connect-btn") as HTMLButtonElement;
  const serverInput = root.querySelector("#server-url") as HTMLInputElement;
  const tokenInput = root.querySelector("#auth-token") as HTMLInputElement;
  const exportBtn = root.querySelector("#export-btn") as HTMLButtonElement;
  const importBtn = root.querySelector("#import-btn") as HTMLButtonElement;
  const importFileInput = root.querySelector("#import-file") as HTMLInputElement;
  const importRoomMeta = root.querySelector("#import-room-meta") as HTMLInputElement;

  // Restore saved credentials
  const savedUrl = localStorage.getItem("obr-mcp-server-url");
  const savedToken = localStorage.getItem("obr-mcp-auth-token");
  if (savedUrl) serverInput.value = savedUrl;
  if (savedToken) tokenInput.value = savedToken;

  btn.addEventListener("click", () => {
    const state = getState();
    if (state === "connected" || state === "connecting" || state === "authenticating") {
      disconnect();
    } else {
      doConnect(serverInput, tokenInput);
    }
  });

  exportBtn.addEventListener("click", () => exportScene(exportBtn));
  importBtn.addEventListener("click", () => importFileInput.click());
  importFileInput.addEventListener("change", () => {
    const file = importFileInput.files?.[0];
    if (file) {
      importScene(file, importRoomMeta.checked, importBtn);
      importFileInput.value = "";
    }
  });

  // Auto-connect if we have saved credentials
  if (savedUrl && savedToken) {
    doConnect(serverInput, tokenInput);
  }
}

function doConnect(serverInput: HTMLInputElement, tokenInput: HTMLInputElement) {
  const url = serverInput.value.trim();
  const token = tokenInput.value.trim();
  if (!url) return;
  if (!token) {
    updateError("Token is required");
    return;
  }
  localStorage.setItem("obr-mcp-server-url", url);
  localStorage.setItem("obr-mcp-auth-token", token);
  connect(url, token, { onStateChange: updateStatus });
}

function updateStatus(state: ConnectionState, error?: string) {
  const dot = document.getElementById("status-dot");
  const label = document.getElementById("status-label");
  const btn = document.getElementById("connect-btn") as HTMLButtonElement | null;
  const serverInput = document.getElementById("server-url") as HTMLInputElement | null;
  const tokenInput = document.getElementById("auth-token") as HTMLInputElement | null;
  const exportBtn = document.getElementById("export-btn") as HTMLButtonElement | null;
  const importBtn = document.getElementById("import-btn") as HTMLButtonElement | null;

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

  const sceneOpsEnabled = state === "connected";
  if (exportBtn) {
    exportBtn.disabled = !sceneOpsEnabled;
    exportBtn.style.opacity = sceneOpsEnabled ? "1" : "0.5";
  }
  if (importBtn) {
    importBtn.disabled = !sceneOpsEnabled;
    importBtn.style.opacity = sceneOpsEnabled ? "1" : "0.5";
  }

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

interface SceneExport {
  version: number;
  exportedAt: string;
  roomMetadata: Metadata;
  sceneMetadata: Metadata;
  items: Item[];
}

async function exportScene(btn: HTMLButtonElement) {
  const origText = btn.textContent;
  btn.textContent = "Exporting...";
  btn.disabled = true;
  try {
    const [roomMetadata, sceneMetadata, items] = await Promise.all([
      OBR.room.getMetadata(),
      OBR.scene.getMetadata(),
      OBR.scene.items.getItems(),
    ]);

    const data: SceneExport = {
      version: EXPORT_VERSION,
      exportedAt: new Date().toISOString(),
      roomMetadata,
      sceneMetadata,
      items,
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const mapItem = items.find((i) => i.layer === "MAP" && i.type === "IMAGE");
    const sceneName = mapItem?.name?.replace(/[^a-zA-Z0-9_-]/g, "-") || "scene";
    a.download = `${sceneName}.json`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    updateError(`Export failed: ${err instanceof Error ? err.message : err}`);
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

async function importScene(file: File, includeRoomMetadata: boolean, btn: HTMLButtonElement) {
  const origText = btn.textContent;
  btn.textContent = "Importing...";
  btn.disabled = true;
  try {
    const text = await file.text();
    const data: SceneExport = JSON.parse(text);

    if (!data.version || !data.items) {
      throw new Error("Invalid scene export file");
    }

    // Delete all existing items
    const existing = await OBR.scene.items.getItems();
    if (existing.length > 0) {
      await OBR.scene.items.deleteItems(existing.map((i) => i.id));
    }

    // Restore scene metadata
    if (data.sceneMetadata) {
      await OBR.scene.setMetadata(data.sceneMetadata);
    }

    // Optionally restore room metadata
    if (includeRoomMetadata && data.roomMetadata) {
      await OBR.room.setMetadata(data.roomMetadata);
    }

    // Add all items back
    if (data.items.length > 0) {
      await OBR.scene.items.addItems(data.items);
    }

    updateError(null);
  } catch (err) {
    updateError(`Import failed: ${err instanceof Error ? err.message : err}`);
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}
