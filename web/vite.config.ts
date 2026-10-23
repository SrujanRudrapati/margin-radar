import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// VITE_BASE lets the static export live under a sub-path (e.g. GitHub Pages /margin-radar/).
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
