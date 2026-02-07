# ComponentType Layout (inferred from wasm)

This is a **best‑effort** field layout for `ComponentType` inferred from `ComponentType_GetBaseStatByCategory` and related helpers. Offsets are the runtime wasm offsets seen in decompilation, not guaranteed IL2CPP field offsets.

## Mapped offsets (runtime / wasm)

| offset | inferred field | notes |
|---:|---|---|
| `+0x30` | `MaxDurability` | read via `ComponentType_GetBaseStatByCategory(1)` |
| `+0x40` | `HeatCapacity` | read via `ComponentType_GetBaseStatByCategory(2)` |
| `+0x50` | `CellData` (FuelCellData) | used for stats 3–5 via `unnamed_function_4285` |
| `+0x70` | `HeatData` (HeatManagementData) | used for stats 6–10 via `unnamed_function_4308` |
| `+0xA8` | `ReactorHeatCapacityIncrease` | used for stat 11 |
| `+0xB8` | `ReactorPowerCapacityIncrease` | used for stat 12 |

## Category → source data (validated)

`ComponentType_GetBaseStatByCategory` uses a switch on stat id (1–12):

- 1 `MaxDurability` → `+0x30`
- 2 `HeatCapacity` → `+0x40`
- 3 `EnergyPerPulse` → `CellData`
- 4 `HeatPerPulse` → `CellData`
- 5 `PulsesProduced` → `CellData`
- 6 `SelfVentRate` → `HeatData`
- 7 `AdjacentVentRate` → `HeatData`
- 8 `ReactorVentRate` → `HeatData`
- 9 `AdjacentTransferRate` → `HeatData`
- 10 `ReactorTransferRate` → `HeatData`
- 11 `ReactorHeatCapacityIncrease` → `+0xA8`
- 12 `ReactorPowerCapacityIncrease` → `+0xB8`

## Notes

- `CellData` appears to be `FuelCellData` / `FuelCellTemplate` style data (Energy/Heat per pulse + pulses produced).
- `HeatData` aligns with `HeatManagementData` (vent/transfer rates).
- If IL2CPP field offsets differ, we’ll adjust based on serialized data and IL2CPP metadata resolution.
