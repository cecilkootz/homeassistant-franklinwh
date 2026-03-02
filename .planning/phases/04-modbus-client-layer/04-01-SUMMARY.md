---
phase: 04-modbus-client-layer
plan: "01"
subsystem: manifest
tags: [dependency, pysunspec2, manifest]
dependency_graph:
  requires: []
  provides: [pysunspec2-installed-by-ha]
  affects: [04-02-modbus-client]
tech_stack:
  added: [pysunspec2==1.3.3]
  patterns: []
key_files:
  modified: [custom_components/franklin_wh/manifest.json]
  created: []
decisions:
  - "Use PyPI distribution name pysunspec2 (not sunspec2) in manifest.json requirements — sunspec2 would fail HA pip install"
metrics:
  duration: "2 min"
  completed: "2026-02-28"
---

# Phase 4 Plan 01: Add pysunspec2 Dependency Summary

**One-liner:** Declared pysunspec2==1.3.3 in manifest.json requirements so HA auto-installs it at integration load time.

## What Was Done

Added `"pysunspec2==1.3.3"` to the `requirements` array in `custom_components/franklin_wh/manifest.json`. This is the only change made.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add pysunspec2==1.3.3 to manifest.json requirements | 88236a4 |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- `custom_components/franklin_wh/manifest.json` modified and verified via python3 JSON parse assertion
- Commit 88236a4 exists
