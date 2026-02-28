# Feature Research

**Domain:** HACS custom integration repository structure migration (content_in_root → custom_components/)
**Researched:** 2026-02-27
**Confidence:** HIGH — based on direct codebase inspection and established HACS/HA integration conventions

---

## Feature Landscape

### Table Stakes (Required for HACS Compliance)

These changes are mandatory. Without them, HACS validation fails or the integration does not load correctly in Home Assistant.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Create `custom_components/franklin_wh/` directory | HACS requires integration files at this path; HA itself expects `custom_components/{domain}/` | LOW | Directory must match the `domain` field in `manifest.json` exactly: `franklin_wh` |
| Move `__init__.py` → `custom_components/franklin_wh/__init__.py` | HA loads the integration package from this path | LOW | No content changes needed; relative imports (`from .const`, `from .coordinator`) remain valid |
| Move `config_flow.py` → `custom_components/franklin_wh/config_flow.py` | Required by `manifest.json` (`"config_flow": true`) | LOW | No content changes needed |
| Move `const.py` → `custom_components/franklin_wh/const.py` | Imported by every other module via relative import | LOW | No content changes needed |
| Move `coordinator.py` → `custom_components/franklin_wh/coordinator.py` | Imported by `__init__.py`, `sensor.py`, `switch.py`, `diagnostics.py` | LOW | No content changes needed |
| Move `diagnostics.py` → `custom_components/franklin_wh/diagnostics.py` | Required for diagnostics support declared in manifest | LOW | No content changes needed |
| Move `sensor.py` → `custom_components/franklin_wh/sensor.py` | Platform file for `Platform.SENSOR` | LOW | No content changes needed |
| Move `switch.py` → `custom_components/franklin_wh/switch.py` | Platform file for `Platform.SWITCH` | LOW | No content changes needed |
| Move `manifest.json` → `custom_components/franklin_wh/manifest.json` | HA reads this from inside the integration package directory | LOW | No content changes needed |
| Move `strings.json` → `custom_components/franklin_wh/strings.json` | HA reads config flow strings from inside the integration package | LOW | No content changes needed |
| Move `services.yaml` → `custom_components/franklin_wh/services.yaml` | HA reads service definitions from inside the integration package | LOW | No content changes needed |
| Move `translations/en.json` → `custom_components/franklin_wh/translations/en.json` | HA resolves translations relative to the integration package directory | LOW | The `translations/` subdirectory must be recreated inside `custom_components/franklin_wh/` |
| Remove `"content_in_root": true` from `hacs.json` | This field is a non-standard workaround; removing it switches to standard structure; HACS validation expects its absence for compliant integrations | LOW | After removal, `hacs.json` should only contain `"name"` (and optionally `"zip_release"`) |

### Internal Import Paths — No Changes Required

All existing Python files use relative imports (e.g., `from .const import ...`, `from .coordinator import ...`). Because all files move together into the same package directory, these relative imports remain correct as-is. No import path changes are needed in any `.py` file.

This was confirmed by inspecting all imports across the six Python modules:
- `__init__.py`: `from .const import ...`, `from .coordinator import ...`
- `config_flow.py`: `from .const import ...`
- `coordinator.py`: `from .const import ...`
- `diagnostics.py`: `from .const import ...`, `from .coordinator import ...`
- `sensor.py`: `from .const import ...`, `from .coordinator import ...`
- `switch.py`: `from .const import ...`, `from .coordinator import ...`

All are relative-only. None reference an absolute package path like `custom_components.franklin_wh`.

### Repository Root After Migration

The root must contain only infrastructure files. HACS expects integration content to live exclusively under `custom_components/`:

| File | Keep at Root? | Notes |
|------|--------------|-------|
| `README.md` | YES | Documentation, stays at root |
| `hacs.json` | YES | HACS metadata, stays at root (updated) |
| `LICENSE` | YES | License, stays at root |
| `.github/` | YES | CI workflows, stays at root |
| `.gitignore` | YES | Git config, stays at root |
| All `.py` files | NO — move | Into `custom_components/franklin_wh/` |
| `manifest.json` | NO — move | Into `custom_components/franklin_wh/` |
| `strings.json` | NO — move | Into `custom_components/franklin_wh/` |
| `services.yaml` | NO — move | Into `custom_components/franklin_wh/` |
| `translations/` | NO — move | Into `custom_components/franklin_wh/translations/` |

### hacs.json Change (Exact Diff)

**Before:**
```json
{
  "name": "FranklinWH",
  "content_in_root": true,
  "zip_release": false
}
```

**After:**
```json
{
  "name": "FranklinWH",
  "zip_release": false
}
```

Only the `"content_in_root": true` line is removed. `"zip_release": false` is kept (it is valid and harmless). Confidence: HIGH — `content_in_root` is the workaround field; removing it is the entire point of this migration.

### Differentiators (Nice to Have During This Migration)

These are not required for HACS compliance but would improve the integration during this migration window.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Atomic git move (`git mv`) for all files | Preserves git file history across the rename; `git log --follow` works after migration | LOW | Use `git mv` instead of `cp` + `rm`; HA does not care but developer experience is better |
| Single atomic commit for all changes | Prevents a broken intermediate state where files have moved but `hacs.json` still declares `content_in_root: true` (or vice versa) | LOW | All file moves + `hacs.json` update in one commit |
| Verify CI passes after migration | The existing `hassfest.yaml` and `validate.yaml` workflows validate both HA compatibility and HACS compliance; a green CI run confirms correctness | LOW | No workflow changes needed; they will automatically validate the new structure |

### Anti-Features (Things to Deliberately NOT Change)

These are in scope creep territory. The migration is structural only.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Add or change any functional Python code | Scope creep; increases risk of introducing bugs during a structural migration | Keep all `.py` file contents byte-for-byte identical; only their filesystem location changes |
| Change `manifest.json` content (version, dependencies, etc.) | Out of scope; version bumps and dependency updates are separate concerns | Move the file unchanged |
| Add tests | Valuable but a separate concern; not required for HACS compliance | Track as a future milestone; do not block this migration on it |
| Update CI workflow versions (`actions/checkout@v3` is outdated) | Out of scope; workflow modernization is a separate concern | Leave `hassfest.yaml` and `validate.yaml` content unchanged |
| Add `"homeassistant"` minimum version to `hacs.json` | Optional HACS field; adding it now is unnecessary churn | Only add if a minimum HA version constraint is actually needed |
| Rename the domain (`franklin_wh`) | Renaming a domain is a breaking change for all existing users (config entries become orphaned) | Keep domain as `franklin_wh` throughout |
| Change the `README.md` installation instructions | Installation docs may need updating but are not blocking HACS compliance | Update README in a follow-up commit after the structure migration |

---

## Feature Dependencies

```
[Create custom_components/franklin_wh/ directory]
    └──required before──> [All file moves]
                              └──required before──> [Remove content_in_root from hacs.json]

[All file moves complete] ──enables──> [CI validation passes]
```

### Dependency Notes

- **Directory creation required first:** All file moves depend on the destination directory existing.
- **hacs.json update must be atomic with file moves:** If `content_in_root: true` is removed before files are moved, HACS validation will fail because it will look in `custom_components/` and find nothing. If files are moved before removing `content_in_root: true`, the integration may load from both locations ambiguously. Do both in one commit.
- **Relative imports have no dependency on move order:** Since all imports are relative, no Python file depends on another being moved first — they all move as a unit.

---

## MVP Definition

### Launch With (v1 — this migration)

The migration is complete when all of these are done:

- [ ] `custom_components/franklin_wh/` directory exists
- [ ] All 6 Python files moved into it (`__init__.py`, `config_flow.py`, `const.py`, `coordinator.py`, `diagnostics.py`, `sensor.py`, `switch.py`)
- [ ] `manifest.json` moved into it
- [ ] `strings.json` moved into it
- [ ] `services.yaml` moved into it
- [ ] `translations/en.json` moved into `custom_components/franklin_wh/translations/en.json`
- [ ] `hacs.json` at repo root updated to remove `"content_in_root": true`
- [ ] All changes in a single atomic commit
- [ ] CI passes (hassfest + HACS validation)

### Add After Validation (v1.x)

- [ ] Update README installation instructions to reflect standard HACS install path
- [ ] Consider upgrading `actions/checkout@v3` → `@v4` in CI workflows

### Future Consideration (v2+)

- [ ] Add tests (pytest-homeassistant-custom-component)
- [ ] Modernize GitHub Actions workflow versions
- [ ] Add `"homeassistant"` minimum version constraint if needed

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Move all integration files to `custom_components/franklin_wh/` | HIGH — HACS compliance unblocked | LOW | P1 |
| Remove `content_in_root` from `hacs.json` | HIGH — eliminates non-standard workaround | LOW | P1 |
| Single atomic commit | MEDIUM — prevents broken intermediate state | LOW | P1 |
| Use `git mv` for history preservation | LOW — developer quality-of-life | LOW | P1 (free win) |
| Update README install instructions | MEDIUM — user-facing correctness | LOW | P2 |
| Add tests | HIGH long-term — prevents regressions | HIGH | P3 (separate milestone) |

---

## Sources

- Direct inspection of `/Users/matt/Development/homeassistant-franklinwh/` — all files inventoried (HIGH confidence)
- `hacs.json` content confirmed via `cat` (HIGH confidence)
- `manifest.json` content confirmed — domain is `franklin_wh` (HIGH confidence)
- All Python import statements confirmed via `grep` across all `.py` files — all relative (HIGH confidence)
- GitHub Actions workflow files inspected — no path-specific configuration that requires updating (HIGH confidence)
- HACS integration structure conventions: `custom_components/{domain}/` as standard, `content_in_root` as workaround (HIGH confidence — this is the defining constraint of the whole migration and is explicitly documented in `PROJECT.md`)

---
*Feature research for: HACS custom integration repository structure migration*
*Researched: 2026-02-27*
