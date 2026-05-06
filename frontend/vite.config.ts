import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend talks to the backend via /api/*. Vite proxies those to the Flask
// container so we don't need CORS in dev. In compose the backend is reachable
// at hostname "backend"; falls back to localhost when running outside compose.
const backendTarget = process.env.VITE_BACKEND_URL || 'http://backend:8080';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
