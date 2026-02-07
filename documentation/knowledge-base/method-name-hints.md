# Method Name Hints (from metadata string table)

These names are present in the IL2CPP string table (global-metadata string section).
They likely correspond to method names even when call‑site xrefs are missing
(UnityEvent / reflection / delegates).

## Sell / Power related

- `Controller.ClickedSellButton` (methodIndex 10247)
- `Controller.TrySellComponent` (10250)
- `Controller.SellAllComponentsOfType` (10251)
- `Reactor.TrySellComponent` (10332)
- `Reactor.SellAllComponentsOfType` (10333)
- `Reactor.GetAutoSellRate` (10353)
- `Reactor.AutoSellPower` (10356)
- `Reactor.ManuallySellPower` (10357)
- `Simulation.ManuallySellPower` (10447)
- `UpgradeManager.GetManualSellMultiplier` (10494)

## UI element names seen

- `SellPowerButton`
- `PowerGenerationPageButton`
- `PowerBar`
- `PowerLabel`

## Scene stub hints

From `decompilation/recovered/recovered_analysis/scene_class_stubs_v2.md`:
- `Controller` has field `SellPowerButton` and method `ClickedSellButton(1)`.
- `Button` class exposes `ClickedAction` and `SetLabel(1)`, consistent with Unity-style
  click wiring (likely done in `Controller.SetButtonFunctionality` / `Controller.Setup`).

## Notes

- Method indices above are from `decompilation/recovered/recovered_metadata/assembly_csharp_types_v2.json`.
- We still need to map `methodIndex -> wasm function` (likely via codegen module tables).
- Mapped in Ghidra: `Controller.ClickedSellButton` → `Controller_ClickedSellButton` (was `unnamed_function_10508`).
- Mapped in Ghidra: `Controller.SetButtonFunctionality` → `Controller_SetButtonFunctionality` (was `unnamed_function_10217`).
- Mapped in Ghidra:
  - `Controller.Awake` → `Controller_Awake` (was `unnamed_function_10219`)
  - `Controller.Update` → `Controller_Update` (was `unnamed_function_10220`)
  - `Controller.Reset` → `Controller_Reset` (was `unnamed_function_10221`)
  - `Controller.Prestige` → `Controller_Prestige` (was `unnamed_function_10222`)
  - `Controller.HandleInput` → `Controller_HandleInput` (was `unnamed_function_10223`)
  - `Controller.Setup` → `Controller_Setup` (was `unnamed_function_10224`)
  - `Controller.ClickedUpgradeButton` → `Controller_ClickedUpgradeButton` (was `unnamed_function_10225`)
  - `Controller.ClickedPrestigeUpgradeButton` → `Controller_ClickedPrestigeUpgradeButton` (was `unnamed_function_10226`)
  - `Controller.ClickedOptionsButton` → `Controller_ClickedOptionsButton` (was `unnamed_function_10227`)
  - `Controller.RefreshResetButtonLabel` → `Controller_RefreshResetButtonLabel` (was `unnamed_function_10228`)
  - `Controller.RefreshPrestigeButtonLabel` → `Controller_RefreshPrestigeButtonLabel` (was `unnamed_function_10229`)
  - `Controller.ClickedResetButton` → `Controller_ClickedResetButton` (was `unnamed_function_10230`)
  - `Controller.ClickedPrestigeButton` → `Controller_ClickedPrestigeButton` (was `unnamed_function_10231`)
  - `Controller.ClickedBackButton` → `Controller_ClickedBackButton` (was `unnamed_function_10232`)
  - `Controller.ClickedHelpButton` → `Controller_ClickedHelpButton` (was `unnamed_function_10233`)
  - `Controller.ClickedImportButton` → `Controller_ClickedImportButton` (was `unnamed_function_10234`)
  - `Controller.ClickedExportButton` → `Controller_ClickedExportButton` (was `unnamed_function_10235`)
  - `Controller.SelectHelpButton` → `Controller_SelectHelpButton` (was `unnamed_function_10236`)
  - `Controller.SelectStatsButton` → `Controller_SelectStatsButton` (was `unnamed_function_10237`)
  - `Controller.ChangeState` → `Controller_ChangeState` (was `unnamed_function_10238`)
  - `Controller.OnUpgradePurchased` → `Controller_OnUpgradePurchased` (was `unnamed_function_10239`)
  - `Controller.OnSolutionChanged` → `Controller_OnSolutionChanged` (was `unnamed_function_10240`)
  - `Controller.GetShouldReplaceCells` → `Controller_GetShouldReplaceCells` (was `unnamed_function_10241`)
  - `Controller.SetPaused` → `Controller_SetPaused` (was `unnamed_function_10242`)
  - `Controller.SetShouldReplace` → `Controller_SetShouldReplace` (was `unnamed_function_10243`)
  - `Controller.GetIsSimPaused` → `Controller_GetIsSimPaused` (was `unnamed_function_10244`)
  - `Controller.PrintPrettyDouble` → `Controller_PrintPrettyDouble` (was `unnamed_function_10245`)
  - `Controller.ClickedVentButton` → `Controller_ClickedVentButton` (was `unnamed_function_10246`)
  - `Controller.BuyComponent` → `Controller_BuyComponent` (was `unnamed_function_10248`)
  - `Controller.ReplaceAllComponentsOfType` → `Controller_ReplaceAllComponentsOfType` (was `unnamed_function_10249`)
  - `Controller.TrySellComponent` → `Controller_TrySellComponent` (was `unnamed_function_10250`)
  - `Controller.SellAllComponentsOfType` → `Controller_SellAllComponentsOfType` (was `unnamed_function_10251`)
  - `Controller.OnComponentSuccessfullySold` → `Controller_OnComponentSuccessfullySold` (was `unnamed_function_10252`)
  - `Controller.CanAffordReplacement` → `Controller_CanAffordReplacement` (was `unnamed_function_10253`)
  - `Controller.FormatInfoBar` → `Controller_FormatInfoBar` (was `unnamed_function_10254`)
  - `Controller..cctor` → `Controller__cctor` (was `unnamed_function_10255`)

## Notes on mapping

- `unnamed_function_10247` was **not** renamed yet: it’s called by `Controller_CanAffordReplacement`
  and contains heavy integer math (`_muldi3/_udivdi3/_i64Add`), which does **not** look like a click handler.
  Need to verify which wasm function corresponds to `Controller.ClickedSellButton` before renaming.
