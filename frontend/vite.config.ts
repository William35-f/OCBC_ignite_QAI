import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// The dev server forwards /api/* to the FastAPI backend.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: { "/api": env.VITE_API_TARGET || "http://127.0.0.1:8000" },
    },
  };
});
