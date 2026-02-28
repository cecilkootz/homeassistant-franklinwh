# Stack Research

**Domain:** HACS Custom Integration Repository Structure
**Researched:** 2026-02-27
**Confidence:** HIGH (verified against two locally-available production HACS integrations and existing workflow files)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Integration runtime | Required by Home Assistant 2024.x+; existing codebase already uses 3.11 |
| Home Assistant Core | 2024.1.0+ | Integration framework | Standard target for HACS integrations; `homeassistant` field in hacs.json pins minimum |
| HACS | Latest | Distribution mechanism | The goal; standard structure eliminates `content_in_root` workaround |

### Repository Structure (Required)

The standard HACS integration layout places ALL integration files under `custom_components/{domain}/`. The repository root contains only infrastructure files.

**Required directory tree after migration:**

```
homeassistant-franklinwh/          ← repository root
├── custom_components/
│   └── franklin_wh/               ← integration package (domain name)
│       ├── __init__.py            ← integration entry point
│       ├── manifest.json          ← HA metadata (MUST be inside the domain dir)
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── sensor.py
│       ├── switch.py
│       ├── const.py
│       ├── diagnostics.py
│       ├── strings.json           ← localization source strings
│       ├── services.yaml          ← service definitions
│       └── translations/
│           └── en.json
├── hacs.json                      ← HACS metadata (MUST be at repo root)
├── README.md
├── LICENSE
└── .github/
    └── workflows/
        ├── validate.yaml          ← runs hacs/action
        └── hassfest.yaml          ← runs home-assistant/actions/hassfest
```

**Confidence:** HIGH — verified against:
- `/Users/matt/Development/sunspec/franklin-wh-sunspec/` (minimal, clean example, no `content_in_root`)
- `/Users/matt/Development/span/` (production integration with `content_in_root: false`)

### hacs.json Specification

**Required fields:**

| Field | Type | Purpose | Notes |
|-------|------|---------|-------|
| `name` | string | Display name in HACS UI | Human-readable, e.g. `"FranklinWH"` |

**Optional but recommended fields:**

| Field | Type | Purpose | Notes |
|-------|------|---------|-------|
| `homeassistant` | string | Minimum HA version | e.g. `"2024.1.0"`; enforced by HACS before install |
| `render_readme` | boolean | Show README.md in HACS UI | `true` preferred so users see docs without leaving HACS |

**Fields to REMOVE:**

| Field | Why Remove | Notes |
|-------|-----------|-------|
| `content_in_root` | This is the workaround being eliminated | Removing it forces HACS to use standard `custom_components/` discovery |
| `zip_release` | Not needed for source-code repos | Only used for pre-built zip releases; `false` is default |
| `filename` | Not needed when standard structure is followed | Only used when package is not named after domain; with `custom_components/franklin_wh/` HACS auto-discovers |

**Minimal valid hacs.json after migration:**
```json
{
  "name": "FranklinWH",
  "homeassistant": "2024.1.0",
  "render_readme": true
}
```

**Confidence:** HIGH — sunspec integration uses exactly this minimal form with no `content_in_root` and works correctly.

### manifest.json Specification

`manifest.json` lives inside `custom_components/franklin_wh/` (not the repo root). Current contents are already compliant and require no changes after relocation.

**Required fields (already present in existing manifest.json):**

| Field | Current Value | Status |
|-------|--------------|--------|
| `domain` | `"franklin_wh"` | Correct — matches directory name |
| `name` | `"FranklinWH"` | Correct |
| `version` | `"1.1.3"` | Correct |
| `codeowners` | `["@JoshuaSeidel"]` | Correct |
| `documentation` | URL | Correct |
| `issue_tracker` | URL | Correct |
| `iot_class` | `"cloud_polling"` | Correct |
| `requirements` | `["franklinwh>=1.0.0"]` | Correct |
| `config_flow` | `true` | Correct |

**Optional fields (already present and valid):**

| Field | Notes |
|-------|-------|
| `integration_type` | `"hub"` — optional but valid |
| `loggers` | `["franklinwh"]` — optional but useful |
| `dependencies` | `[]` — optional |

**Confidence:** HIGH — manifest.json format is unchanged by structural migration; all fields verified against two reference integrations.

### Validation Tools

| Tool | Invocation | Purpose | Notes |
|------|-----------|---------|-------|
| `hacs/action` | GitHub Actions: `uses: hacs/action@main` with `category: integration` | Validates hacs.json, checks `custom_components/` structure, confirms HACS compliance | Already configured in `.github/workflows/validate.yaml` |
| `home-assistant/actions/hassfest` | GitHub Actions: `uses: home-assistant/actions/hassfest@master` | Validates manifest.json, entity definitions, translations, and Python patterns | Already configured in `.github/workflows/hassfest.yaml` |

Both validators are already in the repository's CI workflows. After migration, both should pass without modification to the workflow files themselves.

**Confidence:** MEDIUM — workflow files exist locally; cannot confirm whether they currently pass given broken structure, but the tool choices are standard.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `.python-version` file | Pins Python version (currently `3.11`) | Already present; no changes needed |
| GitHub Actions | CI validation via `hacs/action` and `hassfest` | Already configured; will work post-migration |

## What NOT to Do

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `"content_in_root": true` | HACS workaround that bypasses standard discovery; non-compliant with default HACS expectations | Move files to `custom_components/franklin_wh/` and remove the field entirely |
| Keeping `"zip_release": false` explicitly | Redundant (it is the default); adds noise to hacs.json | Remove the field; HACS defaults to source release |
| Keeping `"filename"` field | Only needed when the package directory name differs from the auto-discovered convention; with standard structure HACS discovers `custom_components/franklin_wh/` automatically | Remove; let HACS auto-discover |
| Placing `manifest.json` at the repository root | Home Assistant expects `manifest.json` inside `custom_components/{domain}/`; a root-level one is ignored | Keep manifest.json inside `custom_components/franklin_wh/` only |
| Placing `hacs.json` inside `custom_components/` | HACS reads `hacs.json` only from the repository root | Keep hacs.json at root only |
| Placing `strings.json` or `services.yaml` at root | Home Assistant loads these relative to the integration package directory | Move inside `custom_components/franklin_wh/` |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| Remove `content_in_root` + move files to `custom_components/franklin_wh/` | Keep `content_in_root: true` | Never — this is the deprecated workaround being eliminated |
| Minimal hacs.json (name + homeassistant + render_readme) | Add `filename` field | Only if the integration directory name does not match the domain; here it does match, so `filename` is unnecessary |
| Source-code release (default) | `zip_release: true` with pre-built zip | Only if the repo contains build steps or compiled assets that need to ship as a zip |

## Version Compatibility

| Component | Compatible With | Notes |
|-----------|----------------|-------|
| `hacs.json` (no `content_in_root`) | HACS 1.x and 2.x | Standard structure has been the requirement since HACS initial stable release |
| `manifest.json` (current fields) | Home Assistant 2024.1.0+ | `integration_type` field added in HA 2023.x; all current fields are valid |
| `hacs/action@main` | GitHub Actions | Already pinned to `main`; no version change needed |
| `home-assistant/actions/hassfest@master` | GitHub Actions | Already pinned to `master`; no version change needed |

## Sources

- `/Users/matt/Development/sunspec/franklin-wh-sunspec/` — Minimal clean HACS integration with standard structure, no `content_in_root`, verified working — HIGH confidence
- `/Users/matt/Development/span/` — Production HACS integration with `content_in_root: false`, standard `custom_components/span_panel/` structure — HIGH confidence
- `/Users/matt/Development/homeassistant-franklinwh/.github/workflows/validate.yaml` — Confirms `hacs/action@main` with `category: integration` is the standard validator — HIGH confidence
- `/Users/matt/Development/homeassistant-franklinwh/.github/workflows/hassfest.yaml` — Confirms `home-assistant/actions/hassfest@master` is the HA compliance validator — HIGH confidence
- Training data on HACS structure conventions — LOW confidence (used only where corroborated by local evidence)

---
*Stack research for: HACS Custom Integration Repository Structure Migration*
*Researched: 2026-02-27*
