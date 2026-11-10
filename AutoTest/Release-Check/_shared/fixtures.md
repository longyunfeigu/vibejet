# Standing fixtures

Test objects that stay in every environment permanently, so verification does not have to build and tear them down every time. Every name starts with `e2e-fixture-` and is the same in every environment; look objects up **by name**, never by id (ids differ per environment).

Rules for using them are in `safety.md` under "Test data and operating boundary": never edit or delete them; if a check item would change one, build a temporary object instead.

## List

| Name | What it is | How it is created | Used by |
|---|---|---|---|
| `e2e-fixture-user-a` | primary test account | `POST /api/v1/auth/register` with `username` = the name, `email` = `e2e-fixture-user-a@example.com`, and the password from the environment config. AutoTest's global setup registers it when login fails because it does not exist | every guide; every AutoTest scenario |
| `e2e-fixture-user-b` | second test account | same as above, with its own name and email | "another account" checks: ownership (a non-owner gets 404), isolation, permissions |

Notes:
- Users cannot be deleted through the API. Never change these accounts' password or profile; a check that needs a different profile registers a temporary `e2e-<guide file name>-xxx` user.
- Data that belongs to these accounts (conversations, documents, files) is **not** a fixture: every guide creates what it needs and deletes it afterwards.
