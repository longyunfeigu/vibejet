# Standing fixtures

> Chinese version: [fixtures-cn.md](fixtures-cn.md). Maintained by QA.

Test objects that stay in the QA test organization (Autotest) permanently, so verification does not have to build and tear them down every time. Every name starts with `e2e-fixture-` and is the same in every environment; look objects up **by name**, never by id (ids differ per environment).

Rules for using them are in `safety.md` under "Test data and operation boundaries": never edit or delete them; if a check item would change one, build a temporary object instead.

## List

All agents below are built from the same baseline (one conversation node, a short generic prompt, English) and differ only in the configuration named here.

| Name | What it is | Key configuration | Used by |
|---|---|---|---|
| `e2e-fixture-chat-published` | Chat Agent, published | `agent_type=chat`, `is_chat_agent=true`; Dialog Flow provider Wiz Chat Flow with a bound flow; orchestration `pregen` (the default: the fixture script does not store `orchestration_mode`, so APIs that omit unset keys, such as session-context, do not return it; set it explicitly on a temporary agent when a check needs the key) (`AutoTest/core/release-check/fixtures/ops.ts:89`); has a published version | text channels, chat, orchestration mode on text channels (the "published" case) |
| `e2e-fixture-chat-draft` | Chat Agent, never published | same as above, but **no published version** (`GET /api/agents/{id}/published-version` returns 404) | the "unpublished" case of the same checks |
| `e2e-fixture-unified` | cascaded voice agent with unified orchestration | `agent_type=call`; `llm_config.provider=wiz_chat_flow`, `llm_config.orchestration_mode=unified`; published | unified orchestration path (`[UNIFIED]` in logs), lazy-client-name style checks |
| `e2e-fixture-guardrail-injection` | cascaded voice agent whose flow has the prompt-injection check on | `agent_type=call`; flow `guardrail_checks.prompt_injection` = `enabled: true, mode: monitor`, the other two checks off; published (the published flow version carries the setting) | guardrail alerts being recorded, guardrail runtime paths |
| `e2e-fixture-voice-openai-realtime` | native voice agent, OpenAI Realtime | `llm_config.provider=e2e_realtime`, `realtime.model` = an `openai`-engine model from `GET /api/v1/admin/realtime-models`; published | voice preview, native-voice settings page checks |
| `e2e-fixture-voice-gemini-live` | native voice agent, Gemini Live | `llm_config.provider=e2e_realtime`, `realtime.model` = a `gemini`-engine model from the same catalog; published | voice preview, native-voice settings page checks |
| `e2e-fixture-voice-gpt-live` | native voice agent, GPT-Live | `llm_config.provider=gpt_live`, `gpt_live` empty (runtime default model and voice); published | voice preview, GPT-Live settings page checks |

Notes:
- **Native voice agents are for voice preview and page checks only.** They are not guaranteed to hold a full call; a check that needs a call on a native model builds its own temporary agent.
- **If the environment has no model for an engine, that fixture does not exist there**, and check items that need it are judged "not applicable" (the model is not deployed in that environment).
- The GPT-Live provider option appears in the UI only for organizations holding the gray-release key `gpt-live`. The fixture itself exists without it; a page check that needs the picker turns the key on for Autotest temporarily, as described in `safety.md` "How to do it".
- `e2e-fixture-unified` uses the baseline single-node flow. A check that needs extra flow content (for example an intent condition plus a KB task with rewrite on) builds a temporary agent with that content.

## Not standing fixtures

These are still created per run, as described in `safety.md` "How to do it":
- accounts (read-only account, account with only `view_agent`, and so on);
- organization gray-release switches and model slots: change them for the run and restore them.

## Creating them in an environment

`AutoTest/core/release-check/fixtures/` creates whatever is missing and is idempotent: an object found by name is never changed; if its configuration differs from this list, the differences are reported (exit code 1) for a person to fix.

```bash
cd AutoTest
export VOICE_AGENT_BASE_URL=<deployment root URL>
export VOICE_AGENT_USERNAME=<QA account>
export VOICE_AGENT_PASSWORD=<its password>      # never write it to a file
export VOICE_AGENT_ORG=Autotest
npm run fixtures:release-check -- --dry-run    # list what would be created
npm run fixtures:release-check                 # create the missing ones
```

Optional: `FIXTURE_OPENAI_REALTIME_MODEL`, `FIXTURE_GEMINI_LIVE_MODEL` pin the realtime model; by default the script takes, in sorted order, the first model of that engine whose id contains none of `preview`, `transcribe`, `shim`.

A change to this list must be made in the script's `spec.ts` at the same time.
