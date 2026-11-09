# 功能检查清单：引入 voice-agent 交付链与 AutoTest（试用期）

> 由 `/feature-checklist` 在**无人值守模式**下产出。HUMAN 项的判定是「自动确认，待你审」，每项附依据。

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
| 8 | HUMAN | AUTH-LGN-003 在翻译未编译的环境上会失败 | 未执行（推断） | 编译前用 curl 实测，接口返回 `auth.password.invalid`，剧本期望 `Invalid username or password`；但没有在编译前实际跑这个场景 |
| 9 | HUMAN | lint-bdd 修复前，嵌套功能目录确实被跳过 | 未执行（推断） | 代码阅读：原版 Check B/C/E/F/H 只拼接 `modules/<m>/<dir>`；没有用原版 lint 对新模块实测 |

### 回归

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 10 | AUTO | 产品代码未改：`git diff --stat 12aded5..HEAD -- backend frontend` | PASS | 0 files changed |
| 11 | AUTO | vj 链 skill 未改：`git diff --name-only 12aded5..HEAD -- '.agents/skills/vj*'` | PASS | 0 个文件 |
| 12 | AUTO | 类型检查：`npm run typecheck` | PASS | 0 errors |
| 13 | AUTO | BDD 规范：`npm run lint:bdd` | PASS | 8/8 项通过 |
| 14 | AUTO | 步骤匹配：`npm run bdd:gen`（含 CI 占位环境变量的跑法） | PASS | exit 0 |

### 部署安全

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 15 | AUTO | 锁文件已提交，可复现安装：`npm ci` | PASS | `AutoTest/package-lock.json`；`npm ci` exit 0 |
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
| 20 | AUTO | 新依赖只在 AutoTest：`git diff --name-only 12aded5..HEAD -- backend/pyproject.toml backend/uv.lock frontend/package.json frontend/pnpm-lock.yaml` | PASS | 0 个文件 |

---

Total: 20 · AUTO: 11 | HUMAN: 9

## Gate Decision

- AUTO：11 PASS / 0 FAIL
- HUMAN：5 PASS（待审）/ 2 未执行（推断，见 #8、#9）/ 2 N/A（有理由）
- Gate：**PASS（自动确认，待你审）**。#8、#9 没有实测，不算作证据；如需证据，可以对这两项各补跑一次。

复盘备注：这次试跑暴露的问题不在清单范围里，而在 vibejet 本地环境（Python 版本、greenlet、翻译编译）。建议在清单模板里加一项「新克隆的仓库按文档能否一次跑起来」。

---

## Decision Log

- 全部关卡 `Gate: auto-confirmed — pending user review`。没有和用户来回讨论的取舍（用户的 4 个决定记在 design.md）。
