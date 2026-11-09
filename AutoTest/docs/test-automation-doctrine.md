# Test Automation Doctrine — The Three-Cost Model

> **Status:** Binding. Any agent extending AutoTest MUST follow this. Referenced as a CRITICAL principle in `AutoTest/AGENTS.md`.

---

## 0. Why this document exists

Human attention is the scarcest resource in this project. The default for every
test case is **automation**; a human in the loop is the **exception that must be
argued for**, not the fallback.

This doctrine exists to kill one specific failure mode:

> An agent declares a capability "not automatable / subjective / needs a real
> environment", and quietly hands the whole thing back to a human — to avoid the
> work of building the harness.

That is almost always wrong. "Hard to automate" and "cannot be automated" are
different claims, and the gap between them is *engineering capex the agent didn't
want to pay*. This document gives every agent a fixed vocabulary to tell those two
apart, and a hard rule that forbids the cop-out.

---

## 1. The Three-Cost Model

Every automated test decomposes into three independent costs. A test feels "hard"
because **exactly one (or more) of these three is expensive** — never because the
test is mystically un-automatable.

| Cost | Question it answers | Examples of "expensive" |
|------|---------------------|-------------------------|
| **Input cost** | How do we produce the stimulus? | Emotional/accented audio, precise pause/barge-in timing, multi-turn reflect scripts |
| **Environment cost** | How do we arrange the system under test? | Point ASR at a dead endpoint, flip a Docker env var, inject a 500, force degradation, then restore |
| **Verdict cost** (oracle) | How do we decide pass/fail deterministically? | "Does this TTS *sound* natural?", real PSTN call quality, conversational naturalness |

Before calling anything "manual", an agent MUST name **which of the three costs**
is the blocker. If it cannot, it has not analysed the problem.

---

## 2. The decisive rule: which costs are one-time, which is irreducible

This is the core of the doctrine. The three costs are **not equal**:

### Input cost and Environment cost are ONE-TIME CAPEX

Build the fixture once → replay it forever. Build the fault-injection / env-orchestration
layer once → every degradation, timeout, and fallback case reuses it.

- The cost is paid **once**, at framework-build time — **not per case**.
- Therefore: **"it is expensive to build" is NEVER a valid reason to hand it to a
  human.** It is a reason to *build the capex*, then automate infinitely.
- A golden audio set (emotion, accent, timing) is capex. A fault-injection
  orchestration layer (mutate env → test → safely restore) is capex. Both are
  in-scope, both must be built, neither is "manual work".

### Verdict cost (the oracle problem) is the ONLY irreducible one

Only "how do we deterministically decide it's *right*" can be genuinely irreducible
— a machine cannot assert "this sounds natural." But even here, the answer is
**not** "give it to a human." The mandated order is:

1. **Push the oracle with a proxy metric first.** Examples:
   - TTS correctness → feed the synthesized audio back through ASR, compare text
     (sidesteps "naturalness", proves "content is right").
   - Naturalness → score with a MOS model, threshold the number.
   - Latency / timing → it is already a number; assert it directly.
2. **Only the residue that survives all proxies goes to a human** — and even then
   as **sampling** (spot-check new/changed features), **never as full regression.**

So the human residual is: subjective quality, sampled, on a shrinking set. Not
"humans run the regression suite."

---

## 3. The anti-cop-out rule (enforcement teeth)

When an agent proposes leaving any case to a human, the proposal is **rejected by
default** unless it carries all of:

1. **The blocking cost, named** — Input, Environment, or Verdict.
2. **If Input or Environment:** it is capex. The agent must scope the capex and
   build it (or file it as an explicit backlog task to build). It is **NOT eligible
   to be labelled "manual" / "non-automatable".** Deferring to a human as the
   *permanent* answer is forbidden.
3. **If Verdict:** the agent must state **which proxy oracle it attempted** (ASR
   read-back, MOS, numeric threshold, log assertion...) and *why* it is
   insufficient, before proposing sampling. The word "subjective" alone is **not**
   a justification.
4. **An audit trail:** every "leave to human" decision is logged with the cost it
   is blocked on, so the human residual stays visible and provably shrinking over
   time.

If an agent says "I automated the easy part, the rest needs a human" without the
above, treat it as an incomplete analysis and push back.

---

## 4. Worked mapping (voice agent, from the source project)

This table comes from the voice-agent project this doctrine was written for. For vibejet, build the same
table for a capability when its first test is planned.

Each capability tagged with its blocking cost and resulting tier. Use this as the
template for classifying any new capability.

| Capability | Input | Env | Verdict | Tier |
|------------|-------|-----|---------|------|
| Language / ASR-routing switch | TTS-synth, cheap | default | log, deterministic | **Automate now** |
| Voice switch / hotword hit | cheap | default | log, deterministic | **Automate now** |
| ASR accuracy | golden audio | default | WER threshold | **Automate now** |
| Emotion recognition / response | **hard — golden set** | default | label, deterministic | **One-time capex (golden audio)** |
| Pause-then-continue / barge-in timing | **human-designed timing (once)** | default | timing, measurable | **One-time capex (golden script)** |
| Reflect multi-turn | **human-designed script (once)** | default | log / state | **One-time capex (golden script)** |
| ASR fallback / degradation | cheap | **fault injection (env/endpoint)** | log, deterministic | **One-time capex (env orchestration)** |
| TTS naturalness / emotional "feel" | cheap | default | **oracle-hard** | **Proxy (MOS / read-back) + sampled human** |
| Real PSTN end-to-end quality | real link | **real telephony** | **oracle-hard** | **Sampled human residual** |

Reading the table: the **only** rows where a human survives are the last two, and
only for the subjective residue after proxy oracles — everything above is either
"automate now" or "capex, then automate".

---

## 5. Relationship to the existing exclusion gate

> Source-project history: vibejet has no such plan, exclusion gate or capability-e2e framework yet. The
> reading rule below still applies to any gate added later.

The `2026-06-12-autotest-80pct-automation` plan defines an **exclusion gate** that
skips `FAULT` (fault-injection) and `voice` cases as "non-automatable". Read that
gate correctly:

- That gate excludes those cases **from a fast UI-generation campaign** — it does
  **not** declare them permanently manual. Under this doctrine they are
  **capex-deferred**: `FAULT` is Environment-cost capex; `voice` is Input-cost
  capex. Both are in-scope for automation; the gate just sequences them after the
  cheap UI work.
- `PROD` (production-unsafe destructive writes) is different: it is excluded for
  **safety**, not cost. That boundary stays real — but even it moves to automation
  once an isolated environment exists. Never automate destructive production writes
  just to satisfy this doctrine.

The **capability-e2e** framework (`modules/voice-agent/capability-e2e/`) is the
existing proof that Environment-cost + oracle can be paid once: it synthesizes
audio, drives the browser, and reads the agent's Docker logs for a deterministic
verdict. New voice capabilities extend it with data-driven recipes — they do not
start a new "leave it to a human" conversation.

---

## 6. Agent checklist (run this before writing any test or deferring any case)

1. Name the capability's three costs. Which one is expensive?
2. Input or Environment expensive? → It is **capex**. Build it (or file a backlog
   task to build it). Do **not** mark it manual.
3. Verdict expensive? → Name the proxy oracle you will use. Only the residue after
   the proxy is human, and only as **sampling**.
4. Deferring to a human? → Log the blocking cost. If it is Input/Environment, you
   are wrong — re-read §3.
5. Is it `PROD`-destructive? → That is the one legitimate safety exclusion. Isolate
   the environment or leave it, but say so explicitly.
