# VJ Runtime Capability Contract

VJ skills describe capabilities, not vendor tool names. The active agent maps these canonical
capabilities to its runtime primitives.

| Capability | Meaning | Claude Code adapter | Codex adapter | Fallback |
|------------|---------|---------------------|---------------|----------|
| `ask_user` | Blocking product or risk decision | structured question tool | request-user-input when available, otherwise plain question | stop with numbered decision |
| `spawn_agent` | Independent bounded task | subagent/task primitive | collaboration spawn primitive | execute inline and record fallback |
| `isolated_worktree` | Filesystem isolation for code changes | worktree task/session | `git worktree` + agent cwd | serial execution in one explicit worktree |
| `invoke_skill` | Load another skill by name | skill invocation | skill discovery/invocation | read that skill's `SKILL.md` directly |
| `write_file` | Create or patch a local artifact | edit/write primitive | apply-patch/edit primitive | shell only for generated binary output |
| `browser` | Drive and inspect a real browser | installed browser skill | installed browser skill | mark UI evidence unavailable; never claim pass |
| `web_search` | Retrieve current external evidence | installed web skill | installed web skill | stop when freshness is required |

## Rules

1. A `vj-*` skill must name the canonical capability in its main procedure. Vendor adapters belong
   here or in a runtime-specific reference, not inline in every skill.
2. Missing optional capabilities may use the documented fallback. Missing a capability required by
   an acceptance criterion is a blocker, not permission to weaken the criterion.
3. Subagents are conditional: use them only for independent work with a clear return contract.
4. Runtime artifacts and evaluation workspaces live under `.vj/` and are never committed.
5. User instructions such as "do not commit" override workflow commit defaults. Record the skipped
   commit policy in run state; do not reinterpret it as permission to omit verification.
