import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Where the dev server forwards /api requests. Locally the backend is on localhost:8000;
// docker-compose.yml sets this to http://backend:8000 (the backend service name).
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on all interfaces so the dev server is reachable from outside a container
    port: 5173,
    proxy: {
      // /api/health -> <apiTarget>/health. Same-origin from the browser's view, so no CORS needed.
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
