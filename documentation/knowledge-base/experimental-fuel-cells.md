# Experimental Fuel Cells (Fuel 7-11) — Special Behaviors

RE source: `Build.wasm_decompiled.c` (Ghidra output), `stringliteral.json` (UI descriptions)

## Overview

Five experimental fuel elements are unlocked via the Experimental tab (requires upgrade #32 Research Grant).
Each element has Single (1-core), Double (2-core), and Quad (4-core) variants.

| Fuel | Element | Type ID | Tier | Cost | MaxDur | EPP | HPP | PPC | Required Upgrade | Special Mechanic |
|------|---------|---------|------|------|--------|-----|-----|-----|-----------------|------------------|
| Fuel7 | Protium | 16 (0x10) | 7 | 3T | 3,600 | 1.25T | 1.25T | 1 | #33 Protium Research | Permanent power boost on depletion |
| Fuel8 | Monastium | 17 (0x11) | 8 | 288T | 345,600 | 2T | 1T | 1 | #46 Monastium Research | 7×7 density penalty on power |
| Fuel9 | Kymium | 18 (0x12) | 9 | 8.64Q | 345,600 | 45T | 45T | 1 | #47 Kymium Research | Cosine power/heat pulsation |
| Fuel10 | Discurrium | 19 (0x13) | 10 | 86.4Q | 345,600 | 100T | 100T | **4** | #48 Discurrium Research | 4 pulses/tick (stat only, no code) |
| Fuel11 | Stavrium | 20 (0x14) | 11 | 4.32Qi | 345,600 | 1Q | 1Q | 1 | #49 Stavrium Research | Row+column pulse distribution |

**Type ID mapping**: `fuel_index + 9` for Fuel 7-11 (e.g., Fuel7 = 7+9 = 16).

**Tier mapping**: `tier = fuel_index` for all fuels (Fuel1=tier 1, ..., Fuel11=tier 11).
Stored at `ComponentType+0x10` in binary. The UI description prefix is `"Tier-" + tier`
(e.g., "Tier-7 power production..."). From `stringliteral.json` address 0x13873C.

**Note**: The existing `wasm-decompilation-notes.md` incorrectly labels type 0x14 (20) as "Discurrium".
It is actually **Stavrium** (Fuel11 = 11+9 = 20). Discurrium (Fuel10 = 10+9 = 19) has no special code path.

---

## Protium (Fuel7, Type 0x10/16)

**UI description**: "After burning up completely, it releases a special form of radiation that permanently increases the power output of other protium cells by 1% per depleted cell."

### Power Generation — fn 10446

**Lines**: 391995-391996 in decompiled C

```c
if (*(int *)(param2 + 0x14) == 0x10) {
    dVar1 = (double)((float)*(int *)(param1 + 0x38) / 100.0 + 1.0);
}
```

**Formula**:
```
basePower = protiumMult * pulseCount * EnergyPerPulse * upgradeBonus
protiumMult = depletedProtiumCount / 100.0 + 1.0
```

**Reactor+0x38** stores the **permanent count of depleted Protium cells** (int). Each time a Protium
cell burns out (durability reaches 0), this counter increments. The counter persists across ticks
and is never zeroed during the tick pipeline.

**Key details**:
- Each depleted Protium cell adds +1% power to ALL surviving Protium cells
- The bonus is permanent (survives the cell being removed, persists in save)
- With 100 depleted Protium cells: 2.0× power multiplier
- The multiplier applies to power only, NOT heat
- All Protium variants (Single/Double/Quad) contribute to and benefit from the counter
- The overheat multiplier, reflector bonus, and other multipliers stack multiplicatively with this

### Heat Generation

Standard fuel cell formula — no special Protium modification:
```
heat = (pulseCount² × HeatPerPulse × upgradeBonus) / cellArea
```

---

## Monastium (Fuel8, Type 0x11/17)

**UI description**: "Its base power output drops by 2% for each other component in the 7 x 7 area surrounding it."

### Density Penalty — fn 10443

**Lines**: 391745-391772 in decompiled C

```c
if (*(int *)(*piVar17 + 0x14) == 0x11) {
    iVar7 = 0;
    for (iVar9 = -3; iVar9 != 4; iVar9 = iVar9 + 1) {
        for (iVar10 = -3; iVar10 != 4; iVar10 = iVar10 + 1) {
            iVar19 = gridWidth * iVar10 + iVar9 + cellIndex;
            // bounds check + non-null check
            iVar7 = (isOccupied & 1) + iVar7;
        }
    }
    dVar11 = 1.0 - (double)iVar7 * 0.02;
}
```

**Algorithm**:
```
occupiedCount = count non-null cells in 7×7 area centered on this cell
powerMult = 1.0 - occupiedCount * 0.02
finalPower = powerMult * basePower
```

**Key details**:
- Scans a 7×7 area: offsets (-3,-3) through (+3,+3) inclusive
- **Counts the Monastium cell itself** despite UI saying "other" — minimum count is 1 (self)
- 2% power penalty per occupied cell (any component type, not just fuel)
- Maximum 49 cells in 7×7 → max penalty = 49 × 2% = 98% (mult = 0.02)
- **Power only** — heat is NOT affected by density
- Out-of-bounds cells are not counted (grid edges reduce the effective scan area)
- Works with linear cell indices: `row * gridWidth + col`

### Heat Generation

Standard fuel cell formula — density penalty does NOT apply to heat.

---

## Kymium (Fuel9, Type 0x12/18)

**UI description**: "It gradually cycles between producing only heat and producing only power."

### Cosine Pulsation — fn 10443

**Lines**: 391720-391736 in decompiled C

```c
if (*(int *)(iVar7 + 0x14) == 0x12) {
    dVar5 = *(double *)(component + 0x20);        // current durability
    dVar3 = GetStatCached(upgradeManager, componentType, stat=1);  // maxDurability with upgrades
    dVar3 = cos((dVar5 / dVar3) * 2.0 * π * 4.0);
    powerMult = 0.5 - dVar3 * 0.5;               // (1 - cos(phase)) / 2
    // Same calculation again for heat:
    heatMult = dVar3 * 0.5 + 0.5;                // (1 + cos(phase)) / 2
}
```

**Formulas**:
```
phase = (currentDurability / maxDurability) * 8π
powerMult = (1 - cos(phase)) / 2
heatMult = (1 + cos(phase)) / 2
```

Where `maxDurability` includes upgrade bonuses (stat 1 via GetStatCached).

**Key details**:
- 4 complete oscillation cycles over the cell's lifetime (8π = 4 × 2π)
- At full durability: phase = 8π → cos = 1 → power=0, heat=1 (all heat, no power)
- At 7/8 durability: phase = 7π → cos ≈ -1 → power=1, heat=0 (all power, no heat)
- powerMult + heatMult = 1.0 always (energy is redistributed, not created/destroyed)
- Power and heat are exactly 180° out of phase
- Uses the UPGRADED maxDurability for phase calculation
- The Monastium density penalty is separate and cannot stack (different type check)

### Phase Visualization

```
Durability:  100%  87.5%  75%  62.5%  50%  37.5%  25%  12.5%  0%
Power:        0     1      0    1      0    1      0    1      0
Heat:         1     0      1    0      1    0      1    0      1
```

---

## Discurrium (Fuel10, Type 0x13/19)

**UI description**: "Each cell produces four pulses per tick instead of the usual one."

### No Special Code Mechanic

Discurrium has **no special handling** in the binary's generation or distribution functions.
Its uniqueness is entirely captured by its JSON stats: **PulsesPerCore = 4** (all other fuels have
PulsesPerCore = 1).

The standard pulse formula `pulses = PulsesPerCore * NumberOfCores` naturally gives Discurrium
4× the pulses of equivalent-core cells. Since power scales linearly with pulses and heat scales
quadratically (`pulseCount² × HeatPerPulse`), Discurrium generates proportionally more heat
relative to power than other fuels.

---

## Stavrium (Fuel11, Type 0x14/20)

**UI description**: "All components aligned vertically or horizontally are considered adjacent to it."

### Row+Column Pulse Distribution — fn 10441

**Lines**: 391435-391456 in decompiled C

```c
if (*(int *)(*piVar12 + 0x14) == 0x14) {
    // Compute cell coordinates from linear index
    z = cellIndex / (gridHeight * gridWidth);
    y = (cellIndex % (gridHeight * gridWidth)) / gridWidth;
    x = cellIndex % gridWidth;

    // Distribute to entire row (same y, all x except self)
    for (col = 0; col < gridWidth; col++) {
        if (col != x) {
            pulseCount[(z*gridHeight + y) * gridWidth + col] += pulses;
        }
    }

    // Distribute to entire column (same x, all y except self)
    for (row = 0; row < gridHeight; row++) {
        if (row != y) {
            pulseCount[gridWidth * (gridHeight*z + row) + x] += pulses;
        }
    }
}
```

**Algorithm**:
```
For standard fuels:
    Distribute pulses to 4 cardinal neighbors only

For Stavrium (type 0x14):
    Distribute pulses to ALL cells in the same row (excluding self)
    Distribute pulses to ALL cells in the same column (excluding self)
    Self still receives scale * pulses (same as standard fuels)
```

**Key details**:
- Creates a cross/plus-shaped distribution pattern spanning the entire grid
- On a 19×16 grid: distributes to up to 18 (row) + 15 (column) = 33 cells (vs 4 for standard)
- `pulses = PulsesPerCore * NumberOfCores` (same calculation as standard)
- Self-pulse addition uses `scale * pulses` where `scale = floor(log2(cores) + 1)` — same as standard
- Row/column distribution does NOT use the scale factor (just raw `pulses`)
- **Only affects pulse distribution** — heat absorption and reflector bonus still use 4 cardinal neighbors
- Reflectors in the same row/column receive pulses, making them wear out faster (pulse damage)
- Other fuel cells in the row/column receive additional pulses, boosting their power/heat output

### Interaction with Other Systems

The row+column adjacency ONLY applies to pulse distribution (fn 10441).
The following still use 4 cardinal neighbors via fn 10439:
- Reflector power bonus (fn 10443 neighbor scan)
- Heat distribution to absorbers (fn 10443)
- Heat exchange via exchangers (fn 10424)
- Inlet/outlet hull transfer (fn 10438)

---

## Overheat Multiplier (All Fuels)

**Function**: fn 10443, lines 391673-391685

All fuel cells (including experimental) receive an overheat power multiplier when reactor heat > 1000:

```
if reactor_heat > 1000:
    overheatMult = (ln(reactor_heat) / ln(1000)) * (CellEffectiveness_upgrade - 1.0) * 0.01 + 1.0
else:
    overheatMult = 1.0
```

Where `CellEffectiveness_upgrade = GetUpgradeStatBonus(1, 0x14)`.

With no upgrades (bonus = 1.0), the multiplier is always 1.0 regardless of heat.

---

## Final Power Formula (All Fuels Combined)

```
basePower = fn_10446(pulseCount, EnergyPerPulse, upgradeBonus)
           = protiumMult * pulseCount * EnergyPerPulse * upgradeBonus   (Protium)
           = pulseCount * EnergyPerPulse * upgradeBonus                  (all others)

finalPower = kymiumPowerMult * monastiumDensityMult * overheatMult * reflectorMult * basePower
```

Where each mult defaults to 1.0 when not applicable to the fuel type.

## Final Heat Formula (All Fuels Combined)

```
baseHeat = fn_10444(pulseCount, HeatPerPulse, upgradeBonus, cellArea)
         = (pulseCount² × HeatPerPulse × upgradeBonus) / cellArea

finalHeat = kymiumHeatMult * baseHeat
```

Note: Monastium density, Protium depletion bonus, and reflector bonus do NOT affect heat.

---

## Implementation Status Summary

| Feature | Status | Location |
|---------|--------|----------|
| Protium: depleted cell power boost | **Implemented** | `simulation.py` — `depleted_protium_count` field, `_drain_durability()` increment, `_generate_power_and_heat()` multiplier |
| Monastium: 7×7 density penalty | **Implemented** | `simulation.py` — `_generate_power_and_heat()` 7×7 scan |
| Kymium: cosine pulsation | **Implemented** | `simulation.py` — `_generate_power_and_heat()` cosine phase calc |
| Discurrium: 4 pulses/core | **Implemented** | PulsesPerCore=4 in JSON, handled by standard formula |
| Stavrium: row+column distribution | **Implemented** | `simulation.py` — `_distribute_pulses()` row+column loop |
| Overheat multiplier | **Implemented** | `simulation.py` — `_generate_power_and_heat()` pre-loop |
| Experimental fuel descriptions | **Implemented** | `catalog.py` — element-specific strings from stringliteral.json |

---

## Binary Function Reference

| Function | Inferred Name | Relevance |
|----------|--------------|-----------|
| fn 10312 | CreateExperimentalFuelCell | Factory for all Fuel 7-11 variants |
| fn 10441 | DistributePulses | Stavrium row+column distribution (type 0x14) |
| fn 10442 | DrainDurability | Fuel -1/tick, reflector -pulses/tick |
| fn 10443 | GeneratePowerAndHeat | Kymium pulsation (0x12), Monastium density (0x11), overheat mult |
| fn 10444 | ComputeHeat | `(pulses² × HPP × bonus) / area` |
| fn 10445 | GetReflectorEffectiveness | `GetUpgradeStatBonus(0xB, 0x18) - 1.0 + 10` |
| fn 10446 | ComputePower | Protium bonus (0x10), `mult × pulses × EPP × bonus` |
