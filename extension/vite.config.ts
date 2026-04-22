import fs from "fs";
import path from "path";
import { defineConfig } from "vite";

const certPath = path.resolve(__dirname, "../server/certs/localhost.pem");
const keyPath = path.resolve(__dirname, "../server/certs/localhost-key.pem");
const httpsConfig =
  fs.existsSync(certPath) && fs.existsSync(keyPath)
    ? { cert: fs.readFileSync(certPath), key: fs.readFileSync(keyPath) }
    : undefined;

export default defineConfig({
  base: "./",
  server: {
    ...(httpsConfig && { https: httpsConfig }),
    cors: true,
  },
});
