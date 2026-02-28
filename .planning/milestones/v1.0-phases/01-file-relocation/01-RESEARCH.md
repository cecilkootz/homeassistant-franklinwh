# Phase 1: File Relocation - Research

**Researched:** 2026-02-27
**Domain:** HACS-compliant Home Assistant custom integration repository structure
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FILE-01 | `custom_components/franklin_wh/` directory created in repository root | Directory created implicitly by `git mv` operations or `mkdir -p` before first mv |
| FILE-02 | `__init__.py` moved via `git mv` | Standard `git mv __init__.py custom_components/franklin_wh/__init__.py` |
| FILE-03 | `config_flow.py` moved via `git mv` | Standard `git mv config_flow.py custom_components/franklin_wh/config_flow.py` |
| FILE-04 | `const.py` moved via `git mv` | Standard `git mv const.py custom_components/franklin_wh/const.py` |
| FILE-05 | `coordinator.py` moved via `git mv` | Standard `git mv coordinator.py custom_components/franklin_wh/coordinator.py` |
| FILE-06 | `diagnostics.py` moved via `git mv` | Standard `git mv diagnostics.py custom_components/franklin_wh/diagnostics.py` |
| FILE-07 | `sensor.py` moved via `git mv` | Standard `git mv sensor.py custom_components/franklin_wh/sensor.py` |
| FILE-08 | `switch.py` moved via `git mv` | Standard `git mv switch.py custom_components/franklin_wh/switch.py` |
| FILE-09 | `manifest.json` moved via `git mv` | Standard `git mv manifest.json custom_components/franklin_wh/manifest.json` |
| FILE-10 | `strings.json` moved via `git mv` | Standard `git mv strings.json custom_components/franklin_wh/strings.json` |
| FILE-11 | `services.yaml` moved via `git mv` | Standard `git mv services.yaml custom_components/franklin_wh/services.yaml` |
| FILE-12 | `translations/en.json` moved via `git mv` (whole directory) | `git mv translations/ custom_components/franklin_wh/translations/` moves directory atomically |
| CONF-01 | `hacs.json` updated to remove `"content_in_root": true` | Edit hacs.json in-place; after removal only `name` key is required |
| CONF-02 | `hacs.json` updated to remove `"zip_release": false` | HACS docs confirm `zip_release` is not required; omitting is cleaner than false |
| CONF-03 | All moves and hacs.json update in a single atomic git commit | Stage all changes, commit once; prevents broken intermediate repository state |
</phase_requirements>

## Summary

This phase is a pure file-system reorganization with no code changes. The repository currently stores all integration files at the repository root with `"content_in_root": true` in `hacs.json`. The goal is to move all files to the HACS-standard location `custom_components/franklin_wh/` and remove the `content_in_root` workaround from `hacs.json`.

The operation is entirely mechanical: create the target directory structure, use `git mv` for each file (and the `translations/` subdirectory), edit `hacs.json` to contain only the `name` field, then commit everything in one shot. There are no library dependencies, no code to write, and no logic to change.

The single risk is committing a partial state (some files moved, others not), which would break the integration for anyone using `content_in_root`. The atomic-commit constraint (CONF-03) fully mitigates this.

**Primary recommendation:** Run all `git mv` commands, edit `hacs.json`, then `git add -A && git commit` in a single operation.

## Current Repository State

Confirmed by direct inspection (2026-02-27):

**Files at repository root that must move:**
- `__init__.py`
- `config_flow.py`
- `const.py`
- `coordinator.py`
- `diagnostics.py`
- `sensor.py`
- `switch.py`
- `manifest.json`
- `strings.json`
- `services.yaml`
- `translations/en.json` (subdirectory)

**Current hacs.json contents:**
```json
{
  "name": "FranklinWH",
  "content_in_root": true,
  "zip_release": false
}
```

**Target hacs.json contents (after phase):**
```json
{
  "name": "FranklinWH"
}
```

**Files that stay at root (do not move):**
- `README.md`
- `hacs.json` (edited in-place, not moved)
- `LICENSE`
- `.github/` (directory — not touched)

## Standard Stack

No libraries or dependencies are required. This is a pure git + filesystem operation.

### Tools Used
| Tool | Purpose | Notes |
|------|---------|-------|
| `git mv` | Move files while preserving git history | Required per FILE-02 through FILE-12 |
| `git commit` | Atomic commit of all changes | Required per CONF-03 |
| Text editor / shell | Edit `hacs.json` | Remove two keys, leave `name` |

## Architecture Patterns

### Target Repository Structure
```
custom_components/
└── franklin_wh/
    ├── __init__.py
    ├── config_flow.py
    ├── const.py
    ├── coordinator.py
    ├── diagnostics.py
    ├── sensor.py
    ├── switch.py
    ├── manifest.json
    ├── strings.json
    ├── services.yaml
    └── translations/
        └── en.json
hacs.json
LICENSE
README.md
.github/
```

### Pattern: Atomic Multi-File Move via git mv

**What:** Stage all `git mv` operations before committing. Git tracks renames as a pair (delete old path, add new path) in the index. You can stage many renames and commit them all at once.

**Why atomic:** If the commit is interrupted, git leaves the working tree in the pre-commit state (all files still at root). There is no half-committed state that would break HACS.

**How:**
```bash
# Step 1: Create target directory (git mv requires destination dir to exist)
mkdir -p custom_components/franklin_wh/translations

# Step 2: Move Python files
git mv __init__.py       custom_components/franklin_wh/__init__.py
git mv config_flow.py    custom_components/franklin_wh/config_flow.py
git mv const.py          custom_components/franklin_wh/const.py
git mv coordinator.py    custom_components/franklin_wh/coordinator.py
git mv diagnostics.py    custom_components/franklin_wh/diagnostics.py
git mv sensor.py         custom_components/franklin_wh/sensor.py
git mv switch.py         custom_components/franklin_wh/switch.py

# Step 3: Move JSON/YAML files
git mv manifest.json     custom_components/franklin_wh/manifest.json
git mv strings.json      custom_components/franklin_wh/strings.json
git mv services.yaml     custom_components/franklin_wh/services.yaml

# Step 4: Move translations directory
git mv translations/en.json custom_components/franklin_wh/translations/en.json

# Step 5: Edit hacs.json (remove content_in_root and zip_release keys)
# Result: {"name": "FranklinWH"}

# Step 6: Stage hacs.json edit and commit everything atomically
git add hacs.json
git commit -m "refactor: migrate files to custom_components/franklin_wh/ for HACS compliance"
```

### Anti-Patterns to Avoid

- **Using `cp` + `git rm` instead of `git mv`:** `cp` followed by `git rm` creates a new file with no history. Git will not detect the rename. Use `git mv` exclusively.
- **Committing in multiple steps:** Committing after each file move creates intermediate states where HACS would fail (files in wrong locations). All moves must land in one commit.
- **Moving `hacs.json`:** `hacs.json` must remain at the repository root — HACS reads it from there regardless of where integration files are.
- **Moving `.github/`:** CI workflow files stay in `.github/workflows/`. Do not touch them.
- **Leaving `translations/` directory at root:** The empty `translations/` directory left behind after moving `en.json` individually would be tracked by git as an empty dir — move the whole subtree.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rename tracking | Custom script using `cp` + `rm` | `git mv` | Only `git mv` preserves rename history in git log |
| Atomic staging | Sequential commits | Single `git commit` after all `git mv` calls | Git staging area holds all pending renames; one commit = one atomic operation |

**Key insight:** `git mv` is just `git add` of the new path + `git rm` of the old path staged together. The commit is atomic regardless of how many files are staged.

## Common Pitfalls

### Pitfall 1: Moving translations/en.json Without Creating the Destination Directory First
**What goes wrong:** `git mv translations/en.json custom_components/franklin_wh/translations/en.json` fails if `custom_components/franklin_wh/translations/` does not yet exist.
**Why it happens:** `git mv` does not create intermediate directories.
**How to avoid:** Run `mkdir -p custom_components/franklin_wh/translations` before any `git mv` calls.
**Warning signs:** `fatal: destination directory 'custom_components/franklin_wh/translations' does not exist`

### Pitfall 2: Committing with Leftover Root Files
**What goes wrong:** Forgetting to `git mv` one file leaves it at the root. HACS validation fails because `content_in_root` is now `false` (removed) but a file still lives at root.
**Why it happens:** Easy to miss a file when running commands manually.
**How to avoid:** Run `git status` before committing and confirm the root has no `.py`, `.yaml`, or non-`hacs.json` `.json` files staged or untracked.
**Warning signs:** `git status` shows untracked Python files at repository root after moves.

### Pitfall 3: Incorrect hacs.json After Edit
**What goes wrong:** Invalid JSON (trailing comma, missing brace) in `hacs.json` causes HACS to reject the repository entirely.
**Why it happens:** Manual editing of small JSON files is error-prone.
**How to avoid:** After editing, validate with `python3 -m json.tool hacs.json` or `cat hacs.json | python3 -c "import sys,json; json.load(sys.stdin); print('valid')"`.
**Warning signs:** HACS shows "Could not parse hacs.json" in the UI.

### Pitfall 4: Moving hacs.json
**What goes wrong:** Moving `hacs.json` to `custom_components/franklin_wh/hacs.json` causes HACS to not find it.
**Why it happens:** Confusion about which files belong in the component directory vs. repository root.
**How to avoid:** `hacs.json` always stays at the repository root. Only integration code and assets move.
**Warning signs:** HACS cannot find the repository after installation.

## Code Examples

### Complete Shell Script for the Migration

```bash
# Source: HACS documentation + git documentation (verified)
# Run from repository root

set -e  # Exit on first error

# Create destination directory structure
mkdir -p custom_components/franklin_wh/translations

# Move all Python files
git mv __init__.py        custom_components/franklin_wh/__init__.py
git mv config_flow.py     custom_components/franklin_wh/config_flow.py
git mv const.py           custom_components/franklin_wh/const.py
git mv coordinator.py     custom_components/franklin_wh/coordinator.py
git mv diagnostics.py     custom_components/franklin_wh/diagnostics.py
git mv sensor.py          custom_components/franklin_wh/sensor.py
git mv switch.py          custom_components/franklin_wh/switch.py

# Move JSON and YAML config files
git mv manifest.json      custom_components/franklin_wh/manifest.json
git mv strings.json       custom_components/franklin_wh/strings.json
git mv services.yaml      custom_components/franklin_wh/services.yaml

# Move translations
git mv translations/en.json custom_components/franklin_wh/translations/en.json

# Update hacs.json: remove content_in_root and zip_release
python3 -c "
import json
with open('hacs.json') as f:
    d = json.load(f)
d.pop('content_in_root', None)
d.pop('zip_release', None)
with open('hacs.json', 'w') as f:
    json.dump(d, f, indent=2)
    f.write('\n')
"

# Validate hacs.json is valid JSON
python3 -m json.tool hacs.json > /dev/null && echo "hacs.json is valid"

# Stage the hacs.json edit and commit everything atomically
git add hacs.json
git status  # Final review before committing
git commit -m "refactor: migrate files to custom_components/franklin_wh/ for HACS compliance"
```

### Verify Root is Clean After Migration

```bash
# Should show only: README.md, hacs.json, LICENSE, .github/
ls -la | grep -v '^d' | grep -v '^\.' | grep -v 'LICENSE\|README\|hacs.json'
# Expected: no output (no stray files)
```

### Verify Target Directory Structure

```bash
find custom_components/franklin_wh -type f | sort
# Expected output:
# custom_components/franklin_wh/__init__.py
# custom_components/franklin_wh/config_flow.py
# custom_components/franklin_wh/const.py
# custom_components/franklin_wh/coordinator.py
# custom_components/franklin_wh/diagnostics.py
# custom_components/franklin_wh/manifest.json
# custom_components/franklin_wh/sensor.py
# custom_components/franklin_wh/services.yaml
# custom_components/franklin_wh/strings.json
# custom_components/franklin_wh/switch.py
# custom_components/franklin_wh/translations/en.json
```

## State of the Art

| Old Approach | Current Approach | Notes |
|---|---|---|
| `content_in_root: true` in hacs.json | Files in `custom_components/<domain>/` | HACS originally supported root-level content; standard structure is now the default |
| `zip_release: false` | Omit `zip_release` entirely | Field is optional; omitting is equivalent to false; cleaner |

**Deprecated/outdated:**
- `content_in_root: true`: A legacy HACS workaround. Repositories with proper `custom_components/<domain>/` structure do not need this field. HACS docs confirmed `name` is the only required field.
- `zip_release: false`: Redundant. When omitted, HACS defaults to source-based installation from the repository. The field is only needed when set to `true`.

## Open Questions

No open questions. The migration is fully deterministic based on the current repository state and HACS documentation.

## Sources

### Primary (HIGH confidence)
- HACS official documentation (https://hacs.xyz/docs/publish/start) — confirmed `name` is only required field; `content_in_root` and `zip_release` are optional fields that can be omitted
- Direct repository inspection (2026-02-27) — confirmed exact list of 11 files + translations/en.json at root

### Secondary (MEDIUM confidence)
- Git documentation: `git mv` behavior for rename tracking and staging (well-established git behavior, consistent across versions)

## Metadata

**Confidence breakdown:**
- File inventory: HIGH — directly inspected repository
- hacs.json target format: HIGH — verified with HACS official docs
- git mv behavior: HIGH — standard git behavior, well-documented
- Architecture (target structure): HIGH — HACS standard is clear and documented

**Research date:** 2026-02-27
**Valid until:** 2026-04-27 (HACS structure conventions are stable)
