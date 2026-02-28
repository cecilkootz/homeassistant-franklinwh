# Requirements: homeassistant-franklinwh HACS Structure Migration

**Defined:** 2026-02-27
**Core Value:** All integration files discoverable by HACS at `custom_components/franklin_wh/` without `content_in_root` workaround

## v1 Requirements

Requirements for the structural migration to HACS-compliant repository layout.

### File Relocation

- [ ] **FILE-01**: `custom_components/franklin_wh/` directory created in repository root
- [ ] **FILE-02**: `__init__.py` moved to `custom_components/franklin_wh/__init__.py` via `git mv`
- [ ] **FILE-03**: `config_flow.py` moved to `custom_components/franklin_wh/config_flow.py` via `git mv`
- [ ] **FILE-04**: `const.py` moved to `custom_components/franklin_wh/const.py` via `git mv`
- [ ] **FILE-05**: `coordinator.py` moved to `custom_components/franklin_wh/coordinator.py` via `git mv`
- [ ] **FILE-06**: `diagnostics.py` moved to `custom_components/franklin_wh/diagnostics.py` via `git mv`
- [ ] **FILE-07**: `sensor.py` moved to `custom_components/franklin_wh/sensor.py` via `git mv`
- [ ] **FILE-08**: `switch.py` moved to `custom_components/franklin_wh/switch.py` via `git mv`
- [ ] **FILE-09**: `manifest.json` moved to `custom_components/franklin_wh/manifest.json` via `git mv`
- [ ] **FILE-10**: `strings.json` moved to `custom_components/franklin_wh/strings.json` via `git mv`
- [ ] **FILE-11**: `services.yaml` moved to `custom_components/franklin_wh/services.yaml` via `git mv`
- [ ] **FILE-12**: `translations/en.json` moved to `custom_components/franklin_wh/translations/en.json` via `git mv`

### Configuration Update

- [ ] **CONF-01**: `hacs.json` updated to remove `"content_in_root": true` line
- [ ] **CONF-02**: `hacs.json` updated to remove `"zip_release": false` (unnecessary field)
- [ ] **CONF-03**: All file moves and `hacs.json` update land in a single atomic git commit

### Verification

- [ ] **VERIF-01**: GitHub Actions HACS validation workflow (`hacs/action`) passes on the migrated branch
- [ ] **VERIF-02**: GitHub Actions hassfest workflow (`home-assistant/actions/hassfest`) passes on the migrated branch
- [ ] **VERIF-03**: README updated to reflect standard HACS installation instructions (no custom path needed)

## v2 Requirements

### Future Improvements

- **DOCS-01**: Release notes drafted to inform existing users about the structural change and how HACS handles the update
- **CI-01**: GitHub Actions workflow pins updated from `@main`/`@master` to tagged versions (e.g., `@v3`) for stability

## Out of Scope

| Feature | Reason |
|---------|--------|
| Functional code changes | Pure structural migration — zero behavior changes |
| Adding new sensors or switches | Separate feature work, not related to HACS compliance |
| Adding tests | Not a blocker for HACS structure compliance |
| Domain renaming | Domain stays `franklin_wh` — matches existing config entries |
| CI workflow logic changes | Workflows already configured correctly, only file locations change |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FILE-01 | Phase 1 | Pending |
| FILE-02 | Phase 1 | Pending |
| FILE-03 | Phase 1 | Pending |
| FILE-04 | Phase 1 | Pending |
| FILE-05 | Phase 1 | Pending |
| FILE-06 | Phase 1 | Pending |
| FILE-07 | Phase 1 | Pending |
| FILE-08 | Phase 1 | Pending |
| FILE-09 | Phase 1 | Pending |
| FILE-10 | Phase 1 | Pending |
| FILE-11 | Phase 1 | Pending |
| FILE-12 | Phase 1 | Pending |
| CONF-01 | Phase 1 | Pending |
| CONF-02 | Phase 1 | Pending |
| CONF-03 | Phase 1 | Pending |
| VERIF-01 | Phase 2 | Pending |
| VERIF-02 | Phase 2 | Pending |
| VERIF-03 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-27*
*Last updated: 2026-02-27 after initial definition*
