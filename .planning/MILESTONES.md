# Milestones

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

