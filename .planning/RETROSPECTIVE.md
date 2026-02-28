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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~3 | 2 | Initial migration — established HACS-compliant structure |

### Top Lessons (Verified Across Milestones)

1. Run verify-work after every phase to maintain 3-source audit coverage
2. Check external service prerequisites (GitHub settings, CI workflow states) during research, not during execution
