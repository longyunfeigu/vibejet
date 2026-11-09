# Release-Check — verification guides for the AI

> Chinese version: [README-cn.md](README-cn.md)

## What this is

Every feature and every bug fix ships with a **verification guide for the AI**: background, goal, and what "correct" looks like. The AI reads the guide, decides how to test in the environment it is pointed at, tests on its own, and returns verdicts backed by evidence. Developers do not join the test run and never explain anything verbally.

A guide is **not** a step-by-step test case and **not** a script: write the why and the observable signals; the AI finds its own path. A guide does not depend on any environment; it can be used anywhere, at any time.

## Layout

```
Release-Check/
  README.md / STANDARD.md / TEMPLATE-feature.md / TEMPLATE-bugfix.md   (+ -cn companions)
  _shared/
    safety.md            how to verify and judge, what may and may not be done
    tools.md             registered tools
    fixtures.md          standing test objects (e2e-fixture-…)
    smoke.md             production smoke items: run on every environment after its upgrade
  DEV-20261021/          one folder per release branch, named exactly like the branch
    feature/<author>-<slug>.md
    bugfix/<author>-<slug>.md
  HOTFIX-xxxx/           same layout
```

## What developers do (in the same MR as the code)

1. Copy `TEMPLATE-feature.md` or `TEMPLATE-bugfix.md` (or the Chinese version; one language is enough) into `<release branch>/feature/` or `<release branch>/bugfix/`, and write it following [STANDARD.md](STANDARD.md). Writing with an AI agent (Claude Code / Codex)? Have it use the `writing-release-check` skill (`.claude/skills/writing-release-check/`) first: it follows the reviewer's checklist step by step and ships a reference self-check script.
2. Check it before pushing and fix every error:

```bash
cd AutoTest
npm run lint:release-check -- Release-Check/DEV-20261021/bugfix/<file>.md
```

An MR with a failing guide is not merged.

## File naming

`<author>-<slug>.md`

- author: your GitLab username (the MR author).
- slug: the branch name without a `feature/` `feat/` `fix/` `bugfix/` `hotfix/` `change` prefix and without the trailing name and date, in lowercase kebab-case.
- `fix/...` branches go under `bugfix/`, everything else under `feature/` (unless it really is a bug fix).

| Branch | Author | File |
|---|---|---|
| `feature/native-voice-preview_Lei_20261016` | `Lei` | `Lei-native-voice-preview.md` |
| `fix/agent-flow-db-conn-held-across-llm_yuehan_20261015` | `yuehan` | `yuehan-agent-flow-db-conn-held-across-llm.md` |
| `feature-batch-agent-search-yosia-20261020` | `yosia` | `yosia-batch-agent-search.md` |
| `fix/text-test-system-time` | `someone` | `someone-text-test-system-time.md` |

## Guide exemption

Pure refactors, CI changes, docs, and AutoTest-only MRs may skip the guide by writing `release-check: exempt <reason>` in the MR description.
