import OBR from "@owlbear-rodeo/sdk";
import { renderUI } from "./ui";

OBR.onReady(async () => {
  const app = document.getElementById("app");
  if (!app) return;

  const role = await OBR.player.getRole();
  if (role !== "GM") {
    app.innerHTML = `<div style="padding: 12px; font-family: system-ui, sans-serif; font-size: 13px; color: #888;">This extension is only available to the GM.</div>`;
    return;
  }

  renderUI(app);
});
