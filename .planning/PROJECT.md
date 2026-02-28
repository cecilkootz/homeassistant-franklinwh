# homeassistant-franklinwh

## What This Is

A Home Assistant custom integration for FranklinWH energy management systems, installable via HACS using the standard `custom_components/franklin_wh/` directory structure. The integration polls the FranklinWH cloud API and exposes sensors (battery SoC, energy flow, grid status) and switches (operation mode, battery reserve) to Home Assistant.

## Core Value

FranklinWH energy management data and controls available in Home Assistant via a first-class HACS integration — no workarounds or custom install paths required.

## Requirements

### Validated

- ✓ FranklinWH cloud API integration (polling, coordinator, sensors, switches) — existing
- ✓ Config flow for user onboarding and reauth — existing
- ✓ Services (set_operation_mode, set_battery_reserve) — existing
- ✓ Diagnostics support — existing
- ✓ Translations (en.json) — existing
- ✓ manifest.json with all required HACS fields — existing
- ✓ Integration files relocated to `custom_components/franklin_wh/` — v1.0
- ✓ `hacs.json` updated to remove `content_in_root` workaround — v1.0
- ✓ `translations/` directory moved inside `custom_components/franklin_wh/` — v1.0
- ✓ `services.yaml` and `strings.json` moved inside `custom_components/franklin_wh/` — v1.0
- ✓ Repository root contains only: `README.md`, `hacs.json`, `LICENSE`, `.github/` — v1.0
- ✓ HACS validation passing (8/8 checks) — v1.0
- ✓ Hassfest validation passing — v1.0
- ✓ franklinwh library vendored into `custom_components/franklin_wh/franklinwh/` — v1.1
- ✓ `Client` and `TokenFetcher` accept injected `httpx.AsyncClient` — v1.1
- ✓ `coordinator.py` and `config_flow.py` use `get_async_client(hass)` — v1.1
- ✓ `manifest.json` has no `franklinwh` PyPI dependency — v1.1
- ✓ No `load_verify_locations` blocking call on HA startup — v1.1

### Active

(No active requirements — planning next milestone)

### Out of Scope

- Adding new integration features — separate from structural work
- Adding tests — separate concern
- Fixing config_flow.py executor/coroutine bug — deferred
- Mobile app / video chat — not applicable

## Context

**Shipped v1.1** — 2026-02-28
- 2,125 LOC Python in `custom_components/franklin_wh/` (incl. 894 vendored franklinwh/)
- Tech stack: Python, Home Assistant integration framework, HACS, httpx (HA-managed)
- franklinwh library vendored and modified for session injection (non-blocking startup)
- CI: HACS validate.yaml + hassfest both passing on main

**Shipped v1.0** — 2026-02-28
- 11 integration files relocated via `git mv` (rename history preserved)
- HACS validate.yaml + hassfest both passing (8/8 checks)

**Known tech debt:**
- Debug-mode: `event_hooks` appended to shared HA httpx client when `debug=True` (edge case)
- BUG-01: `config_flow.py` wraps async `client.get_stats()` in `async_add_executor_job` (pre-existing, deferred)
- No unit or integration tests (TEST-01, TEST-02 deferred)

## Constraints

- **Compatibility**: Must continue to work as a Home Assistant custom integration
- **HACS**: Must pass HACS validation (directory structure at `custom_components/franklin_wh/`)
- **Functional parity**: Vendored library must be functionally identical to upstream except for session injection

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Move files via `git mv` rather than copy | Keeps git history clean, GitHub shows renames | ✓ Good — rename history visible in `git log --follow` |
| Update hacs.json in same commit as file moves | Atomic change prevents broken intermediate state | ✓ Good — single commit 5f5e8cc |
| Use Python to edit hacs.json | Avoids manual JSON formatting errors | ✓ Good |
| Fix manifest.json key ordering in Phase 2 | hassfest requires: domain, name, then alphabetical | ✓ Good — committed 0958b7f |
| Enable disabled_fork validate.yaml via API | GitHub disables upstream workflows on forks by default | ✓ Good — workflow now triggers on push |
| Vendor franklinwh into custom_components rather than fork upstream repo | Minimizes maintenance burden; targeted modification stays local | ✓ Good — no upstream PR needed, changes are HA-specific |
| TokenFetcher injected session called directly (not as context manager) | HA manages the client lifecycle; closing it would break other integrations | ✓ Good — session lifecycle stays with HA |
| Client falls back to `get_client()` when no session injected | Preserves upstream test compatibility and non-HA usage | ✓ Good — library still usable outside HA |
| Pass HA httpx session at construction (not stored globally) | Avoids shared mutable state; each coordinator owns its session reference | ✓ Good — clean dependency injection |

---
*Last updated: 2026-02-28 after v1.1 milestone*
