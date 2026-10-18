import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In Docker the API is reachable as http://api:8000; locally on 127.0.0.1.
declare const process: { env: Record<string, string | undefined> };
const apiTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
