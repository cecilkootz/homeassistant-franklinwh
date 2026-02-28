# Project Research Summary

**Project:** homeassistant-franklinwh HACS Structure Migration
**Domain:** HACS Custom Integration Repository Structure
**Researched:** 2026-02-27
**Confidence:** HIGH

## Executive Summary

This project is a structural migration of an existing, functionally complete Home Assistant custom integration from a non-standard `content_in_root: true` HACS layout to the standard `custom_components/{domain}/` layout. The integration itself — sensors, switches, config flow, coordinator, services — requires zero functional changes. The entire scope is moving files from the repository root into `custom_components/franklin_wh/` and updating `hacs.json` to remove the `content_in_root` workaround field.

The recommended approach is a single atomic `git mv` operation for all files, with the `hacs.json` update included in the same commit. All existing Python files already use relative imports (`from .const`, `from .coordinator`) which remain valid without modification after the move. The two CI workflows already in place (`hacs/action` and `hassfest`) will validate the new structure without requiring changes to the workflow files themselves.

The primary risk is an incomplete migration leaving HACS in a broken intermediate state. This is avoided entirely by committing all changes atomically. Secondary risks are forgetting non-Python files (`translations/`, `strings.json`, `services.yaml`) which fail silently at runtime — the "looks done but isn't" problem. A post-migration checklist covering CI pass, config flow UI, and Developer Tools service selectors eliminates this risk.

## Key Findings

### Recommended Stack

The integration targets Python 3.11+ and Home Assistant 2024.1.0+, matching the existing codebase. No new dependencies are introduced by this migration. HACS itself is the distribution mechanism, and after migration its standard discovery mechanism replaces the current workaround.

**Core technologies:**
- Python 3.11+: Integration runtime — already in use, no change
- Home Assistant 2024.1.0+: Integration framework target — enforced via `hacs.json` `homeassistant` field (optional addition)
- HACS (latest): Distribution — standard `custom_components/` layout replaces `content_in_root` workaround

**Required structure changes:**
- `hacs.json` at repo root: remove `content_in_root`, keep `name` (and optionally add `homeassistant`, `render_readme`)
- All integration files move to `custom_components/franklin_wh/` — the directory name must match `manifest.json` `"domain": "franklin_wh"` exactly (underscore, not hyphen)

### Expected Features

This migration has no user-visible feature changes. Its purpose is HACS compliance, which enables standard installation flow for end users.

**Must have (table stakes — required for HACS compliance):**
- `custom_components/franklin_wh/` directory containing all integration files
- `manifest.json` inside the package directory (not repo root)
- `strings.json` inside the package directory (CI will fail without it)
- `translations/en.json` inside the package subdirectory (silent failure if missing)
- `services.yaml` inside the package directory (services lose UI metadata if missing)
- `hacs.json` at repo root with `content_in_root` removed
- All changes in a single atomic commit

**Should have (quality wins, low cost):**
- Use `git mv` for all file moves (preserves git history)
- CI green (both `hassfest` and `hacs/action` workflows)

**Defer (v2+):**
- Add tests (pytest-homeassistant-custom-component)
- Upgrade CI action versions (`actions/checkout@v3` → `@v4`)
- Add `homeassistant` minimum version field to `hacs.json`
- Update README installation instructions

### Architecture Approach

The migration is purely structural. At runtime, HACS already installs files into `custom_components/franklin_wh/` when using `content_in_root: true` — so the HA runtime behavior is identical before and after. The only change is where files live in the source repository. After migration, HACS reads from `custom_components/franklin_wh/` directly rather than copying from root.

**Major components (all moving as a unit, no content changes):**
1. `custom_components/franklin_wh/` — Python package root, contains all integration files
2. `manifest.json` — Domain declaration; must be inside the package directory
3. `translations/` — Subdirectory inside the package; HA resolves translations relative to the package path
4. `services.yaml` + `strings.json` — Support files inside the package; CI and HA require them there
5. `hacs.json` — Repository root only; updated to remove `content_in_root`

### Critical Pitfalls

1. **Non-atomic commit** — Removing `content_in_root` in a separate commit from file moves creates a broken state for any user who updates HACS between commits. Prevention: single commit for all changes.

2. **Forgetting `translations/`, `strings.json`, or `services.yaml`** — These non-Python files are easy to overlook. Translations fail silently (raw keys in UI); `strings.json` failure is caught by `hassfest` CI; `services.yaml` failure causes services to lose Developer Tools UI metadata. Prevention: explicit checklist, verify CI + UI post-migration.

3. **Directory named with hyphen instead of underscore** — `manifest.json` declares `"domain": "franklin_wh"` (underscore). The directory must be `custom_components/franklin_wh/`, not `franklin-wh`. Mismatch causes HA to fail loading entirely. Prevention: double-check the `mkdir` / `git mv` command.

4. **Using `cp` instead of `git mv`** — Loses all git file history, making future bisection harder. Irreversible. Prevention: use `git mv` exclusively.

5. **Existing HACS users with cached installs** — Users who installed when `content_in_root: true` may need to remove and reinstall via HACS after migration. Prevention: document in release notes.

## Implications for Roadmap

This project maps cleanly to a two-phase roadmap given its well-defined scope and zero functional ambiguity.

### Phase 1: File Relocation and hacs.json Update

**Rationale:** This is the entire migration. All changes are structural, have no dependencies on external systems or API research, and are fully understood from codebase inspection. Can be executed and verified in a single work session.

**Delivers:** HACS-compliant repository structure; `hacs/action` and `hassfest` CI passing; standard HACS installation flow for users.

**Addresses:** All table-stakes features from FEATURES.md (file moves, `hacs.json` update, atomic commit).

**Avoids:**
- Non-atomic commit (do all in one)
- Missing non-Python files (use explicit checklist)
- Directory naming error (verify underscore)
- History loss (use `git mv`)

**Acceptance criteria:**
- `custom_components/franklin_wh/` contains all 7 Python files, `manifest.json`, `strings.json`, `services.yaml`, `translations/en.json`
- Repository root contains only `README.md`, `hacs.json`, `LICENSE`, `.github/`
- `hacs.json` has no `content_in_root` key
- All changes in one commit using `git mv`
- `hassfest` CI passes
- `hacs/action` CI passes

### Phase 2: Post-Migration Verification and User Communication

**Rationale:** Structural correctness (CI green) does not guarantee runtime correctness. A dedicated verification step using an actual HA instance catches silent failures (translations, service metadata) that CI misses.

**Delivers:** Confirmed working integration in a real HA instance; updated README installation instructions; release notes for existing HACS users.

**Addresses:** Should-have features from FEATURES.md (README update, user communication).

**Avoids:** "Looks done but isn't" failures (services missing UI, translations showing raw keys).

**Acceptance criteria:**
- HA log shows no errors after restart
- Config flow shows human-readable field labels (not raw keys)
- Developer Tools > Services shows descriptions and field selectors for `franklin_wh.set_operation_mode` and `franklin_wh.set_battery_reserve`
- README updated with standard HACS install path
- Release notes mention reinstall requirement for existing users

### Phase Ordering Rationale

- Phase 1 before Phase 2: Cannot verify what hasn't been built. The file moves must land before any runtime verification is meaningful.
- No Phase 3 for tests/CI modernization: This is out of scope for the migration. Tracking as future work avoids scope creep that could delay a simple structural change.

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1:** HACS integration structure is fully documented in local reference integrations; no unknowns remain. Standard `git mv` workflow. No additional research needed.
- **Phase 2:** HA runtime verification is a standard dev workflow. No research needed.

No phases require `/gsd:research-phase` — all patterns are well-established and verified against local production integrations.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against two local production HACS integrations (`sunspec`, `span`) and existing workflow files |
| Features | HIGH | All files inventoried directly from codebase; all imports confirmed relative via grep; hacs.json confirmed |
| Architecture | HIGH | HACS loading mechanism well-established; relative import semantics are Python spec; only HA discovery mechanism is MEDIUM (training data) |
| Pitfalls | HIGH | Derived from direct codebase inspection; all pitfalls are concrete and verifiable, not speculative |

**Overall confidence:** HIGH

### Gaps to Address

- **HACS `content_in_root` removal behavior:** Documented as a "workaround/legacy feature" but web verification of current HACS behavior was unavailable. The local evidence (two working integrations without `content_in_root`) is conclusive — this is standard behavior. No action needed, but worth confirming CI green on a branch before merging to main.
- **Existing user cache behavior:** How HACS handles the transition for users who installed with `content_in_root: true` was not verified. Conservative approach: document reinstall in release notes.

## Sources

### Primary (HIGH confidence)
- `/Users/matt/Development/sunspec/franklin-wh-sunspec/` — Minimal clean HACS integration, standard structure, no `content_in_root`, confirmed working
- `/Users/matt/Development/span/` — Production HACS integration with `content_in_root: false`, standard `custom_components/span_panel/` structure
- `/Users/matt/Development/homeassistant-franklinwh/` — Full codebase inspection: all Python imports, hacs.json, manifest.json, services.yaml, strings.json, translations/, workflow files

### Secondary (MEDIUM confidence)
- Training data on HACS `content_in_root` behavior and HA `custom_components/` discovery mechanism — corroborated by local evidence

---
*Research completed: 2026-02-27*
*Ready for roadmap: yes*
