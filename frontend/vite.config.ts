import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em producao o Nginx faz o proxy de /api -> backend (mesma origem).
// No dev (npm run dev), o Vite faz o mesmo para o backend publicado em 8010.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://127.0.0.1:8010",
        changeOrigin: true,
      },
    },
  },
});
