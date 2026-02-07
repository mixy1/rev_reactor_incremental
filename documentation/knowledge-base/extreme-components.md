# Extreme (Tier 6) Components — Special Behaviors

RE source: `Build.wasm_decompiled.c` (Ghidra output)

## Overview

Two components have tier-6-specific special mechanics in the binary:

| Component | Binary Type | Cost | Key Stat (param6) | Special Mechanic |
|-----------|-------------|------|-------------------|------------------|
| ExtremeCoolant (Coolant6) | Coolant (type 10) | 160T | 377.82T | CantLoseHeat flag (thermally isolated) + radius-2 heat absorption |
| ExtremeCapacitor (Capacitor6) | Capacitor (type 13, misidentified as Reflector in JSON) | 104.857T | 5.378T | Auto-sell heat generation |

Nefastium (Fuel6-1/2/4) is tier 6 but has NO special mechanics; it uses the standard fuel cell path.

**Data rotation**: The JSON data for Coolant6 and Capacitor6 is swapped (same rotation
as tiers 1-5, but with no Reflector6 the 3-way cycle collapses to a 2-way swap).
The catalog.py post-loop swap corrects this.

---

## ExtremeCoolant (Coolant6)

**Required upgrade**: #42 (Vortex Cooling)

### Factory Construction — fn 10318 (ConvertToExtremeCoolant)

```
fn 10311 calls:
  fn 10315(0, typeOfComponent=10, sprite_ref, tier=6, cost=160T, param6=377.82T)
  fn 10318(0, component, 0)  // ConvertToExtremeCoolant
```

fn 10318 (lines 377524-377536):
- Sets sprite/name reference
- Sets `+0xCA = 1` (CantLoseHeat flag)
- Does NOT set `+0xC8` (ReflectsPulses)

### Special Mechanic 1: CantLoseHeat (+0xCA = 1)

The `+0xCA` byte flag makes the ExtremeCoolant thermally isolated:

1. **Heat Exchange (fn 10424)**: When `+0xCA == 1`, the directional multiplier in the exchange formula becomes 0. Heat cannot flow in or out through exchangers. Relevant lines 389663-389676:
   ```c
   dVar3 = dVar2 * (double)(int)-((uint)*(byte *)(*piVar13 + 0xc9) & -(*(byte *)(*piVar11 + 0xca) ^ 1));
   ```

2. **Radius-2 absorption (fn 10424)**: The absorption explicitly skips neighbors where `+0xCA != 0` (line 389764), so other ExtremeCoolants don't steal each other's heat:
   ```c
   if ((iVar15 != 0) && (*(char *)(*piVar11 + 0xca) == '\0'))
   ```

3. **Inlet heat transfer (fn 10438)**: Inlets pulling heat from neighbors also check `+0xCA` (line 389837):
   ```c
   if (*(char *)(*piVar11 + 0xca) == '\0')
   ```

**Net effect**: The ExtremeCoolant can accumulate heat (from radius-2 absorption and fuel cell overflow at 2x max reactor heat), but this heat can NEVER be removed by any game mechanic. It's a permanent heat sink.

### CantLoseHeat vs reflects_pulses

In the current implementation, `reflects_pulses > 0` is used as a proxy for CantLoseHeat in several places:
- Heat exchange (simulation.py `_heat_exchange()`): skips neighbors where `reflects_pulses > 0`
- Inlet transfer (simulation.py `_exchange_with_hull()`): skips neighbors where `reflects_pulses > 0`

This works for Reflectors (which have both `+0xC8 = 1` and `+0xCA = 1`), but does NOT cover ExtremeCoolant (which has `+0xCA = 1` but `+0xC8 = 0`). The ExtremeCoolant needs a dedicated `cant_lose_heat` field on `ComponentTypeStats`.

### Special Mechanic 2: Radius-2 Heat Absorption

**Function**: `unnamed_function_10424` (HeatExchange), post-exchange pass
**Lines**: 389706-389778 in decompiled C
**WAT**: Build.wast near function 10424

**Trigger**: After the standard exchanger heat-exchange loop completes, the function iterates all components again looking for `TypeOfComponent == 10 AND tier == 6`.

Note: In the binary's `_COMPONENT_CATEGORY_IDS`, Coolant = 10. The check at `+0x14` uses the runtime type ID.

**Algorithm**:
```
for each component where TypeOfComponent == 10 AND tier == 6:
    neighbors = fn_10440(reactor, cellIndex, radius=2, filterMode=0)
    // Manhattan distance diamond, radius 2 — covers up to 12 cells
    for each neighbor in neighbors:
        if neighbor has HeatCapacity (stat 2 is non-null)
           AND neighbor.CantLoseHeat (+0xCA) == 0:
            absorbed = neighbor.heat * 0.1
            neighbor.heat -= absorbed
            this.heat += absorbed
```

**Key details**:
- Uses Manhattan distance (diamond shape), NOT Chebyshev (square)
- Radius = 2 means the diamond covers offsets like (0,+/-1), (0,+/-2), (+/-1,0), (+/-2,0), (+/-1,+/-1)
- Absorbs 10% of each qualifying neighbor's current heat
- Does NOT check if the ExtremeCoolant is depleted (it has no durability, so this is moot)
- Skips neighbors with `CantLoseHeat` flag (i.e., other ExtremeCoolants)
- No upgrade scaling on the 10% rate
- Heat absorbed is NOT clamped here (only limited by neighbors' available heat)
- Since ExtremeCoolant has CantLoseHeat, absorbed heat is permanently trapped

---

## ExtremeCapacitor (Capacitor6)

**Required upgrade**: #41 (Experimental Capacitance Research)

### Factory Construction — fn 10317 (ConvertToExtremeCapacitor)

```
fn 10311 calls:
  fn 10315(0, typeOfComponent=0xD, sprite_ref, tier=6, cost=104.857T, param6=5.378T)
  fn 10317(0, component, 0)  // ConvertToExtremeCapacitor
```

fn 10317 (lines 377503-377518):
- Sets sprite/name reference
- Copies `+0xB8..+0xC4` (ReactorPowerCapIncrease, Nullable\<double\>) into `+0x40..+0x4C` (HeatCapacity)
- Effect: HeatCapacity = ReactorPowerCapacityIncrease = param6 = 5.378T

**Catalog fixup needed**:
- `type_of_component = "Capacitor"` (JSON says Reflector)
- `reflects_pulses = 0` (JSON says 1.0)
- `max_durability = 0` (no durability — the JSON value is the heat capacity)
- Data swap with Coolant6 (JSON data is rotated)

### Special Mechanic: Auto-Sell Heat Generation

**Function**: `unnamed_function_10430` (Reactor.AutoSellPower)
**Lines**: 390210-390305 in decompiled C

**Trigger**: `TypeOfComponent == 0xD (13) AND tier == 6`, checked during auto-sell each tick.

**Algorithm**:
```
autoSellRate = fn_10417(reactor)  // = (autoSellBonus - 1) * maxPower * 0.01
actualSold = min(storedPower, autoSellRate)

if autoSellRate > 0:
    for each component where TypeOfComponent == 0xD AND tier == 6:
        autoSellMult = fn_10435(upgradeManager)
                     = GetUpgradeStatBonus(category=1, stat=0xF) - 1.0
        powerCapInc = GetStatCached(componentType, stat=0xC)
                    = reactor_power_capacity_increase * upgrade_bonus
        heat_added = autoSellMult * powerCapInc * 0.005 * (actualSold / autoSellRate)
        component.heat += heat_added
        component.heat = clamp(component.heat, 0, heatCapacity)  // fn 10135 with stat=2
```

**Key details**:
- `actualSold` is the GLOBAL total power sold, not per-component
- `actualSold / autoSellRate` is a ratio (0..1), usually 1.0 when enough power exists
- `autoSellMult` is 0 when no auto-sell upgrades are purchased (so no heat generated)
- Heat goes to the individual component, NOT the reactor hull
- Heat is clamped to the component's effective HeatCapacity
- The 0.005 constant means 0.5% (the description's "50%" is misleading)
- ExtremeCapacitor does NOT have CantLoseHeat — its heat CAN be removed by exchangers/inlets

**Supporting functions**:
- fn 10417 (GetAutoSellRate): `(GetUpgradeStatBonus(1, 0xF) - 1.0) * maxPower * 0.01`
- fn 10435 (GetAutoSellMultiplier): `GetUpgradeStatBonus(1, 0xF) - 1.0`
- fn 10370 (GetStatCached): returns `base_stat * upgrade_bonus` for a component type + stat pair

---

## Implementation Status Summary

| Feature | Status | Location |
|---------|--------|----------|
| ExtremeCoolant: CantLoseHeat flag | **Implemented** | `types.py` `cant_lose_heat` field; `catalog.py` sets for Coolant6; `simulation.py` heat exchange + inlet checks |
| ExtremeCoolant: radius-2 heat absorption | **Implemented** | `simulation.py` `_extreme_coolant_absorb()` post-heat-exchange pass |
| ExtremeCoolant: catalog data swap | **Implemented** | `catalog.py` (Coolant6 ↔ Capacitor6 swap) |
| ExtremeCapacitor: auto-sell heat generation | **Implemented** | `simulation.py` `_do_tick()` auto-sell section |
| ExtremeCapacitor: catalog data fixup | **Implemented** | `catalog.py` (type, reflects_pulses, max_durability, data swap) |
| ExtremeCapacitor: power capacity increase | **Implemented** | Standard capacitor contribution path |
| Manhattan distance helper (radius=2) | **Implemented** | `grid.py` `manhattan_neighbors()` method |

---

## Binary Function Reference

| Function | Inferred Name | Relevance |
|----------|--------------|-----------|
| fn 10311 | ComponentTypes.Initialize | Creates all component types, calls Convert functions |
| fn 10315 | CreateReflectorCapacitorCoolantPlating | Shared factory for non-fuel, non-vent components |
| fn 10317 | ConvertToExtremeCapacitor | Copies ReactorPowerCapInc into HeatCapacity (type 13) |
| fn 10318 | ConvertToExtremeCoolant | Sets CantLoseHeat = 1 (type 10) |
| fn 10370 | GetStatCached | Returns base_stat * upgrade_bonus for a type+stat pair |
| fn 10417 | GetAutoSellRate | `(bonus - 1) * maxPower * 0.01` |
| fn 10424 | HeatExchange (both phases) | Post-loop has ExtremeCoolant radius-2 absorption |
| fn 10430 | Reactor.AutoSellPower | ExtremeCapacitor heat generation during auto-sell |
| fn 10435 | GetAutoSellMultiplier | `GetUpgradeStatBonus(1, 0xF) - 1.0` |
| fn 10440 | GetNeighborOffsets(radius) | Manhattan distance diamond search, used for radius=2 |
