import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
var apiTarget = process.env.VITE_API_TARGET || "http://localhost:8000";
export default defineConfig({
    plugins: [react()],
    base: "/",
    build: {
        outDir: process.env.VITE_OUT_DIR || path.resolve(__dirname, "../backend/app/static"),
        emptyOutDir: true,
    },
    server: {
        host: true,
        port: 5173,
        proxy: {
            "/api": {
                target: apiTarget,
                changeOrigin: true,
                secure: apiTarget.startsWith("https://") ? false : true,
            },
        },
    },
});
