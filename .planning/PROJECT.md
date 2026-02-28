# homeassistant-franklinwh HACS Repository Structure Migration

## What This Is

A Home Assistant custom integration for FranklinWH energy management systems, currently installable via HACS using the non-standard `content_in_root: true` workaround. This project migrates the repository to the standard HACS structure where integration files live under `custom_components/franklin_wh/`, eliminating the workaround and making the integration a first-class HACS citizen.

## Core Value

All integration files must be discoverable by HACS at `custom_components/franklin_wh/` so that the integration installs correctly without relying on the deprecated `content_in_root` workaround.

## Requirements

### Validated

- ✓ FranklinWH cloud API integration (polling, coordinator, sensors, switches) — existing
- ✓ Config flow for user onboarding and reauth — existing
- ✓ Services (set_operation_mode, set_battery_reserve) — existing
- ✓ Diagnostics support — existing
- ✓ Translations (en.json) — existing
- ✓ manifest.json with all required HACS fields — existing

### Active

- [ ] Integration files relocated to `custom_components/franklin_wh/`
- [ ] `hacs.json` updated to remove `content_in_root: true` workaround
- [ ] All internal imports updated to reflect new package location
- [ ] `translations/` directory moved inside `custom_components/franklin_wh/`
- [ ] `services.yaml` and `strings.json` moved inside `custom_components/franklin_wh/`
- [ ] Repository root contains only: `README.md`, `hacs.json`, `LICENSE`, `.github/`

### Out of Scope

- Adding new integration features — this is a structural migration only
- Changing any functional behavior of the integration
- Adding tests — separate concern, not blocking HACS compliance

## Context

The integration currently stores all Python files at the repository root and uses `"content_in_root": true` in `hacs.json` as a workaround. HACS requires integrations to live under `custom_components/{domain}/`. The migration involves:

1. Creating `custom_components/franklin_wh/` directory
2. Moving all `.py`, `.json`, `.yaml` integration files into it
3. Moving `translations/` into it
4. Removing `content_in_root` from `hacs.json`

No functional code changes are needed — only file relocation and import path updates.

## Constraints

- **Compatibility**: Must continue to work as a Home Assistant custom integration after migration
- **HACS**: Must pass HACS validation (`hacs.json` without `content_in_root`, proper directory structure)
- **No feature changes**: Zero functional changes — pure structural migration

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Move files rather than copy | Keeps git history clean, avoids duplication | — Pending |
| Update hacs.json in same commit as file moves | Atomic change prevents broken intermediate state | — Pending |

---
*Last updated: 2026-02-27 after initialization*
