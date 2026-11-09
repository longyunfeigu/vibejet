# Tool registry

> Chinese version: [tools-cn.md](tools-cn.md). Maintained by QA. The lint reads **this English file**;
> keep the first column identical in both files.

A guide's `tools` field may list only names from the first column. `Status`: `available` can be used now; `planned` is still being built — whoever runs the verification uses an equivalent read-only means instead; anything that still cannot be done is a test-facility gap, recorded "blocked by environment" with the missing tool named, and QA builds it.

| Name | What it does | Read/Write | Status |
|---|---|---|---|
| `browser` | Drive the web consoles (voice-agent, agent-flow, kbhub, human-agent) like a user | read + write via UI | available |
| `api` | Call product REST APIs; create and delete test data | read + write | available |
| `conversation-bench` | Replay recorded conversation cases against agent-flow and score them | read; spends LLM tokens | available |
| `ai-simulation-call` | Place a simulated call against an agent and get transcript, recording, verdict | write (creates a call); costly | planned |
| `kubectl-readonly` | Inspect pods, images, jobs, configmaps, pod logs, `/metrics`; refuses writes, `exec` and reading Secrets | read only | available |
| `sentry-query` | Look up new Sentry issues and events in a time window | read only | planned |
| `jenkins-build-info` | From the build number in an image tag, find the commit that build actually used | read only | planned |
| `db-readonly` | Run one SQL statement inside the service's own pod, with its own database connection, in a read-only transaction (30 s timeout); prints a table | read only | available |

`kubectl-readonly` and `db-readonly` live in `AutoTest/core/release-check/tools/`; usage is in each script's header. Neither knows any environment: `--via "<command prefix that runs a command on the target>"` says where to run.
