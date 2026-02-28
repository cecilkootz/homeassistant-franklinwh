---
phase: 03-vendor-and-wire-http-client
plan: "01"
subsystem: api
tags: [httpx, franklinwh, vendoring, ssl, async]

requires: []
provides:
  - "custom_components/franklin_wh/franklinwh/ vendored package with modified client"
  - "Client and TokenFetcher accept optional injected httpx.AsyncClient session"
  - "No SSL context created at construction time when session is injected"
affects:
  - 03-02-wire-http-client

tech-stack:
  added: []
  patterns:
    - "Vendor upstream PyPI package into custom_components for targeted modification"
    - "Optional session injection pattern: use injected if provided, else create per-request"

key-files:
  created:
    - custom_components/franklin_wh/franklinwh/__init__.py
    - custom_components/franklin_wh/franklinwh/api.py
    - custom_components/franklin_wh/franklinwh/caching_thread.py
    - custom_components/franklin_wh/franklinwh/client.py
  modified: []

key-decisions:
  - "Vendor franklinwh PyPI library verbatim except for targeted session-injection modifications to avoid forking"
  - "TokenFetcher.fetch_token uses injected session directly (not as context manager) since HA manages the client lifecycle"
  - "Client falls back to get_client() when no session injected, preserving upstream behavior"

patterns-established:
  - "Session injection: def __init__(self, ..., session: httpx.AsyncClient | None = None)"
  - "Long-lived session usage: call session.post() directly rather than async with"

requirements-completed:
  - VEND-01
  - VEND-02

duration: 10min
completed: 2026-02-27
---

# Phase 3 Plan 01: Vendor and Wire HTTP Client Summary

**Vendored franklinwh PyPI library into custom_components with session-injection support in Client and TokenFetcher to eliminate synchronous SSL context creation**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-27T00:00:00Z
- **Completed:** 2026-02-27T00:10:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created franklinwh/ vendored package under custom_components/franklin_wh/ with all four source files
- Modified Client.__init__ to accept optional httpx.AsyncClient session — uses injected session or creates one via get_client()
- Modified TokenFetcher.__init__ and fetch_token to accept and use an injected session (called directly, not as context manager)
- All upstream types (Mode, Stats, SwitchState, GridStatus, etc.) remain importable from vendored package

## Task Commits

Each task was committed atomically:

1. **Task 1: Copy upstream library files verbatim** - `c3c15b8` (chore)
2. **Task 2: Vendor and modify client.py to accept injected httpx.AsyncClient** - `18a7f0c` (feat)

## Files Created/Modified
- `custom_components/franklin_wh/franklinwh/__init__.py` - Package re-exports: Client, TokenFetcher, Mode, Stats, etc.
- `custom_components/franklin_wh/franklinwh/api.py` - DEFAULT_URL_BASE constant
- `custom_components/franklin_wh/franklinwh/caching_thread.py` - CachingThread (verbatim copy)
- `custom_components/franklin_wh/franklinwh/client.py` - Client, TokenFetcher, and all types with injected-session support

## Decisions Made
- Vendored verbatim to avoid forking; only targeted modifications made to Client and TokenFetcher
- TokenFetcher's injected session is called directly (not as async context manager) because HA manages the client lifecycle — closing it would be wrong
- Fell back to creating httpx client per-request when no session injected (preserves upstream behavior exactly)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Vendored package ready for plan 03-02 to wire the HA-managed httpx.AsyncClient into Client and TokenFetcher at integration startup

---
*Phase: 03-vendor-and-wire-http-client*
*Completed: 2026-02-27*
