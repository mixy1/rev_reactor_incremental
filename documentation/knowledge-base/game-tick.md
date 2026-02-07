# Game Tick Observations (partial)

## Tick-related calls seen in ShopManager_RefreshAllButtons

- `Simulation_TickGeneratePowerAndHeat(sim)` (called by `unnamed_function_10426`)
  - Writes a `double` output via pointer (local `param_3`), then:
    - `ResourceStore + 0x38 += param_3`
    - `ResourceStore + 0x20 += param_3`
  - Meaning of these two ResourceStore fields is still unclear.

- `Simulation_Tick(sim, &outA, &outB)` (called by `unnamed_function_10427`)
  - Decrements `*(param1 + 0x30)` by `outA` (likely “stored power/heat” in a manager object).
  - Adds `outB` to `ResourceStore + 0x38` and `ResourceStore + 0x20`.

- `unnamed_function_10429(reactor, controller?, &param1+0x30, &outPowerSold)` (called by `unnamed_function_10428`)
  - Produces `outPowerSold` which is then converted to money:
    - `ResourceStore + 0x08 += outPowerSold`
    - `ResourceStore + 0x28 += outPowerSold`
    - `ResourceStore + 0x40 += outPowerSold`

## Tick entry points (wasm addresses)

- `Simulation_Tick` → `0x8022b7f1` (called by `unnamed_function_10427`)
  - Callees include `Simulation_GetStatCached` and `ReactorUIHandler_RefreshComponentStatsIfDirty`.
  - Performs an iterator loop over components; uses cached stat lookups per entry.
- `Simulation_TickGeneratePowerAndHeat` → `0x8022b972` (called by `unnamed_function_10426`)
  - Callees include `Simulation_GetStatCached` and `ReactorUIHandler_RefreshComponentStatsIfDirty`.
- `Simulation_TickVentReactor` → `0x8022bad9` (called by `unnamed_function_10425`)
  - Uses `Simulation_GetNeighborOffsets` and multiple iterator helpers.
  - Calls `Il2CppObject_New` (allocs scratch objects/arrays) and `Simulation_GetStatCached`.
- `Simulation_TickVentHeat` → `0x8022cd7c` (not yet analyzed in detail).

## Tick field offsets (observed in wasm)

**Simulation**
- `+0x24` → component list (struct with count at `+0x0C`, items at `+0x10 + i*0x20`)
- `+0x28` → double store drained by `Simulation_Tick`
- `+0x40` → double store reduced by `Simulation_Tick`
- `+0x70` → double scale factor used by `Simulation_TickGeneratePowerAndHeat`
- `+0x18/+0x1C` → grid width/height used by `Simulation_GetNeighborOffsets`

**Component entry (from the list)**
- `+0x18` → ComponentType pointer (used in stat lookups)
- `+0x20` → double store reduced by `Simulation_TickVentHeat`
- `+0x28` → double store drained by `Simulation_TickGeneratePowerAndHeat`
- `+0x40` → byte flag used to gate `Simulation_TickVentHeat`

**ComponentType**
- `+0xC8` → byte flag that enables neighbor processing in `Simulation_TickVentHeat`

## Scrounge/Sell power

- `Controller_ClickedSellButton` implements **Scrounge for cash (+1$)** and **Sell All Power**.
  - If `Reactor_CountPlacedComponents(reactor) == 0` and `(currentMoney + storedPower) < 10`:
    - Adds `+1` to `ResourceStore + 0x08/+0x28/+0x40`.
  - Else:
    - Adds `storedPower` to `ResourceStore + 0x08/+0x28/+0x40` and zeroes `storedPower`.

## Implicit Pause During UI Panels — fn 10408 (Controller.Update)

**Lines**: 387652-387665 in decompiled C

The game implicitly pauses simulation ticks when a UI panel (upgrades, prestige, etc.)
is open, **without** toggling the manual pause flag.

```c
// param1 = Controller
piVar7 = *(int **)(param1 + 0x28);   // line 387220: pointer to active panel reference
piVar8 = (int *)(param1 + 0x8c);     // Simulation pointer

if (*(char *)(param1 + 0xa0) == '\0') {   // Controller+0xA0 = manual pause flag
    bVar1 = *piVar7 == 0;                  // *Controller+0x28 == 0 → no panel open
} else {
    bVar1 = false;                         // manually paused → don't run
}

if (bVar1) {
    unnamed_function_10418(*piVar8, 0);    // run tick loop
} else {
    // Reset tick timer to Time.time — prevents tick catch-up on unpause
    iVar13 = *piVar8;
    fVar4 = unnamed_function_16432(0, 0);  // Time.time
    *(float *)(iVar13 + 0x20) = fVar4;
}
```

**Key fields**:
- `Controller+0xA0` (byte): manual pause toggle (0 = running, 1 = paused)
- `Controller+0x28` (int**): indirect pointer to active UI panel object
  - `*Controller+0x28 == 0` → no panel open → ticks can run
  - `*Controller+0x28 != 0` → panel open → ticks suppressed
- `Controller+0x8C` (int*): Simulation pointer

**Behavior**:
- Ticks run ONLY when: `NOT manually_paused AND no_panel_open`
- When either condition is false, the tick timer is reset to current time
- This prevents accumulated time from causing a burst of ticks when resuming
- The manual pause button state is NOT affected by panel open/close

**Panel pointer lifecycle**:
- Set to non-null when UI panels (upgrades, prestige, etc.) are created via `fn 25204`
- Stored at `Controller+0x28` by the panel creation functions
- Set to null when panels are closed/dismissed

**Implementation**: `main.py` — ticks run only when `not sim.paused and sim.view_mode == "reactor"`;
`_tick_accumulator` is reset to 0 in the else branch to match the binary's timer reset.

## Open questions

- Exact meaning of ResourceStore offsets `0x20/0x38` and the object field at `reactor + 0x30`.
- Stats panel label mapping currently conflicts with scrounge logic (see `ui-decompilation-notes.md`).
