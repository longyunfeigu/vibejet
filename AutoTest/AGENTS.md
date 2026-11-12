# AutoTest — AI 操作指南

vibejet 的 E2E 测试框架（Playwright + playwright-bdd）和 Release-Check 验证指导，搬自 voice-agent 的 AutoTest（源 commit `1254c8bbe0`）。核心规则保持原样，只换成 vibejet 的页面、接口和测试账号。**详细 BDD 用例生成规范以 `prd-to-bdd` skill 为唯一权威**，本文件不重复其规则。

试用期状态：`experimental`，与 vj 链并存（见根目录 `AGENTS.md`）。

---

## 前置：先把被测应用跑起来

```bash
SECRET_KEY=$(openssl rand -hex 32) docker compose up -d postgres   # 仓库根目录；SECRET_KEY 只为通过 compose 的变量检查
cd backend
uv sync --extra dev --python 3.11        # 不指定会选到 3.13，asyncpg 0.29 在 3.13 上编译失败
uv pip install greenlet                  # Apple Silicon：uv.lock 里 greenlet 的平台条件不含 arm64，缺它 alembic 跑不了
uv run pybabel compile -d locales/       # 不编译，接口返回原始 key（如 auth.password.invalid）
uv run alembic upgrade head
uv run uvicorn main:app --port 8010      # 前端 dev server 把 /api 代理到 8010
cd ../frontend && pnpm dev               # 5173；不要设 VITE_API_URL（设了就直连后端，要 CORS）
cd ../AutoTest && npm install && npx playwright install chromium
cp config/environments.example.json config/environments.json   # 填测试账号密码（不提交）
```

测试账号 `e2e-fixture-user-a` 不存在时，`config/global-setup.ts` 先调注册接口建它，再走真实登录页登录，把登录态（前端存在 localStorage 的 `vibejet.session`）保存为 `config/auth-state-<env>.json`。

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

必须等待可观测的 DOM 状态变化，而不是猜测时间。见 `core/helpers/wait-utils.ts`。

### API-first 测试数据（CRITICAL）

测试数据的准备/清理一律走 `core/api/entities/*.api.ts`（REST），禁止在 steps/pages 出现 `page.request.*` 做数据 CRUD。UI 操作只允许出现在「被测功能本身」的验证中。各实体的 API 可用性登记在 `core/api/EXCEPTIONS.md`。

- 实体工厂创建时自动登记到 `core/api/registry.ts`，全局 After（`modules/common/steps/e2e-cleanup.steps.ts`）兜底清理。
- 清理走 best-effort（不抛、只 warn）；前置准备失败必须抛（fail-fast）。
- 测试账号是常驻夹具（`Release-Check/_shared/fixtures.md`），只用不改，也删不掉。

### 修改 Feature 必须同步 Case CSV（CRITICAL）

**修改 `.feature` 文件的期望结果/步骤时，必须同步更新同目录 `cases/manual-test-cases-cn.csv`。**

- `.feature` 是执行层（仅英文），`cases/manual-test-cases-cn.csv` 是用例文档层（中文），两者必须一致
- 根据变更的 Case ID 定位到对应 CSV 行，修改「预期结果」列
- vibejet 只维护中文 CSV 一份（源仓库是中英两份）

### 修改共享状态的用例必须用专属测试对象（CRITICAL）

**任何会修改数据或账号设置的用例，必须为每个场景单独创建专属测试对象，不能共用。**

原因：并发执行（WORKERS>1）时多个用例同时修改同一对象，会互相干扰。

规范：
- 名称格式 `e2e-{module}-{case-id}`，全 ASCII；场景开头创建（或复用同名），场景末尾清理
- 源仓库此条针对 agent；vibejet 的对应物是对话、文档、文件、agent 配置等

### 自动化优先，人工是需论证的例外（CRITICAL）

**默认答案永远是自动化；把 case 交给人，是需要论证的例外，不是兜底。** 完整准则见
[测试自动化准则 —— 三成本模型](docs/test-automation-doctrine.md)。

任何测试难点 = **输入 / 环境 / 判定** 三个成本里某一个贵。在把任何东西叫「人工」前，必须点名是哪一个：

- **输入贵 / 环境贵 → 是一次性 capex（夹具数据、故障注入编排层），必须搭，不许标「人工」。**「搭起来贵」不是交给人的理由。
- **只有判定贵（oracle 问题）可能不可约**，但也必须先用代理指标逼近（数值阈值、日志断言、回读）；只有代理之后的主观残余才交给人，且是**抽样**，不是全量回归。

**禁止的偷懒模式：**「我把简单的部分自动化了，剩下的要人来做」—— 若没点名卡住的成本、且该成本是输入/环境，视为分析不完整，必须顶回去。每个「交给人」的决定要连同卡住的成本一起留痕，保证人工残余可见且在收缩。

### Release-Check 验证指导（CRITICAL）

研发写给 AI 的验证指导在 `Release-Check/<YYYY-MM>/{feature,bugfix}/`，入口 [Release-Check/README.md](Release-Check/README.md)，写作规范 [STANDARD.md](Release-Check/STANDARD.md)，用 `npm run lint:release-check` 检查。指导与环境无关，拿去任何环境都能验。

- **按指导验证时禁止开 test-self-heal，禁止修改指导、测试和产品代码**——验证 AI 只按指导执行。
- 怎么验、怎么判、测试数据与操作边界见 `Release-Check/_shared/safety.md`。

---

## 一、BDD 用例文件结构（速查）

每个功能特性的文件都在嵌套目录下：

```
modules/{module}/{feature}/
├── cases/      ← 测试用例文档（manual-test-cases-cn.csv，16 列，中文）
├── features/   ← Gherkin 剧本（仅 .feature 英文执行）
├── pages/      ← Page Object 类（{FeatureName}Page.ts）
└── steps/      ← Step Definitions（{module}-{feature}.steps.ts）
```

**生成或修改 BDD 用例时，请调用 `prd-to-bdd` skill。** 该 skill 包含完整的 CSV 规范（16 列）、Case ID 登记表、Gherkin 规则、POM 模式、Step Definitions 规则、测试隔离原则，以及 Activation Pipeline。

---

## 二、目录结构速查

```
AutoTest/
├── modules/                        ← 核心工作区（按业务模块）
│   ├── auth/login/                 ← 登录（AUTH-LGN）
│   ├── home/dashboard/             ← 首页（HOME-DSH）
│   └── common/steps/               ← 跨模块步骤：session / common / e2e-cleanup
├── core/
│   ├── api/                        ← API-first 测试数据层（client、registry、entities）
│   ├── helpers/                    ← constants.ts, wait-utils.ts
│   ├── runner/                     ← run-bdd.sh、lint-bdd、覆盖率、失败用例 CSV
│   └── release-check/              ← 验证指导 lint + 工具（db-readonly）
├── config/
│   ├── playwright.config.ts
│   ├── env-config.ts
│   ├── global-setup.ts
│   └── environments.example.json
├── Release-Check/                  ← 验证指导（STANDARD、模板、_shared、<YYYY-MM>/）
└── report/                         ← 测试产物（gitignored）
```

---

## 三、npm 命令速查

```bash
# 运行（npm 脚本只预置了 local 环境）
npm run test:all:local       # 全量
npm run test:smoke:local     # 仅 @smoke
npm run test:auth:local      # auth 模块
npm run test:home:local      # home 模块
# 其他环境（config/environments.json 里的环境名）直接调脚本；npm 脚本额外设了 HEADLESS=true
HEADLESS=true ./core/runner/run-bdd.sh <all|smoke|auth|home> <env>

# 检查
npm run bdd:gen              # 验证步骤匹配，无 "Missing step" 报错
npm run typecheck            # TypeScript 类型检查
npm run lint:bdd             # BDD 规范检查（标签 / locator 禁用 / CSV 结构等）
npm run lint:release-check   # 验证指导 lint
npm run test:release-check   # 验证指导 lint 的单测
npm run test:runner          # runner 脚本单测
npm run coverage             # 自动化覆盖率；coverage:check 低于 80% 失败
```

### 测试自愈循环（Loop Engineering）

跑测试 → 读失败 → 分诊 → 自动修测试侧问题 → 重跑验证 → 直到全绿或停止条件触发。
封装在 `test-self-heal` skill，复用 `run-bdd.sh` 与 `gen-failed-cases-csv.mjs`。

```bash
/test-self-heal auth local              # auth 一轮完整自愈闭环（默认无头、单 worker）
/test-self-heal auth local --headed     # 有头模式：看得到浏览器，便于调试登录
/test-self-heal home local --dry-run    # 只分诊+报告，不改代码
/loop 2h /test-self-heal auth local     # 定时无人值守巡检（无头，最长 3 天自停）
```

- 测试侧问题（等待/locator/隔离/flaky）自动修；疑似真 bug 只报告不改。
- 修复后由 `heal-verifier` 子 agent 判定「真修好 vs 过拟合」，过拟合则回退。
- 停止条件硬编码：全绿 / 连续 2 轮无进展 / 达 --rounds（默认 3）/ 判定真 bug。
- State 文件：`report/le-loop-state-{module}-{env}.md`（跨会话可续）。

---

## 四、常见陷阱与修复

| 问题 | 原因 | 修复 |
|------|------|------|
| 用例描述与实际业务不符 | 仅依赖 PRD / delivery doc 想象流程，没核对真实 UI 和代码 | 写用例/Gherkin/POM 前，先读真实组件源码（`.tsx`）确认 label / aria / 真实交互流；必要时用 `web-access` skill 打开真实页面看一遍再写 |
| `Missing step definitions` | feature 步骤没有匹配的 step | 在 steps 文件中添加对应 `Given/When/Then` |
| `Multiple definitions matched` | 两个模块定义了同名 step | 提取到 `modules/common/steps/` |
| `locator.fill Timeout` | 页面未就绪就操作 | POM `open()` 中等关键元素可见（timeout: 30000） |
| `Test timeout 60000ms` | 长耗时场景未设超时 | feature 场景加 `@slow` 标签 |
| 测试数据含非 ASCII | e2e- 前缀资源命名含中文 | 统一使用 `e2e-{ascii-slug}` 格式 |
| global-setup 报「自动登录失败」 | 测试账号存在但密码与 environments.json 不一致 | 修正 environments.json 的密码；账号不存在时 global-setup 会自动注册 |
| 页面/接口显示 `auth.password.invalid` 这类 key | 后端翻译目录没编译 | `cd backend && uv run pybabel compile -d locales/` 后重启后端 |
| `429 Too Many Requests` | 登录/注册接口按 IP 每分钟限流（`RATE_LIMIT_PER_MINUTE`，默认 60） | 复用 storageState，不要在循环里反复登录 |

---

## 五、失败用例 CSV 输出（每次执行后必做）

**每次执行测试后，若存在失败用例，必须在 `report/test-results/` 下输出一个 CSV 文件**，汇总本次所有失败用例。全部通过则不产出。

- **路径**：`report/test-results/failed-cases-{env}-{YYYYMMDD-HHMMSS}.csv`（按环境 + 执行时间命名，不覆盖历史）
- **编码**：UTF-8 with BOM（Excel 直接打开中文不乱码）
- **表头（4 列，顺序固定）**：`用例名称,测试目的,测试步骤,失败原因`

由 `core/runner/gen-failed-cases-csv.mjs` 生成，`core/runner/run-bdd.sh` 在每次执行末尾自动调用。手动补生成（如直接跑了 `npx playwright test` 未经 run-bdd.sh）：`node core/runner/gen-failed-cases-csv.mjs <env>`。
