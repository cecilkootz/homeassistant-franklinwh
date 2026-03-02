# Milestones

## v1.2 SunSpec/Modbus Local API (Shipped: 2026-03-01)

**Phases completed:** 5 phases (4-8), 7 plans
**Requirements:** 11/11 satisfied (MCONF-01/02, MDATA-01–07, MRES-01–03)

**Key accomplishments:**
- `SunSpecModbusClient` reads SunSpec Models 502/701/713/714 via pySunSpec2 in executor — battery SoC, DC power, solar, grid AC, home load available locally at 10s interval
- Config flow and options flow wired for Modbus TCP host/port/slave ID; local mode togglable without re-entering cloud credentials
- Hybrid coordinator: Modbus provides real-time power flow, cloud provides energy totals (kWh) — two data paths coexist cleanly
- Modbus failures fall back to cloud automatically (warning logged, entities stay available); unreachable Modbus at startup no longer blocks integration load
- Options flow changes trigger coordinator reload via `add_update_listener` — no HA restart required to switch modes (Phase 8 gap closure)
- Grid AC power polarity normalized to single negation in coordinator — positive = importing from grid in both cloud and Modbus paths (Phase 8 gap closure)

**Git range:** f7ecbf2 → HEAD (36 commits)
**LOC:** 1,589 Python (custom_components/franklin_wh/), +167 LOC sunspec_client.py new file
**Archive:** .planning/milestones/v1.2-ROADMAP.md

---

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

