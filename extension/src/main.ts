import OBR from "@owlbear-rodeo/sdk";
import { renderUI } from "./ui";

OBR.onReady(async () => {
  const app = document.getElementById("app");
  if (!app) return;
  renderUI(app);
});
