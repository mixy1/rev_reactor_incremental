# Stat ID Map (Category enum)

Source: `Category` enum in `assembly_csharp_types_v2.json` (Assembly-CSharp).
Assumes enum values are assigned in declaration order (0..N).

## Category enum values

| id | name |
|---:|------|
| 0 | None |
| 1 | MaxDurability |
| 2 | HeatCapacity |
| 3 | EnergyPerPulse |
| 4 | HeatPerPulse |
| 5 | PulsesProduced |
| 6 | SelfVentRate |
| 7 | AdjacentVentRate |
| 8 | ReactorVentRate |
| 9 | AdjacentTransferRate |
| 10 | ReactorTransferRate |
| 11 | ReactorHeatCapacityIncrease |
| 12 | ReactorPowerCapacityIncrease |
| 13 | ManualSell |
| 14 | ManualVent |
| 15 | AutoSellRate |
| 16 | AutoVentRate |
| 17 | VentEffectivenessPerComponent |
| 18 | ReplacesSelf |
| 19 | TicksPerSecond |
| 20 | CellEffectiveness |
| 21 | VentCapacityPerComponent |
| 22 | ExchangerEffectivenessPerComponent |
| 23 | ExchangerCapacityPerComponent |
| 24 | ReflectorEffectiveness |
| 25 | ComponentDiscount |
| 26 | UpgradeDiscount |

## Observed usage in wasm (validated for ids 1–12)

- `ComponentType_GetBaseStatByCategory` (was `unnamed_function_10310`) uses a **switch on stat id 1–12** and reads fixed fields from the ComponentType instance. This matches the `Category` enum order.
- That confirms:
  - `1 = MaxDurability`
  - `2 = HeatCapacity`
  - `3 = EnergyPerPulse`
  - `4 = HeatPerPulse`
  - `5 = PulsesProduced`
  - `6 = SelfVentRate`
  - `7 = AdjacentVentRate`
  - `8 = ReactorVentRate`
  - `9 = AdjacentTransferRate`
  - `10 = ReactorTransferRate`
  - `11 = ReactorHeatCapacityIncrease`
  - `12 = ReactorPowerCapacityIncrease`

## Observed usage in wasm (with mapped ids)

- `Simulation_GetStatCached(..., 1, ...)` → `MaxDurability` (used in component UI bars).
- `Simulation_GetStatCached(..., 2, ...)` → `HeatCapacity` (used in component UI bars).
- `Simulation_GetStatCached(..., 4, ...)` → `HeatPerPulse` (used in `Simulation_CreateComponent` cost formula).
- `Simulation_GetStatCached(..., 5, ...)` → `PulsesProduced` (used in `Simulation_TickVentHeat`).
- `Simulation_GetStatCached(..., 6, ...)` → `SelfVentRate` (used in `Simulation_TickGeneratePowerAndHeat`).
- `Simulation_GetStatCached(..., 8, ...)` → `ReactorVentRate` (used in `Simulation_Tick`).
- `Simulation_GetStatCached(..., 12, ...)` → `ReactorPowerCapacityIncrease` (used in `ShopManager_SetShownShopPage`).
- `Simulation_GetStatCached(..., 11, ...)` → `ReactorHeatCapacityIncrease` (used in `Simulation_LoadComponent`).
 
See `componenttype-layout.md` for inferred `ComponentType` offsets and how these stats are sourced.

## Notes

- If any enum values are explicitly assigned in source, this table could be wrong, but the `ComponentType_GetBaseStatByCategory` switch strongly suggests the current ordering is correct.
- Next step: resolve what the `ComponentType` fields at `+0x30/+0x40/+0x50/+0x70/+0xa8/+0xb8` correspond to (names from metadata vs. runtime layout).
