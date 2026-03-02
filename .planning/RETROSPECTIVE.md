# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — HACS Structure Migration

**Shipped:** 2026-02-28
**Phases:** 2 | **Plans:** 2 | **Sessions:** ~3

### What Was Built
- 11 integration files relocated to `custom_components/franklin_wh/` via `git mv` with rename history preserved
- `hacs.json` stripped to name-only — `content_in_root` / `zip_release` workarounds removed
- HACS validation and hassfest both confirmed passing on main branch
- README audited and confirmed clean of workaround language

### What Worked
- Atomic commit approach (all 12 changes in one commit) prevented any broken intermediate state
- Using `git mv` instead of copy+delete gave clean rename history that GitHub displays correctly
- Checking CI immediately after structural change caught the manifest.json key ordering issue early
- Integration checker at audit time confirmed all cross-phase wiring with 100% coverage

### What Was Inefficient
- `verify-work` step was not run for either phase — VERIFICATION.md artifacts are missing, making the 3-source audit cross-reference rely only on SUMMARY frontmatter + CI evidence
- REQUIREMENTS.md checkboxes for VERIF-01 and VERIF-02 were not updated after CI confirmed them passing — required manual correction at audit
- GitHub repository settings (Issues enabled, topics added) had to be fixed by the user mid-execution — could have been surfaced during research phase

### Patterns Established
- Integration files live at `custom_components/franklin_wh/` — HACS standard discovery path
- `manifest.json` key order: `domain`, `name`, then all remaining keys alphabetically (hassfest requirement)
- GitHub `disabled_fork` workflow state must be checked before relying on CI — enable via `gh api PUT .../workflows/{id}/enable`

### Key Lessons
1. **Run verify-work after each phase** — skipping it leaves the audit without VERIFICATION.md artifacts, degrading confidence in 3-source cross-reference
2. **Check GitHub repository settings during research** — Issues enabled, HACS/homeassistant topics, workflow states are prerequisites for HACS validation that aren't obvious from code inspection
3. **hassfest requires strict manifest.json key ordering** — `domain`, `name`, then alphabetical; any deviation fails CI even if all values are correct

### Cost Observations
- Model mix: ~100% sonnet
- Sessions: ~3
- Notable: Pure structural migration with no functional changes — very fast execution, the overhead was GitHub settings discovery

---

## Milestone: v1.1 — Fix Blocking HTTP Client

**Shipped:** 2026-02-28
**Phases:** 1 | **Plans:** 2 | **Sessions:** 1

### What Was Built
- franklinwh PyPI library vendored verbatim into `custom_components/franklin_wh/franklinwh/` with targeted session-injection modifications to `client.py`
- `TokenFetcher` and `Client` both accept optional `httpx.AsyncClient` — when injected, no `httpx.AsyncClient()` construction occurs (eliminates `load_verify_locations` blocking call)
- `coordinator.py` wired to `get_async_client(hass)` — `async_add_executor_job` wrapper removed
- `config_flow.py` wired to same HA-managed client
- `franklinwh>=1.0.0` removed from `manifest.json` requirements

### What Worked
- Single-phase milestone was fast to plan and execute — the problem was well-scoped
- Vendoring approach (copy verbatim + targeted patch) was surgical: 4 library files unchanged, only `client.py` modified
- Optional injection pattern (`session if session is not None else self.get_client()`) preserves upstream behavior for non-HA usage and tests
- Integration checker confirmed all 7 requirements wired with E2E flow traces

### What Was Inefficient
- VERIFICATION.md again not produced — `verifier_enabled: false` in config means audit relied on 2/3 sources (SUMMARY frontmatter + integration checker) rather than 3/3
- `plan-milestone-gaps` was invoked unnecessarily by user — audit status was `tech_debt`, not `gaps_found`; the distinction between statuses could be made clearer in the output

### Patterns Established
- **Session injection pattern**: `TokenFetcher(session=session)` and `Client(session=session)` at construction, obtained once via `get_async_client(hass)` in `coordinator.__init__`
- **Vendoring rule**: never close an HA-managed httpx client; use it directly (not as context manager)
- **Milestone scope**: fix milestones can be single-phase (3 tasks, 1 day execution)

### Key Lessons
1. **Enable verifier in config** — `verifier_enabled: false` saves time but weakens audit confidence; the 3rd source (VERIFICATION.md) provides independent code verification that SUMMARY frontmatter cannot
2. **Audit status routing**: `tech_debt` → `complete-milestone`; `gaps_found` → `plan-milestone-gaps`. Users may not intuitively distinguish these.
3. **httpx client lifecycle in HA**: `get_async_client(hass)` returns a singleton managed by HA; never pass it as async context manager, never close it manually

### Cost Observations
- Model mix: ~100% sonnet
- Sessions: 1
- Notable: Single-day execution — milestones scoped to one fix are very efficient

---

## Milestone: v1.2 — SunSpec/Modbus Local API

**Shipped:** 2026-03-01
**Phases:** 5 (4-8) | **Plans:** 7 | **Sessions:** ~4

### What Was Built
- `SunSpecModbusClient` class reads SunSpec Models 502/701/713/714 using pySunSpec2 in a thread executor — all Modbus I/O non-blocking
- Config flow and options flow wired for Modbus TCP host/port/slave ID; local mode togglable without cloud credential re-entry
- Hybrid coordinator: Modbus for real-time power flow (10s interval), cloud for energy totals (kWh) and all write operations
- Graceful degradation: Modbus failures fall back to cloud automatically; startup unaffected if Modbus unreachable
- Two bug-closure phases (7, 8) added after audit: first-setup options read, async executor misuse, options update listener, grid polarity double-inversion

### What Worked
- Per-phase VERIFICATION.md files (enabled this milestone) caught static code correctness early — verifier found issues Phase 5 static verification missed
- Integration checker at milestone audit found two cross-phase bugs (MCONF-02, MDATA-04) that static per-phase verification passed — cross-phase wiring analysis is non-negotiable
- Audit → gap-closure phases workflow was clean: audit identified specific bugs, Phases 7+8 closed them precisely
- `gsd-verifier` now generates VERIFICATION.md — 3-source cross-reference works correctly; confidence higher than v1.0/v1.1
- Hybrid data strategy (Modbus current + cloud totals) was the right architectural decision — the two data paths are orthogonal and easy to reason about separately

### What Was Inefficient
- Phase 5 SUMMARY.md files were never written — 0 summaries for 2 plans. Integration kept executing and auditing correctly, but accomplishments were undocumented and milestone tooling reported 0 tasks/accomplishments
- ROADMAP.md listed v1.2 as "Phases 4-6" throughout gap-closure phases 7+8 — stale header created confusion; roadmap should be updated as phases are added
- First audit identified MCONF-02 and MDATA-04 bugs that should have been caught during Phase 5 static verification — the double-negation bug and missing `add_update_listener` were detectable from code review

### Patterns Established
- **Options-then-data fallback**: `entry.options.get(KEY, entry.data.get(KEY, DEFAULT))` for all config keys read in `async_setup_entry` — required for first-setup vs options-edit parity
- **`add_update_listener` is mandatory**: Register unconditionally after `async_forward_entry_setups` — missing this breaks all options flow changes
- **Single negation for sign normalization**: Coordinator is the canonical sign normalization point; sensor `value_fn` should be sign-neutral — never invert at two layers
- **Gap-closure phases as first-class phases**: Post-audit bug fixes get their own numbered phases (7, 8) — clean execution trail, proper verification

### Key Lessons
1. **Integration checker is essential** — two bugs in this milestone were caught only at cross-phase audit, not per-phase verification. Always run it.
2. **Write SUMMARY.md files for every plan** — Phase 5's missing summaries meant 0 accomplishments recorded; milestone tooling couldn't extract deliverables. The GSD executor should enforce this.
3. **Update ROADMAP.md header when scope expands** — adding gap-closure phases without updating the milestone header ("Phases 4-6") created a misleading record. Update it as you add phases.
4. **`async_add_executor_job` for sync-only** — pySunSpec2 is synchronous; cloud httpx client is async. Never wrap async methods in executor jobs. Check library type before choosing dispatch pattern.

### Cost Observations
- Model mix: ~100% sonnet
- Sessions: ~4
- Notable: The audit → gap closure → re-audit cycle added 2 phases but closed real correctness bugs. Worth the cost. Initial estimate of 3 phases (4-6) grew to 5 due to bugs found at audit.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~3 | 2 | Initial migration — established HACS-compliant structure |
| v1.1 | 1 | 1 | Single-fix milestone — vendoring + session injection |
| v1.2 | ~4 | 5 (planned 3, grew to 5) | Feature milestone — Modbus local API, hybrid data, gap closure |

### Top Lessons (Verified Across Milestones)

1. **Enable verifier** — `verifier_enabled: false` appeared in v1.0 and v1.1; v1.2 enabled it and audit confidence improved significantly. Always on.
2. **Integration checker at audit is non-negotiable** — per-phase static verification cannot catch cross-phase wiring bugs; v1.2 found two (MCONF-02, MDATA-04) only at cross-phase audit
3. **Write SUMMARY.md for every plan** — missing summaries (Phase 5 in v1.2) degrade milestone tooling and milestone records; executor should enforce this
4. Check external service prerequisites (GitHub settings, CI workflow states) during research, not during execution
