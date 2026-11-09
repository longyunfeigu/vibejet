# runner

## 职责
测试执行和报告生成脚本，提供一键顺序执行全量测试、生成 Markdown 冒烟报告、监听 PRD 目录变更自动唤醒 AI 三项能力。

## 内容

| 文件 | 说明 |
|------|------|
| `run-all-tests.ts` | 顺序执行所有测试套件，统一收集结果 |
| `generate-smoke-report.ts` | 读取测试结果，生成 Markdown 格式冒烟测试报告 |
| `watch-requirements.ts` | 监听 PRD 目录文件变更，自动唤醒 AI 生成或更新测试用例 |

## 使用

```bash
npm run test:all:sg     # 顺序执行全量测试（Singapore 环境）
npm run test:all        # 顺序执行全量测试（默认环境）
npm run smoke:report    # 生成冒烟测试 Markdown 报告
npm run watch:prd       # 启动 PRD 目录监听，文件变更时自动触发 AI
```

注意：`run-all-tests.ts` 按模块顺序执行，避免并发干扰；`watch-requirements.ts` 仅适用于本地开发阶段，不应在 CI 环境启动。
