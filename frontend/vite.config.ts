import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/chat': 'http://localhost:8000',
      '/documents': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
