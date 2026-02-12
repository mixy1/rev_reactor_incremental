# Bevy Implementation Status (2026-02-12)

- `implementation_bevy/` is now a runnable Rust + Bevy port track with `cargo run`.
- Data layer is wired for:
  - `implementation/src/game/component_types.json`
  - `implementation/src/game/upgrade_data.json`
- Save layer supports JSON + base64 codecs and simulation bridge conversion.
- App layer currently provides:
  - reactor grid rendering using recovered component sprites
  - HUD (money/power/heat/tick/selection)
  - placement/removal input
  - run/pause
  - manual save/load (`F5`/`F9`) and timed autosave to `implementation_bevy/save.json`
- Core simulation includes deterministic tests for placement/removal, pulse generation, vent/sell, coolant transfer, reflector effect.
- Remaining parity gaps vs Python:
  - full upgrade/prestige behavior
  - full shop/panel UI parity
  - full original import compatibility (legacy encrypted path)
