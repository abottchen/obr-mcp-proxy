import fs from "fs";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  server: {
    https: {
      cert: fs.readFileSync(
        path.resolve(__dirname, "../server/certs/localhost.pem")
      ),
      key: fs.readFileSync(
        path.resolve(__dirname, "../server/certs/localhost-key.pem")
      ),
    },
    cors: true,
  },
});
