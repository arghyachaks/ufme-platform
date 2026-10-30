import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In Docker the API is reachable as http://api:8000; locally on 127.0.0.1.
declare const process: { env: Record<string, string | undefined> };
const apiTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";
// Stage 5: the identity provider's discovery and token endpoints are proxied same-origin under /idp, so the
// browser never makes cross-origin calls (only the sign-in page itself is on the provider).
const idpTarget = process.env.IDP_PROXY_TARGET ?? "http://127.0.0.1:8081";
const idpRealmPath = process.env.IDP_REALM_PATH ?? "/realms/ufme";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 5173,
    watch: process.env.VITE_POLL === "true" ? { usePolling: true, interval: 300 } : undefined,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/idp": {
        target: idpTarget,
        rewrite: (path: string) => path.replace(/^\/idp/, idpRealmPath),
      },
    },
  },
});
