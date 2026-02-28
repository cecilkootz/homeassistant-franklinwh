---
phase: 01-file-relocation
plan: 01
subsystem: infra
tags: [hacs, home-assistant, git-mv, custom-component]

# Dependency graph
requires: []
provides:
  - "All 11 integration files at custom_components/franklin_wh/ standard HACS discovery path"
  - "hacs.json with only name key — no content_in_root, no zip_release workarounds"
  - "Git rename history preserved for all 11 files"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "git mv for history-preserving file relocation"
    - "Single atomic commit for multi-file structural changes"

key-files:
  created:
    - custom_components/franklin_wh/__init__.py
    - custom_components/franklin_wh/config_flow.py
    - custom_components/franklin_wh/const.py
    - custom_components/franklin_wh/coordinator.py
    - custom_components/franklin_wh/diagnostics.py
    - custom_components/franklin_wh/sensor.py
    - custom_components/franklin_wh/switch.py
    - custom_components/franklin_wh/manifest.json
    - custom_components/franklin_wh/strings.json
    - custom_components/franklin_wh/services.yaml
    - custom_components/franklin_wh/translations/en.json
  modified:
    - hacs.json

key-decisions:
  - "Used git mv for all 11 files to preserve rename history rather than cp + git rm"
  - "Single atomic commit for all renames and hacs.json edit to prevent broken intermediate state"
  - "Removed content_in_root and zip_release from hacs.json — HACS standard discovery now applies"

patterns-established:
  - "Integration files live at custom_components/franklin_wh/ — HACS standard path"

requirements-completed: [FILE-01, FILE-02, FILE-03, FILE-04, FILE-05, FILE-06, FILE-07, FILE-08, FILE-09, FILE-10, FILE-11, FILE-12, CONF-01, CONF-02, CONF-03]

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 1 Plan 1: File Relocation Summary

**11 integration files relocated from repo root to `custom_components/franklin_wh/` via `git mv`, with `hacs.json` stripped of `content_in_root`/`zip_release` workarounds — all in one atomic commit with full rename history preserved**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-27T00:34:31Z
- **Completed:** 2026-02-27T00:37:30Z
- **Tasks:** 2
- **Files modified:** 12 (11 renames + hacs.json edit)

## Accomplishments
- All 7 Python integration files moved to `custom_components/franklin_wh/` with git rename history
- All 4 JSON/YAML/translations config files moved to standard paths
- `hacs.json` reduced to `{"name": "FranklinWH"}` — repository is now HACS-compliant without workarounds
- Repository root is clean (only README.md, hacs.json, LICENSE, .github/)

## Task Commits

Each task was committed atomically:

1. **Task 1 & 2: Move files + verify + commit** - `5f5e8cc` (refactor)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `custom_components/franklin_wh/__init__.py` - Integration entry point (relocated from root)
- `custom_components/franklin_wh/config_flow.py` - Config flow (relocated)
- `custom_components/franklin_wh/const.py` - Constants (relocated)
- `custom_components/franklin_wh/coordinator.py` - Data coordinator (relocated)
- `custom_components/franklin_wh/diagnostics.py` - Diagnostics (relocated)
- `custom_components/franklin_wh/sensor.py` - Sensor platform (relocated)
- `custom_components/franklin_wh/switch.py` - Switch platform (relocated)
- `custom_components/franklin_wh/manifest.json` - Integration manifest (relocated)
- `custom_components/franklin_wh/strings.json` - UI strings (relocated)
- `custom_components/franklin_wh/services.yaml` - Service definitions (relocated)
- `custom_components/franklin_wh/translations/en.json` - English translations (relocated)
- `hacs.json` - Stripped to name-only (removed content_in_root, zip_release)

## Decisions Made
- Used `git mv` (not `cp` + `git rm`) so GitHub and git clients show these as renames, not new files
- All 12 changes committed atomically to prevent any broken intermediate state
- Used Python to edit hacs.json to avoid manual JSON formatting errors

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Repository is fully HACS-compliant. HACS can now discover the integration at `custom_components/franklin_wh/` without any workaround keys.
- Phase 2 (if any) can build on the clean standard directory structure.

---
*Phase: 01-file-relocation*
*Completed: 2026-02-27*
