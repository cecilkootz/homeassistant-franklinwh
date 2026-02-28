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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~3 | 2 | Initial migration — established HACS-compliant structure |
| v1.1 | 1 | 1 | Single-fix milestone — vendoring + session injection |

### Top Lessons (Verified Across Milestones)

1. **Enable verifier** — `verifier_enabled: false` has appeared in both milestones, consistently degrading audit confidence
2. Check external service prerequisites (GitHub settings, CI workflow states) during research, not during execution
3. Single-phase fix milestones execute in one session — scope tightly and ship fast
