# Core Method Index Map

Method indices from IL2CPP metadata (v24). For wasm, functions appear as `unnamed_function_{methodIndex}`.

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

Methods (name → methodIndex):

- .ctor → 10431
- Initialize → 10432
- Reset → 10433
- ResetTickTimer → 10434
- LogicalUpdate → 10435
- Tick → 10436
- TickGeneratePowerAndHeat → 10437
- TickVentReactor → 10438
- IsEmpty → 10439
- TickExchangeWithReactor → 10440
- SetShown → 10441
- TickVentHeat → 10442
- TickCleanup → 10443
- CreateComponent → 10444
- LoadComponent → 10445
- ManuallyVentHeat → 10446
- ManuallySellPower → 10447
- OnSolutionChanged → 10448
- GetHoveredPosition → 10449
- GetLastPowerChange → 10450
- GetLastHeatChange → 10451
- GetTicksPerSecond → 10452
- GetShouldReplaceCells → 10453

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

Methods (name → methodIndex):

- .ctor → 10409
- Initialize → 10410
- Update → 10411
- OnUpgradePurchased → 10412
- SetShownShopPage → 10413
- GetSelectedType → 10414
- GetDisplayedType → 10415
- Reset → 10416
- OnBuyableComponentSelected → 10417
- OnBuyableComponentHovering → 10418
- RefreshAllButtons → 10419
- RefreshButtonState → 10420
- Deselect → 10421

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

Methods (name → methodIndex):

- .ctor → 10500
- Initialize → 10501
- Update → 10502
- BuyUpgrade → 10503
- HideActiveUpgradePage → 10504
- OpenUpgradePage → 10505
- OpenBasicUpgradePage → 10506
- OpenPrestigeUpgradePage → 10507
- GetHoveredUpgradeType → 10508
- IsHoveredUpgradeLocked → 10509
- OnUpgradeHovering → 10510

## StatisticsManager

Fields:

- Header
- Body

Methods (name → methodIndex):

- .ctor → 10456
- SetVisible → 10457

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

Methods (name → methodIndex):

- .ctor → 10395
- Initialize → 10396
- GetHorizontalScrollbarLength → 10397
- GetVerticalScrollbarLength → 10398
- UpdateScrollbarPositions → 10399
- AttachComponent → 10400
- InformColor → 10401
- SetShown → 10402
- Drag → 10403
- GetRelativeMousePosition → 10404
- Clear → 10405

## BuyableComponent

Fields:

- Image
- Type
- isHovering
- isSelected
- canAfford
- clickAction
- hoverAction

Methods (name → methodIndex):

- .ctor → 10190
- Setup → 10191
- OnMouseEnter → 10192
- OnMouseExit → 10193
- OnMouseDown → 10194
- SetSelected → 10195
- SetCanAfford → 10196
- RefreshAppearance → 10197

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

Methods (name → methodIndex):

- .ctor → 10213
- OnKongregateAPILoaded → 10214
- SubmitKongregateStatistics → 10215
- HandleKongregate → 10216
- SetButtonFunctionality → 10217
- OnGameLoaded → 10218
- Awake → 10219
- Update → 10220
- Reset → 10221
- Prestige → 10222
- HandleInput → 10223
- Setup → 10224
- ClickedUpgradeButton → 10225
- ClickedPrestigeUpgradeButton → 10226
- ClickedOptionsButton → 10227
- RefreshResetButtonLabel → 10228
- RefreshPrestigeButtonLabel → 10229
- ClickedResetButton → 10230
- ClickedPrestigeButton → 10231
- ClickedBackButton → 10232
- ClickedHelpButton → 10233
- ClickedImportButton → 10234
- ClickedExportButton → 10235
- SelectHelpButton → 10236
- SelectStatsButton → 10237
- ChangeState → 10238
- OnUpgradePurchased → 10239
- OnSolutionChanged → 10240
- GetShouldReplaceCells → 10241
- SetPaused → 10242
- SetShouldReplace → 10243
- GetIsSimPaused → 10244
- PrintPrettyDouble → 10245
- ClickedVentButton → 10246
- ClickedSellButton → 10247
- BuyComponent → 10248
- ReplaceAllComponentsOfType → 10249
- TrySellComponent → 10250
- SellAllComponentsOfType → 10251
- OnComponentSuccessfullySold → 10252
- CanAffordReplacement → 10253
- FormatInfoBar → 10254
- .cctor → 10255

## InfoBanner

Fields:

- NameLabel
- DescriptionLabel
- CostLabel
- StatusLabel
- PowerLabel
- HeatLabel

Methods (name → methodIndex):

- .ctor → 10265

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

Methods (name → methodIndex):

- .ctor → 10180
- Update → 10181

## HelpElement

Fields:

- Label
- DrawArea

Methods (name → methodIndex):

- .ctor → 10260
- OnGUI → 10261

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

Methods (name → methodIndex):

- .ctor → 10422
- SetIsOpen → 10423
- SetIsLocked → 10424
- OnMouseEnter → 10425
- OnMouseExit → 10426
- OnMouseDown → 10427
- OnMouseUp → 10428
- OnMouseUpAsButton → 10429
- RefreshAppearance → 10430

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

Methods (name → methodIndex):

- .ctor → 10458
- OnMouseEnter → 10459
- OnMouseExit → 10460
- OnMouseDown → 10461
- OnMouseUp → 10462
- OnMouseUpAsButton → 10463
- SetState → 10464
- Update → 10465

