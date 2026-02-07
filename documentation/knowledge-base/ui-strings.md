# UI Strings (Recovered from Build.data)

Source: `decompilation/build/Build.data` (offset ~3381685).

## Nearby strings

- nstead of the usual one.StavriumAll components aligned vertically or horizontally are considered adjacent to it.kongregate.stats.submitExoticParticlesScoreif(typeof(kongregateUnitySupport) != 'undefined'){ kongregateUnitySupport.initAPI('Controller', 'OnKongregateAPILoaded');}; EP) Heat (- per tick)Scrounge for cash (+1$)Sell All Power: + $ (+ $ per tick)Build Version:
- Current Money:
- Total Money:
- Money earned this game:
- Current Power:
- Total Power produced:
- Power produced this game:
- Current Reactor Heat:
- Total Heat dissipated:
- Heat dissipated this game:
- Current Exotic Particles:
- Total Exotic Particles:
- Exotic Particles earned from next prestige:
- Click again to confirmReset GameClick again to confirm (Will restart game)Refund prestige upgrades?Prestige for  exotic particles.??????This upgrade is locked. You must purchase  before it becomes available.Cost: ??? Exotic Parti

## String literal indices (global-metadata.dat)

These labels live in the string-literal table (not the normal string table).
Indices below are `stringLiteralIndex` values. The literal table entry at memory
`0x00047b0c` is the contiguous list starting at index `2947`.

- 2947: Scrounge for cash (+1$)
- 2948: Sell All Power: +
- 2949:  $ (+
- 2950:  $ per tick)
- 2951: Build Version:
- 2952: Current Money:
- 2953: Total Money:
- 2954: Money earned this game:
- 2955: Current Power:
- 2956: Total Power produced:
- 2957: Power produced this game:
- 2958: Current Reactor Heat:
- 2959: Total Heat dissipated:
- 2960: Heat dissipated this game:
- 2961: Current Exotic Particles:
- 2962: Total Exotic Particles:
- 2963: Exotic Particles earned from next prestige:
- 2964: \n\n
- 2965: Click again to confirm
- 2966: Reset Game
- 2967: Click again to confirm (Will restart game)
- 2968: Refund prestige upgrades?
- 2969: Prestige for 
- 2970:  exotic particles.
- 2971: ??????
- 2972: This upgrade is locked. You must purchase 
- 2973:  before it becomes available.
- 2974: Cost: ???

Secondary table at `0x00047b1c` starts at index `2951` (Build Version + stats + reset/prestige strings).

Component description table at `0x00047a0c` starts at index `2883` and includes:
- Capacitor5/6, Coolant6, tier labels (Basic/Advanced/Super/Wondrous/Ultimate/Extreme)
- “Cell Tier- power production…” and related descriptions for fuel cells (Double/Quad, etc.)

## Address mapping (stats label pointers)

The stats label string pointers are laid out in RAM starting at `0x001388f8`.
Index mapping: `index = 2951 + (addr - 0x001388f8) / 4`.

Examples:
- `0x001388f8` → 2951 → Build Version
- `0x001388fc` → 2952 → Current Money
- `0x00138900` → 2953 → Total Money
- `0x00138904` → 2954 → Money earned this game
- `0x00138908` → 2955 → Current Power
- `0x0013890c` → 2956 → Total Power produced
- `0x00138910` → 2957 → Power produced this game
- `0x00138914` → 2958 → Current Reactor Heat
- `0x00138918` → 2959 → Total Heat dissipated
- `0x0013891c` → 2960 → Heat dissipated this game
- `0x00138920` → 2961 → Current Exotic Particles
- `0x00138924` → 2962 → Total Exotic Particles
- `0x00138928` → 2963 → Exotic Particles earned from next prestige
- `0x0013892c` → 2964 → "\\n\\n"
- `0x00138930` → 2965 → Click again to confirm
- `0x00138934` → 2966 → Reset Game
- `0x00138938` → 2967 → Click again to confirm (Will restart game)

## Code anchor (literal table usage)

- WAST shows a function that references the literal table base `0x00047b0c`:
  `Build.wast` line ~1,057,7xx: `(i32.const 293900)` which is `0x47b0c`.
  This corresponds to `UI_UpdateLabel_FromLiteralTable` (see ui-decomp notes).
