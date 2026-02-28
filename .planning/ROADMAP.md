# Roadmap: homeassistant-franklinwh HACS Structure Migration

## Overview

The integration exists and works. This migration moves all integration files from the repository root into `custom_components/franklin_wh/` and removes the `content_in_root: true` workaround from `hacs.json`. Phase 1 executes the atomic file relocation. Phase 2 verifies runtime correctness and updates user-facing documentation.

## Phases

- [x] **Phase 1: File Relocation** - Move all integration files to `custom_components/franklin_wh/` and update `hacs.json` in one atomic commit (completed 2026-02-28)
- [ ] **Phase 2: Verification and Documentation** - Confirm CI passes, runtime behavior is correct, and README reflects standard installation

## Phase Details

### Phase 1: File Relocation
**Goal**: Repository has HACS-compliant structure with all integration files under `custom_components/franklin_wh/` and `hacs.json` updated
**Depends on**: Nothing (first phase)
**Requirements**: FILE-01, FILE-02, FILE-03, FILE-04, FILE-05, FILE-06, FILE-07, FILE-08, FILE-09, FILE-10, FILE-11, FILE-12, CONF-01, CONF-02, CONF-03
**Success Criteria** (what must be TRUE):
  1. `custom_components/franklin_wh/` contains all 7 Python files, `manifest.json`, `strings.json`, `services.yaml`, and `translations/en.json`
  2. Repository root contains only `README.md`, `hacs.json`, `LICENSE`, and `.github/` — no loose Python or JSON integration files
  3. `hacs.json` has no `content_in_root` key and no `zip_release` key
  4. All file moves were made via `git mv` (file history preserved) and land in a single atomic commit
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md — Move 11 integration files via git mv, update hacs.json, create atomic commit

### Phase 2: Verification and Documentation
**Goal**: Migration is confirmed correct at runtime and existing users have clear guidance
**Depends on**: Phase 1
**Requirements**: VERIF-01, VERIF-02, VERIF-03
**Success Criteria** (what must be TRUE):
  1. GitHub Actions `hacs/action` workflow passes on the migrated branch
  2. GitHub Actions `hassfest` workflow passes on the migrated branch
  3. README installation instructions reference standard HACS install (no custom path or `content_in_root` mention)
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md — Remove empty root translations/ dir, verify README, confirm CI passes for hacs/action and hassfest

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. File Relocation | 1/1 | Complete   | 2026-02-28 |
| 2. Verification and Documentation | 0/1 | Not started | - |
