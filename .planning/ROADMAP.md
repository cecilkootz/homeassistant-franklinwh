# Roadmap: homeassistant-franklinwh

## Milestones

- ✅ **v1.0 HACS Structure Migration** — Phases 1-2 (shipped 2026-02-28)
- 🚧 **v1.1 Fix Blocking HTTP Client** — Phase 3 (in progress)

## Phases

<details>
<summary>✅ v1.0 HACS Structure Migration (Phases 1-2) — SHIPPED 2026-02-28</summary>

- [x] Phase 1: File Relocation (1/1 plans) — completed 2026-02-28
- [x] Phase 2: Verification and Documentation (1/1 plans) — completed 2026-02-28

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 Fix Blocking HTTP Client (In Progress)

**Milestone Goal:** Eliminate the `load_verify_locations` event loop warning by vendoring the franklinwh library and injecting HA's managed httpx client.

- [ ] **Phase 3: Vendor and Wire HTTP Client** - Vendor franklinwh into the integration, inject HA's httpx client, remove PyPI dependency

## Phase Details

### Phase 3: Vendor and Wire HTTP Client
**Goal**: The integration uses HA's managed httpx client with no blocking SSL calls on startup
**Depends on**: Phase 2
**Requirements**: VEND-01, VEND-02, VEND-03, HAINT-01, HAINT-02, HAINT-03, HAINT-04
**Success Criteria** (what must be TRUE):
  1. `custom_components/franklin_wh/franklinwh/` exists with all source files from the upstream library
  2. `Client` and `TokenFetcher` accept an `httpx.AsyncClient` parameter — no SSL context is created at import or init time
  3. `coordinator.py` and `config_flow.py` import from `.franklinwh` and pass `get_async_client(hass)` at construction
  4. `manifest.json` has no `franklinwh` entry in `requirements`
  5. Home Assistant startup logs contain no `load_verify_locations` blocking call warning from this integration
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Vendor franklinwh library and modify client to accept injected httpx.AsyncClient
- [ ] 03-02-PLAN.md — Wire coordinator.py and config_flow.py to use HA httpx client; remove PyPI dependency

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. File Relocation | v1.0 | 1/1 | Complete | 2026-02-28 |
| 2. Verification and Documentation | v1.0 | 1/1 | Complete | 2026-02-28 |
| 3. Vendor and Wire HTTP Client | 1/2 | In Progress|  | - |
