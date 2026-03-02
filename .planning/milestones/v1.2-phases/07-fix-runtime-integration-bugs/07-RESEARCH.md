# Phase 7: Fix Runtime Integration Bugs - Research

**Researched:** 2026-03-01
**Domain:** Home Assistant config entry data/options lifecycle; Python async/executor patterns
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Bug 1 fix: entry.data / entry.options split (MCONF-01, MDATA-06)**

- In `__init__.py`, read Modbus settings from `entry.options` first (for users who configured via Options Flow after initial setup), then fall back to `entry.data` (for first-setup users who entered Modbus settings in the initial config form)
- Use `.get()` with fallback: `entry.options.get(KEY) or entry.data.get(KEY, DEFAULT)`
- Do NOT restructure the config flow or move Modbus fields between forms — the least-invasive fix wins
- This resolves MCONF-01 (Modbus activates on first setup) and unblocks MDATA-06 (10s interval applies when use_local_api=True)

**Bug 2 fix: async coroutine in executor job (MDATA-07)**

- In `_fetch_cloud_stats_fallback()`, replace `await self.hass.async_add_executor_job(self.client.get_stats)` with `await self.client.get_stats()` directly
- Same for `get_smart_switch_state` — call `await self.client.get_smart_switch_state()` directly
- The franklinwh client methods are already async (1.0.0+); no executor wrapping needed
- Do NOT restructure `_fetch_cloud_stats_fallback()` beyond fixing the async calls — keep the method's existing error handling and fallback logic

### Claude's Discretion

- Exact `.get()` fallback pattern wording (as long as options take priority over data)
- Whether to add a comment explaining the data/options merge rationale
- Test coverage additions are Claude's discretion (add tests if straightforward, skip if complex)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCONF-01 | User can optionally configure a Modbus TCP host, port (default 502), and slave ID (default 1) during initial integration setup | Bug 1 fix: options-with-data-fallback pattern ensures coordinator receives Modbus params whether user configured via initial setup (entry.data) or options flow (entry.options) |
| MDATA-06 | Integration polls Modbus at 10-second interval when local Modbus is enabled | Unblocked by MCONF-01 fix: coordinator's update_interval is already set to DEFAULT_LOCAL_SCAN_INTERVAL when use_local_api=True; fix ensures use_local_api is read correctly on first setup |
| MDATA-07 | Sensors with no Modbus equivalent (energy totals) continue to use cloud data when local Modbus is enabled | Bug 2 fix: removing async_add_executor_job wrapper from async coroutines in _fetch_cloud_stats_fallback() restores energy total retrieval |
</phase_requirements>

## Summary

Phase 7 targets two surgical runtime fixes identified by the v1.2 milestone audit. Both bugs exist as wiring mistakes — correctly designed components connected incorrectly — rather than missing logic. No new features are added.

**Bug 1** (`__init__.py` lines 43–46): Home Assistant's initial config setup flow stores user input in `entry.data`. The options flow stores subsequent changes in `entry.options`. The current code reads Modbus settings exclusively from `entry.options`, which is empty on first setup. Every user who enables Modbus during initial setup silently gets `use_local_api=False`. The fix adds `entry.data` as a fallback: `entry.options.get(KEY, entry.data.get(KEY, DEFAULT))`.

**Bug 2** (`coordinator.py` lines 285 and 292): `_fetch_cloud_stats_fallback()` passes async coroutine functions (`self.client.get_stats`, `self.client.get_smart_switch_state`) to `async_add_executor_job`, which expects a synchronous callable. Both methods are confirmed `async def` in the vendored client (client.py lines 651, 556). The executor receives a coroutine object but does not await it — it returns `None` immediately. The fix is direct `await` calls, matching the pattern used in the non-Modbus code path (coordinator.py lines 145, 159).

**Primary recommendation:** Implement both fixes as a single plan with two tasks. Each fix is 4–5 lines changed. The plan requires no new dependencies, no architectural changes, and no new files.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Home Assistant ConfigEntry | HA 2024.x+ | Config entry data/options lifecycle | Built-in HA API; entry.data and entry.options are the canonical storage split |
| Python asyncio | 3.12 | Async coroutine execution | Native; `await coroutine()` is the correct pattern for async methods |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| franklinwh vendored client | 1.0.0+ | Cloud API calls | All cloud data fetches; methods are async |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| options-with-data-fallback | Migrate entry.data to entry.options in async_migrate_entry | Migration is correct long-term but requires version bumping, is more code, and is out of scope for this targeted fix |
| Direct await of async methods | Run sync equivalents in executor | No sync equivalents exist in the vendored client; adding them would be more invasive than the fix |

## Architecture Patterns

### Home Assistant entry.data vs entry.options Lifecycle

**What:** When a config entry is first created via `async_step_user`, HA stores the result in `entry.data`. The data dict is immutable after creation. When the user changes settings via the Options Flow (`async_step_init`), HA stores the result in `entry.options`. Options are updated on each options flow save. On first setup, `entry.options` is always empty (`{}`).

**Pattern for reading with fallback:**
```python
# entry.options takes priority (updated by options flow)
# entry.data is fallback (populated at initial setup)
use_local_api = entry.options.get(CONF_USE_LOCAL_API, entry.data.get(CONF_USE_LOCAL_API, False))
local_host = entry.options.get(CONF_LOCAL_HOST, entry.data.get(CONF_LOCAL_HOST))
local_port = entry.options.get(CONF_LOCAL_PORT, entry.data.get(CONF_LOCAL_PORT, DEFAULT_LOCAL_PORT))
local_slave_id = entry.options.get(CONF_LOCAL_SLAVE_ID, entry.data.get(CONF_LOCAL_SLAVE_ID, DEFAULT_LOCAL_SLAVE_ID))
```

**Why this pattern:** Options flow users who change settings get options priority. First-setup users who have no options yet get their initial data values. No data migration required.

### Async Coroutine vs Executor Job

**What:** `hass.async_add_executor_job(fn, *args)` runs a synchronous blocking function `fn` in a thread pool. It must receive a callable (not a coroutine). If `fn` is an `async def` function, calling it produces a coroutine object. The executor runs the coroutine object in a thread, but the coroutine is never awaited — it returns `None` immediately.

**Correct pattern for async client methods:**
```python
# WRONG: async function passed to executor
stats = await self.hass.async_add_executor_job(self.client.get_stats)

# CORRECT: async method awaited directly on the event loop
stats = await self.client.get_stats()
```

**When to use executor:** Only for synchronous blocking I/O (e.g., pySunSpec2 Modbus reads, file I/O). The franklinwh cloud client uses httpx async HTTP — it belongs on the event loop, not in the executor.

### Existing Correct Pattern (coordinator.py lines 144–159)

The non-Modbus path in `_async_update_data()` already calls these methods correctly:
```python
# coordinator.py line 145 — correct pattern
stats = await self.client.get_stats()

# coordinator.py line 159 — correct pattern
switch_state = await self.client.get_smart_switch_state()
```

`_fetch_cloud_stats_fallback()` should mirror this pattern exactly.

### Anti-Patterns to Avoid

- **Wrapping async methods in executor:** Causes silent None return or TypeError; no exception unless the coroutine raises before the event loop discards it.
- **Reading only entry.options for Modbus config:** On first setup, options is empty; coordinator silently disables Modbus even when user explicitly configured it.
- **Restructuring config flow to store to entry.options:** Out of scope; requires migration handling and version bumping.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Options/data priority merge | Custom migration logic | Two-level `.get()` chain | Migration adds version complexity and is unnecessary for this fix scope |
| Async detection at runtime | isinstance(fn, Coroutine) checks | Always call async methods with await directly | Runtime type checking is fragile; the fix is knowing which methods are async |

## Common Pitfalls

### Pitfall 1: Partial Fix Leaves MDATA-06 Broken

**What goes wrong:** Only fixing the `use_local_api` key in the options/data fallback but forgetting `local_host`, `local_port`, or `local_slave_id`.

**Why it happens:** The MDATA-06 description mentions interval; it's easy to focus on `use_local_api` and overlook that `local_host=None` would also prevent Modbus activation (coordinator checks `if self.use_local_api and self.local_host`).

**How to avoid:** Fix all four Modbus keys (`CONF_USE_LOCAL_API`, `CONF_LOCAL_HOST`, `CONF_LOCAL_PORT`, `CONF_LOCAL_SLAVE_ID`) with the options-first/data-fallback pattern.

**Warning signs:** `use_local_api=True` but `local_host=None` — coordinator's Modbus path is gated by both.

### Pitfall 2: Executor Comment Left in Place

**What goes wrong:** Fixing the code but leaving the `# Fetch stats via executor (HA's httpx is not thread-safe)` comment at coordinator.py line 283.

**Why it happens:** The comment is outdated — httpx in HA is async-safe; the franklinwh client uses async httpx. Leaving the comment creates confusion.

**How to avoid:** Remove or update the misleading comment when fixing the two executor calls.

### Pitfall 3: Breaking the Fallback's None-Return Contract

**What goes wrong:** During the fix, accidentally removing a `try/except` block or letting exceptions propagate.

**Why it happens:** `_fetch_cloud_stats_fallback()` has a documented contract: never raises, returns `None` on failure. The fix must preserve the outer try/except structure while only removing the executor wrapper from the inner calls.

**How to avoid:** Change only lines 285 and 292. Leave all surrounding try/except blocks intact.

## Code Examples

Verified patterns from the codebase and HA conventions:

### Bug 1: Correct options-with-data-fallback (to replace __init__.py lines 43–46)

```python
# Source: audit recommendation + HA ConfigEntry docs pattern
# Read from entry.options first (options flow users), fall back to entry.data (first-setup users)
use_local_api = entry.options.get(CONF_USE_LOCAL_API, entry.data.get(CONF_USE_LOCAL_API, False))
local_host = entry.options.get(CONF_LOCAL_HOST, entry.data.get(CONF_LOCAL_HOST))
local_port = entry.options.get(CONF_LOCAL_PORT, entry.data.get(CONF_LOCAL_PORT, DEFAULT_LOCAL_PORT))
local_slave_id = entry.options.get(CONF_LOCAL_SLAVE_ID, entry.data.get(CONF_LOCAL_SLAVE_ID, DEFAULT_LOCAL_SLAVE_ID))
```

### Bug 2: Correct async calls (to replace coordinator.py lines 284–294)

```python
# Source: coordinator.py lines 145/159 — the existing correct pattern in the non-Modbus path
try:
    stats = await self.client.get_stats()
    if stats is None:
        _LOGGER.debug("Cloud stats fetch returned None")
        return None

    switch_state = None
    try:
        switch_state = await self.client.get_smart_switch_state()
    except Exception as err:
        _LOGGER.debug("Failed to fetch switch state: %s", err)

    return FranklinWHData(stats=stats, switch_state=switch_state)
except Exception as err:
    _LOGGER.warning("Cloud fallback fetch failed: %s", err)
    return None
```

### Verification: client methods are async (confirmed in source)

```python
# custom_components/franklin_wh/franklinwh/client.py line 651
async def get_stats(self) -> Stats:

# custom_components/franklin_wh/franklinwh/client.py line 556
async def get_smart_switch_state(self) -> SwitchState:
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync franklinwh client methods | Async client methods (franklinwh 1.0.0+) | Phase 3 vendoring | Executor wrappers are now wrong; direct await is correct |
| entry.options-only read | options-with-data-fallback | This phase | First-setup Modbus config is honored |

## Open Questions

1. **Is there any scenario where entry.options contains an explicit False for use_local_api that should override entry.data?**
   - What we know: Options flow allows disabling Modbus (`use_local_api=False`). If the user disables via options flow, `entry.options[CONF_USE_LOCAL_API]` will be `False`.
   - What's unclear: The two-level `.get()` chain naturally handles this — `entry.options.get(CONF_USE_LOCAL_API, ...)` returns `False` from options, which is correct behavior.
   - Recommendation: No issue. The `or` variant in CONTEXT.md (`entry.options.get(KEY) or entry.data.get(KEY, DEFAULT)`) would short-circuit a legitimate `False` from options to check data instead — use the nested `.get()` form instead: `entry.options.get(KEY, entry.data.get(KEY, DEFAULT))`.

2. **Should the outdated executor comment at coordinator.py line 283 be removed?**
   - What we know: The comment says "Fetch stats via executor (HA's httpx is not thread-safe)" — this is factually wrong for the async franklinwh client.
   - Recommendation: Remove or replace the comment when fixing the two lines below it. Claude's discretion per CONTEXT.md.

## Sources

### Primary (HIGH confidence)

- `custom_components/franklin_wh/franklinwh/client.py` lines 556, 651 — direct inspection confirming `get_stats` and `get_smart_switch_state` are `async def`
- `custom_components/franklin_wh/__init__.py` lines 42–46 — current options-only read (the lines to patch)
- `custom_components/franklin_wh/coordinator.py` lines 145, 159 — existing correct direct-await pattern
- `custom_components/franklin_wh/coordinator.py` lines 283–294 — the executor-wrapped async calls to fix
- `.planning/v1.2-MILESTONE-AUDIT.md` — authoritative description of both bugs with exact line numbers and evidence

### Secondary (MEDIUM confidence)

- HA developer docs pattern: `entry.data` = initial setup, `entry.options` = options flow; options-with-data-fallback is a common HA integration pattern for this scenario

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by direct source inspection, no external libraries involved
- Architecture: HIGH — both bugs diagnosed from source code; both fixes match existing correct patterns in the same file
- Pitfalls: HIGH — derived from static analysis of the code and audit evidence

**Research date:** 2026-03-01
**Valid until:** Stable (no fast-moving dependencies; pure bug fix)
