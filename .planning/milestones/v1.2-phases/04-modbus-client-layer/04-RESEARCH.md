# Phase 4: Modbus Client Layer - Research

**Researched:** 2026-02-28
**Domain:** pySunSpec2 Modbus TCP client, SunSpec DER models, Home Assistant executor pattern
**Confidence:** MEDIUM — core library API verified via official source code; model 502 identity is a critical open question

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

User deferred all implementation decisions to Claude. The following are standard approaches the planner should apply:

- **Connection lifecycle** — Use connect/disconnect per read (simpler, more resilient for infrequent polling). Persistent connections are an optimization for Phase 5+ if needed.
- **Failure contract** — Raise exceptions on Modbus failure. Let the coordinator (Phase 5) handle retry/fallback logic, consistent with the existing consecutive-failure pattern in `coordinator.py`.
- **Unit & sign normalization** — Return values in watts (W) as floats, using SunSpec sign conventions (discharge/export positive). Document the sign convention clearly in code. The home_load formula is fixed: `solar_power + battery_dc_power - grid_ac_power`.
- **sunspec2 usage mode** — Target models directly by address rather than auto-discovery scans. Faster, more predictable for a known device.
- **File placement** — New file `custom_components/franklin_wh/sunspec_client.py` containing `SunSpecModbusClient` class and a `SunSpecData` dataclass for the return type.

### Claude's Discretion

None — all decisions locked.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MDATA-01 | Integration reads battery state of charge from SunSpec Model 713 when local Modbus is enabled | Model 713 (DER Storage Capacity) confirmed in FranklinWH registry; SoC point name is `SoC`, units Pct, use `.cvalue` for scale-factor-applied float |
| MDATA-02 | Integration reads battery DC power (charge/discharge) from SunSpec Model 714 when local Modbus is enabled | Model 714 (DER DC Measurement) confirmed in FranklinWH registry; DC power is in a repeating port group; point name is `DCW`, units W, use `.cvalue` |
| MDATA-03 | Integration reads solar production power from SunSpec Model 502 when local Modbus is enabled | OPEN QUESTION: FranklinWH registry lists models 1 and 701-715 only; model 502 is not registered. See Open Questions section. |
| MDATA-04 | Integration reads grid AC power from SunSpec Model 701 when local Modbus is enabled | Model 701 (DERMeasureAC) confirmed in FranklinWH registry; total AC power point is `W`, units W, positive = generation/export, use `.cvalue` |
| MDATA-05 | Integration calculates home load as `solar_power + battery_dc_power - grid_ac_power` | Formula is fixed per user decision; computed in `SunSpecData` dataclass |
</phase_requirements>

## Summary

Phase 4 builds a standalone `SunSpecModbusClient` class in a new file `custom_components/franklin_wh/sunspec_client.py`. The library is `pysunspec2` (PyPI distribution name) version 1.3.3, imported as `sunspec2`. The HA manifest.json requirements entry must use the PyPI distribution name `pysunspec2==1.3.3`, not `sunspec2`.

The practical implementation of "target models directly" requires an initial `scan(full_model_read=False)` call to discover model addresses (this is how pySunSpec2 works — it must build the models dict before targeted reads), followed by individual `model.read()` calls per model. The `ha-sunspec` reference integration (CJNE/ha-sunspec) uses exactly this pattern. All blocking calls run via `hass.async_add_executor_job()`.

There is a critical open question about model 502: FranklinWH's SunSpec Alliance registry entry lists models 1 and 701-715 only — model 502 ("Solar Module", a DC-DC converter) is not registered. Solar production data from the FranklinWH aGate likely comes from a different model in the 701-715 range. The planner must handle this as a discovery-at-runtime concern: implement the client to attempt model 502 first, and document that if it is absent after scan, the model must be identified via device scan on real hardware.

**Primary recommendation:** Use `pysunspec2==1.3.3`, run `scan(full_model_read=False)` once per read cycle (connect → scan → read models → disconnect), raise exceptions on failure, and flag the model 502 uncertainty as a known risk in code comments.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pysunspec2 | 1.3.3 | SunSpec Modbus TCP client — device discovery, model reads, scale factor math | Official SunSpec Alliance Python library; only production-grade SunSpec client for Python |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python dataclasses | stdlib | `SunSpecData` typed return object | Already used in project (`FranklinWHData`); zero dependencies |
| asyncio executor | stdlib (via HA) | Run blocking pySunSpec2 calls off event loop | Mandatory for HA integrations with blocking I/O |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pysunspec2 | pymodbus directly | pysunspec2 handles scale factors, model definitions, and SunSpec-specific framing; pymodbus is raw registers and requires hand-rolling all of that |
| pysunspec2 | homeassistant.components.modbus | HA built-in Modbus only does raw register reads; no SunSpec model awareness |

**Installation (PyPI):**
```bash
pip install pysunspec2==1.3.3
```

**manifest.json entry:**
```json
"requirements": ["pysunspec2==1.3.3"]
```

Note: The import path is `import sunspec2.modbus.client as modbus_client` — the PyPI distribution name (`pysunspec2`) differs from the importable package name (`sunspec2`).

## Architecture Patterns

### Recommended Project Structure

```
custom_components/franklin_wh/
├── sunspec_client.py    # NEW: SunSpecModbusClient class + SunSpecData dataclass
├── coordinator.py       # EXISTING: will import SunSpecModbusClient in Phase 5
├── const.py             # EXISTING: will add CONF_LOCAL_PORT, CONF_LOCAL_SLAVE_ID in Phase 5
└── manifest.json        # EXISTING: add pysunspec2==1.3.3 to requirements
```

### Pattern 1: Connect-per-Read with Executor

The CONTEXT.md decision specifies connect/disconnect per read cycle for simplicity and resilience.

```python
# Source: pySunSpec2 official README + ha-sunspec api.py (verified)
import sunspec2.modbus.client as modbus_client
from sunspec2.modbus.client import (
    SunSpecModbusClientError,
    SunSpecModbusClientTimeout,
    SunSpecModbusClientException,
)

def _read_sunspec_blocking(host: str, port: int, slave_id: int) -> SunSpecData:
    """Blocking Modbus read — must run in executor."""
    device = modbus_client.SunSpecModbusClientDeviceTCP(
        slave_id=slave_id,
        ipaddr=host,
        ipport=port,
    )
    try:
        device.connect()
        # full_model_read=False: discover addresses without reading all data
        device.scan(connect=False, full_model_read=False)

        # Read each required model
        device.models[713][0].read()
        device.models[714][0].read()
        device.models[701][0].read()
        device.models[502][0].read()  # See Open Questions

        return _extract_data(device)
    finally:
        device.disconnect()

async def read_data(self) -> SunSpecData:
    """Async wrapper — calls blocking read in executor."""
    return await self._hass.async_add_executor_job(
        _read_sunspec_blocking, self._host, self._port, self._slave_id
    )
```

### Pattern 2: Point Value Extraction

```python
# Source: pySunSpec2 README (verified — cvalue applies scale factor)
# .cvalue = computed value (scale factor applied) → use for physical units
# .value  = raw register value → do not use for watts/percent

battery_soc: float = device.models[713][0].SoC.cvalue    # Pct, 0-100
battery_dc_power: float = device.models[714][0].groups["DCSrc"][0].DCW.cvalue  # W
grid_ac_power: float = device.models[701][0].W.cvalue     # W, positive=export
solar_power: float = device.models[502][0].OutPw.cvalue   # W (if model 502 exists)
```

Note on model 714 group access: Model 714 has a repeating port group. The DC power point `DCW` is inside the port group (named `DCSrc` or similar — exact group name must be verified against the device). The model-level `DCW` point (if present) provides a summed total; prefer that if available. Must validate against real hardware.

### Pattern 3: SunSpecData Dataclass

```python
# Source: project pattern — matches existing FranklinWHData in coordinator.py
from dataclasses import dataclass

@dataclass
class SunSpecData:
    """Typed result from SunSpecModbusClient.read()."""
    battery_soc: float          # Percent, 0-100
    battery_dc_power: float     # Watts; positive=discharge (SunSpec convention)
    solar_power: float          # Watts; positive=production
    grid_ac_power: float        # Watts; positive=export (SunSpec convention)
    home_load: float            # Watts; computed: solar + battery_dc - grid_ac
```

### Anti-Patterns to Avoid

- **Calling modbus_client methods on the HA event loop directly:** pySunSpec2 is synchronous blocking I/O. Any `device.connect()`, `device.scan()`, or `model.read()` call outside an executor will freeze the HA event loop.
- **Using `.value` instead of `.cvalue`:** `.value` returns the raw integer register value before scale factor application. Power readings in watts require `.cvalue` to get the physically correct float.
- **Assuming model 502 is present:** FranklinWH's registered SunSpec models are 1 and 701-715. Model 502 may not appear after scan. The client must handle `KeyError` on `device.models[502]` gracefully.
- **Persistent connections without reconnect logic:** This phase uses connect-per-read. Persistent connections require timeout/reconnect handling and are deferred to Phase 5+.
- **Using `sunspec2` as the manifest.json requirement:** The PyPI distribution name is `pysunspec2`. Using the import name `sunspec2` will fail HA's pip install step.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scale factor arithmetic | Custom register × scale_factor math | `point.cvalue` | SunSpec scale factors are signed integers; overflow and special values require SunSpec-spec-compliant handling that pySunSpec2 implements |
| Model address discovery | Hardcoded register addresses | `device.scan()` | SunSpec base addresses can be 0, 40000, or 50000; model lengths vary by firmware; scan handles all of this |
| Modbus frame construction | Raw socket or struct packing | `sunspec2.modbus.client` | Modbus TCP framing, transaction IDs, function codes — all error-prone to hand-roll |
| Type coercion from registers | uint16/int16 bit manipulation | pySunSpec2 model objects | Models define point types (uint16, int16, float32, enum16); library handles all conversions |

**Key insight:** SunSpec data is useless without scale factors applied. A power reading might be `1500` raw but `15.0` W or `150.0` W or `1500.0` W depending on the scale factor point. Always use `.cvalue`.

## Common Pitfalls

### Pitfall 1: PyPI Name vs Import Name Mismatch

**What goes wrong:** `manifest.json` lists `"sunspec2==1.3.3"` instead of `"pysunspec2==1.3.3"`. HA's pip install step fails silently or raises "No matching distribution found."

**Why it happens:** The importable Python package is `sunspec2` but the PyPI distribution is `pysunspec2` — inconsistent naming is unusual and easily missed.

**How to avoid:** In `manifest.json` requirements, use the PyPI distribution name: `"pysunspec2==1.3.3"`. In Python source code, import with: `import sunspec2.modbus.client`.

**Warning signs:** HA logs "No matching distribution found for sunspec2" at integration load time.

### Pitfall 2: Model 502 Not Present on FranklinWH

**What goes wrong:** Code calls `device.models[502][0].read()` but model 502 is not in the device's model map; raises `KeyError` or `IndexError`.

**Why it happens:** FranklinWH's SunSpec Alliance registry entry lists models 1 and 701-715. Model 502 ("Solar Module") is a DC-DC converter module model and is not registered for the aGate device.

**How to avoid:** After scan, check `502 in device.models` before accessing. Treat absent model as an unresolvable data gap and raise an informative exception. The correct model for solar production must be confirmed with real hardware scan output.

**Warning signs:** `device.models` after scan does not contain key `502`.

### Pitfall 3: Model 714 DC Power in Repeating Group

**What goes wrong:** Code accesses `device.models[714][0].DCW.cvalue` at the model level, but DCW inside the port group (repeating) is different from the model-level DCW. May return None or wrong value.

**Why it happens:** Model 714 has both a model-level `DCW` (sum) and per-port `DCW` inside a repeating group. The model-level summed value is what this integration needs, but it may be None if the device only populates per-port values.

**How to avoid:** After `model.read()`, check `device.models[714][0].DCW.cvalue` first; if None, iterate `device.models[714][0].groups['DCSrc']` and sum port-level DCW values. Must validate on real hardware.

**Warning signs:** `device.models[714][0].DCW.cvalue` returns `None` after a successful read.

### Pitfall 4: sign Convention Confusion

**What goes wrong:** Code negates values or applies wrong sign, producing inverted battery/grid readings in HA.

**Why it happens:** SunSpec 701 convention: `W` is positive for DER generation (export) and negative for absorption (import). Battery model 714: `DCW` is positive for discharge. These are the native SunSpec signs and must pass through as-is.

**How to avoid:** Do not negate any value. The `home_load` formula `solar_power + battery_dc_power - grid_ac_power` is already defined per project decision to match SunSpec sign conventions. Document the conventions in code comments.

### Pitfall 5: Blocking I/O on Event Loop

**What goes wrong:** `device.scan()` or `model.read()` is called directly in an `async def` method without executor wrapping, causing HA event loop to block (freezes all integrations for the duration of the Modbus TCP round-trip).

**Why it happens:** pySunSpec2 is a synchronous blocking library. Developers unfamiliar with HA async patterns call blocking functions directly.

**How to avoid:** Wrap the entire read sequence (connect → scan → read models → disconnect → extract data) in a single synchronous function, then dispatch it once via `await hass.async_add_executor_job(func)`. Do not `await` inside the blocking function.

## Code Examples

Verified patterns from official sources and ha-sunspec reference implementation:

### Full Client Structure

```python
# Source: ha-sunspec api.py (GitHub: CJNE/ha-sunspec, verified 2026-02-28)
#         pySunSpec2 README.rst (GitHub: sunspec/pysunspec2, verified 2026-02-28)

from __future__ import annotations

import logging
from dataclasses import dataclass

import sunspec2.modbus.client as modbus_client
from sunspec2.modbus.client import (
    SunSpecModbusClientError,
    SunSpecModbusClientTimeout,
    SunSpecModbusClientException,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SunSpecData:
    """Typed result from a SunSpecModbusClient read cycle."""
    battery_soc: float       # Percent (0-100)
    battery_dc_power: float  # Watts; positive = discharge (SunSpec convention)
    solar_power: float       # Watts; positive = production
    grid_ac_power: float     # Watts; positive = export (SunSpec convention)
    home_load: float         # Watts; computed: solar + battery_dc - grid_ac


class SunSpecModbusClient:
    """Standalone SunSpec Modbus TCP client for FranklinWH aGate."""

    def __init__(self, host: str, port: int, slave_id: int) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id

    def _read_blocking(self) -> SunSpecData:
        """Blocking Modbus read. Must be called from executor, never event loop."""
        device = modbus_client.SunSpecModbusClientDeviceTCP(
            slave_id=self._slave_id,
            ipaddr=self._host,
            ipport=self._port,
        )
        try:
            device.connect()
            # full_model_read=False: discover model addresses without reading data yet
            device.scan(connect=False, full_model_read=False)

            # Read each required model (raises SunSpecModbusClientError on failure)
            device.models[713][0].read()
            device.models[714][0].read()
            device.models[701][0].read()
            device.models[502][0].read()  # WARNING: may not exist — see Open Questions

            battery_soc = float(device.models[713][0].SoC.cvalue)
            battery_dc_power = float(device.models[714][0].DCW.cvalue)  # may need group access
            grid_ac_power = float(device.models[701][0].W.cvalue)
            solar_power = float(device.models[502][0].OutPw.cvalue)

            home_load = solar_power + battery_dc_power - grid_ac_power

            return SunSpecData(
                battery_soc=battery_soc,
                battery_dc_power=battery_dc_power,
                solar_power=solar_power,
                grid_ac_power=grid_ac_power,
                home_load=home_load,
            )
        finally:
            device.disconnect()

    async def read(self, hass) -> SunSpecData:
        """Read all required SunSpec models. Returns typed data."""
        return await hass.async_add_executor_job(self._read_blocking)
```

### Exception Hierarchy

```python
# Source: pySunSpec2 sunspec2/modbus/client.py (verified)
# Catch order matters: most specific first
try:
    data = client._read_blocking()
except SunSpecModbusClientTimeout as err:
    # TCP timeout — device not responding
    raise
except SunSpecModbusClientException as err:
    # Modbus protocol error
    raise
except SunSpecModbusClientError as err:
    # Base class for all pySunSpec2 Modbus errors
    raise
except KeyError as err:
    # Model not present after scan (e.g., model 502 missing)
    raise
```

### manifest.json Update

```json
{
  "domain": "franklin_wh",
  "name": "FranklinWH",
  "requirements": ["pysunspec2==1.3.3"]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pySunSpec (v1) | pySunSpec2 (v2) | ~2022 | Not backward compatible; v2 uses JSON model defs, v1 used SMDX XML; ha-sunspec uses v2 |
| `sunspec.core.client.SunSpecClientError` | `sunspec2.modbus.client.SunSpecModbusClientError` | v2 migration | Exception class names changed; don't import from v1 paths |
| Full scan with all data read | `scan(full_model_read=False)` + targeted `model.read()` | pySunSpec2 API | Faster discovery; reads only what you need |

**Deprecated/outdated:**
- `pySunSpec` (v1): Replaced by `pySunSpec2`. Import paths differ entirely. Do not mix.

## Open Questions

1. **Does FranklinWH implement SunSpec model 502?**
   - What we know: FranklinWH's SunSpec Alliance Product Certification Registry entry lists models 1 and 701-715. Model 502 is "Solar Module" (a DC-DC optimizer/converter model) and is NOT in FranklinWH's registered list.
   - What's unclear: The project roadmap and REQUIREMENTS.md both specify model 502 for solar production (MDATA-03). This may be incorrect, or FranklinWH may implement it without registering it.
   - Recommendation: Implement the client to attempt model 502 after scan, check `502 in device.models`, and raise an informative `KeyError`-derived exception if absent. Add a code comment noting the discrepancy. Solar power may come from a different model (candidates: 701 via a second channel, or a vendor-specific model). This must be validated by running a full scan on real FranklinWH hardware and inspecting `device.models.keys()`.

2. **What is the correct group/point path for Model 714 DCW?**
   - What we know: Model 714 has a model-level `DCW` (sum) and per-port `DCW` inside a repeating group. The model-level sum is preferred. The port group name is likely `DCSrc` based on the JSON definition.
   - What's unclear: Whether the FranklinWH device populates the model-level `DCW` or only the per-port values.
   - Recommendation: Implement to read model-level `DCW` first; add fallback to sum port group values. Must validate on real hardware.

3. **What version of pySunSpec2 does HACS/HA use?**
   - What we know: PyPI latest is `pysunspec2==1.3.3`. The ha-sunspec reference integration pinned `pysunspec2==1.1.5` (as of its last check). HA custom components are free to pin any version.
   - What's unclear: Whether 1.3.3 introduces any breaking changes vs 1.1.5 used by ha-sunspec.
   - Recommendation: Pin `pysunspec2==1.3.3` (latest stable). If integration breaks, fall back to `1.1.5`.

## Sources

### Primary (HIGH confidence)
- `sunspec/pysunspec2` GitHub README.rst — library API, `scan()`, `.cvalue` vs `.value`, exception classes, TCP client constructor
- `sunspec/models` GitHub — model_701.json (W point), model_713.json (SoC point), model_714.json (DCW point), model_502.json (OutPw point)
- `CJNE/ha-sunspec` api.py (GitHub) — full working HA integration using pySunSpec2 in executor; verified full source code
- PyPI `pysunspec2` JSON API — confirmed latest version 1.3.3, Python ≥3.5, no required dependencies

### Secondary (MEDIUM confidence)
- SunSpec Alliance Product Certification Registry (via WebSearch) — FranklinWH registered models are 1 and 701-715; model 502 absent
- pySunSpec2 GitHub repository — `scan(full_model_read=False)` parameter confirmed in source code

### Tertiary (LOW confidence)
- WebSearch: model 502 description as "Solar Module" (DC-DC converter) — not verified against official SunSpec spec document directly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pySunSpec2 is the sole production library; PyPI name and version verified directly
- Architecture: HIGH — ha-sunspec full source code verified; executor pattern confirmed in existing codebase
- Pitfalls: MEDIUM — PyPI/import name mismatch verified; model 502 absence is verified via registry; model 714 group structure is MEDIUM (JSON verified, device behavior unconfirmed)
- Model point names: MEDIUM — 701.W, 713.SoC, 714.DCW verified from model JSON; 502.OutPw verified from JSON but model may be absent on device

**Research date:** 2026-02-28
**Valid until:** 2026-09-01 (stable library, slow-moving domain)
