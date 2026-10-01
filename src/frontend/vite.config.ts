// Vite configuration for the OSI frontend: React, Tailwind, and a development proxy to the FastAPI backend.
// In development, /api and /health go to the backend on port 8000, so the browser sees one origin.
// In production, Firebase Hosting forwards the same paths to Cloud Run, so the frontend code never changes.
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: BACKEND_URL, changeOrigin: true },
      '/health': { target: BACKEND_URL, changeOrigin: true },
    },
  },
})
