# Click & Input Events — Complete Reverse Engineering

Reverse-engineered from the decompiled WASM (`Build.wasm_decompiled.c`) and
IL2CPP metadata (`dump.cs`). All function references are `unnamed_function_NNNNN`
in the decompiled C file.

---

## Input API Layer

| WASM Function | Unity API | Purpose |
|---------------|-----------|---------|
| `unnamed_function_2344(0, button, 0)` | `Input.GetMouseButton(button)` | **Held** — true every frame the button is down |
| `unnamed_function_2345(0, button, 0)` | `Input.GetMouseButtonDown(button)` | **Pressed** — true only the frame the button goes down |
| `unnamed_function_2346(0, button, 0)` | `Input.GetMouseButtonUp(button)` | **Released** — true only the frame the button goes up |
| `unnamed_function_2347(&out, 0, 0)` | `Input.mousePosition` | Returns screen-space (x, y) |
| `unnamed_function_2342(0, keycode, 0)` | `Input.GetKey(keycode)` | Keyboard held |
| `unnamed_function_2343(0, keycode, 0)` | `Input.GetKeyDown(keycode)` | Keyboard pressed |

Button indices: **0 = Left**, **1 = Right**, 2 = Middle.

---

## Main Update Function

### `unnamed_function_10410` — ShopManager / ReactorInputHandler Update
**Lines 387715–388250** (≈535 lines). This is the single function that handles
all reactor grid + shop input every frame.

### Flow Overview

```
10410 Update
├─ Debug keys (guarded by param1+0xc debug flag)
│  ├─ Key 0x125: money *= 10
│  ├─ Key 0x124 (held): +10000 power AND +10000 heat
│  ├─ Key 0x123 (held): increment reactor counter at +0x38
│  └─ Key 0x1B (ESC): deselect component OR close shop overlay
│
├─ Get mouse position → unnamed_function_2347
├─ Camera transform  → unnamed_function_2161, 16507
├─ Update price label → unnamed_function_10459
│
├─ Key 0x20 (Space): toggle pause (writes to PauseButton.IsToggled at +0x40→+0x2A)
│
├─ If NOT in shop overlay mode (param1+0x88 == 0):
│  ├─ Raycast grid   → unnamed_function_10460 (screen→grid cell)
│  ├─ Check UI hover → unnamed_function_4283 (is mouse over UI?)
│  │
│  ├─ [A] Mouse NOT over grid cell (raycast miss):
│  │   └─ RMB Down (2345, button 1) → deselect (10458)
│  │
│  └─ [B] Mouse IS over grid cell:
│      ├─ Get component at cell  → unnamed_function_10461
│      ├─ Get hovered component  → unnamed_function_4416
│      ├─ Check compatibility    → unnamed_function_10462
│      ├─ Check if cell occupied → unnamed_function_10365
│      │
│      ├─ Key 0x130 / 0x12F pressed: (keyboard shortcuts, skip to goto)
│      │
│      ├─ LMB NOT held (2344, button 0 == 0):
│      │   ├─ RMB held (2344, button 1 == 1):
│      │   │   ├─ Cell empty (uVar7 == 0):
│      │   │   │   └─ RMB Down (2345, button 1): deselect → 10458
│      │   │   └─ Cell occupied (uVar7 != 0):
│      │   │       └─ **SELL component** → 10465
│      │   │
│      │   └─ RMB NOT held:
│      │       └─ LMB Down (2345, button 0):
│      │           └─ **Start drag origin** → store at +0xB0
│      │
│      ├─ LMB held (iVar14 != 0) AND cell has selected component (iVar5 != 0):
│      │   ├─ Compatible types (uVar3 != 0) OR different type (uVar15 != 0):
│      │   │   ├─ If occupied: **SELL existing** → 10465
│      │   │   └─ **PLACE component** → 10466
│      │   │
│      │   └─ Same type, not compatible:
│      │       └─ (no action)
│      │
│      ├─ LMB held AND no selected component:
│      │   ├─ LMB Down (2345, button 0) AND compatible:
│      │   │   └─ **Single-cell place** → 10464
│      │   │
│      │   └─ LMB Down AND uVar3 set:
│      │       └─ **Drag-place with rotation** → 10463
│      │
│      └─ (after goto label code_r0x8022810c):
│          └─ If drag origin exists (+0xB0 valid):
│              ├─ LMB Released (2346, button 0):
│              │   └─ **Drag-sell rectangle** → 10467 (sell all in drag rect)
│              └─ LMB still held:
│                  └─ Update drag rectangle endpoint
│
└─ If in shop overlay mode (param1+0x88 != 0):
    └─ ESC → unnamed_function_10332 (close overlay)
```

---

## Grid Click Actions — Detailed

### LEFT CLICK — Place Component

**Trigger**: `GetMouseButtonDown(0)` (button 0, single frame) or
`GetMouseButton(0)` (button 0, held for drag-to-place).

**Handler**: `unnamed_function_10466` (lines 393071–393126)

```
10466(param1=inputHandler, param2=gridPosition, param3=componentType):
  1. Get resource store → unnamed_function_10344()
  2. cost = *(double*)(param3 + 0x28)          // ComponentType.Cost
  3. money = *(double*)(resourceStore + 0x08)   // ResourceStore.Money
  4. if (cost <= money):
       money -= cost                            // Deduct cost
       unnamed_function_10364(reactor, gridPos, componentType)  // Place on grid
  5. else: do nothing (silently fail)
```

**Key detail**: Cost is at ComponentType+0x28 (matches the known field layout).
Placement is **silent fail** if you can't afford — no error message, no sound.

### LEFT CLICK — Drag-to-place with rotation

**Trigger**: `GetMouseButton(0)` held, and `GetMouseButtonDown(0)` on a new cell.

**Handler**: `unnamed_function_10463` → calls `unnamed_function_10470`
Passes both the component type and the drag direction to enable
rotation/orientation of placed component.

### LEFT CLICK — Single-cell place

**Trigger**: `GetMouseButtonDown(0)` on a valid empty cell with a selected component.

**Handler**: `unnamed_function_10464` → calls `unnamed_function_10469`

### LEFT CLICK — Drag-sell rectangle

**Trigger**: Click on empty cell to start drag (`GetMouseButtonDown(0)`),
hold and release (`GetMouseButtonUp(0)`).

**Handler**: `unnamed_function_10467` (lines 393130+)

When left-mouse is released after a drag:
1. Compute rectangle from drag origin (+0xB0) to current mouse position
2. Call `unnamed_function_10467` which iterates all cells in the rectangle
3. For each occupied cell: sell the component (refund + remove)

This is the **drag-to-sell-rectangle** mechanic — draw a box to mass-sell.

### LEFT CLICK — Replace mode

When Replace mode is active (`GetShouldReplaceCells()` returns true) and
you left-click a cell that already has a component:

1. `unnamed_function_10465` is called first to **sell the existing component**
2. Then `unnamed_function_10466` is called to **place the new component**

This is the two-step: sell-then-place that makes Replace mode work.

---

### RIGHT CLICK — Sell Component

**Trigger**: `GetMouseButton(1)` (button 1, held = drag-to-sell).

**Handler**: `unnamed_function_10465` (lines 393014–393067)

```
10465(param1=gridData, param2=inputHandler, param3=gridPosition):
  1. index = (z * height + y) * width + x     // Grid cell index
  2. Bounds check: 0 <= index < grid.Count
  3. component = grid[index]                   // Get component at cell
  4. null check: unnamed_function_2273(component) != 0
  5. if component exists:
       unnamed_function_10468(inputHandler, component)   // Calculate refund + add money
       unnamed_function_10433(gridData, index)           // Remove from grid
```

**Key detail**: Right-click selling uses `GetMouseButton(1)` (held state),
not `GetMouseButtonDown(1)`. This means you can **drag to sell multiple
components** by holding right-click and moving the mouse across cells.

### RIGHT CLICK — Deselect (on empty cell)

**Trigger**: `GetMouseButton(1)` held on a cell where `uVar7 == 0` (no
component), plus `GetMouseButtonDown(1)`.

**Handler**: `unnamed_function_10458` — deselects the current shop selection.

```
10458(shopRef):
  1. If a component is currently selected (offset +0x34 valid):
       - Clear selection flag: *(byte*)(selected + 0x15) = 0
       - Call unnamed_function_10308 to refresh visuals
  2. Reset selection to "none" (empty Maybe at +0x34)
```

---

## Sell Price / Refund Calculation

### `unnamed_function_10456` — GetSellValue (lines 392506–392559)

```
GetSellValue(component, upgradeManager, refundFuel):
  baseCost = *(double*)(componentType + 0x28)     // ComponentType.Cost

  // If component has HeatCapacity (nullable at +0x40):
  if (hasHeatCapacity):
    currentHeat = *(double*)(component + 0x28)    // Component.Heat
    maxHeat = unnamed_function_10370(upgMgr, type, 2)  // upgraded heat cap
    heatRatio = 1.0 - (currentHeat / maxHeat)
    baseCost *= heatRatio * heatRatio             // Quadratic penalty for heat

  // If component has MaxDurability (nullable at +0x30):
  if (hasMaxDurability):
    currentDur = *(double*)(component + 0x20)     // Component.Durability
    maxDur = unnamed_function_10370(upgMgr, type, 1)  // upgraded max durability
    durRatio = currentDur / maxDur
    baseCost *= durRatio * durRatio               // Quadratic penalty for use

  // If component has CellData (+0x50) and refundFuel is false:
  if (hasCellData && !refundFuel):
    baseCost = 0.0                                // No refund for fuel cells!

  return baseCost
```

**Key findings**:
- Refund is **NOT full price** — it degrades quadratically with use
- Heat-storing components lose value as they store more heat:
  `refund = cost × (1 - heat/maxHeat)²`
- Components with durability lose value as durability decreases:
  `refund = cost × (durability/maxDurability)²`
- **Fuel cells return $0** unless `refundFuel=true`
  (fuel cells have CellData, so the CellData check zeroes the refund)
- The `refundFuel` flag is passed as `true` only during prestige/reset

### `unnamed_function_10468` — AddRefund (lines 393332–393366)

```
AddRefund(inputHandler, component):
  sellValue = unnamed_function_10456(component, upgradeManager, refundFuel=false)
  resourceStore = unnamed_function_10344()
  *(double*)(resourceStore + 0x08) += sellValue   // Money += sellValue
```

The `refundFuel` parameter is hardcoded to **0 (false)** in `10465` (right-click sell)
and `10469` (drag-sell-all), meaning **fuel cells always refund $0 when manually sold**.

---

## Button Click Handlers

All game buttons use the Unity `OnMouseUpAsButton()` pattern (click = press + release
over the same element). The custom `Button` class at dump.cs:76243 fires a
`ClickedAction` delegate.

### Vent Heat Button

**Class method**: `Simulation.ManuallyVentHeat(Button)` (RVA 0x74B)
→ calls `Reactor.ManuallyVentHeat(out double heatVented)` (RVA 0x73C)

From the Reactor class, ManuallyVentHeat vents heat from the reactor hull.
The amount vented is determined by the **ManualVentRate** upgrade stat.
With no upgrades, the base manual vent rate is used. The upgrade category is
`UpgradeType.Category = 12` (ManualVent).

### Sell Power Button

**Class method**: `Simulation.ManuallySellPower(Button)` (RVA 0x74C)
→ calls `Reactor.ManuallySellPower(out double powerSold)` (RVA 0x73B)

Sells **all** accumulated power in the reactor. The conversion rate is
modified by the **ManualSell** upgrade (category 13). The money gained is:
`money += storedPower × manualSellMultiplier`.

The button label shows `"Sell All Power: + $X (+ Y per tick)"` or
`"Scrounge for cash (+1$)"` when no power is stored and no components
are placed.

### Scrounge Mechanic

From the Controller class, the sell button has dual behavior:
- **If reactor is empty** (no components, power ≈ 0): the button becomes
  "Scrounge for cash (+1$)" and adds $1 per click
- **Otherwise**: sells all stored power

This matches our implementation's `can_scrounge()` check.

### Pause Button (Toggle)

**Class**: `ToggleButton` (dump.cs:77654)
**Handler**: `Controller.SetPaused(bool)` (RVA 0x72C)

Toggles `IsToggled` flag. When paused:
- Simulation ticks stop
- Components don't generate power/heat
- Manual buttons still work

### Replace Button (Toggle)

**Class**: `ToggleButton` (dump.cs:77654)
**Handler**: `Controller.SetShouldReplace(bool)` (RVA 0x72D)

When Replace mode is active:
- **Left-clicking an occupied cell** sells the existing component first,
  then places the selected component (if affordable after refund)
- Normal left-click on empty cells works the same as without Replace

### Shop Tab Buttons (Power / Heat / Experimental / Arcane)

**Class**: `ShopPageButton` (dump.cs:77490)
**Handler**: `ShopManager.SetShownShopPage(ShopPageButton)` (RVA 0x743)

Each tab has states: `isOpen`, `isLocked`, `isHovering`, `isClicked`.
Locked tabs (Experimental requires prestige 1, Arcane requires prestige 2)
show `LockedSprite` and ignore clicks.

### Shop Item Buttons (BuyableComponent)

**Class**: `BuyableComponent` (dump.cs:76284)
**Handler**: `OnMouseDown()` triggers `clickAction` → selects the component

Fields: `isHovering`, `isSelected`, `canAfford`.
- **Click**: Sets this component as selected for placement
- **Hover**: Shows component info in the top banner via `hoverAction`
- `SetCanAfford(bool)` controls grayed-out appearance

### Upgrade Buttons

**Class**: `Upgrade` (dump.cs:77697)
**Handler**: `OnMouseUpAsButton()` → `clickedAction` → `UpgradeShopManager.BuyUpgrade(Upgrade)`

Fields: `canAfford`, `isLocked`, `isHovering`, `isClicked`.
- **Click**: Purchases the upgrade if affordable and not locked
- **Hover**: Shows upgrade description via `hoverAction`

### Menu Buttons (Controller class)

| Button | Handler | RVA | Action |
|--------|---------|-----|--------|
| Upgrade | `ClickedUpgradeButton` | 0x71F | Open basic upgrades panel |
| Prestige Upgrade | `ClickedPrestigeUpgradeButton` | 0x720 | Open prestige upgrades panel |
| Options | `ClickedOptionsButton` | 0x721 | Open options menu |
| Reset | `ClickedResetButton` | 0x722 | Prestige confirmation (shows "Click again to confirm") |
| Prestige | `ClickedPrestigeButton` | 0x723 | Execute prestige ("Click again to confirm (Will restart game)") |
| Back | `ClickedBackButton` | 0x724 | Return from any menu panel |
| Help | `ClickedHelpButton` | 0x725 | Open help/statistics panel |
| Import | `ClickedImportButton` | 0x726 | Import save from text field |
| Export | `ClickedExportButton` | 0x727 | Export save to text field |
| Vent Heat | `ClickedVentButton` | 0x72E | → `Simulation.ManuallyVentHeat` |
| Sell Power | `ClickedSellButton` | 0x72F | → `Simulation.ManuallySellPower` |

---

## Debug / Cheat Keys

Guarded by a debug flag at `param1 + 0xC` (only active in debug builds):

| Key Code | Key | Condition | Action |
|----------|-----|-----------|--------|
| 0x125 | ? | `GetKeyDown` + debug | `money *= 10` |
| 0x124 | ? | `GetKey` (held) + debug | `power += 10000`, `heat += 10000` |
| 0x123 | ? | `GetKey` (held) + debug | `reactor.counter++` |
| 0x1B | ESC | Always | Deselect component / close shop overlay |
| 0x20 | Space | Always | Toggle pause (PauseButton.IsToggled) |
| 0x130 | ? | Always | (keyboard shortcut, skips to goto) |
| 0x12F | ? | Always | (keyboard shortcut, skips to goto) |

---

## Grid Data Structures

### Grid Cell Index Calculation

```
index = (z * gridHeight + y) * gridWidth + x
```

Grid data array at `Reactor + 0x24`. Each cell is 0x20 (32) bytes:
- Cell data at `array + 0x10 + index * 0x20`

### Reactor.Tile Structure (from dump.cs:77232)

| Offset | Type | Field |
|--------|------|-------|
| +0x00 | ReactorComponent | Component |
| +0x08 | double | LastHeat |
| +0x10 | double | HeatPressure |
| +0x18 | int | CachedPulses |

### ReactorComponent Fields (from dump.cs:77242)

| Offset | Type | Field |
|--------|------|-------|
| +0x0C | Image | Image (sprite) |
| +0x10 | BarWithLabel | HeatBar |
| +0x14 | BarWithLabel | DurabilityBar |
| +0x18 | ComponentType | Type |
| +0x20 | double | Durability |
| +0x28 | double | Heat |
| +0x30 | double | LastPower |
| +0x38 | double | LastHeat |
| +0x40 | bool | depleted |

---

## Key Helper Functions

| Function | Purpose |
|----------|---------|
| `10344` | Get ResourceStore singleton |
| `10364` | Place component on grid (Reactor.CreateComponent) |
| `10365` | Check if cell is occupied |
| `10370` | Get upgraded stat value (stat_id: 1=durability, 2=heat) |
| `10433` | Remove component from grid by index |
| `10456` | Calculate sell value (with degradation) |
| `10458` | Deselect current shop selection |
| `10459` | Update price label (affordable check) |
| `10460` | Screen→grid raycast (mouse to cell coordinates) |
| `10461` | Get component info at grid cell (for hover) |
| `10462` | Check type compatibility (can replace?) |
| `10463` | Drag-place with rotation |
| `10464` | Single-cell place |
| `10465` | Sell component at cell (right-click sell) |
| `10466` | Buy and place component (with cost check) |
| `10467` | Drag-rectangle sell (sell all in dragged area) |
| `10468` | Add refund to money (calls 10456 for value) |
| `10469` | Sell all components of type (iterates grid) |
| `10470` | Place with rotation/direction |
| `10472` | Grid hit test (is point inside grid?) |
| `2273`  | Null/validity check (returns 0 if null) |
| `4283`  | Maybe.HasValue check |
| `4416`  | Maybe.Value getter |

---

## Summary of All Click Events

### Left Mouse Button (0)

| State | Context | Action | Handler |
|-------|---------|--------|---------|
| **Down** | Empty grid cell | Start drag origin | stores at +0xB0 |
| **Down** | Grid cell + selected component | Place component (deduct cost) | `10466` |
| **Held** | Dragging across empty cells | Extend drag rectangle | updates +0xB0 |
| **Held** | Dragging with Replace mode ON | Sell existing + place new | `10465` → `10466` |
| **Up** | After drag | Sell all in drag rectangle | `10467` |
| **Down** | Shop item | Select component for placement | `BuyableComponent.OnMouseDown` |
| **Down** | Shop tab | Switch shop page | `ShopPageButton.OnMouseUpAsButton` |
| **Down** | UI button | Fire button action | `Button.OnMouseUpAsButton` |
| **Down** | Upgrade item | Purchase upgrade | `Upgrade.OnMouseUpAsButton` |

### Right Mouse Button (1)

| State | Context | Action | Handler |
|-------|---------|--------|---------|
| **Held** | Grid cell with component | Sell component (drag-to-sell) | `10465` |
| **Down** | Empty grid cell | Deselect shop selection | `10458` |
| **Down** | No grid cell (outside grid) | Deselect shop selection | `10458` |

### Keyboard

| Key | State | Action |
|-----|-------|--------|
| ESC (0x1B) | Pressed | Deselect / close shop overlay |
| Space (0x20) | Pressed | Toggle pause |

---

## Implementation Differences (Current vs Original)

| Feature | Original | Our Implementation | Status |
|---------|----------|-------------------|--------|
| Left-click place | Down (single) | Down (drag) | Slightly different — ours uses held state |
| Right-click sell | Held (drag-to-sell) | Held (drag-to-sell) | Correct |
| Right-click deselect | Down on empty cell | Down on empty cell | Correct |
| Left-drag sell rectangle | Down→drag→Up = sell area | Not implemented | Missing |
| Replace mode | Toggle button, sell+place | Not implemented | Missing |
| Sell price degradation | Quadratic on heat+durability | Full refund | Needs fix |
| Fuel cell refund | $0 (unless prestige) | Full refund | Needs fix |
| ESC deselect | Deselects component | Not implemented | Missing |
| Space toggle pause | Toggles simulation pause | Not implemented | Missing |
| Scrounge | When empty + no power | When empty + money+power < 10 | Close enough |
