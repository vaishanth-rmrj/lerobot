import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  base: '/static/frontend/',
  build: {
    outDir: '../static/frontend', // place the build output in the FastAPI static folder
    emptyOutDir: true,
  },
  server: {
    // setup a proxy to forward API calls to FastAPI during development
    proxy: {
      '/api': 'http://localhost:8000',
      '/static': 'http://localhost:8000',
      '/robot': 'http://localhost:8000',
    },
  },
})
