# Wasm Decompilation Notes (Core Systems)

## Mapping rule
- IL2CPP `methodIndex` does NOT map 1:1 to `unnamed_function_{methodIndex}` in Ghidra.
- Metadata indices and WASM function indices happen to be in the same numerical range but the
  **metadata method names don't match** the actual WASM function behavior at corresponding indices.
- Always validate by tracing the actual call graph from known entry points.

## Full Tick Pipeline

### Timer loop: `unnamed_function_10418` (Simulation.LogicalUpdate)
- Reads `Time.time` via `unnamed_function_16432`
- While `Time.time - *(param1 + 0x20) > 1.0 / ticksPerSecond`:
  - Call `unnamed_function_10419` (single tick)
  - `*(param1 + 0x20) += 1.0 / ticksPerSecond`
- `unnamed_function_10420` returns cached ticks/second (via stat 0x13 on category 1)

### Single tick: `unnamed_function_10419` (Simulation.Tick)
Pipeline order (all called in sequence):

1. **Zero accumulators** — `+0x30..0x3c` (lastHeatChange, lastPowerChange) set to 0
2. **`unnamed_function_10422(Reactor)`** — PrepareMultipliers
   - Calls `OnSolutionChanged` to refresh caches
   - Computes global upgrade multipliers stored on the Reactor object:
     - `+0x70` = `(GetUpgradeStatBonus(Coolant=0xD, stat=0x11) - 1) * count * 0.01 + 1` (SelfVentRate multiplier)
     - `+0x78` = `(GetUpgradeStatBonus(Coolant=0xD, stat=0x16) - 1) * count * 0.01 + 1` (HeatExchangeRate multiplier)
     - `*(+0x80)+0x10` = `(GetUpgradeStatBonus(Plating=0xC, stat=0x15) - 1) * count * 0.01 + 1` (Power cap multiplier)
     - `*(+0x80)+0x08` = `(GetUpgradeStatBonus(Plating=0xC, stat=0x17) - 1) * count * 0.01 + 1` (Heat cap multiplier)
   - `unnamed_function_10447(Reactor, category)` returns count of components of that category
3. **`unnamed_function_10423(Simulation)`** — TickGeneratePowerAndHeat
   - Inits `power = 0`, `heat = 0`
   - Calls three sub-phases on Reactor:
     - `unnamed_function_10441(Reactor)` — DistributePulses (one-shot when dirty flag `+0x68` is set)
     - `unnamed_function_10442(Reactor)` — DrainDurability
     - `unnamed_function_10443(Reactor, &power, &heat)` — GeneratePowerAndHeat
   - Adds power to `Simulation+0x38` (lastPowerChange)
   - Adds heat to `Simulation+0x30` (lastHeatChange)
   - Updates Player stats (total power generated)
4. **`unnamed_function_10424(Reactor, mode=1)`** — HeatExchange phase 1 (snapshot + redistribution)
   - Copies each component's heat (`+0x28`) into list entry `+0x18`
   - Zeroes list entry `+0x20` accumulators
   - Then: for each component with stat 9 (HeatExchangeRate) > 0 (scaled by `+0x78`):
     - Gets 4 cardinal neighbors, checks each has HeatCapacity (`ComponentType+0x40` not null)
     - Computes target fill ratio: `(selfHeat + neighborHeat) / (selfHeatCap + neighborHeatCap)` (clamped 0-1)
     - Redistributes heat toward equilibrium using directional flags (+0xC9, +0xCA)
     - Writes to list entry `+0x20` accumulators (not directly to component heat)
5. **`unnamed_function_10424(Reactor, mode=0)`** — HeatExchange phase 2 (with correction + ExtremeCoolant)
   - Same exchange logic but with additional correction factor using current/accumulated heat ratio
   - Writes directly to `component+0x28` (actual heat stores)
   - Post-loop: handles **ExtremeCoolant** (TypeOfComponent == 10, tier == 6):
     - Uses `unnamed_function_10440` to get neighbors within radius=2, Manhattan distance filter
     - For each neighbor within range: absorbs 10% of their heat (`neighbor.heat * 0.1`)
6. **`unnamed_function_10425(Simulation)`** → `unnamed_function_10438(Reactor, &heat)` — VentReactor
   - Subtracts vented heat from `Simulation+0x30` (lastHeatChange)
7. **`unnamed_function_10426(Simulation)`** → `unnamed_function_10437(Reactor, &heat)` — VentHeatToAir
   - Updates Player stats (total heat vented, total heat produced)
8. **`unnamed_function_10427(Simulation)`** → `unnamed_function_10436(Reactor, &out1, &out2)` — ExchangeWithHull
   - Subtracts exchanged heat from `Simulation+0x30`
   - Updates Player stats
9. **`unnamed_function_10428(Simulation)`** → `unnamed_function_10429(Reactor, Sim, &power, &heat)` — EarnMoney
   - Calls `unnamed_function_10430` first (passive coolant income)
   - Handles power-to-money conversion with reactor heat capacity check
   - Updates Player stats (money earned, total power sold)
10. **Final** — `unnamed_function_10409` + cache ticks per second in Nullable at `+0x40..0x4c`

---

## Sub-Phase Details

### unnamed_function_10441 — DistributePulses
- Only runs when dirty flag `Reactor+0x68` is set (cleared after execution)
- Zeroes all list entry `+0x28` values (pulse accumulator per cell)
- For each active fuel cell (has CellData at `ComponentType+0x50`, alive flag `+0x40 == 0`):
  - Gets stat 5 = PulsesProduced, converts to int
  - Reads param_7 (NumberOfCores from CellData)
  - `pulses = PulsesProduced * cores`
  - Log2 scaling: `scale = floor(log2(cores) + 1)`
  - Stores `listEntry[+0x28] += scale * pulses`
  - **Stavrium** (TypeOfComponent == 0x14 / 20): distributes pulses to entire row AND column
  - **All others**: distributes pulses to 4 cardinal neighbors only

### unnamed_function_10442 — DrainDurability
- For each non-null component:
  - Gets stat 5 = PulsesProduced
  - If PulsesProduced > 0 AND component active: `component+0x20 -= 1.0` (fuel cells lose 1 durability/tick)
  - If `ComponentType+0xC8 != 0` (reflector): iterates 4 cardinal neighbors, sums their PulsesProduced,
    then `component+0x20 -= sum` (reflectors lose durability proportional to adjacent pulse output)

### unnamed_function_10443 — GeneratePowerAndHeat
- **Overheat multiplier**: if reactor heat (`+0x28`) > 1000:
  - `mult = (ln(heat) / ln(1000)) * (CellEffectiveness_upgrade - 1.0) * 0.01 + 1.0`
- For each active fuel cell:
  - **Kymium** (type 0x12/18): cosine pulsation over lifetime
    - `phase = (durability / maxDurability) * 8π`
    - `powerMult = (1 - cos(phase)) / 2`, `heatMult = (1 + cos(phase)) / 2`
    - Power and heat alternate sinusoidally (4 full cycles over lifetime)
  - **Monastium** (type 0x11/17): density penalty
    - Scans 7×7 area centered on cell, counts occupied cells
    - `mult = 1.0 - occupiedCount * 0.02` (2% penalty per occupied cell)
  - **Protium** (type 0x10/16): extra scaling from `Reactor+0x38` (depleted Protium count)
  - Heat computed via `unnamed_function_10444(Reactor, componentType, adjacentPulseCount)`
    - Formula: `(adjacentPulses² × HeatPerPulse) / (cellWidth × cellHeight)`
  - Heat distributed to neighbors with `ComponentType+0xC9 != 0` (heat absorbers)
    - If no absorbers adjacent → heat goes to reactor store
    - If absorbers exist → heat split equally among them
  - **Reflector neighbors** (`ComponentType+0xC8 != 0`): multiplicative power boost
    - Each reflector neighbor adds `reflectorEffectiveness / 100` to power multiplier
  - Power computed via `unnamed_function_10446(Reactor, componentType, adjacentPulseCount)`
    - Formula: `scale × adjacentPulses × EnergyPerPulse`
  - Final: `component+0x30 = finalPower`, `component+0x38 = finalHeat`
  - Stored power (`Reactor+0x30`) increased, clamped to max capacity

---

## Simulation Object Memory Layout

| Offset | Size | Type | Field |
|--------|------|------|-------|
| `+0x08` | 4 | ptr | upgradeManager (passed to stat lookups) |
| `+0x0C` | 4 | ptr | UIHandler / sub-object (bar color updates) |
| `+0x18` | 4 | int | gridWidth |
| `+0x1C` | 4 | ptr | Reactor object |
| `+0x20` | 4 | float | timeSinceLastTick |
| `+0x24` | 4 | ptr | componentList (if on Simulation; Reactor also has one) |
| `+0x28` | 8 | double | reactorHeatStore |
| `+0x30` | 8 | double | lastHeatChange (zeroed each tick, accumulated) |
| `+0x38` | 8 | double | lastPowerChange (zeroed each tick, accumulated) |
| `+0x40` | 16 | Nullable | cachedTicksPerSecond |

## Reactor Object Memory Layout

| Offset | Size | Type | Field |
|--------|------|------|-------|
| `+0x08` | 4 | ptr | upgradeManager |
| `+0x18` | 4 | int | gridWidth |
| `+0x1C` | 4 | int | gridHeight |
| `+0x24` | 4 | ptr | componentList (array struct) |
| `+0x28` | 8 | double | reactorHeatStore |
| `+0x30` | 8 | double | storedPower |
| `+0x68` | 1 | byte | isDirty / needsPulseRecalc |
| `+0x69` | 1 | byte | needsCacheRefresh |
| `+0x70` | 8 | double | selfVentRateMultiplier (from upgrades) |
| `+0x78` | 8 | double | heatExchangeRateMultiplier (from upgrades) |
| `+0x80` | 4 | ptr | sub-struct with +0x08=heatCapMult, +0x10=powerCapMult |

## Component List Structure

At `*(Reactor+0x24)`:
- `+0x0C` = int count
- `+0x10 + i*0x20` = component instance pointer (or null)
- `+0x18 + i*0x20` = double: heat snapshot (copied from component+0x28 during exchange phase 1)
- `+0x20 + i*0x20` = double: heat exchange accumulator (zeroed at phase start)
- `+0x28 + i*0x20` = int: pulse count (from DistributePulses)

## Component Instance Layout

| Offset | Type | Field |
|--------|------|-------|
| `+0x18` | ptr | ComponentType pointer |
| `+0x20` | double | remainingDurability |
| `+0x28` | double | componentHeatStore |
| `+0x30` | double | lastPowerGenerated (per tick, for UI) |
| `+0x38` | double | lastHeatGenerated (per tick, for UI) |
| `+0x40` | byte | isDepleted flag (0=alive, nonzero=dead) |

## ComponentType Layout

| Offset | Type | Field |
|--------|------|-------|
| `+0x10` | int | tier (1-6) |
| `+0x14` | int | TypeOfComponent (ComponentCategory enum) |
| `+0x28` | double | Cost |
| `+0x30..0x3F` | Nullable<double> | MaxDurability |
| `+0x40..0x4F` | Nullable<double> | HeatCapacity |
| `+0x50` | ptr | CellData (FuelCellData; null for non-fuel) |
| `+0x70..0xA7` | struct | HeatData |
| `+0xC8` | byte | ReflectsPulses / IsReflector (provides boost + takes pulse damage) |
| `+0xC9` | byte | AbsorbsNeighborHeat (vents/exchangers receive fuel heat) |
| `+0xCA` | byte | IsHeatSource / CantLoseHeat (prevents receiving heat in exchange) |

## ComponentCategory Enum (TypeOfComponent at +0x14)

| Value | Category | Special Behavior |
|-------|----------|-----------------|
| 0x0A (10) | Reflector | +0xC8=1, takes pulse damage, provides power boost |
| 0x0B (11) | Capacitor | ReactorHeatCapacityIncrease |
| 0x0C (12) | Plating | ReactorPowerCapacityIncrease |
| 0x0D (13) | Coolant | ReactorHeatCapacityIncrease; tier 6 = ExtremeCoolant (absorbs 10% heat radius 2) |
| 0x10 (16) | Protium | Permanent +1% power per depleted cell (Reactor+0x38 counter) |
| 0x11 (17) | Monastium | 7×7 density penalty (2% per occupied cell) |
| 0x12 (18) | Kymium | Cosine pulsation (4 cycles over lifetime) |
| 0x13 (19) | Discurrium | 4 pulses/core (PulsesPerCore=4 in stats, no special code) |
| 0x14 (20) | Stavrium | Pulses spread to entire row+column (not just 4 neighbors) |

## Stat IDs (used in GetStatCached / GetUpgradeStatBonus)

| ID | Name | Used In |
|----|------|---------|
| 1 | MaxDurability | Kymium phase calc, durability checks |
| 2 | HeatCapacity | Heat exchange redistribution |
| 3 | EnergyPerPulse | Power generation (via fn 10446) |
| 4 | HeatPerPulse | Heat generation (via fn 10444) |
| 5 | PulsesProduced | Pulse distribution, durability drain |
| 6 | SelfVentRate | Vent heat to air (fn 10437) |
| 8 | ReactorVentRate | Exchange with reactor hull (fn 10436) |
| 9 | HeatExchangeRate | Cell-to-cell heat exchange (fn 10424) |
| 12 | ReactorPowerCapacityIncrease | Power cap computation |
| 0x11 (17) | CoolantSelfVentRate | Global vent rate multiplier |
| 0x13 (19) | TicksPerSecond | Cached in LogicalUpdate |
| 0x14 (20) | CellEffectiveness | Overheat multiplier |
| 0x15 (21) | ReactorPowerCapacity | Global power cap multiplier |
| 0x16 (22) | HeatExchangeRateGlobal | Global exchange rate multiplier |
| 0x17 (23) | HeatCapacityGlobal | Global heat cap multiplier |
| 0x18 (24) | ReflectorEffectiveness | Reflector neighbor power boost |

## Shared Helpers

### GetNeighborOffsets — Cardinal (unnamed_function_10439)
- Returns list of 4 offsets: `-1`, `+1`, `-gridWidth`, `+gridWidth` (with bounds checking)

### GetNeighborOffsets — Radius (unnamed_function_10440)
- Parameters: `(Reactor, cellIndex, radius, filterMode)`
- `filterMode=0`: Manhattan distance filter (diamond shape)
- `filterMode≠0`: full square
- Returns `List<int>` of linear offsets

### GetStatCached (unnamed_function_10370)
- Cached lookup of `(componentType, statId)` → double
- Special scaling for ComponentCategory 8,9 using global multipliers at `+0x28`

### GetUpgradeStatBonus (unnamed_function_10371)
- Aggregates additive + multiplicative upgrade bonuses for `(category, statId)`

### OnSolutionChanged (unnamed_function_10391)
- Checks dirty flag at `+0x69`, rebuilds caches at `+0x48..+0x64` if set

### Player.get_Instance (unnamed_function_10344)
- Singleton accessor; Player stores stats at various offsets (+0x08=money, +0x18=totalPowerGenerated, etc.)
