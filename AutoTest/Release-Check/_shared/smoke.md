# Production smoke items

Run on every environment after its upgrade. Independent of what changed: they only answer "after this upgrade, do the most basic user paths still work here". Every item is `[P0]` and runs as written per `STANDARD.md` 1.5; verdicts follow `safety.md`, and any failure stops this environment from being released.

- Identity: the test account `e2e-fixture-user-a` (`fixtures.md`).
- Safety: `readonly`.

## How to verify

1. [P0] **Login**: log in through the browser at `/login` with `e2e-fixture-user-a`; the home page heading reads `你好，<full name or username>` (`frontend/src/features/home/components/HomeDashboard.tsx:43`). In the same session `GET /api/v1/auth/me` (`backend/api/routes/auth.py:111`, prefix `/api/v1` from `backend/main.py:187`) returns 200 and its body contains `"username": "e2e-fixture-user-a"`.
2. [P0] **Service liveness**: `GET /health/live` and `GET /health/ready` both return 200 (`backend/api/routes/health.py:15`, `backend/api/routes/health.py:20`).
3. [P0] **Core API**: `GET /api/v1/conversations` (`backend/api/routes/conversations.py:57`) with the account's token returns 200.

## Test data and cleanup

Standing fixtures only; nothing is created, edited, or deleted.

## Easy to misjudge

- `GET /health` (without `/live` or `/ready`) also exists; the two probes above are the ones that say whether the service accepts traffic.
- An empty conversation list is a pass: the item checks that the API answers, not that the account has data.
