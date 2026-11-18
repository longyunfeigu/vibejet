---
name: verify
description: 把这次改动真跑起来，用证据证明它能用——按改动面先跑便宜检查（lint / 类型 / 单测），再在隔离环境（独立 postgres 容器、随机端口的后端和前端）里起应用、走注册登录和带鉴权的接口、跑 AutoTest 的 @smoke 浏览器场景并截图，最后给出逐步报告和可贴进 commit 的 `Verified:` trailer。任何会改变运行行为的改动在说"做完了"或 commit 之前用；vj-work、run-test、vj-test、diff-aware-qa 需要一个跑着的应用时也用它起。用户说"verify""验证一下""跑起来看看""冒烟""smoke test""起个环境""启动下服务"时使用。
---

# verify — 把改动跑起来再说做完

单元测试全过、功能照样可能是坏的（实测一次前端 78 个单测全过，端到端仍抓出 3 个功能问题）。
所以"做完"的凭据是把应用真跑起来走一遍，而不是读代码或只跑单测。这个 skill 只回答一个问题：
**这次改动跑起来能用吗**——它要快、要稳，每次改动都能跑。完整回归归 `run-test`，读代码找设计问题归 `review`。

## 怎么跑

```bash
python3 .agents/skills/verify/scripts/verify.py run            # 最常用：检查 → 起环境 → 冒烟 → 关环境
python3 .agents/skills/verify/scripts/verify.py run --keep     # 跑完留着环境，给人亲手试（用完 down）
python3 .agents/skills/verify/scripts/verify.py run --base main   # 分支上已经 commit 的改动也算进来
python3 .agents/skills/verify/scripts/verify.py up --level ui  # 只起环境：vj-work 开工起一次，各切片共用
python3 .agents/skills/verify/scripts/verify.py smoke          # 对已起的环境再跑一遍冒烟
python3 .agents/skills/verify/scripts/verify.py status | down
```

在仓库根目录或 worktree 根目录跑都行；每个 worktree 有自己的容器名和状态目录（`.vj/verify/`），并行不打架。
本机已有的 `user_db` 容器、8010 / 5173 端口不碰。第一次跑会装依赖和 Playwright 浏览器，较慢；之后整轮在一分钟内。

## 档位：按改动面自动选

| 改动                                    | 档位   | 做什么                                                                                |
| --------------------------------------- | ------ | ------------------------------------------------------------------------------------- |
| 只有文档、`.agents/`、`.claude/`、`.md` | `none` | 只跑便宜检查（没有就什么都不跑）                                                      |
| 只有 `backend/`                         | `api`  | 后端检查 → 起库和后端 → 健康检查、注册、登录、带 token 读自己、读一个按归属过滤的列表 |
| 碰了 `frontend/`、`AutoTest/` 或其他    | `ui`   | 再加前端检查 → 起前端 → AutoTest `@smoke` 场景 → 登录后首页截图                       |

没有任何改动时按 `ui` 验。判断错了用 `--level` 指定，例如后端改了登录接口、想顺便看页面：`run --level ui`。

## 失败了怎么办

报告（`.vj/verify/report.md`）逐步列出通过 / 失败、耗时和失败原因；服务日志在 `.vj/verify/*.log`，
浏览器失败截图在 `AutoTest/report/test-artifacts/`。先看是哪一步：

- **检查或冒烟失败**：是这次改动的问题 → 修代码，再跑 `verify.py run`。同一个失败修了 3 轮还过不了，
  停下，把最后的报错、试过什么写给用户，不要继续猜。
- **环境起不来**（依赖、端口、docker）：先对照 `AutoTest/AGENTS.md`「常见陷阱与修复」，修的是环境不是代码。
- **浏览器步骤时好时坏**：不加等待、不重试到通过、不跳过——这正是要找的问题。是测试写法的问题交给
  `test-self-heal`，它只修测试；是功能的问题就修功能。

不要为了让 verify 变绿去改 verify 本身、`@smoke` 场景或它们的断言；它们要改，单独提出来给用户看。

## 证据和 commit

- 回复用户时贴报告里的步骤表（或至少结果和失败那一步），有截图就给 `.vj/verify/home.png` 的路径。
- commit 时把报告最后一行的 trailer 带上：`Verified: smoke-ui` / `smoke-api` / `checks`；没跑或跑失败也要如实写
  `Verified: none (原因)`，这样以后能查出哪些提交没验证过。
- 没法跑（没有 docker、用户说不要起服务）时如实说"未运行验证"，不能拿单测结果顶替。

## 谁会调它

| 调用方                                   | 用法                                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------------- |
| `vj` Patch / Story 轨                    | 改完跑 `run`，报告贴进收尾回复                                                  |
| `vj-work`                                | 开工 `up --level ui` 起环境跑基线，收尾 `down`                                  |
| `run-test` / `vj-test` / `diff-aware-qa` | 应用没起时先 `up --level ui`，再用 `status` 里的 `frontend_url` / `backend_url` |

在 verify 起的环境上跑 AutoTest 的任意模块（测试账号 `e2e-fixture-user-a`，密码每次随机，`env` 会一并给出）：

```bash
eval "$(python3 .agents/skills/verify/scripts/verify.py env)"
cd AutoTest && HEADLESS=true ./core/runner/run-bdd.sh <all|smoke|auth|home> verify
```

环境起着的时候改代码：后端（`--reload`）和前端（Vite 热更新）都会自动生效；新加的数据库迁移不会，
`smoke` 开头会先应用，所以加了迁移后先跑一次 `smoke`，再直接跑 AutoTest。
