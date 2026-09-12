import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serves the SPA under /health-platform/; set GITHUB_PAGES_PATH
// for that build. Dev and docker builds stay root-relative.
// Normalized to always end with "/" (import.meta.env.BASE_URL consumers
// concatenate paths directly).
const base = `${(process.env.GITHUB_PAGES_PATH || '/').replace(/\/+$/, '')}/`

export default defineConfig({
  base,
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
    },
  },
})
