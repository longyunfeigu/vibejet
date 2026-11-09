# T6: External Dependency Change — Checklist Template

**Feature**:
**Type**: T6 (External Dependency Change)
**Dependency**: [name and version change, e.g., litellm 1.2.3 → 1.5.0]
**Changelog URL**:
**Date**:

---

## Upstream Review (CRITICAL — Complete Before Coding)

- [ ] [HUMAN] Full changelog read between old and new version
- [ ] [HUMAN] List of breaking changes documented here: ___
- [ ] [HUMAN] For each breaking change: confirm it is handled in our code

## Behavior Parity

- [ ] [AUTO] All existing tests pass with new dependency version
- [ ] [HUMAN] Key integration paths tested manually (not just unit tests)
- [ ] [HUMAN] Error handling still works correctly for new error types/formats

## Regression Risk

- [ ] [AUTO] No new deprecation warnings that indicate future breakage
- [ ] [HUMAN] Behavior of the dependency in edge cases verified (e.g., timeout handling, rate limits)

## Deployment Safety

- [ ] [HUMAN] New dependency version tested in staging environment
- [ ] [HUMAN] Rollback plan: confirm old version can be restored if issues occur
- [ ] [AUTO] Lock file updated (requirements.txt or package-lock.json pinned to exact version)

## Security (if security-relevant dependency)

- [ ] [HUMAN] CVE check run on new version
- [ ] [HUMAN] No new permissions or data access patterns introduced

## Performance

- [ ] [HUMAN] Performance benchmarks run if dependency is in a hot path
         (especially for llm-proxy, agent-flow, voice-agent core)

## Architecture Compliance

- [ ] [AUTO] Dependency added only in the appropriate layer (not imported by wrong modules)
