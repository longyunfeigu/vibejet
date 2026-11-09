# Production smoke items

> Chinese version: [smoke-cn.md](smoke-cn.md). Maintained by QA.

Run on every production environment after its upgrade, and on UAT too. Independent of what this release changed: they only answer "after this upgrade, do the most basic user paths still work here". Every item is `[P0]` and runs as written per `STANDARD.md` 1.5; verdicts follow `safety.md`, and any failure stops this environment from being released.

- Identity: the test organization Autotest + the QA test account (same as for guides).
- Safety: `costly`, 1 call per environment.
- Standing fixture used: `e2e-fixture-unified` (`fixtures.md`). If this environment lacks it, create it per `fixtures.md` first; if the script cannot create it, the environment or the script is broken: record "blocked by environment" and report it for fixing.

## How to verify

1. [P0] **Login**: log in through the browser with the QA test account; after entering the Autotest organization the agent list page shows `e2e-fixture-unified`. In the same session `GET /api/v1/me/permissions` returns 200 (`RD/voice-agent/backend/app/api/v1/permissions_me.py:29`).
2. [P0] **Service liveness**: `GET /api/health` and `GET /api/health/ready` both return 200 (`RD/voice-agent/backend/app/api/v1/health.py:14`, `:23`).
3. [P0] **Core APIs**: `GET /api/agents` returns 200 and includes `e2e-fixture-unified` (`RD/voice-agent/backend/app/api/v1/agents.py:176`); `GET /api/calls` returns 200 with a paginated list (`RD/voice-agent/backend/app/api/v1/calls.py:786`).
4. [P0] **One call**: place 1 simulated call to `e2e-fixture-unified` through ai-simulation; the call ends normally. The call then appears in `GET /api/calls` with a duration above 0, and `GET /api/calls/{call_id}/messages` (`calls.py:1593`) returns 200 with at least one agent turn and one user turn.

## Test data and cleanup

Standing fixtures only; nothing is created, edited, or deleted. The call record stays in Autotest and needs no cleanup.

## Easy to misjudge

- Right after an agent upgrade, old replicas are still draining calls (up to about 100 minutes); a new call lands on a new replica and does not affect the verdict.
- The opening line and content of a simulated call vary with the model; judge only that both sides spoke and the call ended normally, not what was said.
