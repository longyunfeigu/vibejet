import path from 'node:path'

import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [
      // tanstackRouter 必须在 react() 之前
      tanstackRouter({ target: 'react', autoCodeSplitting: true }),
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          // API_PROXY_TARGET 只改代理目标、不暴露给浏览器（verify 起隔离环境时用它指向随机端口的后端）；
          // VITE_API_URL 会同时让 apiClient 直连后端，需要 CORS
          target: env.API_PROXY_TARGET || env.VITE_API_URL || 'http://localhost:8010',
          changeOrigin: true,
        },
      },
    },
  }
})
