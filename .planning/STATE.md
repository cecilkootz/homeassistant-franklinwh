---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: SunSpec/Modbus Local API
status: in_progress
last_updated: "2026-02-27T00:00:00.000Z"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27 after v1.2 milestone start)

**Core value:** FranklinWH energy management data and controls in Home Assistant via first-class HACS integration
**Current focus:** Phase 4 — Modbus Client Layer

## Current Position

Phase: 4 — Modbus Client Layer
Plan: —
Status: Not started
Last activity: 2026-02-27 — v1.2 roadmap created (Phases 4-6)

Progress: [░░░░░░░░░░] 0% (v1.2 in progress)

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 9 min
- Total execution time: 18 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 03-vendor-and-wire-http-client | 2/2 | 18 min | 9 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Prior milestone decisions preserved for context:

- [v1.0 Setup]: Move files via `git mv` to preserve git history
- [v1.0 01-01]: Used Python to edit hacs.json to avoid manual JSON formatting errors
- [v1.0 02-01]: manifest.json keys must be alphabetically sorted after domain/name (hassfest requirement)
- [v1.0 02-01]: validate.yaml was disabled_fork on GitHub — enabled via API
- [v1.1 03-01]: Vendor franklinwh PyPI library verbatim into custom_components to allow targeted modifications without forking
- [v1.1 03-01]: TokenFetcher injected session called directly (not as context manager) since HA manages the client lifecycle
- [v1.1 03-01]: Client falls back to get_client() when no session injected, preserving upstream behavior
- [Phase 03-02]: Pass HA httpx session into both TokenFetcher and Client at construction (not stored globally)
- [Phase 03-02]: franklinwh removed from manifest.json requirements as it is now fully vendored

### v1.2 Implementation Notes

- pySunSpec2 (`sunspec2` PyPI package) is synchronous blocking I/O — must run in executor, never on the HA event loop
- `use_local_api` and `local_host` stub fields already exist in const.py; `CONF_LOCAL_PORT` and `CONF_LOCAL_SLAVE_ID` need to be added
- Config flow already imports `CONF_USE_LOCAL_API`, `CONF_LOCAL_HOST` from const.py but does not use them yet
- The Modbus client layer (SunSpec device connect/scan/read) is net-new code
- The coordinator needs a hybrid update path: Modbus for reads, cloud for writes and fallback
- Sensor `value_fn` lambdas may need updating if data model shape changes with Modbus data merged in
- Options flow for toggling local mode is not yet implemented

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-27
Stopped at: v1.2 roadmap created — ready to begin Phase 4 planning
Resume file: None
