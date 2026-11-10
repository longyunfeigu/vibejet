# T1: Presentation Layer Change — Checklist Template

**Feature**:
**Type**: T1 (Presentation Layer)
**Date**:

---

## UI/UX Verification

- [ ] [HUMAN] Visual output matches the design spec or requirement description
- [ ] [HUMAN] Change is correct across relevant screen sizes / breakpoints (if responsive)
- [ ] [AUTO] No new TypeScript / ESLint errors introduced

## Regression Risk

- [ ] [AUTO] Changed components have no modified prop interfaces (no logic change leaked in)
- [ ] [AUTO] Snapshot tests (if any) updated to reflect new visual output
- [ ] [AUTO] No changes to API call logic, state management, or event handlers

## Architecture Compliance

- [ ] [AUTO] No hardcoded strings that should be i18n keys (if project uses i18n)
- [ ] [AUTO] No inline styles introduced where CSS classes should be used (per project convention)
