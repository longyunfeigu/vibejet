# VJ Workflow Evals

这套 eval 测 `vj-*` 工作流本身，不测产品业务代码。每个 trial 使用系统临时目录下的独立
worktree，运行结果写入已忽略的 `.vj/evals/`，主工作区只读。Codex runner 使用
`workspace-write`；runner prompt 同时禁止访问父仓库。Claude CLI 没有等价的 OS 级路径
sandbox，因此只在可信 case 上使用，不能把 prompt 隔离当成安全边界。

## 指标

- `pass@1`：每个 case 的首次 trial 通过率。
- `pass^3`：每个 case 前三次 trial 全部通过的比例。
- `human_interventions`：无人值守 case 中额外向人提问的次数。
- `rework_rounds`：同一 trial 内验证失败后的修复轮数。
- `invalid_command_rate`：`workflow_doctor.py` 判定无效的验证命令占比。
- `tokens` / `duration_ms`：runner 返回的 token 与墙钟耗时。

`human_interventions` 和 `rework_rounds` 当前优先读取 agent 最终的 `VJ_EVAL_RESULT`；这是
自报指标，不能替代 assertion。决定 pass/fail 的仍是文件、命令和 doctor 等外部 grader。
Case 变更 assertion 或关键 prompt 时递增 `revision`；summary 不混用旧 revision。额度耗尽、
认证或连接错误记为无效 trial，不计入 pass@1 / pass³。
只有 `case revision + runner + model + budget + harness` 相同的 baseline/candidate 才能做因果 A/B；
跨 runner 结果只能证明各自产物能否过 grader，不能比较 token、时长或宣称工作流优化幅度。
每次 run 还记录 `workflow_fingerprint`；summary 按 fingerprint 分组，不把修改前后的 trial 拼成
pass³。

## 使用

```bash
python3 .agents/evals/vj-workflow/scripts/vj_eval.py list

# 当前工作树候选版
python3 .agents/evals/vj-workflow/scripts/vj_eval.py run \
  --case router-epic --variant candidate --runner claude --trials 3

# 冻结的旧版；baseline root 内应含 skills/、AGENTS.md、ai-workflow.md
python3 .agents/evals/vj-workflow/scripts/vj_eval.py run \
  --case router-epic --variant baseline --runner claude --trials 3 \
  --baseline-root /tmp/vibejet-vj-baseline-20260710

python3 .agents/evals/vj-workflow/scripts/vj_eval.py summarize
```

当前只有 routing case。artifact case（vj-epic-story / vj-epic-plan 产物）依赖一份 PRD 与 Epic
夹具，仓库里目前没有在轨产品，需要时随夹具一起显式新增。完整实现类 eval 必须显式新增 case，
并使用测试 DB、隔离外部副作用和 `不要提交 commit` 的 prompt；不要拿主工作区充当 eval sandbox。
