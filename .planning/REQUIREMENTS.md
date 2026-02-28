# Requirements: homeassistant-franklinwh

**Defined:** 2026-02-27
**Core Value:** FranklinWH energy management data and controls in Home Assistant via first-class HACS integration

## v1.1 Requirements

### Library Vendoring

- [ ] **VEND-01**: Vendored franklinwh library resides at `custom_components/franklin_wh/franklinwh/` with all necessary source files
- [ ] **VEND-02**: Vendored `client.py` accepts an injected `httpx.AsyncClient` session parameter on `Client.__init__` and `TokenFetcher.__init__`, eliminating the synchronous SSL context initialization
- [ ] **VEND-03**: `manifest.json` no longer lists `franklinwh>=1.0.0` in requirements

### HA Integration

- [ ] **HAINT-01**: `coordinator.py` imports `Client`, `TokenFetcher`, `Mode` from the local vendored library (`.franklinwh`)
- [ ] **HAINT-02**: `coordinator.py` passes `get_async_client(hass)` from `homeassistant.helpers.httpx_client` into `TokenFetcher` and `Client`
- [ ] **HAINT-03**: `config_flow.py` imports from the local vendored library (`.franklinwh`)
- [ ] **HAINT-04**: Home Assistant no longer logs the `load_verify_locations` blocking call warning on integration startup

## Future Requirements

### Testing

- **TEST-01**: Unit tests for vendored client session injection
- **TEST-02**: Integration tests for coordinator update cycle

### Bug Fixes (Deferred)

- **BUG-01**: Fix config_flow.py wrapping async `client.get_stats()` in `async_add_executor_job` (incorrect usage)

## Out of Scope

| Feature | Reason |
|---------|--------|
| New sensors or controls | Not part of this bug fix milestone |
| config_flow executor bug fix | Deferred — pre-existing, separate concern |
| Tests | Separate milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VEND-01 | Phase 3 | Pending |
| VEND-02 | Phase 3 | Pending |
| VEND-03 | Phase 3 | Pending |
| HAINT-01 | Phase 3 | Pending |
| HAINT-02 | Phase 3 | Pending |
| HAINT-03 | Phase 3 | Pending |
| HAINT-04 | Phase 3 | Pending |

**Coverage:**
- v1.1 requirements: 7 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 7 ⚠️

---
*Requirements defined: 2026-02-27*
*Last updated: 2026-02-27 after initial definition*
