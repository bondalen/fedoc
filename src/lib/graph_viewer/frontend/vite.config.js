import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// Читаем порт API сервера из переменной окружения
const API_PORT = process.env.VITE_API_PORT || '15000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      },
      '/socket.io': {
        target: `ws://127.0.0.1:${API_PORT}`,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
