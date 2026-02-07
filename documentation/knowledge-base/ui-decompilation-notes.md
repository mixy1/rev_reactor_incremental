# UI / Shop Decompilation Notes

## ShopManager (selected methods)

### ShopManager_Update (was `unnamed_function_10411`)
- Large UI update routine.
- Iterates multiple UI elements from `param1 + 0x2C` (likely `Root` or page buttons list).
- Performs many UI text updates via helper calls (string formatting / localization helpers).
- Uses `param1 + 0x88` to branch (likely active page or mode).
- References methods that look like:
  - `unnamed_function_10450`, `10451`, `10452`, `10453`, `10454`, `10455`, `10456` — likely formatting/visibility helpers.
  - `Simulation_GetStatCached` for stat lookup.

### ShopManager_RefreshAllButtons (was `unnamed_function_10419`)
- Clears cached fields at `param1 + 0x30..0x3C`.
- Calls a set of helpers: `10422..10428` (likely per‑page button refresh + layout).
- Updates `param1 + 0x40..0x4C` from formatted string results.
- Appears to recompute UI text buffers and selection state.

### ShopManager_RefreshButtonState (was `unnamed_function_10420`)
- If `param1 + 0x40` is empty, computes a value via `unnamed_function_10421` and stores a formatted string.
- Returns `unnamed_function_4374(param1 + 0x40, ...)` (likely string to double or formatted value).

### ShopManager_SetShownShopPage (was `unnamed_function_10413`)
- Computes a double value (starts with `unnamed_function_10371(..., arg=0xC)` scaled by 100).
- Adds per‑component contributions via `Simulation_GetStatCached(..., arg=0xC)`.
- Stores formatted result into `param1 + 0x58..0x64`.
- Returns formatted numeric via `unnamed_function_4374(param1 + 0x58, ...)`.

### ShopManager_OnBuyableComponentSelected (was `unnamed_function_10417`)
- Returns `Simulation.LogicalUpdate * SetShownShopPage * 0.01`.
- This likely computes a normalized value or UI percent when selecting a component.

## UpgradeShopManager

### UpgradeShopManager_Update (was `unnamed_function_10502`)
- Only sets two flags: `param1 + 0xA1` and `param1 + 0x84`.
- Likely marks UI as dirty or toggles visibility.

## BuyableComponent

### BuyableComponent_RefreshAppearance (was `unnamed_function_10197`)
- Thin wrapper over `unnamed_function_24266` (unknown helper).
- Probably applies sprite/opacity state based on `isSelected`/`canAfford`.

### BuyableComponent_Setup (was `unnamed_function_10191`)
- Thin wrapper over `unnamed_function_24256` (unknown helper).
- Likely initializes a BuyableComponent UI entry (labels/sprite/button handlers).

## Button (metadata method indices ~10182–10189)

### unnamed_function_10189 (likely `Button.SetLabel`, metadata index 10189)
- Wrapper: `return unnamed_function_24256(this)`; ignores other params.
- Called from `BuyableComponent_Setup` and an internal helper at `0x80208c13`.
- `unnamed_function_24256` does:
  - `tmp = unnamed_function_17440(*(this + 0x8))`
  - `return *(tmp + 0x94)`
- `unnamed_function_17440` does: `return unnamed_function_17426(*(param + 0x8))`.
- Net effect: fetches a pointer at `(*(unnamed_function_17426(*(this+0x8))) + 0x94)`.
- **Interpretation:** likely a cached child UI component (label/text), not yet confirmed.

### unnamed_function_10187 (likely `Button.OnMouseUpAsButton`, metadata index 10187)
- Disassembly summary (no decompiler output; server errors):
  - One‑time call gate using flag at `0x1669f4`. On first call:
    - Loads `*(0x4a448)` and calls `unnamed_function_24203` (large helper).
    - Sets flag to 1.
  - Then calls `unnamed_function_27942(local1, *(0x133bd0))`.
  - Returns `(i16_s from result) - (i16_u from second call)` masked to `0xFFFF`.
- **Interpretation:** looks like a compare or input state delta; needs deeper pass.

### unnamed_function_10186 / unnamed_function_10188
- Both compute `(param1 & 0xFFFF) - (param2 & 0xFFFF)` and return.
- Likely helper compare/diff; not enough context yet.

## Controller button wiring (metadata index ~10217)

### Controller_SetButtonFunctionality (was `unnamed_function_10217`)
- Wrapper: `return unnamed_function_24276(param1, param2, param3)`.
- Renamed based on metadata index mapping.

### unnamed_function_10216
- Wrapper: `return unnamed_function_24276(param1, 1, 1)`.
- Likely “enable + visible” or similar default button state.

### unnamed_function_10228
- Wrapper: `return unnamed_function_24276(param1, 0, 0)`.
- Likely “disable + hidden” or similar default button state.

### unnamed_function_10219
- Lazy‑init helper:
  - One‑time call gate using flag at `0x1669fe`, calls `unnamed_function_24203(*(0x4902c))`.
  - If `*(param1 + 0xC)` is null: allocates via `*(0x133d38)` and `unnamed_function_807fda6a`, stores it.
  - If `*(param1 + 0x8)` is null: calls `unnamed_function_24276(param1, 1, 0)` and stores it.
  - Returns the cached object at `*(param1 + 0x8)`.

### unnamed_function_24276 (core helper)
- Called by: `Controller_SetButtonFunctionality`, `unnamed_function_10216`, `unnamed_function_10219`, `unnamed_function_10228`.
- Large helper with multiple branches and calls to `unnamed_function_24931`, `unnamed_function_24410`, `unnamed_function_24496`.
- Likely central UI state/interaction handler; needs deeper pass for field mapping.
- Chooses a mode value `1/2/3` based on `(param2,param3)` and passes it to `unnamed_function_24496`.
- `unnamed_function_24496` zeros a 3‑int buffer then calls `unnamed_function_24493` (large dispatcher).
 - `unnamed_function_24410` is a thin wrapper over `unnamed_function_25379`.
 - `unnamed_function_24931` checks byte at `param + 0x14`; if negative, calls `unnamed_function_13031` (trap/exception path).

## Controller main flow (metadata 10219–10229)

### Controller_Awake (was `unnamed_function_10219`)
- Lazy‑init helper (see above in button wiring).

### Controller_Update (was `unnamed_function_10220`)
- Calls `unnamed_function_10173` and `unnamed_function_24336` (large UI helper).
- Uses one‑time init gate similar to other UI init patterns (`unnamed_function_24203`).

### Controller_Reset (was `unnamed_function_10221`)
- Calls `unnamed_function_10170` and `unnamed_function_24336`.
- Similar initialization pattern as Update.

### Controller_Prestige (was `unnamed_function_10222`)
- Calls `unnamed_function_10166`, `unnamed_function_24336`, `unnamed_function_24379`, plus init gate.
- More complex than Reset/Update (extra helper paths).

### Controller_HandleInput (was `unnamed_function_10223`)
- Uses `call_indirect` through vtable-ish tables at offsets from `param1`.
- Likely routes input to sub‑components based on state flags.

### Controller_Setup (was `unnamed_function_10224`)
- Wrapper: `return unnamed_function_24261(param1, param2)`.
- `unnamed_function_24261` is a large helper; likely the core UI wiring method.
  - Uses string table pointer `0x105364` ("ConstructorInfo") via `unnamed_function_25387`.
  - Checks `(*(param1 + 0x8 + 0x4) & 0x40000000)` before calling `unnamed_function_24410`.
  - Calls `unnamed_function_25379` and `unnamed_function_24931` at the end of the setup path.
  - **Observation:** this is the only xref to the "ConstructorInfo" string.
  - **Inference:** `unnamed_function_25387` likely constructs a managed string from the ASCII table entry
    (uses string helpers `26036/26044/25890`); treat as tentative.

### Controller_ClickedUpgradeButton (was `unnamed_function_10225`)
- Wrapper: `return unnamed_function_24262(param1)`.

### Controller_ClickedPrestigeUpgradeButton (was `unnamed_function_10226`)
- Wrapper: `return unnamed_function_24260(param1)`.

### Controller_ClickedOptionsButton (was `unnamed_function_10227`)
- Wrapper: `return unnamed_function_24257(param1)`.

### Controller_RefreshResetButtonLabel (was `unnamed_function_10228`)
- Wrapper: `return unnamed_function_24276(param1, 0, 0)`.

### Controller_RefreshPrestigeButtonLabel (was `unnamed_function_10229`)
- Wrapper: `return unnamed_function_24277(param1)`.

### Controller_ClickedResetButton (was `unnamed_function_10230`)
- Uses `call_indirect` through vtable-like tables and iterates a list; complex UI logic.
- Calls `unnamed_function_6209` at end (likely modal/confirm flow).

### Controller_ClickedPrestigeButton (was `unnamed_function_10231`)
- Wrapper: `return unnamed_function_24259(param1)`.

### Controller_ClickedBackButton (was `unnamed_function_10232`)
- Uses `unnamed_function_6262` + `unnamed_function_9830` and init gating (`unnamed_function_24203`).
- Likely handles returning from sub‑menus.

### Controller_ClickedHelpButton (was `unnamed_function_10233`)
- Loops and calls `unnamed_function_4833` and `unnamed_function_27537`.
- Likely toggles help overlay/panel.

### Controller_ClickedImportButton (was `unnamed_function_10234`)
- Wrapper: `return unnamed_function_4834(param1, 1)`.

### Controller_ClickedExportButton (was `unnamed_function_10235`)
- Large routine; allocates objects and writes out state.
- Uses `unnamed_function_27530/27531/27536/27543` and `unnamed_function_24336`.
- Probably export/serialization flow.

### Controller_SelectHelpButton (was `unnamed_function_10236`)
- Uses `unnamed_function_2367/6021/4825/27536` and `call_indirect` loops.
- Likely selects help tab and updates UI lists.

### Controller_SelectStatsButton (was `unnamed_function_10237`)
- Wrapper: `return unnamed_function_4833(param1, param2, 1)`.

### Controller_ChangeState (was `unnamed_function_10238`)
- Mutates `param1 + 0xC` to 1, loops through list pointers and uses `unnamed_function_4833`.
- Called by `Controller_OnUpgradePurchased`.

### Controller_OnUpgradePurchased (was `unnamed_function_10239`)
- Calls `Controller_ChangeState` after init gate (`unnamed_function_24203`).
- Likely updates UI/state on upgrade purchase.

## Controller misc (metadata 10240–10255)

### Controller_OnSolutionChanged (was `unnamed_function_10240`)
- Init gate via `unnamed_function_24203`, then calls `unnamed_function_27930` and `unnamed_function_2367`.
- Likely reacts to a change in reactor solution/placement.

### Controller_GetShouldReplaceCells (was `unnamed_function_10241`)
- Wrapper with two helper calls: `unnamed_function_27930` + `unnamed_function_10568`.
- Returned value likely depends on a controller flag/state.

### Controller_SetPaused (was `unnamed_function_10242`)
- Init gate via `unnamed_function_24203`, uses `unnamed_function_27930` + `unnamed_function_10568`.

## Money / number formatting

### FormatNumberWithSuffix (ram:8020e34f)
- **Inputs:** `(param1, value: double, param3)`; returns a string.
- **Core logic:**
  - If `value == 0.0`: returns `"0"`.
  - `exp = floor(log10(abs(value)))`.
  - If `exp < -2`: `group = 0`, else `group = int(exp / 3)` (C-style trunc toward zero).
  - `scale = 10^(group * 3)`, `scaled = value / scale`, `int_part = trunc(scaled)`.
  - If `value < 0` and `int_part >= 0`, prepend `"-"` (handles `-0.xxx`).
  - `frac = abs((scaled - int_part) * 1000)`, `frac_int = trunc(frac)`.
    - If `frac_int >= 1`, append decimal separator, pad to 3 digits, append `frac_int`.
    - Then `TrimEnd("0,")` (removes trailing zeros and commas).
  - Append suffix string at index `group` from the label list built in `UI_InitLabelList_All`.

### Suffix list source
- `UI_InitLabelList_All` (ram:80230feb) constructs a 22‑entry list (first entry is empty).
- The suffix string block appears in `Build.data` between `"Power Per Tick: "` and `"BuildVersion"`:
  - `KBTQaQiSxSpONUDDDTDQuDQaDSxDSpDODNDV`

## Shop layout (implementation heuristic)

We still need to extract the `Dictionary<ComponentType, Index2>` tables from wasm. For now the implementation
uses **metadata-derived** category + tier info to place items into a 5-column grid.

Current placement logic (temporary):
- **Power page**: Fuel 1–6 in rows 0–5 (cols 0/2/4 for 1/2/4‑core). Capacitor tiers 1–5 on row 6 (cols 0–4).
- **Heat page**: Vent / Exchanger / Coolant / Inlet / Outlet mapped to columns 0–4, row by tier (1–5).
  - Coolant tier 6 (Extreme) is routed to Experimental page.
- **Experimental page**: Reflector (col 0) + Plating (col 1) row by tier; Extreme Capacitor (col 2, row 5);
  Extreme Coolant (col 3, row 5).
- **Arcane page**: Fuel 7–11 in rows 0–4 (cols 0/2/4 for 1/2/4‑core) plus Clock/Infinity placeholder on row 6.

**TODO:** locate the real page dictionaries (PowerGenerationPage / HeatManagementPage / ExperimentalComponentsPage)
in wasm and replace the heuristic mapping with exact `Index2` positions + unlock logic.
- Parsed into tokens (capital letter + optional lowercase, with explicit `*D` tiers):
  - `["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "O", "N", "U", "D", "DD", "TD", "QuD", "QaD", "SxD", "SpD", "OD", "ND", "V"]`
  - **Note:** `"M"` is inferred to match the 22‑entry list length (21 suffixes + empty); the concatenated block does not include an obvious `"M"` token.

## Grid / placement (ReactorUIHandler)

### ReactorUIHandler_GridToLocal (ram:8021ad97)
- Converts grid coordinates to local space using **32px cells**:
  - `local = (x << 5, y << 5)` (multiply by 32).
  - Adds per‑layer offsets from a layer table: `+ (layer.offsetX << 5, layer.offsetY << 5)` using fields at `+0x18/+0x1c`.
  - If layer flag at `+0x20` is set, adds `(+16, +16)` (half‑cell offset).

### ReactorUIHandler_PlaceComponentAtGrid (ram:8021a1bf)
- Linear index formula for grid cache:
  - `index = ((height * layer) + y) * width + x`
  - `width = *(param1 + 0x18)`, `height = *(param1 + 0x1c)`, `layer = param3[2]`.
- Grid cache pointer at `param1 + 0x24`.
- Component pointer stored at `grid_cache + 0x10 + index * 0x20`.
- After placement: `ReactorUIHandler_SetComponentTransform` + `ReactorUIHandler_UpdateComponentStatsUI`.

### ReactorUIHandler_RebuildGridFromComponents (ram:80219b01)
- Computes `width/height` as **max** of per‑layer extents (layer entries at `iVar13 + 0x10 + i*0x14`).
- `depth = layer_count` stored at `param1 + 0x20`.
- Allocates grid cache sized `width * height * depth`.
- Calls `ReactorUIHandler_BuildGridTiles` which loops **x/y/layer** and skips non‑placeable cells.

### ReactorUIHandler_BuildGridTiles (ram:8021afb3)
- Triple nested loop: `for x in width`, `for y in height`, `for layer in depth`.
- Calls `ReactorUIHandler_IsCellPlaceable` before instantiating a tile.
- Uses `GridToLocal` and builds extents with `±16` offsets for bounds.

## Shop / store flow (ShopManager)

### ShopManager_UpdatePriceLabel (ram:8022e600)
- Fetches price from `*(label + 0x10) + 0x28` (double).
- Compares to `ResourceStore_GetSingleton()->money` at offset `+8`.
- If affordable: uses `DAT_ram_00135604` template (likely “Buy”/price).
- If not: uses `DAT_ram_00135600` template (likely “Can’t afford”/disabled).

### ShopManager_SetHoverComponentInfo (ram:8022e9b0)
- Uses the same grid cache indexing formula as `ReactorUIHandler_PlaceComponentAtGrid`.
- If a component exists at hovered cell, formats info via `DAT_ram_001356cc`.
- If not, sets label to `DAT_ram_001355c4` (blank/empty).

### ShopManager_OnPlaceTypeInput / OnSellTypeInput
- `ShopManager_OnPlaceTypeInput` → `ReactorUIHandler_TryPlaceComponentType`.
- `ShopManager_OnSellTypeInput` → `ReactorUIHandler_SellComponentsOfType`.

### Store icon button assets
- `IconButton`, `IconHoverButton`, `IconClickedButton`, `IconButtonLocked` sprites are **48x52**.
- Likely used for shop grid slots (component icons are 32x32, centered).

### Unity layout anchor for store grid
- `Shop Root` RectTransform top-left: `(7, 247)` size `(64, 64)` in the 900x630 canvas.
- Used as the store slot anchor in the prototype layout until we decode ShopManager positioning logic.

### SideGrid store container (asset-derived)
- `SideGrid.png` contains a distinct store area fill color; bounding box is `(15, 265)` size `(240, 302)`.
- Prototype now anchors the store slots inside this container (derived directly from the UI asset).
- Horizontal separators inside the store area imply row height `30` with separator height `4` (9 rows total).
- Store items are 5 columns; only the shop page buttons are 4 columns.
- Item cells are drawn directly on the panel background (no per-item block background).
- Shop list now sourced from `ComponentTypes` field order in `assembly_csharp_types_v2.json` (mapped to sprites), with a fallback to `monobehaviour_index.csv`. Excludes depleted (`-e`) and GenericHeat/GenericPower variants. Current page grouping is derived from component names (Fuel 1-6 + Capacitor -> Power, vents/coolants/exchangers/reflectors/plates/inlets/outlets -> Heat, Clock/GenericInfinity -> Experimental, Fuel 7-11 -> Unknown). Prestige gating is still provisional.

### Recovered component list (source data)
- `decompilation/recovered/recovered_mono/monobehaviour_index.csv` contains many component GameObject names
  (Fuel/Coolant/Capacitor/etc). These are used to seed the store list in the Python prototype until the full
  ComponentType data is decoded.
- Very hot call target (many xrefs) — appears to be central pause toggle.

### Controller_SetShouldReplace (was `unnamed_function_10243`)
- Similar shape to `SetPaused`; uses `unnamed_function_27930` + `unnamed_function_10568`.

### Controller_GetIsSimPaused (was `unnamed_function_10244`)
- Wrapper to `unnamed_function_27930` + `unnamed_function_10568`.

### Controller_PrintPrettyDouble (was `unnamed_function_10245`)
- Uses `unnamed_function_25810` (formatting) after init gate.
- Likely number formatting used by UI labels.

### Controller_ClickedVentButton (was `unnamed_function_10246`)
- Thin wrapper over `unnamed_function_25810` with many args; likely a UI command entry.

### Controller_BuyComponent (was `unnamed_function_10248`)
- Very small compare function; returns 0/1 based on param comparisons.
- Behavior does **not** look like a full “buy” flow; mapping may be off or inlined elsewhere.

### Controller_ReplaceAllComponentsOfType (was `unnamed_function_10249`)
- Non‑trivial loop with 16‑bit comparisons; called by `Controller_OnComponentSuccessfullySold`.

### Controller_TrySellComponent (was `unnamed_function_10250`)
- Writes flags and calls helpers `9697/9698/9699/9679` (sell flow helpers).

#### Sell flow helper cluster (called by TrySell/SellAll/CanAffordReplacement)
- `unnamed_function_9679`:
  - Init gate via `unnamed_function_24203`, calls `unnamed_function_24336` and `unnamed_function_9683`.
  - Called by `Controller_TrySellComponent`, `Controller_SellAllComponentsOfType`, `Controller_CanAffordReplacement`.
- `unnamed_function_9697`:
  - Init gate + `unnamed_function_24336`, `unnamed_function_9701`, `unnamed_function_27663`.
  - Called by `Controller_TrySellComponent`, `Controller_SellAllComponentsOfType`, `Controller_OnComponentSuccessfullySold`.
- `unnamed_function_9698`:
  - Dispatch/branch helper; calls `unnamed_function_9679` (appears to wrap/route).
  - Called by `Controller_TrySellComponent`, `Controller_SellAllComponentsOfType`.
- `unnamed_function_9699`:
  - Init gate + `unnamed_function_24336`, `unnamed_function_9700`, `unnamed_function_9695`.
  - Called by `Controller_TrySellComponent` only.

### Controller_SellAllComponentsOfType (was `unnamed_function_10251`)
- Similar helper pattern to `TrySellComponent` with additional guard checks.

### Controller_OnComponentSuccessfullySold (was `unnamed_function_10252`)
- Large; uses `Controller_ReplaceAllComponentsOfType` plus many 64‑bit ops.

### Controller_CanAffordReplacement (was `unnamed_function_10253`)
- Large; calls `unnamed_function_10247` (heavy integer math helper) and `unnamed_function_24336`.

### Controller_FormatInfoBar (was `unnamed_function_10254`)
- Small compare/return; likely a helper rather than full formatting.

### Controller__cctor (was `unnamed_function_10255`)
- Static constructor stub.

### unnamed_function_10247 (NOT renamed)
- Heavy integer math (`_muldi3/_udivdi3/_i64Add`) and `unnamed_function_24336`.
- Called by `Controller_CanAffordReplacement`, not by any button handler.
- **Do not rename** until we confirm correct method mapping.

## ReactorUIHandler

### ReactorUIHandler_Initialize (was `unnamed_function_10396`)
- Iterates component list at `param1 + 0x24`, clears/removes entries via `unnamed_function_16590`.
- Sets a flag at `param1 + 0x69`.
- Likely resets per‑component UI state and marks UI dirty.

### ReactorUIHandler_AttachComponent (was `unnamed_function_10400`)
- Ensures a singleton object stored at `DAT_ram_00134ac8 + 0x50` exists.
- If null, allocates via `Il2CppObject_New`, initializes via `ReactorUIHandler_InitAttachContext`, and caches it.
- Returns the cached singleton (appears to be a shared UI handler/context).

### ReactorUIHandler_Drag (was `unnamed_function_10403`)
- Large routine for drag handling; builds grid coordinate lists via `ReactorUIHandler_GetGridCache` and `unnamed_function_8798`.
- Sets up cached lists and computes placement/selection candidates.
- Likely handles drag‑to‑place logic across the reactor grid.
- Ghidra decompiler currently errors (function too large); use call‑graph to prioritize helpers:
  - `ReactorUIHandler_GetGridCache`, `unnamed_function_10392`, `unnamed_function_10393` (grid/list helpers).
  - `unnamed_function_8727`, `8759`, `8798`, `8886` (vector/list transforms).
  - `unnamed_function_24921`, `Il2CppObject_New` (alloc / factory paths).
  - Disassembly shows long repeats of `ReactorUIHandler_GetGridCache` + `unnamed_function_8798` (hash insert), implying nested grid loops.

### ReactorUIHandler method index 10397 (metadata says `GetHorizontalScrollbarLength`)
- Decompiled body is **large** and performs full UI wiring (allocs objects, hooks callbacks, calls `ReactorUIHandler_Drag`).
- This does **not** match the name; likely inlining/metadata mismatch or the method is overloaded by compiler transforms.
- Keep as `unnamed_function_10397` for now; revisit once we resolve method table mapping.

## ShopManager (init)

### ShopManager_Initialize (was `unnamed_function_10410`)
- Large initialization routine; wires up UI elements and event handlers.
- Needs deeper pass for field mapping and helper resolution.
- Ghidra decompiler currently errors (function too large); initial callees suggest setup of many UI helpers:
  - `ShopManager_SetLabel`, `ShopManager_UpdatePriceLabel`, `ShopManager_UpdateHoverFromRect`,
    `ShopManager_SetHoverComponentInfo`, `ShopManager_IsSameComponentType`,
    `ShopManager_OnPlaceTypeInput`, `ShopManager_OnSellTypeInput`, `ShopManager_SellComponentAtCell`.
  - `ShopManager_ApplyOpenPageVisibility`, `ResourceStore_GetSingleton`, `unnamed_function_10365` (input/string/UI helpers).

### ShopManager_ApplyOpenPageVisibility (was `unnamed_function_10332`)
- Writes `param1 + 0x88` (likely `openPage`).
- Toggles multiple UI objects based on the page value (shows/hides widgets at `+0x58/+0x5c/+0x70/+0x74/+0x6c/+0x64`).
- Calls `unnamed_function_10334/10335/10336` depending on the page id.

### ShopManager_SetLabel (was `unnamed_function_10458`)
- Clears/updates a text field at `param1 + 0x34` via `unnamed_function_10308`.
- Formats a string using the singleton at `DAT_ram_00134aa0 + 0x50` (likely localization/text source).

### ShopManager_UpdatePriceLabel (was `unnamed_function_10459`)
- Reads a numeric value from `*(obj + 0x10) + 0x28` and compares it to a threshold from `ResourceStore_GetSingleton`.
- If sufficient, uses `unnamed_function_4356` to update a UI field; otherwise writes a fallback string (`DAT_ram_00135600`).

### ShopManager_UpdateHoverFromRect (was `unnamed_function_10460`)
- Computes screen-space positions from a UI element using `unnamed_function_17371` + `unnamed_function_2135`.
- Builds a transform and forwards to `ReactorUIHandler_UpdateHoverCell` (likely layout/placement).

### ShopManager_SetHoverComponentInfo (was `unnamed_function_10461`)
- Computes a grid index from `(x,y)` and validates within bounds.
- If a component exists, updates a UI field with its reference; otherwise writes a fallback string (`DAT_ram_001355c4`).

### ShopManager_IsSameComponentType (was `unnamed_function_10462`)
- Compares two objects for equality using `+0x50` and `+0x14` fields; returns 0/1.

### ShopManager_OnPlaceTypeInput (was `unnamed_function_10463`)
- Packs a 16‑bit value into two bytes and forwards to `ReactorUIHandler_TryPlaceComponentType` (likely input handling).

### ShopManager_OnSellTypeInput (was `unnamed_function_10464`)
- Packs a 16‑bit value into two bytes and forwards to `ReactorUIHandler_SellComponentsOfType`.

### ShopManager_SellComponentAtCell (was `unnamed_function_10465`)
- Computes grid index from `(x,y)` and sells/removes the component at that cell (if any).

### ResourceStore_GetSingleton (was `unnamed_function_10344`)
- Singleton accessor used to read/write a `double` at `+0x8` (used as a currency or resource pool).
- Used by `Shop_TryPurchaseComponent` and `unnamed_function_10459` for affordability checks.

### Shop_TryPurchaseComponent (was `unnamed_function_10466`)
- Checks resource availability via `ResourceStore_GetSingleton`.
- If affordable, deducts `*(double *)(component + 0x28)` and calls `ReactorUIHandler_CreateComponentInstance` (likely finalize purchase).
- **Tentative** name: behavior matches “spend resource + finalize purchase.”

### ReactorUIHandler_TryPlaceComponentType (was `unnamed_function_10470`)
- Iterates components in `param1 + 0x24` and matches by type (`component + 0x18 == param3`).
- Handles type gating via `Shop_CanAffordWithRefund` / `ResourceStore_AddRefund` / `unnamed_function_10433`, then computes grid coords and calls `Shop_TryPurchaseComponent`.
- **Tentative**: seems to be “place selected component type into grid.”

### ReactorUIHandler_UpdateHoverCell (was `unnamed_function_10472`)
- Converts screen coords → grid coords, validates bounds, and updates a UI label (`unnamed_function_4334`).
- On invalid cell, writes a fallback string (`DAT_ram_00135714`).
- **Tentative**: hover/placement feedback for grid.

### ReactorUIHandler_UpdateScrollAndLayout (was `unnamed_function_10467`)
- Updates scroll/offset (`param1 + 0x2c`, `+0x30`), clamps within bounds, updates transforms.
- Calls `unnamed_function_10378` at end (likely re-layout tiles).
- **Tentative**: scroll/drag layout maintenance.

### ResourceStore_AddRefund (was `unnamed_function_10468`)
- Computes a value via `unnamed_function_10456` and adds it to the resource pool at `ResourceStore_GetSingleton + 0x8`.
- **Tentative**: refund or credit logic for component removal.

### ReactorUIHandler_SellComponentsOfType (was `unnamed_function_10469`)
- Iterates all components; for matches on `component + 0x18 == param3`, triggers `ResourceStore_AddRefund` and `unnamed_function_10433`.
- **Tentative**: remove/sell all components of a given type.

### Shop_CanAffordWithRefund (was `unnamed_function_10471`)
- Returns true if `ResourceStore_GetSingleton + refund_value` exceeds `*(double *)(component + 0x28)`.
- **Tentative**: affordability check that considers a potential refund.

### ReactorUIHandler_CreateComponentInstance (was `unnamed_function_10364`)
- Allocates a component instance via `unnamed_function_16677`, writes `component + 0x18 = param3` (type).
- Calls `ReactorUIHandler_PlaceComponentAtGrid` with a 3‑value vector (likely position).
- **Tentative**: spawn/place component into grid.

### ReactorUIHandler_PlaceComponentAtGrid (was `unnamed_function_10367`, `0x8021a1bf`)
- Validates `(x,y,z)` within grid bounds and writes the component into `param1 + 0x24` list.
- Computes a linear cell index using `param1 + 0x18/0x1c` and a 3‑int vector at `param2`
  (exact formula still unclear; involves `param2+0x0/+0x4/+0x8` and multiplies by `param1+0x18/0x1c`).
- Stores the component at `*(gridBase + 0x10 + (index << 5))` → **cell struct size = 0x20 bytes**.
- Calls `ReactorUIHandler_SetComponentTransform` and `ReactorUIHandler_UpdateComponentStatsUI`.
- Marks UI dirty via `param1 + 0x69 = 1`.

### ReactorUIHandler_SetComponentTransform (was `unnamed_function_10368`)
- Sets a component’s transform relative to the reactor grid and current scroll offset.
- Uses `param1 + 0x2c/+0x30` (scroll offset) and cell size `(16,16)`.
- Writes the transform back via `unnamed_function_16447`.

### ReactorUIHandler_UpdateComponentStatsUI (was `unnamed_function_10369`)
- Updates UI text/sprites for the component using `Simulation_GetStatCached` with stat ids `1` and `2`.
- Clamps internal counters at `param1 + 0x20/+0x28`.
- Toggles visibility of two UI elements depending on flags at `component + 0x30/+0x40`.

### ReactorUIHandler_IsCellPlaceable (was `unnamed_function_10375`)
- Recursively checks child handlers, then calls a vtable function on a list at `param1 + 0x14`.
- Returns non‑zero if the cell is placeable (used by hover/placement logic).

## Drag helper notes (from partial decomp)

### ReactorUIHandler_GetGridCache (was `unnamed_function_10321`)
- Singleton getter for a cached grid/list object stored at `DAT_ram_00134aa8 + 0x50`.
- Allocates via `Il2CppObject_New` then initializes via `unnamed_function_10311`.
- Returns the cached instance pointer.

### ReactorUIHandler_InitAttachContext (was `unnamed_function_10406`)
- Initializes a context object used by `ReactorUIHandler_AttachComponent`.
- Builds small structs/arrays via `unnamed_function_27530`/`27563` and stores into the new object.
- Links a shared list from `DAT_ram_00135724` into a cached object at `DAT_ram_00134ac8 + 0x50`.

### unnamed_function_10392
- Iterates components from `param1 + 0x24` via `unnamed_function_8759` + iterator helpers (`1918`, `1899`, `1852`, `1867`).
- Calls `ReactorUITile_UpdateBlockedState` for each component.

### unnamed_function_10393
- Large routine that:
  - Clears/updates lists, toggles a byte at `component + 0x22`.
  - Uses `unnamed_function_8759` enumerator + several list helpers.
  - Builds/updates UI elements laid out on a grid with offsets `(x*0x30, y*-0x22)` (48 px horizontal, 34 px vertical).
  - Creates per-entry UI via `unnamed_function_16677` and hooks callbacks via `unnamed_function_10303`.
  - Sets transforms through `unnamed_function_16257/16447` and links to a container via `unnamed_function_3594`.

## Reactor grid rebuild & layout (new pass)

### ShopManager_ResetOrOpen (still `unnamed_function_10330`)
- Clears per‑slot cache at `param1 + 0x8c` (zeroes `+0x08..+0x50`).
- Calls:
  - `unnamed_function_10384` on `*(param1 + 0x10) + 0x1c`
  - `unnamed_function_10385` on `param1 + 0x14`
  - `unnamed_function_10386` on `param1 + 0x1c`
- Initializes UI flags at `param1 + 0x84/+0xa0..+0xa4` and toggles two button states via
  `*(param1 + 0x40) + 0x2a` and `*(param1 + 0x44) + 0x2a`.
- Pulls a singleton via `unnamed_function_10316()` and calls `unnamed_function_10387(param1, singleton + 0xd0)`.

### unnamed_function_10384
- Clears several fields at `param1 + 0x28..0x38`.
- Builds two text buffers via `unnamed_function_4290` and writes them into `param1 + 0x48..0x54` and `+0x58..0x64`.
- Calls `ReactorUIHandler_Initialize(param1, 0)`.
- **Likely** a UI init for the reactor panel (tentative).

### unnamed_function_10386
- Iterates a list at `*(param1 + 8)` and removes entries when `component + 0x28 == 0` or `param2 != 0`
  using `unnamed_function_8864(...)`.
- Ends with `unnamed_function_10379(...)` (updates local text/labels).
- **Likely** refreshes the component list (tentative).

### unnamed_function_10387
- Calls `unnamed_function_10388`, `10389`, `10390` and then sets `param1 + 0x84 = 1`.
- **Likely** rebinds UI state for an open page (tentative).

### ReactorUIHandler_UpdateBlockedStates (was `unnamed_function_10392`)
- Iterates components from `param1 + 0x24` and calls `ReactorUITile_UpdateBlockedState` for each.

### ReactorUIHandler_RefreshComponentStatsIfDirty (was `unnamed_function_10391`)
- If `param1 + 0x69` is set:
  - Rebuilds two text buffers via `unnamed_function_4290` into `param1 + 0x48..0x64`.
  - Iterates components and calls `ReactorUIHandler_UpdateComponentStatsUI` when `unnamed_function_2273(...)` is non‑zero.
  - Clears the dirty flag at `param1 + 0x69`.

### ReactorUIHandler_RebuildGridFromComponents (was `unnamed_function_10360`)
- Uses `ReactorUIHandler_CollectPlacedComponents` to gather placed items (if any).
- Uses `ReactorUIHandler_BuildGridTiles` to rebuild the grid tiles.
- When prior data exists, re‑maps components into the new grid and calls
  `ReactorUIHandler_SetComponentTransform` for each entry.
- Computes grid extents by scanning a list at `iVar6 + 8` to find max X/Y sizes.

### ReactorUIHandler_CollectPlacedComponents (was `unnamed_function_10345`)
- Iterates the 3D grid (`x`, `y`, `z`) and collects non‑empty components.
- Packages `(x, y, z, component)` into a list via `unnamed_function_3395` and `unnamed_function_3555`.

### ReactorUIHandler_ResetTileStates (was `unnamed_function_10373`)
- Iterates tiles from `param1 + 0x24`, resolves each to a UI entry via `unnamed_function_2207`,
  then calls `unnamed_function_10348` on each.

### ReactorUIHandler_BuildGridTiles (was `unnamed_function_10374`, `0x8021afb3`)
- Main grid builder:
  - Loops over `x/y/z` and calls `ReactorUIHandler_IsCellPlaceable` for each cell.
  - Creates a UI tile for each placeable cell and sets its transform.
  - Tracks a bounding box using `±16.0` to compute min/max extents.
  - Computes scroll/viewport sizing via `unnamed_function_16348` and related helpers.
  - Stores an origin offset at `param1 + 0x34/+0x38` using `unnamed_function_16257`.
- Confirmed callees: `ReactorUIHandler_GridToLocal`, `ReactorUIHandler_GetScrollRatioX/Y`,
  `ReactorUIHandler_UpdateScrollHandles`, `ReactorUIHandler_IsCellPlaceable`.
- Uses `param3 * 0x10 - 0x10` and `param4 * 0x10 - 0x10` (cell spacing is 16 units).

### ReactorUIHandler_GridToLocal (was `unnamed_function_10372`, `0x8021ad97`)
- Converts `(x, y, z)` grid coords into local UI positions.
- Base offset is `x << 5`, `y << 5` (32‑unit cell size).
- Adds per‑layer offsets from a table at `param1 + 0x10` with stride `0x14`
  (uses `z * 0x14`, reads offsets at `+0x8/+0xC`).
- If a per‑layer flag at `+0x10` (within that `0x14` entry) is set, adds `+16` to both axes.

### ReactorUIHandler_GetScrollRatioX / ReactorUIHandler_GetScrollRatioY (was `unnamed_function_10376/10377`)
- Compute scroll ratios:
  - `10376` uses `unnamed_function_16251` (vector magnitude?) → `(view^2)/content`.
  - `10377` uses `unnamed_function_11404` (alt magnitude?) → `(view^2)/content`.
- Used by `unnamed_function_10378` to position scroll handles.

### ReactorUIHandler_UpdateScrollHandles (was `unnamed_function_10378`)
- Updates scroll handle positions based on offsets at `param1 + 0x2c/+0x30`.
- Uses `unnamed_function_16503/16508/16447` to set UI transforms.
- Recomputes both axes if content size exceeds view size.

## Resource / cash UI (new pass)

> Note: metadata in `assembly_csharp_types_v2.json` labels method indices 10480–10493 as
> `UpgradeManager.*`, and 10384–10387 as `ReactorLayout` / `SpaceValidityDelegate`.
> The decompiled behavior here looks like UI/resource wiring; treat metadata mapping as unreliable.

### unnamed_function_10481
- Runs `unnamed_function_10384` and `unnamed_function_10386` (reactor panel refresh).
- Resets several ResourceStore fields: `+0x08`, `+0x18`, `+0x20`, `+0x28` → `0`.
- Calls `unnamed_function_10380` and enforces `ResourceStore + 0x48` minimum (adjusts `+0x10`).
- Sets multiple flags on `param1 + 0xA0..+0xA4` and toggles two UI button states at
  `*(param1 + 0x40) + 0x2a` and `*(param1 + 0x44) + 0x2a`.
- Calls `unnamed_function_10324(param1, ...)` at end (possibly a UI notification).

### unnamed_function_10493
- Handles `param1 + 0xA2` / `+0xA4` flags:
  - If `A2 == 0` and `A4 == 0`: sets `A2 = 1`.
  - If `A2 == 0` and `A4 != 0`: refreshes components via `unnamed_function_10386`,
    calls `unnamed_function_10387`, sets `ResourceStore + 0x10 = +0x48`,
    clears `A4`, marks UI dirty.
  - Else: calls `unnamed_function_10481`.
- Always ends with `unnamed_function_10491` and `unnamed_function_10490`.

### unnamed_function_10490
- Updates the label at `param1 + 0x5c`.
- If `A2 == 0` and `A4 == 0`, formats a value using `unnamed_function_10380()` and
  `ResourceStore + 0x48` (appears to compute a delta).
- If `A4 != 0`, uses a static string (`DAT_ram_00138860`).
- If `A2 != 0`, uses a static string (`DAT_ram_0013885c`).
- **Likely** “current money / total money / pending” label (string IDs unresolved).

### unnamed_function_10491
- Updates the label at `param1 + 0x58`.
- Chooses between two static strings based on `param1 + 0xA3`.

### unnamed_function_10380
- Reads ResourceStore `+0x30` and `+0x38` and picks the smaller one.
- If the selected value ≥ `1e12`, computes a scaled value using `unnamed_function_25942` and `pow(4, log-12)`.
- **Likely** a tier/scaling calculation used by `unnamed_function_10481/10490`.

## UI string table anchor

### UI_UpdateLabel_FromLiteralTable (was `unnamed_function_11530`)
- Calls `unnamed_function_24203(DAT_ram_00047b0c, ...)` which resolves the literal table containing
  UI labels (Scrounge/Sell All Power/Current Money/etc).
- Appears to format a label using a layout helper (`UI_GetStringTable_Stats`) and then
  `unnamed_function_25201` with `DAT_ram_00134594` (string formatting).
- This likely wires up or updates one of the visible UI labels/buttons.
- WAST: function index `8591` contains `i32.const 293900` (`0x47b0c`). Mapping to Ghidra
  is not 1:1 but this is the only observed use of the label table in code.

### UI_InitLabelList_All (was `unnamed_function_10509`)
- Builds a `List<string>`-like object and pushes a large sequence of label constants
  (`DAT_ram_001388ac` … `DAT_ram_001388f4`).
- Ends by assigning the list to `**(DAT_ram_00134a98 + 0x50)`.
- Notable tail labels include:
  - `DAT_ram_001388f0` → “Scrounge for cash (+1$)”
  - `DAT_ram_001388f4` → “Sell All Power: +”
 - This list is consumed by `FormatNumberWithSuffix` as a suffix lookup table
   (`**(DAT_ram_00134a98 + 0x50) + 0x10 + idx * 4`), so the list likely includes
   the numeric suffix strings near the front. The scrounge/sell labels sit later
   in the same list but their UI usage is still not located.

### UI_GetStringTable_Stats (was `unnamed_function_11507`)
- Calls `unnamed_function_24203(DAT_ram_00047b1c, ...)` to resolve the secondary literal table.
- Returns/refreshes a cached pointer at `param1 + 0x28`.
- Likely a string‑table accessor used by `unnamed_function_11530` when formatting labels.

## Statistics panel build (new pass)

### Stats_BuildPanel (was `unnamed_function_10337`)
- Calls `Stats_BuildStatsRows`, then `Stats_BuildStatEntries`, then `Stats_CreatePanel`.
- Appears to build the full “stats” panel from rows + entries.

### Stats_BuildStatsRows (was `unnamed_function_10339`)
- Builds a list of key/value rows using ResourceStore values and reactor component info.
- Uses many `DAT_ram_001389xx` constants as labels (literal table entries from `0x00047b1c`,
  which starts at string literal index 2951).
- Pulls:
  - ResourceStore: `+0x8, +0x10, +0x18, +0x20, +0x28, +0x30, +0x38, +0x40, +0x48`
  - Reactor component list via `ReactorUIHandler_CollectPlacedComponents`
- Produces a list object via `Il2CppObject_New(DAT_ram_00134b0c)` and `unnamed_function_10342/10343`.
- Label mapping (addresses → literal indices → text; from `global-metadata.dat`):
  - `DAT_ram_001388f8` → 2951 → “Build Version: ”
  - `DAT_ram_001388fc` → 2952 → “Current Money: ”
  - `DAT_ram_00138900` → 2953 → “Total Money: ”
  - `DAT_ram_00138904` → 2954 → “Money earned this game: ”
  - `DAT_ram_00138908` → 2955 → “Current Power: ”
  - `DAT_ram_0013890c` → 2956 → “Total Power produced: ”
  - `DAT_ram_00138910` → 2957 → “Power produced this game: ”
  - `DAT_ram_00138914` → 2958 → “Current Reactor Heat: ”
  - `DAT_ram_00138918` → 2959 → “Total Heat dissipated: ”
  - `DAT_ram_0013891c` → 2960 → “Heat dissipated this game: ”
  - `DAT_ram_00138920` → 2961 → “Current Exotic Particles: ”
  - `DAT_ram_00138924` → 2962 → “Total Exotic Particles: ”
  - `DAT_ram_00138928` → 2963 → “Exotic Particles earned from next prestige: ”
  - `DAT_ram_0013892c` → 2964 → “\\n\\n”
  - `DAT_ram_00138930` → 2965 → “Click again to confirm”
  - `DAT_ram_00138934` → 2966 → “Reset Game”
  - `DAT_ram_00138938` → 2967 → “Click again to confirm (Will restart game)”
- Value sources (by order of `unnamed_function_10343` calls):
  - Build Version → `**(DAT_ram_00134ac0 + 0x50)` (string)
  - Current Money → `ResourceStore + 0x08`
  - Total Money → `*(param3 + 0x1c) + 0x28`
  - Money earned this game → `*(param3 + 0x1c) + 0x30`
  - Current Exotic Particles → `*(param3 + 0x1c) + 0x38`
  - Total Exotic Particles → `ResourceStore + 0x38`
  - Exotic Particles earned from next prestige → `ResourceStore + 0x30`
  - Current Reactor Heat → `ResourceStore + 0x20`
  - Power produced this game → `ResourceStore + 0x18`
  - Total Heat dissipated → `ResourceStore + 0x28`
  - Heat dissipated this game → `ResourceStore + 0x40`
  - “\\n\\n” separator row → `ResourceStore + 0x10` (value meaning unknown)
  - “Click again to confirm” row → `ResourceStore + 0x48` (value meaning unknown)
  - Current Power → `*(byte *)(param2 + 0xa1)`
  - Total Power produced → `*(byte *)(param2 + 0xa0)`
- The “Reset Game” / “Click again to confirm (Will restart game)” labels are added after
  building two lists of component-derived entries (likely reset / confirm UI).
 - **Note:** `Controller_ClickedSellButton` updates `ResourceStore + 0x28` and
   `ResourceStore + 0x40` as money totals when selling power. This conflicts with
   the label mapping above (heat dissipated). One of these interpretations is wrong
   and needs re‑validation.

### FormatNumberWithSuffix (was `unnamed_function_10295`)
- Formats large numbers with a suffix selected from the label list at
  `**(DAT_ram_00134a98 + 0x50)`.
- Index is based on `log10(abs(x))` rounded down to a multiple of 3, then used
  to select a suffix string and append to the formatted number.
- Used widely for stat labels (money/power/heat/etc).

### Controller_ClickedSellButton (was `unnamed_function_10508`)
- Click handler that implements **Scrounge for cash** and **Sell All Power**.
- Logic:
  - If `Reactor_CountPlacedComponents(reactor)` returns 0 and `(currentMoney + storedPower) < 10`,
    then add `+1.0` to:
      - `ResourceStore + 0x08` (current money)
      - `ResourceStore + 0x28` (total money)
      - `ResourceStore + 0x40` (money earned this game)
  - Otherwise, move all `storedPower` (reactor `+0x30`) into money totals and zero it.
- Likely the backing method for metadata name `Controller.ClickedSellButton`.

### Controller_ClickedSellButton_Invoke (was `unnamed_function_10507`)
- Thin wrapper that forwards to `Controller_ClickedSellButton` with `param1 + 0x10`.

### Reactor_CountPlacedComponents (was `unnamed_function_10448`)
- Iterates `reactor + 0x24` list, counts entries where `unnamed_function_2273` returns true.
- Used to gate “Scrounge for cash” (only allowed when count == 0).

### Scene wiring hints (metadata stubs)
- `Controller` has field `SellPowerButton` and method `ClickedSellButton(1)`
  (from `scene_class_stubs_v2.md`), so the button likely binds to
  `Controller_ClickedSellButton` via `Controller.SetButtonFunctionality` / `Controller.Setup`.

### Stats_BuildStatEntries (was `unnamed_function_10340`)
- Converts rows into UI entries via `unnamed_function_11004` and `unnamed_function_9152`.
- Iterates row data from `param1 + 8` (likely list of `(label, value)` pairs).

### Stats_CreatePanel (was `unnamed_function_10341`)
- Builds the final UI panel using several Unity UI helpers and the entry list.
- Appears to instantiate objects, bind layout, and return a UI object handle.

## Component description table (new pass)

### ComponentDescription_Show (was `unnamed_function_12193`)
- Calls `unnamed_function_24203(DAT_ram_00047a0c, ...)` to resolve the component description
  literal table (fuel cells, tiers, etc.).
- Uses `ComponentDescription_GetEntry(0x32, param1)` to fetch a string entry.
- Likely pushes the description text into a UI element via `unnamed_function_9930/24379`.

### ComponentDescription_GetEntry (was `unnamed_function_12187`)
- Indexes into a vtable table at `*param2 + 0xb4 + index * 8` and returns the value.
  - Spawns/updates UI objects via `Il2CppObject_New` + `unnamed_function_793` and binds them to lists.
- Likely core of “rebuild drag placement overlays” or “refresh tiles” logic.
  - Calls `ReactorUITile_UpdateAppearance` after toggling flags.

### ReactorUITile_UpdateBlockedState (was `unnamed_function_10395`)
- Evaluates adjacent occupancy and sets a flag at `tile + 0x23`.
- Calls `ReactorUITile_UpdateAppearance` to apply the correct sprite/visual.

### ReactorUITile_UpdateAppearance (was `unnamed_function_10394`)
- Selects sprite/material based on flags at `tile + 0x20..0x23`.
- Routes to `unnamed_function_11419(tile->Image, sprite, 0)`.

### unnamed_function_8759 / 8798 / 8886 / 8727
- `unnamed_function_8759` appears to allocate + initialize an enumerator object (generic list iterator).
- `unnamed_function_8798` and `unnamed_function_8886` are hash‑table insertions (keys hashed via `unnamed_function_811/801`).
- `unnamed_function_8727` invokes a vtable function pointer on an object (likely a virtual list/collection op).

## Implementation bridge (hover text + costs)
- UI hover panel expects `Title`, `Description`, and `Cost` strings.
- Implementation currently reads optional JSON overrides:
  - `decompilation/recovered/recovered_analysis/component_texts.json`:
    `{ "ComponentName": { "title": "...", "description": "..." } }`
  - `decompilation/recovered/recovered_analysis/component_costs.json`:
    `{ "ComponentName": 1234.0 }`
- When missing, the UI falls back to a prettified name and shows `Cost: ?`.

### Hover label literals (stringliteral table)
- `Cost: ???` (index 2941)
- `Cost: ` (index 2945)
- `Durability: ` (index 2951)
- `Heat: ` (index 2950)
- `Heat Per Tick: ` (index 2952)
- `Power Per Tick: ` (index 2953)
- `Sells for: ` (index 2949)
- `Depleted ` (index 2947)
- `This cell has run out of fuel and is now inert. Right-click to remove it.` (index 2948)
