# homeassistant-franklinwh

## What This Is

A Home Assistant custom integration for FranklinWH energy management systems, installable via HACS using the standard `custom_components/franklin_wh/` directory structure. The integration supports two data paths: cloud API polling (always required for writes) and optional local SunSpec Modbus TCP polling for faster real-time sensor data. Exposes sensors (battery SoC, battery DC power, solar production, grid AC power, home load, energy totals) and switches (operation mode, battery reserve) to Home Assistant.

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
- ✓ User can configure Modbus TCP host, port (default 502), and slave ID (default 1) during setup — v1.2
- ✓ User can enable/disable local Modbus via options flow without HA restart — v1.2
- ✓ Integration reads battery SoC, DC power, solar power, grid AC power from SunSpec at 10s interval — v1.2
- ✓ Write operations (set_operation_mode, set_battery_reserve, switches) always use cloud — v1.2
- ✓ Sensors without Modbus equivalent (energy totals) use cloud data in hybrid mode — v1.2
- ✓ Modbus failures degrade gracefully without marking integration unavailable — v1.2
- ✓ Integration loads successfully when Modbus unreachable at startup — v1.2

### Active

(No active requirements — planning next milestone)

### Out of Scope

- Adding unit/integration tests — separate milestone concern (TEST-01, TEST-02 deferred)
- Fixing config_flow.py executor/coroutine bug (BUG-01) — pre-existing, deferred
- Modbus write support (set_operation_mode via Modbus) — no confirmed register mapping for FranklinWH
- Making `scan_interval` user-configurable via options flow — options UI field exists but coordinator ignores it; v1.3 concern

## Context

**Shipped v1.2** — 2026-03-01
- 1,589 LOC Python in `custom_components/franklin_wh/` (5 phases, 7 plans, 36 commits)
- New file: `sunspec_client.py` (167 LOC) — SunSpec Modbus TCP client, executor-safe
- Hybrid coordinator: Modbus for power flow (10s), cloud for energy totals (60s) and writes
- All 11 v1.2 requirements satisfied; 2 gap-closure phases (7, 8) added post-audit
- Hardware validation still needed: Model 502 presence, Model 714 DCW fallback path

**Shipped v1.1** — 2026-02-28
- 2,125 LOC Python in `custom_components/franklin_wh/` (incl. 894 vendored franklinwh/)
- franklinwh library vendored and modified for session injection (non-blocking startup)
- CI: HACS validate.yaml + hassfest both passing on main

**Shipped v1.0** — 2026-02-28
- 11 integration files relocated via `git mv` (rename history preserved)
- HACS validate.yaml + hassfest both passing (8/8 checks)

**Known tech debt:**
- Debug-mode: `event_hooks` appended to shared HA httpx client when `debug=True` (edge case)
- BUG-01: `config_flow.py` wraps async `client.get_stats()` in `async_add_executor_job` (pre-existing, deferred)
- No unit or integration tests (TEST-01, TEST-02 deferred)
- `scan_interval` options field in UI is wired but ignored by coordinator — silently discarded after options save
- Model 502 (solar) on FranklinWH hardware: unconfirmed presence; `RuntimeError` if absent

## Constraints

- **Compatibility**: Must continue to work as a Home Assistant custom integration
- **HACS**: Must pass HACS validation (directory structure at `custom_components/franklin_wh/`)
- **Functional parity**: Vendored library must be functionally identical to upstream except for session injection
- **Blocking I/O**: pySunSpec2 Modbus client is synchronous — must run in executor, never on HA event loop

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
| Use PyPI name `pysunspec2` (not `sunspec2`) in manifest.json | `sunspec2` is the import name; `pysunspec2` is the PyPI distribution name — HA pip installs from PyPI | ✓ Good — install works correctly |
| All Modbus I/O in `_read_blocking()`, dispatched via `async_add_executor_job` | pySunSpec2 is synchronous blocking — cannot run on HA event loop | ✓ Good — no event loop blocking |
| Hybrid data strategy: Modbus for Stats.current, cloud for Stats.totals | Modbus has no energy accumulator; cloud kWh data fills the gap cleanly | ✓ Good — both data paths complement each other |
| `_fetch_cloud_stats_fallback()` returns None on failure (no exception propagation) | Allows hybrid path to continue with last-known totals without failing the update cycle | ✓ Good — resilient to cloud blips |
| Read Modbus settings with options-then-data fallback in `__init__.py` | `entry.options` is empty on first setup; data fallback ensures Modbus activates correctly on first boot | ✓ Good — Phase 7 fix closed first-setup bug |
| `add_update_listener(async_reload_entry)` unconditional, after `async_forward_entry_setups` | Options changes must always trigger reload regardless of mode; missed in Phase 5, closed in Phase 8 | ✓ Good — options toggle now works without HA restart |
| Single negation for `grid_use` in coordinator:233 only; sensor `value_fn` sign-neutral | Two negations cause double inversion (Phase 5 bug); canonical normalization belongs in coordinator | ✓ Good — Phase 8 fix restored correct polarity |

---
*Last updated: 2026-03-01 after v1.2 milestone*
