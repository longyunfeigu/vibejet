---
type: bugfix                  # feature | bugfix
source_branch: fix/xxx        # full branch name
author: your-gitlab-username
services: [voiceAgent.backend] # keys from STANDARD.md section 3
safety: readonly              # readonly | writes-test-data | costly
risk: high                    # high | medium | low
regression: false             # optional, default false; true = keep in every future verification
tools: [browser]              # names from _shared/tools.md
# cost_estimate: 3 calls      # required when safety is costly
# requires: [gray:gpt-live]  # environment dependencies: gray key / model / service / outbound, see STANDARD.md 1.15
# supersedes: DEV-20261014/feature/someone-old.md   # older guide whose behavior you changed on purpose
---

## Background and goal
<!-- Who is this for and what problem does it solve? What happened before, what happens now? -->

## Entry points
<!-- Where the AI starts: page path, API, config key. No environment names, hosts, or accounts.
     Put a `file:line` from the source-branch code (repo-root path) right after every endpoint, log or page element, one per endpoint even when a line lists several (1.13).
     Writing with an AI agent? Use the `writing-release-check` skill first. -->

## How to verify
<!-- Observable signals: field values, status codes, DB rows, log keywords, numbers with thresholds, what the AI says on a call.
     At least one signal must be checkable by a program. No "works as expected".
     Write a list and tag every item (see STANDARD.md 1.4):
     [P0] the basic function works / the bug is fixed   [P1] main scenarios
     [P2] minor issue that does not block the main flow; a failure is only recorded
     Do not write "not applicable", and do not ask to reproduce the old bug or use the old version (STANDARD.md 1.11, 1.12); give a `file:line` for each endpoint, log or page element you name (1.13).
     A [P0] runs as written: Autotest only, no stopped services, no waiting for traffic, no long observation, safe on production (1.5).
1. [P0] ...
2. [P1] ...
-->

## Must not break
<!-- Neighboring features and old behaviors that must stay the same. Untagged items count as [P1]; start an item with [P2] if it only needs recording. -->

## Test data and cleanup
<!-- What data is needed, how to create it (prefer APIs, e2e- prefix), how to remove it. "Read-only, no data" is a valid answer. Standing fixtures in _shared/fixtures.md (e2e-fixture-…) can be referred to by name, with nothing to create or remove, but must not be changed. -->

## Easy to misjudge
<!-- Things that look like bugs but are not, and the reverse. -->

## This change
<!-- What this MR changed and what the new behavior should be. -->

## Depth hints
<!-- Optional: edge cases, concurrency, languages you think are most likely to break. -->

## Behavior on old version
<!-- What the old version visibly did wrong: status code, log line, wrong value, call behavior. -->

## Expected after fix
<!-- What you see after the fix, as concrete signals. -->

## Root cause
<!-- One sentence. Helps the AI find neighboring scenarios hit by the same cause. -->
