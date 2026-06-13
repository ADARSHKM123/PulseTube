import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Honor a PORT injected by the launcher; fall back to Vite's default.
    port: process.env.PORT ? Number(process.env.PORT) : 5173,
    // Dev convenience: the dashboard calls /api/* same-origin in both dev
    // (this proxy) and production (nginx proxy) — no env juggling.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
