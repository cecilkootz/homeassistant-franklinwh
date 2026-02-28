# Architecture Research

**Domain:** Home Assistant HACS custom integration — repository structure migration
**Researched:** 2026-02-27
**Confidence:** HIGH (codebase inspection) / MEDIUM (HA/HACS loading mechanism — training data, web verification unavailable)

## Standard Architecture

### System Overview

```
Repository Root (after migration)
├── README.md
├── hacs.json                         # HACS metadata — no content_in_root
├── LICENSE
└── custom_components/
    └── franklin_wh/                  # Python package — HA discovers this
        ├── __init__.py               # Integration entry point
        ├── manifest.json             # Domain declaration, requirements
        ├── const.py
        ├── coordinator.py
        ├── config_flow.py
        ├── sensor.py
        ├── switch.py
        ├── diagnostics.py
        ├── services.yaml
        ├── strings.json
        └── translations/
            └── en.json
```

### Component Responsibilities

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| `custom_components/franklin_wh/` | Python package root — HA loads this as the integration | Directory name must equal `domain` in manifest.json |
| `manifest.json` | Declares domain, version, requirements, codeowners | Must live inside the package directory |
| `__init__.py` | Integration entry/exit lifecycle | Unchanged functionally |
| `translations/` | UI string localization | Must be a subdirectory of the package |
| `services.yaml` / `strings.json` | Service and string definitions | Must be inside the package directory |

---

## How Home Assistant Discovers Custom Integrations

**Confidence: MEDIUM** (well-established mechanism, training data supported by code inspection)

Home Assistant scans the `custom_components/` directory at startup. For each subdirectory that contains a `manifest.json` with a `"domain"` field, HA treats it as an installed integration. The directory name must exactly match the `domain` value in `manifest.json`.

Discovery sequence:
1. HA scans `<config_dir>/custom_components/`
2. For each subdirectory, reads `manifest.json`
3. If `manifest.json` contains `"domain": "franklin_wh"`, HA registers the integration under that domain
4. When loading, HA imports `custom_components.franklin_wh` as a Python package
5. `__init__.py` is the integration entry point — `async_setup_entry` and `async_unload_entry` are called from here

The `custom_components/franklin_wh/` directory becomes the Python package `custom_components.franklin_wh`. All files inside it are modules of that package.

**Critical:** The directory name (`franklin_wh`) must match `manifest.json` `"domain"`. In this codebase, `manifest.json` already declares `"domain": "franklin_wh"`, so no change needed there — only the file needs to be relocated inside the new directory.

---

## Python Package and Import Path Implications

### Current State (files at repo root)

When HACS installs with `content_in_root: true`, it copies root files directly into `<config_dir>/custom_components/franklin_wh/`. The files land inside the package directory, so the runtime import path is already `custom_components.franklin_wh.*`. The repo root layout is an installation-time concern only.

All intra-module imports in the current codebase use **relative imports** with the dot notation:

```python
# coordinator.py
from .const import DEFAULT_LOCAL_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

# sensor.py
from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator, FranklinWHData

# __init__.py
from .const import (CONF_GATEWAY_ID, DOMAIN, ...)
from .coordinator import FranklinWHCoordinator

# config_flow.py
from .const import (...)

# diagnostics.py
from .const import CONF_GATEWAY_ID, DOMAIN
from .coordinator import FranklinWHCoordinator

# switch.py
from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator
```

### After Migration (files in `custom_components/franklin_wh/`)

**The relative imports require zero changes.** Relative imports (`.module`) resolve relative to the package the importing module belongs to. When `coordinator.py` moves from the repo root into `custom_components/franklin_wh/`, it still belongs to the same package — `custom_components.franklin_wh` — and `.const` still resolves to `custom_components.franklin_wh.const`.

The only thing that changes is the absolute path on disk. The Python import semantics are identical.

### External imports — no change needed

All external imports (franklinwh library, homeassistant modules) use absolute paths and are unaffected:

```python
from franklinwh import Client, TokenFetcher, Mode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
```

These remain identical before and after migration.

### Logger names — no change needed

All modules use:
```python
_LOGGER = logging.getLogger(__name__)
```

`__name__` evaluates to the fully-qualified module name at runtime (e.g., `custom_components.franklin_wh.coordinator`). Before migration, HACS installs files into `custom_components/franklin_wh/` anyway, so `__name__` is already `custom_components.franklin_wh.*` at runtime. After migration, nothing changes.

---

## HACS Loading Mechanism Impact

**Confidence: HIGH** (directly observable from hacs.json and project context)

Current `hacs.json`:
```json
{
  "name": "FranklinWH",
  "content_in_root": true,
  "zip_release": false
}
```

`content_in_root: true` tells HACS: "The integration files are at the repository root, not under `custom_components/{domain}/`." HACS then copies them into the user's `custom_components/franklin_wh/` directory during installation.

After migration, `hacs.json` becomes:
```json
{
  "name": "FranklinWH"
}
```

HACS then looks for `custom_components/franklin_wh/` in the repository and copies its contents into the user's config directory. This is the standard, fully supported HACS integration layout. `content_in_root` has been considered a workaround/legacy feature in HACS and may be removed in future HACS versions.

---

## Architectural Patterns

### Pattern 1: Relative Imports Throughout Integration

**What:** All intra-package imports use dot-relative syntax (`from .module import X`), never absolute (`from custom_components.franklin_wh.module import X`).

**When to use:** Always, for all intra-integration imports. This is the HA-mandated pattern.

**Why it works post-migration:** Relative imports are resolved by the Python runtime based on the package the module belongs to, not the filesystem path. Moving all files together into a new directory preserves all relative relationships.

**Example:**
```python
# Works identically in both repo root and custom_components/franklin_wh/
from .const import DOMAIN
from .coordinator import FranklinWHCoordinator
```

### Pattern 2: Package-as-Integration Identity

**What:** The directory name under `custom_components/` is the integration's identity in Home Assistant. It must match `manifest.json` `"domain"`.

**When to use:** Always — this is how HA discovers and loads integrations.

**For this migration:** `manifest.json` already declares `"domain": "franklin_wh"`. The target directory must be `custom_components/franklin_wh/`. This is consistent and requires no manifest changes beyond physical relocation of the file.

### Pattern 3: Translations as Package Subdirectory

**What:** The `translations/` directory must reside inside the integration package directory, not at the repository root.

**Why:** Home Assistant resolves translation files relative to the integration package path. It looks for `<integration_path>/translations/<lang>.json`. With `content_in_root`, HACS could place the top-level `translations/` dir into the package directory. After migration, `translations/` must be explicitly placed inside `custom_components/franklin_wh/`.

---

## Data Flow (unchanged after migration)

```
[Home Assistant startup]
    ↓
[Scans custom_components/ directory]
    ↓
[Finds franklin_wh/manifest.json]
    ↓
[Imports custom_components.franklin_wh (loads __init__.py)]
    ↓
[async_setup_entry() creates FranklinWHCoordinator]
    ↓
[Forwards setup to sensor, switch platforms]
    ↓
[Entities created, registered, polling begins]
```

This data flow is entirely unaffected by the structural migration. All file moves are transparent to the HA runtime because HACS already installs into `custom_components/franklin_wh/` with the current workaround.

---

## Build Order: What to Do First, Second, etc.

**Confidence: HIGH** (derived from dependency analysis and atomicity requirements)

### Step 1: Create the package directory
Create `custom_components/franklin_wh/` in the repository. This is a prerequisite for all subsequent moves.

### Step 2: Move Python source files
Move all `.py` files from root into `custom_components/franklin_wh/`:
- `__init__.py`
- `manifest.json`
- `const.py`
- `coordinator.py`
- `config_flow.py`
- `sensor.py`
- `switch.py`
- `diagnostics.py`

No import changes needed — all relative imports work identically.

### Step 3: Move support files
Move non-Python integration files into `custom_components/franklin_wh/`:
- `services.yaml`
- `strings.json`

### Step 4: Move translations directory
Move `translations/` directory (including `en.json`) into `custom_components/franklin_wh/translations/`.

### Step 5: Update hacs.json
Remove `"content_in_root": true` from `hacs.json`. This is the atomic completion step — do this in the same commit as all the file moves to prevent a broken intermediate state where files are relocated but HACS still uses the old install path.

### Atomicity note
Steps 1-5 should be committed atomically (single commit). A partially-migrated state where some files are in the new location and `hacs.json` still has `content_in_root: true` is valid and non-breaking for existing installs, but a state where files are moved AND `content_in_root` is removed without all files being present would break HACS installation. The safest approach: complete all file moves first, then update `hacs.json` in a single commit.

---

## Anti-Patterns

### Anti-Pattern 1: Absolute intra-integration imports

**What people do:** Convert relative imports to absolute during migration:
```python
# Wrong after migration
from custom_components.franklin_wh.const import DOMAIN
```

**Why it's wrong:** Breaks portability, violates HA conventions, and is fragile if domain name changes. HA community and codebase standards mandate relative imports within an integration.

**Do this instead:**
```python
from .const import DOMAIN
```

### Anti-Pattern 2: Splitting the commit

**What people do:** Move files in one commit, update `hacs.json` in a second commit.

**Why it's wrong:** The intermediate state (files moved, `content_in_root` still true) is confusing. The second intermediate state (files moved, `content_in_root` removed) is safe but risks the commit getting lost, leaving a permanently broken state.

**Do this instead:** Single atomic commit that moves all files and updates `hacs.json` simultaneously.

### Anti-Pattern 3: Forgetting non-Python files

**What people do:** Move only `.py` files, forgetting `services.yaml`, `strings.json`, `translations/`.

**Why it's wrong:** HA resolves these files relative to the integration package path. If they remain at the repo root, HACS won't install them into the correct location, and HA will fail to load service definitions and translations.

**Do this instead:** Move all integration-owned files: `.py`, `manifest.json`, `services.yaml`, `strings.json`, and `translations/`.

---

## Integration Points

### HACS → Repository

| Concern | Before Migration | After Migration |
|---------|-----------------|-----------------|
| Install source | Repository root (via `content_in_root`) | `custom_components/franklin_wh/` |
| HACS validation | Workaround accepted | Standard layout, fully validated |
| `hacs.json` | `content_in_root: true` | No `content_in_root` key |

### HA Runtime → Package

| Concern | Before Migration | After Migration |
|---------|-----------------|-----------------|
| Discovery path | `custom_components/franklin_wh/` (HACS copies there) | `custom_components/franklin_wh/` (same) |
| Python package name | `custom_components.franklin_wh` | `custom_components.franklin_wh` (same) |
| Relative imports | Work | Work (unchanged) |
| Translations | `translations/en.json` relative to package | `translations/en.json` relative to package (same) |

---

## Sources

- Codebase inspection: `/Users/matt/Development/homeassistant-franklinwh/*.py` (HIGH confidence — direct observation)
- `manifest.json` domain field: direct file inspection (HIGH confidence)
- `hacs.json` `content_in_root` behavior: training data + project context (MEDIUM confidence — web verification unavailable)
- HA `custom_components/` discovery mechanism: training data (MEDIUM confidence)
- Relative import Python semantics: language specification (HIGH confidence)

---
*Architecture research for: HACS custom integration repository structure migration*
*Researched: 2026-02-27*
