// input: src/ 测试文件 (*.test.ts/tsx), src/test/setup.ts
// output: Vitest 配置（jsdom 环境 + testing-library setup + @ 别名）
// owner: wanhua.gu
// pos: 前端测试配置 - Vitest 入口配置；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import path from 'node:path'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    passWithNoTests: true,
  },
})
