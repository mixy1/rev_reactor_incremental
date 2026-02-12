# implementation_bevy

Rust + Bevy reimplementation track for Rev Reactor.

## Requirements

- Rust toolchain (stable)
- Cargo

## Build and Run

```bash
cd implementation_bevy
cargo check
cargo test
cargo run
```

## Current Status

The crate now includes:

- A playable Bevy app loop (`src/app/*`) with:
  - grid rendering
  - HUD text (money/power/heat/tick + selected component)
  - place/remove interactions
  - pause/run toggle
  - save/load hotkeys + autosave
- Deterministic engine-agnostic simulation core (`src/core/*`)
- Engine-agnostic models (`src/model/*`)
- Data loaders for component/upgrade JSON (`src/data/*`)
- Save codecs for JSON + base64 round-trip (`src/save/*`)

## App Controls

- `1..9`: quick-select first 9 components from loaded catalog
- `Q` / `E`: previous/next component selection
- `Left Click` on a grid cell: place selected component (if affordable and empty)
- `Right Click` on a grid cell: remove/sell component (50% refund)
- `Space` or `P`: toggle simulation run/pause
- `F5`: save immediately to `implementation_bevy/save.json`
- `F9`: load from `implementation_bevy/save.json`

## Layout

- `src/main.rs`: Bevy app bootstrap/plugin wiring
- `src/app/`: Bevy-facing state/resources/systems/view/input
- `src/core/`: deterministic simulation and resource accounting
- `src/model/`: shared component/grid domain types
- `src/data/`: serde DTOs + loader helpers for catalog/upgrade data
- `src/save/`: serde save payload + JSON/base64 codecs
- `tests/`: deterministic simulation tests
