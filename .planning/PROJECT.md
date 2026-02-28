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

### Active

(None — all v1.0 requirements validated. See /gsd:new-milestone for v1.1 requirements.)

### Out of Scope

- Adding new integration features — separate from structural work
- Changing any functional behavior of the integration
- Adding tests — separate concern, not blocking HACS compliance
- Mobile app / video chat — not applicable

## Context

**Shipped v1.0** — 2026-02-28
- 1,232 LOC Python in `custom_components/franklin_wh/`
- Tech stack: Python, Home Assistant integration framework, HACS
- 11 integration files relocated via `git mv` (rename history preserved)
- CI: HACS validate.yaml + hassfest both passing on main

**Known tech debt from v1.0:**
- VERIFICATION.md artifacts not created for either phase (phases completed without running verify-work)
- REQUIREMENTS.md VERIF-01/VERIF-02 checkboxes were not updated in real-time (resolved at milestone audit)

## Constraints

- **Compatibility**: Must continue to work as a Home Assistant custom integration
- **HACS**: Must pass HACS validation (directory structure at `custom_components/franklin_wh/`)
- **No feature changes**: Structural migration only — zero functional changes in v1.0

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Move files via `git mv` rather than copy | Keeps git history clean, GitHub shows renames | ✓ Good — rename history visible in `git log --follow` |
| Update hacs.json in same commit as file moves | Atomic change prevents broken intermediate state | ✓ Good — single commit 5f5e8cc |
| Use Python to edit hacs.json | Avoids manual JSON formatting errors | ✓ Good |
| Fix manifest.json key ordering in Phase 2 | hassfest requires: domain, name, then alphabetical | ✓ Good — committed 0958b7f |
| Enable disabled_fork validate.yaml via API | GitHub disables upstream workflows on forks by default | ✓ Good — workflow now triggers on push |

---
*Last updated: 2026-02-28 after v1.0 milestone*
