# Implementation Notes (Prototype)

This is a minimal Python + raylib prototype that uses **original sprite assets** from the Unity export.

## Location

- Code: `implementation/src`
- Assets: `decompilation/recovered/recovered_assets`
- Packaging: `pyproject.toml` + `uv.lock` at repo root

## Run (local)

1. Sync dependencies with `uv`.
2. Run:

```
uv sync
uv run rev-reactor
```

## Asset path override

If you relocate assets, set:

```
REV_REACTOR_ASSETS_DIR=/path/to/recovered_assets
```

## Current scope

- Draws the grid using the original `AltGrid.png` sprite.
- Renders original `Heat.png` and `Power.png` icons with simple bars.
- Supports a **reference overlay** to align layout (toggle with **F1**; cycle with **F2/F3**).
- Simulation step is a placeholder that uses validated stat names but **not** original values yet.
- A `ResourceStore` now holds money/power/heat/exotic counters and last‑tick deltas.
- The grid tracks cell occupancy and exposes neighbor helpers (matches wasm neighbor offsets).
- Left‑click places a placeholder component on the grid and draws its original sprite.
- Store panel now renders a grid of **IconButton** slots (48x52) derived from recovered sprites; icons are populated from recovered component sprite names.
- Store catalog is seeded from `decompilation/recovered/recovered_mono/monobehaviour_index.csv` and filtered by component sprite names.
- `implementation/layout.json` controls layout constants for aligning to reference screenshots.
- `decompilation/tools/extract_ui_layout.py` regenerates `implementation/layout.json` from Unity RectTransforms (Build.data).

Next: decode serialized component stats from recovered MonoBehaviour blobs and wire the store list + prices to those values.

## Web crash note (2026-02-08)

- Renderer minidump for `https://nuclear.mixy.one` shows Windows fail-fast `0xC0000409` with parameter `0xD` (`int 0x29` in `ntdll`), not a Python traceback.
- Initial mitigation applied: upgraded web runtime from `pyodide v0.27.0` to `v0.29.3` in `web/index.html` and `dist/index.html`.

## Web crash note (2026-02-12)

- Added iframe watchdog architecture: `web/index.html` is now a host page and `web/game.html` runs the game runtime.
- Child frame emits `postMessage` heartbeat every 500ms; host reloads iframe on stalled heartbeat (6s timeout, 20s startup grace).
- Save persistence remains in web localStorage (`rev_reactor_save`), so iframe restarts do not clear saved progress.
- Updated iframe sandbox mode to `sandbox="allow-scripts"` and moved save/load/theme state sync to a parent↔child `postMessage` bridge (`RevReactorHostBridge`) so web save persistence still works without `allow-same-origin`.

## Save compatibility note (2026-02-13)

- Options panel now exposes **Export Old** and **Export New** buttons.
- `Export Old` emits original Reactor Idle encrypted save text (AES-256-CBC with the game's PasswordDeriveBytes-compatible key derivation), bounded to legacy schema.
- `Export New` emits unrestricted base64-JSON (full reimplementation state, no legacy bounds).
- Import remains backward-compatible with all three formats: raw JSON, base64-JSON, and original encrypted text.
- Original `ProtiumDepleted` now round-trips through import/export (`depleted_protium_count`).
- In sandboxed iframe mode (`sandbox="allow-scripts"`), exports now route through the host page via `postMessage` (`rev-reactor-download`) so file downloads still work without relaxing iframe sandbox flags.
- Legacy component index mapping now follows `ComponentTypes` field order (fixes old-export misloads such as Ultimate Reflector/Extreme Capacitor becoming coolants).
- Legacy export/import now convert Y coordinates between runtime grid space and original save space (vertical axis inversion fix).
