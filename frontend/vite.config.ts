// input: ./tsconfig.app.json (paths), frontend/.env (VITE_API_URL), @vitejs/plugin-react
// output: Vite dev server (port 5173) + production build + /api proxy to backend
// owner: unknown
// pos: 前端构建配置 - Vite + React + path alias + backend proxy；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { tanstackRouter } from '@tanstack/router-plugin/vite';
import path from 'node:path';

const rootDir = import.meta.dirname;

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, rootDir, '');
  const apiUrl = env.VITE_API_URL || 'http://localhost:8000';

  return {
    plugins: [
      tanstackRouter({
        target: 'react',
        autoCodeSplitting: true,
      }),
      react(),
    ],
    resolve: {
      alias: {
        '@': path.resolve(rootDir, './src'),
        '~types': path.resolve(rootDir, './src/types'),
        '~components': path.resolve(rootDir, './src/components'),
        '~features': path.resolve(rootDir, './src/features'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
        },
      },
    },
  };
});
