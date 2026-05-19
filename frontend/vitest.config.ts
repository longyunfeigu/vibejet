// input: src/test/setup.ts, alias mirror of vite.config.ts
// output: Vitest test runner config（jsdom 环境 + testing-library matchers）
// owner: unknown
// pos: 前端测试运行器配置 - Vitest + jsdom；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

const rootDir = import.meta.dirname;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(rootDir, './src'),
      '~types': path.resolve(rootDir, './src/types'),
      '~components': path.resolve(rootDir, './src/components'),
      '~features': path.resolve(rootDir, './src/features'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules', 'dist', '**/*.config.*', '**/*.d.ts'],
    },
  },
});
