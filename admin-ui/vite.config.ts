import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI server runs on :8000; proxying avoids CORS in development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/admin/api": "http://127.0.0.1:8000" },
  },
});
