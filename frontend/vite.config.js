import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server proxies /api -> FastAPI backend so the frontend can call
// relative URLs (no CORS juggling). Backend default port is 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
