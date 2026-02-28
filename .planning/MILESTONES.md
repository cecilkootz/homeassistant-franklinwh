# Milestones

## v1.1 Fix Blocking HTTP Client (Shipped: 2026-02-28)

**Phases completed:** 1 phase, 2 plans, 4 tasks

**Key accomplishments:**
- Vendored franklinwh PyPI library into `custom_components/franklin_wh/franklinwh/` — targeted modification without forking upstream
- Modified `TokenFetcher` and `Client` to accept injected `httpx.AsyncClient` — no SSL context created at construction time
- Wired `coordinator.py` to HA's managed httpx client via `get_async_client(hass)` — `async_add_executor_job` wrapper removed
- Wired `config_flow.py` to same HA-managed client — config validation is now non-blocking
- Removed `franklinwh>=1.0.0` from `manifest.json` requirements — library fully vendored, no PyPI install

**Git range:** c3c15b8 → a343457
**LOC:** 1,359 across key files (806 vendored client.py, 242 coordinator.py, 223 config_flow.py)
**Archive:** .planning/milestones/v1.1-ROADMAP.md

---

## v1.0 HACS Structure Migration (Shipped: 2026-02-28)

**Phases completed:** 2 phases, 2 plans, 0 tasks

**Key accomplishments:**
- 11 integration files relocated to `custom_components/franklin_wh/` via `git mv` with full rename history preserved
- `hacs.json` stripped to `{"name": "FranklinWH"}` — `content_in_root` and `zip_release` workarounds removed
- All 12 file changes landed in single atomic commit (5f5e8cc) — no broken intermediate state
- `manifest.json` key ordering fixed for hassfest compliance (domain, name, then alphabetical)
- HACS `validate.yaml` workflow enabled (was `disabled_fork`) and confirmed passing — 8/8 checks
- Hassfest confirmed passing — integration fully HACS-compliant and ready for submission

**Git range:** 5f5e8cc → 3aa334b
**LOC:** 1,232 Python (custom_components/franklin_wh/)
**Archive:** .planning/milestones/v1.0-ROADMAP.md

---

