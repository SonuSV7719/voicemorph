import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Vite config tuned for Tauri: fixed dev port, no clearing the terminal so
// Rust/Tauri logs stay visible.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
  },
  build: {
    target: "es2020",
    outDir: "dist",
  },
});
