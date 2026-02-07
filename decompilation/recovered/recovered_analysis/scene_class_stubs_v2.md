# Scene MonoBehaviour Stubs (v2 metadata)

## BarWithLabel

Fields:
- MinColor
- MaxColor
- Fill
- TextOverlay
- Label
- Suffix
- Max
- Value

Methods (name/paramCount):
- .ctor(0)
- Update(0)

## Button

Fields:
- Image
- Text
- BaseSprite
- HoverSprite
- PressedSprite
- IsClicked
- IsHovering
- IsImportant
- ClickedAction

Methods (name/paramCount):
- .ctor(0)
- OnMouseEnter(0)
- OnMouseExit(0)
- OnMouseDown(0)
- OnMouseUp(0)
- OnMouseUpAsButton(0)
- Update(0)
- SetLabel(1)

## BuyableComponent

Fields:
- Image
- Type
- isHovering
- isSelected
- canAfford
- clickAction
- hoverAction

Methods (name/paramCount):
- .ctor(0)
- Setup(3)
- OnMouseEnter(0)
- OnMouseExit(0)
- OnMouseDown(0)
- SetSelected(1)
- SetCanAfford(1)
- RefreshAppearance(0)

## Controller

Fields:
- isDebug
- Sim
- ShopManager
- UpgradeShopManager
- UpgradeManager
- StatisticsManager
- UpgradePanel
- MoneyLabel
- Info
- HeatBar
- PowerBar
- HeatVentButton
- SellPowerButton
- PauseButton
- ReplaceButton
- HelpButtons
- UpgradeButton
- PrestigeUpgradeButton
- OptionsButton
- ResetButton
- PrestigeButton
- ViewStatsButton
- BackButton
- HelpButton
- ImportExportField
- ImportButton
- ExportButton
- activeHelpButton
- lastSaveTime
- needToSave
- menuState
- player
- isKongregateLoaded
- userID
- username
- gameAuthToken
- isPaused
- shouldReplaceCells
- isConfirmingPrestige
- isConfirmingReset
- canResetPrestigeUpgrade
- HoveredComponent
- clickAndDragOrigin
- BigNumberSuffixes

Methods (name/paramCount):
- .ctor(0)
- OnKongregateAPILoaded(1)
- SubmitKongregateStatistics(0)
- HandleKongregate(0)
- SetButtonFunctionality(2)
- OnGameLoaded(1)
- Awake(0)
- Update(0)
- Reset(0)
- Prestige(0)
- HandleInput(0)
- Setup(2)
- ClickedUpgradeButton(1)
- ClickedPrestigeUpgradeButton(1)
- ClickedOptionsButton(1)
- RefreshResetButtonLabel(0)
- RefreshPrestigeButtonLabel(0)
- ClickedResetButton(1)
- ClickedPrestigeButton(1)
- ClickedBackButton(1)
- ClickedHelpButton(1)
- ClickedImportButton(1)
- ClickedExportButton(1)
- SelectHelpButton(1)
- SelectStatsButton(1)
- ChangeState(1)
- OnUpgradePurchased(1)
- OnSolutionChanged(0)
- GetShouldReplaceCells(0)
- SetPaused(1)
- SetShouldReplace(1)
- GetIsSimPaused(0)
- PrintPrettyDouble(1)
- ClickedVentButton(1)
- ClickedSellButton(1)
- BuyComponent(2)
- ReplaceAllComponentsOfType(3)
- TrySellComponent(2)
- SellAllComponentsOfType(2)
- OnComponentSuccessfullySold(2)
- CanAffordReplacement(2)
- FormatInfoBar(0)
- .cctor(0)

## HelpElement

Fields:
- Label
- DrawArea

Methods (name/paramCount):
- .ctor(0)
- OnGUI(0)

## InfoBanner

Fields:
- NameLabel
- DescriptionLabel
- CostLabel
- StatusLabel
- PowerLabel
- HeatLabel

Methods (name/paramCount):
- .ctor(0)

## ReactorUIHandler

Fields:
- GenericTilePrefab
- HorizontalScrollbar
- VerticalScrollbar
- TileRoot
- ComponentRoot
- BackerSprite
- tiles
- parentReactor
- layoutOffset
- gridOffsetMin

Methods (name/paramCount):
- .ctor(0)
- Initialize(4)
- GetHorizontalScrollbarLength(0)
- GetVerticalScrollbarLength(0)
- UpdateScrollbarPositions(0)
- AttachComponent(2)
- InformColor(2)
- SetShown(1)
- Drag(1)
- GetRelativeMousePosition(1)
- Clear(0)

## ShopManager

Fields:
- PowerGenerationPage
- HeatManagementPage
- ExperimentalComponentsPage
- BuyableComponentPrefab
- PowerGenerationPageButton
- HeatManagementPageButton
- ExperimentalComponentsPageButton
- TheUnknownPageButton
- Root
- shopPageButtons
- upgradeManager
- openPage
- activePageComponents
- selectedComponent
- hoveredComponent

Methods (name/paramCount):
- .ctor(0)
- Initialize(1)
- Update(0)
- OnUpgradePurchased(1)
- SetShownShopPage(1)
- GetSelectedType(0)
- GetDisplayedType(0)
- Reset(0)
- OnBuyableComponentSelected(1)
- OnBuyableComponentHovering(2)
- RefreshAllButtons(0)
- RefreshButtonState(1)
- Deselect(0)

## ShopPageButton

Fields:
- Image
- BaseSprite
- HoverSprite
- PressedSprite
- LockedSprite
- isClicked
- isHovering
- isOpen
- isLocked
- ClickedAction

Methods (name/paramCount):
- .ctor(0)
- SetIsOpen(1)
- SetIsLocked(1)
- OnMouseEnter(0)
- OnMouseExit(0)
- OnMouseDown(0)
- OnMouseUp(0)
- OnMouseUpAsButton(0)
- RefreshAppearance(0)

## Simulation

Fields:
- ReactorComponentPrefab
- ExplosionPrefab
- UIHandler
- Collider
- Reactor
- timeSinceLastTick
- controller
- upgradeManager
- lastHeatChange
- lastPowerChange
- cachedTicksPerSecond

Methods (name/paramCount):
- .ctor(0)
- Initialize(3)
- Reset(0)
- ResetTickTimer(0)
- LogicalUpdate(0)
- Tick(0)
- TickGeneratePowerAndHeat(0)
- TickVentReactor(0)
- IsEmpty(0)
- TickExchangeWithReactor(0)
- SetShown(1)
- TickVentHeat(0)
- TickCleanup(0)
- CreateComponent(2)
- LoadComponent(4)
- ManuallyVentHeat(1)
- ManuallySellPower(1)
- OnSolutionChanged(0)
- GetHoveredPosition(1)
- GetLastPowerChange(0)
- GetLastHeatChange(0)
- GetTicksPerSecond(0)
- GetShouldReplaceCells(0)

## StatisticsManager

Fields:
- Header
- Body

Methods (name/paramCount):
- .ctor(0)
- SetVisible(1)

## ToggleButton

Fields:
- Image
- BaseSprite
- HoverSprite
- PressedSprite
- BaseSpriteOn
- HoverSpriteOn
- PressedSpriteOn
- IsClicked
- IsHovering
- IsToggled
- ClickedAction

Methods (name/paramCount):
- .ctor(0)
- OnMouseEnter(0)
- OnMouseExit(0)
- OnMouseDown(0)
- OnMouseUp(0)
- OnMouseUpAsButton(0)
- SetState(1)
- Update(0)

## UpgradeShopManager

Fields:
- UpgradePrefab
- BasicUpgradePage
- PrestigeUpgradePage
- Root
- controller
- upgradeManager
- visibleUpgrades
- hoveredUpgrade

Methods (name/paramCount):
- .ctor(0)
- Initialize(2)
- Update(0)
- BuyUpgrade(1)
- HideActiveUpgradePage(0)
- OpenUpgradePage(1)
- OpenBasicUpgradePage(0)
- OpenPrestigeUpgradePage(0)
- GetHoveredUpgradeType(0)
- IsHoveredUpgradeLocked(0)
- OnUpgradeHovering(2)

## UnityEngine.EventSystems.EventSystem

- Note: type not found in metadata

Fields:
- m_Name

## UnityEngine.EventSystems.StandaloneInputModule

- Note: type not found in metadata

Fields:
- m_Name

## UnityEngine.UI.GraphicRaycaster

- Note: type not found in metadata

Fields:
- m_Name

## UnityEngine.UI.Image

- Note: type not found in metadata

Fields:
- m_Name

## UnityEngine.UI.InputField

- Note: type not found in metadata

Fields:
- m_Name

## UnityEngine.UI.Text

- Note: type not found in metadata

Fields:
- m_Name

