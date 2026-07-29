import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: process.env.AFS_STUDIO_WEB_BASE ?? "/studio/",
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    allowedHosts: ["terminal.local"],
    proxy: {
      "/api": "http://127.0.0.1:8790",
      "/auth": "http://127.0.0.1:8790"
    }
  },
  build: {
    target: "es2022",
    sourcemap: true
  }
});
