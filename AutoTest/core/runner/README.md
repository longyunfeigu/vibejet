# runner

## 职责
测试执行、BDD 规范检查和覆盖率统计脚本。

## 内容

| 文件 | 说明 |
|------|------|
| `run-bdd.sh` | 生成 BDD spec → 按模块执行 → 失败时输出失败用例 CSV |
| `gen-failed-cases-csv.mjs` | 读 Playwright JSON 报告,输出四列失败用例 CSV |
| `lint-bdd.ts` | BDD 规范检查(标签、定位器、测试数据命名、稳定性、Case ID、CSV 结构、API-first、等待预算) |
| `automation-coverage.mjs` | 自动化覆盖率 = 有可执行 `.feature` 标签的 Case ID / 用例 CSV 里的 Case ID |
| `classify-cases.mjs` | 给用例 CSV 的「执行方式」列按规则分类 |

## 使用

```bash
npm run test:all:local    # 全量
npm run lint:bdd          # 规范检查
npm run coverage          # 覆盖率
```
