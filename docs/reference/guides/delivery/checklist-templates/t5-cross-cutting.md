# T5: Cross-Cutting Change — Checklist Template

**Feature**:
**Type**: T5 (Cross-Cutting Change)
**Complete Usage Map**: [paste or link from design document]
**Date**:

---

## Completeness (CRITICAL)

- [ ] [AUTO] Grep for old reference across entire codebase — result must be 0 occurrences
         Command: `grep -r "[OLD_ELEMENT]" --include="*.py" --include="*.ts" .`
- [ ] [AUTO] Check for dynamic/string-based references that grep may miss
         (e.g., `getattr(obj, field_name)` where field_name is a variable)
- [ ] [HUMAN] Review Usage Map — confirm every listed location has been updated

## Per-Location Verification

For each location in the Usage Map:
- [ ] [HUMAN] [Location 1]: _____ — verified correct
- [ ] [HUMAN] [Location 2]: _____ — verified correct
- [ ] (add one item per location in the Usage Map)

## Regression Risk

- [ ] [AUTO] All existing tests pass
- [ ] [AUTO] Tests that reference the changed element are updated
- [ ] [HUMAN] Updated tests still test meaningful behavior (not just renamed)

## Data Compatibility

- [ ] [AUTO] If schema field renamed, migration handles existing data
- [ ] [AUTO] API response backward compatibility maintained or versioned

## Architecture Compliance

- [ ] [AUTO] No print() used
- [ ] [AUTO] All new/modified functions have type hints
