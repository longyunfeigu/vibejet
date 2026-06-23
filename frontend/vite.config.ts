// input: VITE_API_URL 环境变量, src/ 源码, tsconfig 路径别名
// output: Vite dev/build 配置（React + Tailwind v4 + TanStack Router 插件, @ 别名, /api 代理）
// owner: wanhua.gu
// pos: 前端构建配置 - Vite 入口配置；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
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
          target: env.VITE_API_URL || 'http://localhost:8010',
          changeOrigin: true,
        },
      },
    },
  }
})
