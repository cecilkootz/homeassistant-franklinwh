# Phase 8: Fix Options Listener and Grid Sensor Polarity - Research

**Researched:** 2026-03-01
**Domain:** Home Assistant config entry options lifecycle, sensor sign convention normalization
**Confidence:** HIGH

---

## Summary

Phase 8 closes two critical integration bugs identified by the v1.2 milestone audit. Both bugs are surgical, well-understood, and have exact fixes already documented in the audit report. No new libraries, patterns, or architectural decisions are required.

**Bug 1 (MCONF-02):** `async_setup_entry` in `__init__.py` never registers `async_reload_entry` as an options update listener. When the user saves new options (e.g., toggling "Use local Modbus" off), `entry.options` is updated but the running coordinator is never notified. The coordinator keeps its stale `use_local_api=True` and continues polling Modbus at 10-second intervals indefinitely. Fix: one line — `entry.add_update_listener(async_reload_entry)` added to `async_setup_entry` after storing the coordinator.

**Bug 2 (MDATA-04):** `grid_use` has a double sign inversion: `coordinator.py:233` negates `grid_ac_power` during mapping (`grid_use = -sunspec_data.grid_ac_power / 1000.0`), and `sensor.py:99` negates again (`grid_use * -1`). The two negations cancel in the cloud path by coincidence (cloud data is already sign-normalized), but in the Modbus path the double inversion causes the sensor to show the wrong polarity. Fix: remove the `* -1` from `sensor.py:99`. The coordinator's single negation becomes the canonical sign normalization for both paths.

**Primary recommendation:** Execute both fixes sequentially in a single plan; each is 1–3 lines of code with clear before/after state. No refactoring, no new patterns, no new dependencies.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCONF-02 | User can enable or disable local Modbus mode via the options flow without re-entering cloud credentials | `entry.add_update_listener(async_reload_entry)` registration in `async_setup_entry` is the complete fix. `async_reload_entry` already exists at `__init__.py:156`. |
| MDATA-04 | Integration reads grid AC power from SunSpec Model 701 when local Modbus is enabled | Remove `* -1` from `sensor.py:99`. `coordinator.py:233` already applies the correct single negation. Both cloud and Modbus paths will then produce `grid_use` with consistent sign convention. |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.config_entries.ConfigEntry` | HA built-in | Options listener registration via `entry.add_update_listener()` | The HA-native pattern for reacting to options flow saves |

### Supporting

No new libraries required. This phase only modifies existing code in `__init__.py` and `sensor.py`.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `entry.add_update_listener(async_reload_entry)` | A custom options listener that reconstructs the coordinator in-place | Full reload (unload + setup) is simpler, idiomatic, already implemented in `async_reload_entry`. In-place reconstruction would require resetting coordinator state, reconnecting Modbus, etc. — not worth the complexity. |
| Remove `* -1` in `sensor.py` | Remove negation in `coordinator.py:233` instead | Removing from `sensor.py` is safer: the coordinator negation is intentional (cloud data comes with positive = export, and cloud path also applies `* -1` in `sensor.py`, so changing the coordinator would break the cloud path). Removing from `sensor.py` makes the sensor layer sign-neutral and keeps normalization in the coordinator. |

**Installation:** None required.

---

## Architecture Patterns

### Pattern 1: HA Options Update Listener Registration

**What:** `ConfigEntry.add_update_listener(listener)` registers an async callback that HA calls whenever the options flow saves new options. The listener receives `(hass, entry)`. The standard idiom for HA integrations is to reload the entire entry on options change.

**When to use:** Whenever an integration's coordinator or runtime state must respond to options flow changes.

**Example:**
```python
# In async_setup_entry, after coordinator is stored:
entry.add_update_listener(async_reload_entry)
```

The listener signature HA expects:
```python
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
```

This function already exists at `__init__.py:156–159`. Only the registration call is missing.

**Confidence:** HIGH — this is the canonical HA pattern, used across the HA codebase. The function signature matches what `add_update_listener` expects.

### Pattern 2: Single Sign-Normalization Point

**What:** Normalization of raw hardware values (sign, unit conversion) should happen in exactly one layer. For this integration, the coordinator's `_map_sunspec_to_stats_current()` is the normalization layer. Sensors must be sign-neutral.

**Current broken state:**
- `coordinator.py:233`: `grid_use = -sunspec_data.grid_ac_power / 1000.0` (single inversion — correct)
- `sensor.py:99`: `value_fn = lambda data: data.stats.current.grid_use * -1` (second inversion — breaks Modbus path)

**Why the cloud path worked by coincidence:** The cloud path's `grid_use` field is already in the "positive = consumption from grid" convention when it arrives from the FranklinWH cloud API. The `* -1` in `sensor.py` was likely added to match a display convention but was only correct for cloud data. When Modbus data is mapped through `_map_sunspec_to_stats_current()`, the coordinator already applies the single negation to match the cloud convention, so the sensor's second `* -1` inverts it again — wrong.

**Fix:** Remove `* -1` from `sensor.py:99`. The sensor becomes:
```python
value_fn=lambda data: data.stats.current.grid_use if data.stats else None,
```

The coordinator `grid_use = -sunspec_data.grid_ac_power / 1000.0` stays unchanged and is now the sole normalization point.

**Verification:** After this fix, grid import (consuming from grid) must show as negative `grid_ac_power` in SunSpec (positive = export), which becomes positive after negation in coordinator, which the sensor reports as-is (positive = importing). Confirm this matches the cloud-path behavior.

**Confidence:** HIGH — the audit provides a precise line-by-line diagnosis and the fix is unambiguous.

### Anti-Patterns to Avoid

- **Touching `_map_sunspec_to_stats_current()` sign logic:** The coordinator's single negation at line 233 is correct and must not be changed. Only `sensor.py` changes.
- **Adding the listener inside a conditional:** `entry.add_update_listener(async_reload_entry)` must be called unconditionally in `async_setup_entry`. Do not guard it behind `if use_local_api`.
- **Double-registering the listener:** `add_update_listener` returns a callable to de-register. In this integration pattern (reload-based), the listener is re-registered on each reload via a fresh `async_setup_entry`, which is correct behavior. No manual de-registration is needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Notifying coordinator of options changes | Custom pub/sub, polling entry.options periodically, hass.bus listeners | `entry.add_update_listener()` | HA handles the callback lifecycle; built-in, one line |
| Reconstructing coordinator in-place after options change | Resetting coordinator attributes at runtime | Full entry reload via `async_reload_entry` | Simpler, correct, already implemented |

---

## Common Pitfalls

### Pitfall 1: Forgetting the Listener Registration is Not Persisted

**What goes wrong:** Developer adds `entry.add_update_listener()` only in a conditional path, or assumes HA auto-registers it.
**Why it happens:** Nothing in HA auto-registers listeners; every integration must call `add_update_listener` explicitly.
**How to avoid:** Place the call unconditionally in `async_setup_entry`, after the coordinator is stored and platforms are set up.
**Warning signs:** Options flow saves without triggering a coordinator reload — entities retain stale state.

### Pitfall 2: Removing the Wrong Negation (Breaking the Cloud Path)

**What goes wrong:** Developer removes the negation from `coordinator.py:233` instead of `sensor.py:99`, which breaks the cloud path.
**Why it happens:** The double-negation is subtle; either removal appears to "fix" the Modbus path in isolation.
**How to avoid:** Understand which path each layer serves. The coordinator maps both cloud and Modbus data through `_map_sunspec_to_stats_current()` for Modbus only. The cloud path's `grid_use` arrives pre-normalized. The `sensor.py` `* -1` was the "extra" negation that only worked for cloud because cloud data didn't need coordinator re-mapping.
**Warning signs:** After the fix, run both code paths mentally — cloud `grid_use` from API → sensor (no extra negation) = correct positive value when consuming; Modbus `grid_ac_power` → coordinator negation → `grid_use` → sensor (no extra negation) = correct positive value when consuming.

### Pitfall 3: Listener Signature Mismatch

**What goes wrong:** Passing a listener with the wrong signature to `add_update_listener`.
**Why it happens:** HA expects `async def listener(hass: HomeAssistant, entry: ConfigEntry) -> None`.
**How to avoid:** `async_reload_entry` at `__init__.py:156` already has this exact signature. No changes to the function are needed.

---

## Code Examples

### Fix 1: Register Options Listener (MCONF-02)

Current `async_setup_entry` in `__init__.py` (relevant section):
```python
# Store coordinator
hass.data.setdefault(DOMAIN, {})
hass.data[DOMAIN][entry.entry_id] = coordinator

# Set up platforms
await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

After fix — add one line after platform setup:
```python
# Store coordinator
hass.data.setdefault(DOMAIN, {})
hass.data[DOMAIN][entry.entry_id] = coordinator

# Set up platforms
await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

# Register options update listener so coordinator reloads when options change
entry.add_update_listener(async_reload_entry)
```

`async_reload_entry` already exists at `__init__.py:156`:
```python
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
```

No changes to `async_reload_entry` are needed.

### Fix 2: Remove Double Negation (MDATA-04)

Current `sensor.py:99` (grid_use sensor):
```python
FranklinWHSensorEntityDescription(
    key="grid_use",
    name="Grid Use",
    native_unit_of_measurement=UnitOfPower.KILO_WATT,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda data: data.stats.current.grid_use * -1 if data.stats else None,
),
```

After fix — remove `* -1`:
```python
FranklinWHSensorEntityDescription(
    key="grid_use",
    name="Grid Use",
    native_unit_of_measurement=UnitOfPower.KILO_WATT,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda data: data.stats.current.grid_use if data.stats else None,
),
```

`coordinator.py:233` stays unchanged:
```python
grid_use=-sunspec_data.grid_ac_power / 1000.0,
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No options listener | `entry.add_update_listener()` | HA introduced options flows | Integrations that don't register a listener silently ignore options changes |
| Sign normalization split across layers | Single normalization in coordinator | Phase 8 | Sensor layer becomes sign-neutral; both data paths produce consistent output |

---

## Open Questions

1. **Does removing `* -1` from `grid_use` sensor break the cloud path?**
   - What we know: Cloud path `grid_use` field from the FranklinWH API arrives pre-normalized (positive = consumption). The `sensor.py * -1` was inverting a value that was already in the correct sign. Removing it should be correct.
   - What's unclear: The original author may have intended `* -1` for a specific cloud API convention. No test coverage exists to validate.
   - Recommendation: After the fix, document the expected sign convention explicitly in a comment in `_map_sunspec_to_stats_current()` so future developers understand the normalization contract. Manual verification against a live device or known cloud API sample is the definitive test.

2. **Should `battery_use` sensor's `* -1` at `sensor.py:54` also be reviewed?**
   - What we know: `sensor.py:54` applies `battery_use * -1`. The coordinator maps `battery_use = sunspec_data.battery_dc_power / 1000.0` (no negation). SunSpec Model 714 positive = discharge. The `* -1` in the sensor converts discharge-positive to charge-positive for display.
   - What's unclear: Whether this matches the cloud API convention for `battery_use`.
   - Recommendation: Out of scope for Phase 8 (MDATA-04 specifically targets `grid_use`). Flag as a future verification item but do not change in this phase.

---

## Validation Architecture

> `nyquist_validation` is `false` in `.planning/config.json` — this section is skipped.

---

## Sources

### Primary (HIGH confidence)

- `.planning/v1.2-MILESTONE-AUDIT.md` — authoritative diagnosis of both bugs, exact line numbers, exact fix instructions
- `custom_components/franklin_wh/__init__.py` — direct code inspection, confirmed `async_reload_entry` exists at line 156, `add_update_listener` call absent from `async_setup_entry`
- `custom_components/franklin_wh/coordinator.py:233` — confirmed `grid_use = -sunspec_data.grid_ac_power / 1000.0`
- `custom_components/franklin_wh/sensor.py:99` — confirmed `value_fn=lambda data: data.stats.current.grid_use * -1`
- `custom_components/franklin_wh/sunspec_client.py` — confirmed `grid_ac_power` docstring: "positive = export to grid, negative = import from grid (SunSpec Model 701 convention)"
- `.planning/phases/07-fix-runtime-integration-bugs/07-01-SUMMARY.md` — confirmed Phase 7 completed; current codebase state is post-Phase-7

### Secondary (MEDIUM confidence)

- HA developer documentation pattern for `entry.add_update_listener()` — standard HA options integration pattern, confirmed by codebase inspection of how `async_reload_entry` is structured

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; both fixes use existing HA and project patterns
- Architecture: HIGH — bugs and fixes are precisely documented in the audit with line-level specificity
- Pitfalls: HIGH — double-negation and missing listener registration are concrete, verifiable issues

**Research date:** 2026-03-01
**Valid until:** Stable indefinitely (fixes are surgical; no external dependencies change)
