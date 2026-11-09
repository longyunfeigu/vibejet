# 功能检查清单：引入 voice-agent 交付链与 AutoTest（试用期）

> 由 `/feature-checklist` 在**无人值守模式**下产出。HUMAN 项的判定是「自动确认，待你审」，每项附依据。
>
> **2026-11-09 修正**：#15 初版误判为 PASS（锁文件其实没提交）；#8、#9 原来只是推断，现已更新；新增复盘补查 #21、#22；总数初版也数错了。修正处都标了「修正」。
>
> **范围说明**：本清单里的 git 命令只覆盖第一次试跑的 commit（`12aded5..244609f`）。之后分支上的 bug 修复（第二次试跑）和依赖安全升级都改了 `backend/`，所以用 `..HEAD` 重跑会得到不同的结果。

Feature: 引入 voice-agent 交付链与 AutoTest E2E 框架
Type: T6 — External Dependency Change
Generated: 2026-11-09
Design: [design.md](./design.md)
Release-Check: 豁免（只改 AutoTest、文档、CI，没有运行时行为变化）；分支上的 commit 带 `Release-Check: exempt` trailer

---

## 检查清单与结果

### 上游审查（T6）

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 1 | HUMAN | 依赖版本与源仓库一致（`@playwright/test` 1.59.1、`playwright-bdd` ^8.5.0） | PASS（待审） | `AutoTest/package.json`；源仓库同版本 |
| 2 | HUMAN | 列出破坏性变更 | N/A | 全部是新增依赖，没有旧版本可比 |

### 行为一致

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 3 | AUTO | 适配后，源仓库自带的验证指导 lint 单测全部通过：`npm run test:release-check` | PASS | 71/71 |
| 4 | AUTO | runner 单测：`npm run test:runner` | PASS | 6/6 |
| 5 | AUTO | 真实端到端：`npm run test:all:local`（Postgres + 后端 :8010 + Vite :5173，无头 Chromium） | PASS | 7 passed（14.2s）；无失败，不生成失败用例 CSV |
| 6 | HUMAN | 关键集成路径是真实跑的，不只是单测 | PASS（待审） | 全局前置日志：`已注册测试账号 e2e-fixture-user-a` → `登录成功 … auth-state-local.json 已保存` |
| 7 | HUMAN | 错误路径有覆盖 | PASS（待审） | AUTH-LGN-003（密码错误 → 提示 + 无会话）、HOME-DSH-002（无效 token → 会话失效页 → 清会话 → 回登录页） |

### 区分度（每条检查都要能在旧行为上失败）

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 8 | HUMAN | AUTH-LGN-003 在翻译未编译的环境上会失败 | N/A（修正：前提已失效） | 初版只是推断，没有实测。第二次试跑的修复（`526dd47`）让翻译缺失时退回英文默认文案：`PasswordErrorException` 的默认文案就是 `Invalid username or password`，和英文翻译、剧本期望一字不差。所以这个场景不再能发现「翻译没编译」，要靠中文场景断言 `用户名或密码错误` 才行 |
| 9 | HUMAN | lint-bdd 修复前，嵌套功能目录确实被跳过 | PASS（修正：已补实测） | 在 `modules/auth/login/features/auth-login.feature` 里故意加一个没有标签的场景：原版 lint-bdd（voice-agent 原样，配它自己的 runner 库）结果 `All checks passed`，exit 0；适配版报 `Tag compliance: 1 violation(s)` 和 `TC tag coverage: 1 violation(s)`，exit 1 |

### 回归

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 10 | AUTO | 产品代码未改：`git diff --stat 12aded5..244609f -- backend frontend` | PASS | 0 files changed |
| 11 | AUTO | vj 链 skill 未改：`git diff --name-only 12aded5..244609f -- '.agents/skills/vj*'` | PASS | 0 个文件 |
| 12 | AUTO | 类型检查：`npm run typecheck` | PASS | 0 errors |
| 13 | AUTO | BDD 规范：`npm run lint:bdd` | PASS | 8/8 项通过 |
| 14 | AUTO | 步骤匹配：`npm run bdd:gen`（含 CI 占位环境变量的跑法） | PASS | exit 0 |

### 部署安全

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 15 | AUTO | 锁文件已提交，可复现安装：`npm ci` | FAIL → 已修（修正：初版误判为 PASS） | 初版在工作区跑 `npm ci` 通过，只是因为文件刚好在磁盘上：`AutoTest/.gitignore` 原样带来的 `package-lock.json` 规则把它忽略了，它从未提交，干净克隆上 `npm ci` exit 1。修复 `8137458`：在 `AutoTest/.gitignore` 里放行。干净克隆复验 exit 0 |
| 16 | HUMAN | 回滚方式 | PASS（待审） | 删分支，或 revert 5 个 commit；不涉及数据迁移 |
| 17 | HUMAN | 在 staging 上验证 | N/A | 开发期工具，不部署 |

### 安全

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 18 | AUTO | 凭据不入库 | PASS | AutoTest/config/environments.json: ignored; AutoTest/config/auth-state-local.json: ignored; backend/.env: ignored |
| 19 | AUTO | CI 新 job 不需要 secret | PASS | `ci.yml` 的 `autotest-checks` 只用占位环境变量 |

### 架构合规

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 20 | AUTO | 新依赖只在 AutoTest：`git diff --name-only 12aded5..244609f -- backend/pyproject.toml backend/uv.lock frontend/package.json frontend/pnpm-lock.yaml` | PASS | 0 个文件 |

### 干净克隆（复盘补查，修正新增）

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 21 | AUTO | 干净克隆上跑 CI 的 AutoTest 步骤 | FAIL → 已修 | 根 `.gitignore` 的 `lib/` 规则让 `AutoTest/core/runner/lib/` 的 4 个文件（`case-index.mjs`、`classify-rules.mjs`、`guardrails.mjs`、`guardrails.d.mts`）从未提交。干净克隆上 `test:release-check`、`lint:release-check`、`test:runner`、`lint:bdd`、`typecheck`、`bdd:gen` 全部失败（`Cannot find module './lib/guardrails.mjs'`）。修复 `8137458` 后，干净克隆上 `npm ci` 和这六步全部 exit 0；CI 不跑的 `coverage`、`coverage:check`、`classify` 也 exit 0 |
| 22 | AUTO | `test-self-heal` 要派发的 `.claude/agents/heal-verifier.md` 已提交 | FAIL → 已修 | 根 `.gitignore` 的 `.claude/*` 把它忽略了。修复 `61f3c9f`：只对这一个文件 `git add -f`，不改根 `.gitignore`（主目录里它有未提交的改动） |

---

Total: 22 · AUTO: 14 | HUMAN: 8（修正：初版写成 AUTO 11 / HUMAN 9，数错了；实际是 12 / 8，再加补查的 2 项 AUTO）

## Gate Decision

- AUTO：11 PASS；3 项 FAIL 已修（#15、#21、#22），在干净克隆上复验通过。
- HUMAN：5 PASS（待审，#9 已补实测）/ 3 N/A（#2、#17 有理由；#8 前提已失效）
- Gate：**PASS（修正后，自动确认，待你审）**。初版 Gate 是在工作区上判的，漏掉了「文件根本没提交」这一类问题。

复盘备注：这次试跑暴露的问题不在清单范围里，而在 vibejet 本地环境（Python 版本、greenlet、翻译编译）。建议在清单模板里加一项「新克隆的仓库按文档能否一次跑起来」。

---

## Decision Log

- 全部关卡 `Gate: auto-confirmed — pending user review`。没有和用户来回讨论的取舍（用户的 4 个决定记在 design.md）。

复盘备注（修正时补）：上面这条建议应验在本清单自己身上。凡是「已提交」「可复现安装」这类结论，都必须在干净克隆上验证；在工作区里跑通不算证据，被 `.gitignore` 忽略的文件也在磁盘上。
