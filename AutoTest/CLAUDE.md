# AutoTest — AI 操作指南

本文件是 Claude Code 在此项目中的全局指南。**详细 BDD 用例生成规范以 `/prd-to-bdd` skill 为唯一权威**,本文件不重复其规则。

---

## 零、核心原则（违反即 BLOCK）

### 禁止硬等待（CRITICAL）

**绝对禁止** `page.waitForTimeout()` 或任何固定毫秒等待。

```typescript
// ❌ 永远不这样写
await page.waitForTimeout(2000);

// ✅ 等具体业务状态
await expect(locator).toBeVisible({ timeout: 30000 });
await expect(locator).toBeHidden({ timeout: 10000 });
await expect(locator).toBeEnabled({ timeout: 10000 });
```

必须等待可观测的 DOM 状态变化,而不是猜测时间。见 `core/helpers/wait-utils.ts`。

### API-first 测试数据（CRITICAL）

测试数据的准备/清理一律走 `core/api/entities/*.api.ts`(REST),禁止在 steps/pages 出现 `page.request.*` 做数据 CRUD。UI 操作只允许出现在「被测功能本身」的验证中。无 REST API 的实体登记在 `core/api/EXCEPTIONS.md` 并走单文件 UI fallback(仅语义定位)。

- 建/删 agent 用 `agentApi`(`core/api/entities/agent.api.ts`):`create` / `ensureFresh` / `deleteByName`,创建时自动登记到 registry,全局 After 兜底清理。
- 清理走 best-effort(不抛、只 warn);前置准备失败必须抛(fail-fast)。
- 模板系统级,只 create/get,绝不 delete。

### 修改 Feature 必须同步 Case CSV（CRITICAL）

**修改 `.feature` 文件的期望结果/步骤时，必须同步更新同目录 `cases/` 下的 `manual-test-cases-en.csv` 和 `manual-test-cases-cn.csv`。**

- `.feature` 是执行层（仅英文，无 `.cn.feature` 中文副本），`cases/*.csv` 是用例文档层，两者必须保持一致
- 英文 CSV（`manual-test-cases-en.csv`）和中文 CSV（`manual-test-cases-cn.csv`）都要更新
- 根据变更的 Case ID 定位到对应 CSV 行，修改「预期结果」列

### 修改/新建 E2E 用例必须使用专属 Agent（CRITICAL）

**任何需要修改 Agent 配置的 E2E 用例,必须为每个场景单独创建专属 e2e agent,不能共用现有 agent。**

原因:并发执行(WORKERS=6)时多个用例同时修改同一 agent 的状态(如 hotwords、language 配置),导致互相干扰。

规范:
- 场景开头:`Given a dedicated agent "e2e-{module}-{case-id}" is ready`(创建或复用同名 agent)
- 场景末尾:`Given agent "e2e-{module}-{case-id}" is cleaned up`(删除 agent)
- Agent 名称格式:`e2e-{module}-{case-id}`,如 `e2e-hotwords-va030`、`e2e-ai-sim-ai001`

### 自动化优先，人工是需论证的例外（CRITICAL）

**默认答案永远是自动化;把 case 交给人,是需要论证的例外,不是兜底。** 完整准则见
[测试自动化准则 —— 三成本模型](docs/test-automation-doctrine-cn.md)（英文正本 `docs/test-automation-doctrine.md`）。

任何测试难点 = **输入 / 环境 / 判定** 三个成本里某一个贵。在把任何东西叫"人工"前,必须点名是哪一个:

- **输入贵 / 环境贵 → 是一次性 capex(黄金音频集、故障注入编排层),必须搭,不许标"人工"。** "搭起来贵"不是交给人的理由。
- **只有判定贵(oracle 问题)可能不可约**,但也必须先用代理指标逼近(ASR 回读、MOS 打分、数值阈值);只有代理之后的主观残余才交给人,且是**抽样**,不是全量回归。

**禁止的偷懒模式:** "我把简单的部分自动化了,剩下的要人来做" —— 若没点名卡住的成本、且该成本是输入/环境,视为分析不完整,必须顶回去。每个"交给人"的决定要连同卡住的成本一起留痕,保证人工残余可见且在收缩。

### Release-Check 验证指导（CRITICAL）

研发写给 AI 的验证指导在 `Release-Check/<发版分支>/{feature,bugfix}/`，入口 [Release-Check/README-cn.md](Release-Check/README-cn.md)，写作规范 [STANDARD-cn.md](Release-Check/STANDARD-cn.md)，用 `npm run lint:release-check` 检查。指导与环境、升级无关，拿去任何环境都能验。

- **按指导验证时禁止开 test-self-heal，禁止修改指导、测试和产品代码**——验证 AI 只按指导执行。
- 怎么验、怎么判、测试数据与操作边界见 `Release-Check/_shared/safety-cn.md`。

---

## 一、BDD 用例文件结构（速查）

每个功能特性的文件都在嵌套目录下:

```
modules/{module}/{feature}/
├── cases/      ← 测试用例文档（CSV，16 列，中英双语）
├── features/   ← Gherkin 剧本（仅 .feature 英文执行；不再维护 .cn.feature 中文副本）
├── pages/      ← Page Object 类（{FeatureName}Page.ts）
└── steps/      ← Step Definitions（{module}-{feature}.steps.ts）
```

**生成或修改 BDD 用例时,请调用 `/prd-to-bdd` skill。** 该 skill 包含完整的 CSV 规范(16 列)、Case ID 注册表、Gherkin 规则、POM 模式、Step Definitions 规则、测试隔离原则,以及 Activation Pipeline。

---

## 二、目录结构速查

```
AutoTest/
├── modules/                        ← 核心工作区（按业务模块）
│   ├── knowledge-base/
│   │   └── base/
│   │       ├── cases/              ← manual-test-cases-en.csv / cn.csv
│   │       ├── features/           ← knowledge-base-base.feature
│   │       ├── pages/
│   │       └── steps/
│   ├── voice-agent/
│   │   ├── hotwords/               ← 各 feature 平级目录
│   │   ├── lifecycle/
│   │   ├── audio-e2e-latency/
│   │   └── ...
│   ├── ai-simulation/
│   ├── mcp-registry/
│   ├── whatsapp/
│   ├── phone-number/
│   └── common/
│       └── steps/                  ← common.steps.ts（跨模块复用步骤）
├── core/
│   ├── runner/                     ← 执行脚本
│   ├── helpers/                    ← wait-utils.ts, constants.ts, agent-factory.ts
│   └── archive/                    ← 历史参考（只读）
├── config/
│   ├── playwright.config.ts
│   ├── env-config.ts
│   └── tsconfig.json
└── report/                         ← 测试产物（gitignored）
```

---

## 三、npm 命令速查

```bash
# 全量运行
npm run test:all:sg          # SG 环境
npm run test:all:uat         # UAT 环境
npm run test:all:dev         # DEV 环境

# Smoke 运行（仅 @smoke 标签）
npm run test:smoke:sg
npm run test:smoke:uat

# 单模块运行（环境后缀：:sg | :uat | :dev）
npm run test:kb:sg           # knowledge-base
npm run test:va:sg           # voice-agent
npm run test:ai:sg           # ai-simulation
npm run test:mcp:sg          # mcp-registry
npm run test:wa:sg           # whatsapp
npm run test:pn:sg           # phone-number

# 调试工具
npm run bdd:gen              # 验证步骤匹配，无 "Missing step" 报错
npm run typecheck            # TypeScript 类型检查
npm run lint:bdd             # BDD 规范检查（标签合规 / locator 禁用 / CSV 结构等）

# 自动化
npm run watch:prd            # 监听 /Product 目录，PRD 变更自动触发 AI 生成 .feature
```

### 测试自愈循环（Loop Engineering）

跑测试 → 读失败 → 分诊 → 自动修测试侧问题 → 重跑验证 → 直到全绿或停止条件触发。
封装在 `test-self-heal` skill，复用 `run-test` 与 `gen-failed-cases-csv.mjs`。

```bash
/test-self-heal kb uat              # knowledge-base 一轮完整自愈闭环（默认无头、单 worker）
/test-self-heal kb uat --headed     # 有头模式：看得到浏览器，便于调试 / 排查 SSO 登录
/test-self-heal va uat --workers 6  # 6 路并行，更快（参考 test:parallel:uat）
/test-self-heal va uat --dry-run    # 只分诊+报告，不改代码
/loop 2h /test-self-heal kb uat     # 定时无人值守巡检（无头，最长 3 天自停）
```

- 浏览器模式：默认**无头**（适合 /loop 巡检、不弹窗、更快）；`--headed` 切有头看过程。底层即 `HEADLESS=true` 前缀，`playwright.config.ts` 默认有头。
- 并行：默认 **1 worker**；`--workers N` 加 `WORKERS=N` 前缀并行（默认 1）。并行更快但可能引入「共用 agent 状态干扰」型 flaky——skill 会自动用 `--workers 1` 隔离重跑来区分**并发干扰**与**真问题**，验证修复时也强制单 worker。
- 测试侧问题（等待/locator/隔离/flaky）自动修；疑似真 bug 只报告不改。
- 修复后由 `heal-verifier` 子 agent 判定「真修好 vs 过拟合」，过拟合则回退。
- 停止条件硬编码：全绿 / 连续 2 轮无进展 / 达 --rounds（默认 3）/ 判定真 bug。
- State 文件：`report/le-loop-state-{module}-{env}.md`（跨会话可续）。

---

## 四、常见陷阱与修复

| 问题 | 原因                                       | 修复 |
|------|------------------------------------------|------|
 用例描述与实际业务不符 | 仅依赖 PRD / delivery doc 想象流程,没核对真实 UI 和代码 | 写用例/Gherkin/POM 前,先读真实组件源码(`.tsx`)确认 placeholder / aria-label / 真实交互流;必要时 agent-browser 跑一遍真实页面再写 |
| `Missing step definitions` | feature 步骤没有匹配的 step                     | 在 steps 文件中添加对应 `Given/When/Then` |
| `Multiple definitions matched` | 两个模块定义了同名 step                           | 提取到 `modules/common/steps/common.steps.ts` |
| `locator.fill Timeout` | 页面/iframe 未就绪就操作                         | POM `navigate()` 中加 `waitFor({ timeout: 30000 })` |
| `409 Conflict` | 创建的资源已存在                                 | `deleteXxxIfExists()` 前等待删除完成 (`not.toBeVisible`) |
| `Test timeout 60000ms` | 长耗时场景未设超时                                | feature 场景加 `@slow` 标签（timeout × 3 = 180s） |
| `click Timeout` | 搜索结果未加载就点击                               | 用 `waitFor({ state: 'visible' })` 替代 `waitForTimeout` |
| 测试数据含非 ASCII | e2e- 前缀资源命名含中文                           | 统一使用 `e2e-{ascii-slug}` 格式,如 `e2e-test-kb` |

---

## 五、失败用例 CSV 输出（每次执行后必做）

**每次执行测试后,若存在失败用例,必须在 `report/test-results/` 下输出一个 CSV 文件**,汇总本次所有失败用例。全部通过则不产出。

### 文件规范

- **路径**:`report/test-results/failed-cases-{env}-{YYYYMMDD-HHMMSS}.csv`（按环境 + 执行时间命名,每次执行一个,不覆盖历史）
- **编码**:UTF-8 with BOM（Excel 直接打开中文不乱码）
- **格式**:逗号分隔;字段内若含逗号 / 换行 / 双引号,用双引号包裹并将内部 `"` 转义为 `""`
- **表头（4 列,顺序固定）**:`用例名称,测试目的,测试步骤,失败原因`

### 列来源

| 列 | 来源 |
|------|------|
| **用例名称** | 失败 scenario 的 Case ID 标签（`@VA-XXX-NNN`,多个则用 `/` 连接）+ scenario 标题 |
| **测试目的** | scenario 标题（Gherkin `Scenario:` 行本身即用例目的） |
| **测试步骤** | 该 scenario 的全部 `Given/When/Then/And` 步骤,按顺序用 ` / ` 连接 |
| **失败原因** | Playwright 首条 `error.message`,去除 ANSI 颜色码,截断到合理长度（如 500 字符） |

### 数据获取

- **失败清单 + 报错**:读本次执行产物 `report/test-reports-{env}/playwright/results.json`（json reporter 已在 `config/playwright.config.ts` 配置）,筛选 `ok=false` 或 status 非 `expected` 的用例,取其 `title`、`tags`、`errors[0].message`。
- **测试步骤文本**:按 Case ID 在 `modules/**/features/*.feature` 中定位对应 scenario,提取其步骤行。

### 落地方式（已实现）

由脚本 `core/runner/gen-failed-cases-csv.mjs` 生成,`core/runner/run-bdd.sh` 在每次执行末尾自动调用（`node core/runner/gen-failed-cases-csv.mjs "$ENV"`）。脚本读取 `report/test-reports-{env}/playwright/results.json`,从 `spec.tags`（Case ID）、`spec.title`（目的）、`result.steps[].title`（Gherkin 步骤）、`result.errors[0].message`（失败原因,去 ANSI、压空白、截断 500 字）提取四列,仅在有失败用例时写出。

手动补生成（如直接跑了 `npx playwright test` 未经 run-bdd.sh）:`node core/runner/gen-failed-cases-csv.mjs <env>`。
