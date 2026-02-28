# Pitfalls Research

**Domain:** HACS custom integration repository structure migration (content_in_root to custom_components/)
**Researched:** 2026-02-27
**Confidence:** HIGH (based on direct codebase inspection + well-established HACS/HA ecosystem patterns)

---

## Critical Pitfalls

### Pitfall 1: Relative Imports Break When Package Root Changes

**What goes wrong:**
All Python files in this repo use relative imports (`from .const import ...`, `from .coordinator import ...`). These relative imports work correctly because Python resolves them relative to the package root. When files are moved to `custom_components/franklin_wh/`, the package root changes — but if any import uses an absolute path like `from const import ...` or `import coordinator` (without the dot), it will fail with `ModuleNotFoundError` at HA startup.

**Why it happens:**
In the `content_in_root=true` layout, HA loads the integration from root. With `custom_components/franklin_wh/`, HA loads from the subdirectory as a proper Python package. The move does not break the existing relative imports (they are already correct — every file already uses `from .const`, `from .coordinator`, etc.), but any absolute-style imports added carelessly during or after migration will break.

**How to avoid:**
Audit every import in every file before and after the move. All cross-module imports within the integration must use relative syntax (`.module` prefix). Confirmed current state: all six Python files (`__init__.py`, `config_flow.py`, `const.py`, `coordinator.py`, `diagnostics.py`, `sensor.py`, `switch.py`) already use relative imports — no change required for imports. The risk is accidental regression during the move.

**Warning signs:**
- HA log shows `ModuleNotFoundError` or `ImportError` when loading the integration after migration
- Integration appears in the integration list but fails to initialize

**Phase to address:**
File relocation phase — verify with a grep for any non-relative cross-module imports immediately after moving files, before testing.

---

### Pitfall 2: translations/ Directory Left at Repository Root

**What goes wrong:**
Home Assistant loads translation files from `custom_components/{domain}/translations/`. If `translations/en.json` remains at the repo root (or is moved to any other location), HA silently uses built-in fallback strings — no error is logged. The config flow will render field labels as raw translation keys (e.g., `"username"` instead of `"Email Address"`).

**Why it happens:**
Developers move the Python files and update `hacs.json` but forget that `translations/` is a subdirectory, not a Python file. It's easy to overlook when constructing the `git mv` commands.

**How to avoid:**
Move `translations/` as a directory into `custom_components/franklin_wh/translations/`. The final path must be `custom_components/franklin_wh/translations/en.json`. Verify by checking the HA developer tools after migration — the config flow labels should show human-readable strings, not key names.

**Warning signs:**
- Config flow shows raw keys like `"username"`, `"password"`, `"gateway_id"` as field labels instead of human-readable text
- No error logged — this fails silently

**Phase to address:**
File relocation phase — include `translations/` in the explicit move checklist.

---

### Pitfall 3: strings.json Left at Repository Root (or Omitted Entirely)

**What goes wrong:**
`strings.json` is the canonical source for UI strings used during development and HACS validation. It must live at `custom_components/franklin_wh/strings.json`. Leaving it at root causes `hassfest` validation to fail with an error about missing strings, and HACS validation (`hacs/action`) may also reject the integration.

**Why it happens:**
`strings.json` and `translations/en.json` serve overlapping purposes and developers assume moving `translations/` is sufficient. The CI (`hassfest`) will catch this, but only if CI is run — developers who test locally by restarting HA may not notice.

**How to avoid:**
Move `strings.json` to `custom_components/franklin_wh/strings.json` as part of the same commit as all other file moves. Run the `hassfest` GitHub Actions workflow on the branch before merging.

**Warning signs:**
- `hassfest` CI job fails with a complaint about missing or invalid `strings.json`
- HACS validation job fails

**Phase to address:**
File relocation phase — `strings.json` must be in the explicit move checklist alongside `translations/`.

---

### Pitfall 4: services.yaml Left at Repository Root

**What goes wrong:**
HA loads service descriptions from `custom_components/{domain}/services.yaml`. If `services.yaml` remains at the root, the services (`set_operation_mode`, `set_battery_reserve`) still register and function (because registration happens in `__init__.py` via `hass.services.async_register`), but the Service Developer Tools in the HA UI will show no description, no field labels, and no selector UI for the services.

**Why it happens:**
`services.yaml` is a data file, not a Python file, so it does not cause an import error if omitted. The services work — they just lose their UI metadata. This makes it easy to declare "migration complete" prematurely.

**How to avoid:**
Move `services.yaml` to `custom_components/franklin_wh/services.yaml`. Verify post-migration by opening HA Developer Tools > Services and checking that `franklin_wh.set_operation_mode` and `franklin_wh.set_battery_reserve` show their full descriptions and field selectors.

**Warning signs:**
- Services still work when called, but Developer Tools shows them with no description and no field UI
- `hassfest` may flag this depending on version

**Phase to address:**
File relocation phase — include in the move checklist. Verification step in acceptance testing.

---

### Pitfall 5: hacs.json Updated in a Separate Commit from File Moves

**What goes wrong:**
If `content_in_root: true` is removed from `hacs.json` before the files are moved (or vice versa), there is a broken intermediate commit in the repository. If that commit is pushed to `main`, any user who updates HACS during that window will get a broken installation. HACS will look for files under `custom_components/franklin_wh/` (because `content_in_root` is gone), find nothing, and fail to install.

**Why it happens:**
Developers sometimes stage changes incrementally for easier review, splitting the `hacs.json` change and the file moves into separate PRs or commits.

**How to avoid:**
Make the `hacs.json` change and all file moves in a single atomic commit. The project's own `KEY DECISIONS` table already captures this rationale. Do not create a PR that updates `hacs.json` separately from the file moves.

**Warning signs:**
- Any intermediate commit or branch where `hacs.json` does not have `content_in_root` but `custom_components/franklin_wh/` does not exist (or is incomplete)
- CI passes on partial state (HACS validation only validates structure, not atomicity)

**Phase to address:**
Pre-commit review — enforce in commit message or PR checklist that both changes land together.

---

### Pitfall 6: manifest.json domain Field Mismatch with Directory Name

**What goes wrong:**
HACS and HA both require that the directory name under `custom_components/` exactly matches the `"domain"` field in `manifest.json`. The current `manifest.json` has `"domain": "franklin_wh"`. The directory must be named `custom_components/franklin_wh/` — not `franklinwh`, `franklin-wh`, or any other variation. A mismatch causes HA to fail loading the integration entirely.

**Why it happens:**
Developers sometimes name the directory after the repository (`homeassistant-franklinwh`) or use a different casing. The repository name contains a hyphen; the domain uses an underscore.

**How to avoid:**
Verify: `manifest.json` says `"domain": "franklin_wh"` → directory must be `custom_components/franklin_wh/`. This is already correct in the project context, but worth explicitly verifying the directory creation step uses the underscore form.

**Warning signs:**
- HA logs: `Integration franklin_wh not found` or similar
- Integration does not appear in the UI at all after migration

**Phase to address:**
Directory creation step — double-check the `mkdir` or `git mv` command uses `franklin_wh` (underscore, not hyphen).

---

### Pitfall 7: Git History Lost for Moved Files

**What goes wrong:**
Using `git rm` + `git add` (copy-and-delete) to move files causes git to treat them as deletions and new additions, losing all history. `git log -- sensor.py` will show nothing after the move. While this does not break functionality, it is a significant loss for debugging future regressions.

**Why it happens:**
Developers use file manager moves, `cp`, or IDE refactoring tools that do not go through `git mv`.

**How to avoid:**
Use `git mv` for every file move. Git will track the rename and preserve history. Command pattern:
```
git mv sensor.py custom_components/franklin_wh/sensor.py
git mv translations/ custom_components/franklin_wh/translations/
```
After the move, verify with `git log --follow custom_components/franklin_wh/sensor.py` — history should include pre-migration commits.

**Warning signs:**
- `git status` shows `deleted: sensor.py` and `new file: custom_components/franklin_wh/sensor.py` instead of `renamed: sensor.py -> custom_components/franklin_wh/sensor.py`

**Phase to address:**
File relocation phase — use `git mv` exclusively.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Copy files instead of `git mv` | Easier with some tools | History lost, harder to bisect future bugs | Never — use `git mv` |
| Split `hacs.json` and file moves into separate commits | Easier incremental review | Broken intermediate state pushed to main | Never — must be atomic |
| Skip verifying `translations/`, `strings.json`, `services.yaml` move | Faster | Silent failures; services lose UI metadata | Never |
| Test only via HACS install (not HA restart) | Simpler test | HACS install caches; doesn't catch all HA-level errors | Never for final verification |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| HACS validation (`hacs/action`) | Assumes passing CI means the install works end-to-end | HACS CI validates structure but not HA runtime behavior; test actual HA restart |
| `hassfest` | Runs on root, not on `custom_components/`; may need path config | The existing `hassfest.yaml` uses `home-assistant/actions/hassfest@master` which auto-discovers `custom_components/` — no config needed |
| HA config entry | Existing user config entries store `domain: franklin_wh` — domain does not change, so existing entries survive migration | No data migration needed for this structural-only change |
| HACS cache | HACS may cache the old root-level file layout | Users may need to remove and re-add the repository in HACS after migration |

---

## Performance Traps

Not applicable for a structural migration — no performance-sensitive code changes are involved.

---

## Security Mistakes

Not applicable for a structural migration — no credential handling or API logic changes.

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Existing HACS users get broken install during intermediate broken state | Integration stops working until user manually reinstalls | Atomic commit; coordinate release with migration complete |
| Users who installed with `content_in_root` may have files in wrong HA path | HA loads old files from old path; migration has no effect | Communicate in release notes that users should remove and reinstall via HACS after migration |
| Config flow labels become raw key strings if `translations/` is misplaced | Users see `"username"` instead of `"Email Address"` during setup | Move `translations/` correctly; verify in UI before releasing |

---

## "Looks Done But Isn't" Checklist

- [ ] **Python files moved:** All `.py` files are under `custom_components/franklin_wh/` — verify no `.py` files remain at root except if intentionally excluded
- [ ] **translations/ moved:** `custom_components/franklin_wh/translations/en.json` exists — verify config flow shows human-readable labels
- [ ] **strings.json moved:** `custom_components/franklin_wh/strings.json` exists — verify `hassfest` CI passes
- [ ] **services.yaml moved:** `custom_components/franklin_wh/services.yaml` exists — verify Developer Tools shows service field selectors
- [ ] **manifest.json moved:** `custom_components/franklin_wh/manifest.json` exists with correct `"domain": "franklin_wh"`
- [ ] **hacs.json updated atomically:** `content_in_root` removed in same commit as file moves — verify no intermediate broken state
- [ ] **Repository root clean:** Only `README.md`, `hacs.json`, `LICENSE`, `.github/` remain at root
- [ ] **HACS validation CI passes:** `validate.yaml` (`hacs/action`) green
- [ ] **Hassfest validation CI passes:** `hassfest.yaml` green
- [ ] **HA loads integration:** Restart HA and verify integration loads without errors in HA log
- [ ] **Config flow works:** New config entry can be created via UI
- [ ] **Services visible in Developer Tools:** Both `set_operation_mode` and `set_battery_reserve` show descriptions and field selectors

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Relative import broken | LOW | Find the broken import, add the `.` prefix, commit fix |
| translations/ in wrong location | LOW | `git mv translations/ custom_components/franklin_wh/translations/`, commit |
| strings.json in wrong location | LOW | `git mv strings.json custom_components/franklin_wh/strings.json`, commit |
| services.yaml in wrong location | LOW | `git mv services.yaml custom_components/franklin_wh/services.yaml`, commit |
| Broken intermediate state pushed to main | MEDIUM | Hotfix commit completing the migration; notify HACS users to reinstall |
| Directory named wrong (hyphen vs underscore) | LOW | `git mv custom_components/franklinwh/ custom_components/franklin_wh/` |
| History lost (used cp instead of git mv) | HIGH (irreversible) | Cannot recover history; prevent with pre-move checklist |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Relative imports break | File relocation — grep before and after | `grep -r "^from [a-z]" custom_components/` returns no results |
| translations/ misplaced | File relocation — explicit move checklist | Config flow shows human-readable labels |
| strings.json misplaced | File relocation — explicit move checklist | `hassfest` CI passes |
| services.yaml misplaced | File relocation — explicit move checklist | Developer Tools shows service field selectors |
| Non-atomic hacs.json + file move | Pre-commit review | Single commit contains both changes |
| Domain/directory name mismatch | Directory creation step | `ls custom_components/` shows `franklin_wh` (underscore) |
| Git history lost | File relocation — use `git mv` | `git log --follow custom_components/franklin_wh/sensor.py` shows pre-migration history |
| HACS cache confusion for existing users | Release notes | Document reinstall requirement for existing HACS users |

---

## Sources

- Direct inspection of repository codebase (HIGH confidence): all `.py` files, `hacs.json`, `manifest.json`, `strings.json`, `services.yaml`, `translations/en.json`, `.github/workflows/`
- HACS integration structure requirements (HIGH confidence — well-established, stable convention): `custom_components/{domain}/` with matching `manifest.json` domain field
- HA custom component loading behavior (HIGH confidence — core HA architecture): domain = directory name = `manifest.json` domain field
- `hassfest` action behavior (HIGH confidence — inspected `hassfest.yaml`): auto-discovers `custom_components/` directories
- git mv vs copy behavior (HIGH confidence — git fundamentals)

---
*Pitfalls research for: HACS content_in_root to custom_components/ migration — homeassistant-franklinwh*
*Researched: 2026-02-27*
