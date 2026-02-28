---
phase: 03-vendor-and-wire-http-client
plan: "02"
subsystem: api
tags: [httpx, homeassistant, franklinwh, coordinator, config_flow]

requires:
  - phase: 03-01
    provides: Vendored franklinwh package with session injection support in TokenFetcher and Client

provides:
  - coordinator.py wired to HA httpx client via get_async_client, no executor job wrapping
  - config_flow.py wired to HA httpx client via get_async_client, no executor job wrapping
  - manifest.json with franklinwh removed from requirements (now vendored)

affects: []

tech-stack:
  added: []
  patterns:
    - "Use get_async_client(hass) to obtain HA-managed httpx session; never close it"
    - "Inject session into TokenFetcher and Client constructors at construction time"
    - "Client construction is non-blocking — no async_add_executor_job needed"

key-files:
  created: []
  modified:
    - custom_components/franklin_wh/coordinator.py
    - custom_components/franklin_wh/config_flow.py
    - custom_components/franklin_wh/manifest.json

key-decisions:
  - "Pass HA httpx session into both TokenFetcher and Client at construction (not stored globally)"
  - "Removed async_add_executor_job wrapping since session-injected client construction is non-blocking"
  - "franklinwh removed from manifest.json requirements as it is now fully vendored"

patterns-established:
  - "get_async_client pattern: obtain once per coordinator/validate_input call, pass to constructors"

requirements-completed: [VEND-03, HAINT-01, HAINT-02, HAINT-03, HAINT-04]

duration: 8min
completed: 2026-02-27
---

# Phase 3 Plan 02: Wire HTTP Client Summary

**coordinator.py and config_flow.py updated to use HA-managed httpx client via get_async_client, removing all async_add_executor_job client construction and franklinwh PyPI dependency from manifest**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-27T00:15:00Z
- **Completed:** 2026-02-27T00:23:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- coordinator.py now imports from .franklinwh (local vendored package) and injects HA httpx session into TokenFetcher and Client
- config_flow.py now imports from .franklinwh and injects HA httpx session in validate_input, removing executor job wrapping
- manifest.json requirements array cleared — franklinwh is no longer a PyPI dependency

## Task Commits

1. **Task 1: Update coordinator.py** - `912302a` (feat)
2. **Task 2: Update config_flow.py and manifest.json** - `a343457` (feat)

## Files Created/Modified

- `custom_components/franklin_wh/coordinator.py` - Updated imports to .franklinwh, added get_async_client, injected session into constructors, removed executor wrapping
- `custom_components/franklin_wh/config_flow.py` - Updated imports to .franklinwh alias, added get_async_client, injected session, removed executor wrapping in validate_input
- `custom_components/franklin_wh/manifest.json` - Removed franklinwh>=1.0.0 from requirements array

## Decisions Made

- Used `from . import franklinwh as franklinwh_lib` alias in config_flow.py to avoid shadowing the module name while keeping access to TokenFetcher and Client
- Stored http session as `self._http_session` in coordinator for use during lazy client initialization

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 is fully complete — franklinwh vendored and wired to HA httpx client
- Integration no longer has blocking SSL calls on startup
- v1.1 milestone requirements VEND-03, HAINT-01 through HAINT-04 are satisfied

---
*Phase: 03-vendor-and-wire-http-client*
*Completed: 2026-02-27*
