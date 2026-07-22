import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

/**
 * Dev proxy: Gateway yokken tarayıcı CORS'a takılmadan
 * Incident (:8002) + Gamification (:8004) konuşur.
 * Gateway gelince VITE_API_BASE_URL=http://localhost:8000 yapıp proxy'siz de çalışır.
 */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api/v1/telemetry': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/v1/incidents': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/v1/game': { target: 'http://localhost:8004', changeOrigin: true },
      '/api/v1/ai': { target: 'http://localhost:8003', changeOrigin: true },
      '/api/v1/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/v1/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
