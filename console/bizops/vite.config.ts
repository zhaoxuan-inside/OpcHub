import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@opchub/console-ui": path.resolve(__dirname, "../packages/ui/src/index.ts"),
      "@opchub/console-api": path.resolve(__dirname, "../packages/api/src/index.ts"),
      "@opchub/console-admin": path.resolve(__dirname, "../packages/admin/src/index.tsx"),
    },
  },
  server: {
    port: 4603,
    proxy: {
      "/api": { target: "http://127.0.0.1:3000", changeOrigin: true },
    },
  },
});
