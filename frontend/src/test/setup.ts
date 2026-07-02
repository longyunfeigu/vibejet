// input: vitest 测试运行时
// output: 全局测试 setup（注入 @testing-library/jest-dom 匹配器）
// owner: wanhua.gu
// pos: 测试基础设施 - 全局 setup；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import '@testing-library/jest-dom/vitest'
