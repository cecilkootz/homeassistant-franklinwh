# Phase 7: Fix Runtime Integration Bugs - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix two specific runtime bugs identified in the v1.2 milestone audit that prevent Modbus from activating on first setup and energy totals from working in hybrid mode. No new features — correcting broken wiring in existing code.

</domain>

<decisions>
## Implementation Decisions

### Bug 1 fix: entry.data / entry.options split (MCONF-01, MDATA-06)

- In `__init__.py`, read Modbus settings from `entry.options` first (for users who configured via Options Flow after initial setup), then fall back to `entry.data` (for first-setup users who entered Modbus settings in the initial config form)
- Use `.get()` with fallback: `entry.options.get(KEY) or entry.data.get(KEY, DEFAULT)`
- Do NOT restructure the config flow or move Modbus fields between forms — the least-invasive fix wins
- This resolves MCONF-01 (Modbus activates on first setup) and unblocks MDATA-06 (10s interval applies when use_local_api=True)

### Bug 2 fix: async coroutine in executor job (MDATA-07)

- In `_fetch_cloud_stats_fallback()`, replace `await self.hass.async_add_executor_job(self.client.get_stats)` with `await self.client.get_stats()` directly
- Same for `get_smart_switch_state` — call `await self.client.get_smart_switch_state()` directly
- The franklinwh client methods are already async (1.0.0+); no executor wrapping needed
- Do NOT restructure `_fetch_cloud_stats_fallback()` beyond fixing the async calls — keep the method's existing error handling and fallback logic

### Claude's Discretion

- Exact `.get()` fallback pattern wording (as long as options take priority over data)
- Whether to add a comment explaining the data/options merge rationale
- Test coverage additions are Claude's discretion (add tests if straightforward, skip if complex)

</decisions>

<specifics>
## Specific Ideas

- Both fixes are surgical — change as few lines as possible
- The v1.2 audit evidence (`v1.2-MILESTONE-AUDIT.md`) is the source of truth for what's broken and why

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `__init__.py:42-46`: Current options-only read (the lines to patch)
- `coordinator.py:260-304`: `_fetch_cloud_stats_fallback()` (the method to patch)
- `coordinator.py:283-294`: The two executor-wrapped async calls to fix

### Established Patterns
- `entry.options.get(KEY, DEFAULT)` pattern already used throughout `config_flow.py` and `__init__.py`
- Async client methods called directly with `await` in the main `_async_update_data()` path (lines 145, 159) — fallback should match this pattern

### Integration Points
- `__init__.py` → `FranklinWHCoordinator.__init__()`: passes `use_local_api`, `local_host`, `local_port`, `local_slave_id`
- `coordinator.py` → `_fetch_cloud_stats_fallback()`: called from `_async_update_data()` Modbus path (line 121)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-fix-runtime-integration-bugs*
*Context gathered: 2026-03-01*
