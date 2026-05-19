// input: @testing-library/jest-dom matchers
// output: 全局扩展 Vitest expect 以支持 toBeInTheDocument 等 DOM matchers
// owner: unknown
// pos: 测试运行环境初始化 - Vitest setupFile；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import '@testing-library/jest-dom/vitest';
