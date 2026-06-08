import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// dev-прокси на core; на демо фронт собирается в статику и ходит через gateway nginx.
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
