# Tool registry

The lint reads the **first column** of this table; a guide's `tools` field may list only these names. `Status`: `available` can be used now; `planned` is still being built — whoever runs the verification uses an equivalent read-only means instead; anything that still cannot be done is a test-facility gap, recorded "blocked by environment" with the missing tool named.

| Name | What it does | Read/Write | Status |
|---|---|---|---|
| `browser` | Drive the vibejet web app like a user: Playwright through `AutoTest/`, or the `web-access` skill for an ad-hoc check | read + write via UI | available |
| `api` | Call vibejet REST APIs with a test account's bearer token: `POST /api/v1/auth/login` with body `{"username", "password"}` (`backend/application/dto.py:214`), token at `data.access_token` (`backend/application/dto.py:239`); create and delete test data | read + write | available |
| `db-readonly` | Run one SQL statement in a read-only transaction (30 s timeout) inside the Postgres container; prints a table | read only | available |
| `app-logs` | Read the backend's log output for a time window (`docker logs` of the app container, or the dev server's terminal output) | read only | available |
| `e2e-suite` | Run AutoTest BDD scenarios by module or tag (`npm run test:<module>:<env>` in `AutoTest/`) | read + write test data | available |

`db-readonly` lives in `AutoTest/core/release-check/tools/db-readonly.sh`; usage is in the script header. It knows no environment: `--container` names the database container and `--via "<command prefix>"` runs it on another host.
